#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iterator>
#include <optional>
#include <span>
#include <vector>

#include "color.hpp"

// Picks a stable background from a band of app pixels next to the taskbar, and keeps
// taskbar icons/text readable on it. Pure functions, no Windows APIs.
namespace Util::ColorMatch {
	struct PickResult {
		Color color;
		double coverage; // fraction of pixels within tolerance of color, 0..1
	};

	namespace impl {
		constexpr int Distance(const Color &a, const Color &b) noexcept
		{
			return std::max({ std::abs(a.R - b.R), std::abs(a.G - b.G), std::abs(a.B - b.B) });
		}

		constexpr std::size_t BucketOf(const Color &c) noexcept
		{
			return (static_cast<std::size_t>(c.R >> 4) << 8) | (static_cast<std::size_t>(c.G >> 4) << 4) | static_cast<std::size_t>(c.B >> 4);
		}

		struct Accumulator {
			std::uint64_t r = 0, g = 0, b = 0, n = 0;

			void Add(const Color &c) noexcept
			{
				r += c.R;
				g += c.G;
				b += c.B;
				++n;
			}

			Color Mean() const noexcept
			{
				const auto avg = [this](std::uint64_t sum) { return static_cast<std::uint8_t>((sum + n / 2) / n); };
				return { avg(r), avg(g), avg(b), 255 };
			}
		};

		inline double Linear(std::uint8_t c) noexcept
		{
			const double v = c / 255.0;
			return v <= 0.04045 ? v / 12.92 : std::pow((v + 0.055) / 1.055, 2.4);
		}
	}

	// Dominant color of the pixels and how much of the strip it covers.
	// A low coverage means the strip is busy (photo, mixed UI) and a single solid color would look wrong.
	inline std::optional<PickResult> PickDominant(std::span<const Color> pixels, int tolerance = 24)
	{
		if (pixels.empty())
		{
			return std::nullopt;
		}

		// Coarse 16-level buckets per channel find the most common color family.
		std::array<std::uint32_t, 4096> counts { };
		for (const auto &p : pixels)
		{
			++counts[impl::BucketOf(p)];
		}
		const auto key = static_cast<std::size_t>(std::distance(counts.begin(), std::max_element(counts.begin(), counts.end())));

		impl::Accumulator members;
		for (const auto &p : pixels)
		{
			if (impl::BucketOf(p) == key)
			{
				members.Add(p);
			}
		}
		const Color seed = members.Mean();

		// Refine with every pixel close to the seed, so a color on a bucket boundary isn't split in half.
		impl::Accumulator close;
		for (const auto &p : pixels)
		{
			if (impl::Distance(p, seed) <= tolerance)
			{
				close.Add(p);
			}
		}

		return PickResult { close.Mean(), static_cast<double>(close.n) / static_cast<double>(pixels.size()) };
	}

	// WCAG relative luminance, 0 (black) to 1 (white).
	inline double Luminance(const Color &c) noexcept
	{
		return 0.2126 * impl::Linear(c.R) + 0.7152 * impl::Linear(c.G) + 0.0722 * impl::Linear(c.B);
	}

	inline double Contrast(double l1, double l2) noexcept
	{
		return (std::max(l1, l2) + 0.05) / (std::min(l1, l2) + 0.05);
	}

	inline Color Mix(const Color &a, const Color &b, double t) noexcept
	{
		const auto lerp = [t](std::uint8_t x, std::uint8_t y) { return static_cast<std::uint8_t>(std::lround(x + (y - x) * t)); };
		return { lerp(a.R, b.R), lerp(a.G, b.G), lerp(a.B, b.B), a.A };
	}

	// Row-major grid: columns run along the taskbar, rows run away from it.
	// Matching side margins identify the surrounding UI in document viewers, where
	// a white page can otherwise take over the sample as it scrolls past the edge.
	// With no shared surround, blend the area mean toward its dominant background.
	// The continuous weight avoids a hard coverage threshold (and transparent gaps).
	inline std::optional<Color> PickBackground(std::span<const Color> pixels, std::size_t columns)
	{
		if (columns < 8 || pixels.empty() || pixels.size() % columns != 0)
		{
			return std::nullopt;
		}

		std::vector<Color> left, right;
		impl::Accumulator all;
		const std::size_t margin = columns / 8;
		for (std::size_t i = 0; i < pixels.size(); ++i)
		{
			all.Add(pixels[i]);
			const auto x = i % columns;
			if (x < margin) left.push_back(pixels[i]);
			if (x >= columns - margin) right.push_back(pixels[i]);
		}

		const auto l = PickDominant(left);
		const auto r = PickDominant(right);
		if (l->coverage >= 0.65 && r->coverage >= 0.65 && impl::Distance(l->color, r->color) <= 24)
		{
			return Mix(l->color, r->color, 0.5);
		}

		const auto dominant = PickDominant(pixels);
		const double weight = std::clamp((dominant->coverage - 0.5) / 0.35, 0.0, 1.0);
		return Mix(all.Mean(), dominant->color, weight);
	}

	// A time-based low-pass filter: event bursts must not accelerate adaptation.
	// Reset at app changes so a new window never inherits the old window's tint.
	inline Color SmoothBackground(const Color &previous, const Color &sample, double elapsedSeconds)
	{
		return Mix(previous, sample, 1.0 - std::exp(-std::max(0.0, elapsedSeconds) / 0.35));
	}

	// Nudge the color toward black (white taskbar text) or white (black taskbar text)
	// just enough for the text to reach minContrast. Unchanged if it already does.
	inline Color EnsureReadable(const Color &c, bool lightText, double minContrast)
	{
		const double textLum = lightText ? 1.0 : 0.0;
		if (minContrast <= 1.0 || Contrast(Luminance(c), textLum) >= minContrast)
		{
			return c;
		}

		const Color toward = lightText ? Color { 0, 0, 0, c.A } : Color { 255, 255, 255, c.A };
		double lo = 0.0, hi = 1.0; // smallest blend factor that passes, by bisection
		for (int i = 0; i < 20; ++i)
		{
			const double t = (lo + hi) / 2;
			if (Contrast(Luminance(Mix(c, toward, t)), textLum) >= minContrast)
			{
				hi = t;
			}
			else
			{
				lo = t;
			}
		}

		return Mix(c, toward, hi);
	}

	// Ease-out cubic: fast start, gentle landing. t in [0, 1].
	constexpr double EaseOut(double t) noexcept
	{
		t = std::clamp(t, 0.0, 1.0);
		const double inv = 1.0 - t;
		return 1.0 - inv * inv * inv;
	}

	// Blend all four channels (including alpha), for fading in/out and between colors.
	inline Color Blend(const Color &a, const Color &b, double t) noexcept
	{
		const auto lerp = [t](std::uint8_t x, std::uint8_t y) { return static_cast<std::uint8_t>(std::lround(x + (y - x) * t)); };
		return { lerp(a.R, b.R), lerp(a.G, b.G), lerp(a.B, b.B), lerp(a.A, b.A) };
	}

	// A subtle separator shade: lighter on dark colors, darker on light ones.
	inline Color DividerColor(const Color &c, double strength = 0.15)
	{
		const Color toward = Luminance(c) < 0.4 ? Color { 255, 255, 255, c.A } : Color { 0, 0, 0, c.A };
		return Mix(c, toward, strength);
	}
}
