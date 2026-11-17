#include <gtest/gtest.h>
#include <vector>

#include "util/colormatch.hpp"

using namespace Util::ColorMatch;
using Util::Color;

namespace {
	std::vector<Color> Repeat(Color c, std::size_t n)
	{
		return std::vector<Color>(n, c);
	}

	void Append(std::vector<Color> &v, Color c, std::size_t n)
	{
		v.insert(v.end(), n, c);
	}

	bool SameRgb(const Color &a, const Color &b)
	{
		return a.R == b.R && a.G == b.G && a.B == b.B;
	}
}

TEST(Util_ColorMatch_PickDominant, SolidStripReturnsThatColorWithFullCoverage)
{
	const auto px = Repeat({ 30, 30, 30 }, 100);
	const auto result = PickDominant(px);
	ASSERT_TRUE(result);
	ASSERT_TRUE(SameRgb(result->color, { 30, 30, 30 }));
	ASSERT_DOUBLE_EQ(result->coverage, 1.0);
}

TEST(Util_ColorMatch_PickDominant, SmallDetailsDoNotChangeDominantColor)
{
	auto px = Repeat({ 43, 87, 151 }, 90);
	Append(px, { 255, 255, 255 }, 10);
	const auto result = PickDominant(px);
	ASSERT_TRUE(result);
	ASSERT_TRUE(SameRgb(result->color, { 43, 87, 151 }));
	ASSERT_DOUBLE_EQ(result->coverage, 0.9);
}

TEST(Util_ColorMatch_PickDominant, ColorOnBucketBoundaryIsNotSplit)
{
	auto px = Repeat({ 15, 15, 15 }, 50);
	Append(px, { 16, 16, 16 }, 50);
	const auto result = PickDominant(px);
	ASSERT_TRUE(result);
	ASSERT_DOUBLE_EQ(result->coverage, 1.0);
	ASSERT_GE(result->color.R, 15);
	ASSERT_LE(result->color.R, 16);
}

TEST(Util_ColorMatch_PickDominant, BusyStripHasLowCoverage)
{
	std::vector<Color> px;
	for (int i = 0; i < 300; ++i)
	{
		px.push_back({ static_cast<uint8_t>((i * 37) % 256), static_cast<uint8_t>((i * 91) % 256), static_cast<uint8_t>((i * 53) % 256) });
	}
	const auto result = PickDominant(px);
	ASSERT_TRUE(result);
	ASSERT_LT(result->coverage, 0.3);
}

TEST(Util_ColorMatch_PickDominant, EmptyStripHasNoResult)
{
	ASSERT_FALSE(PickDominant({}));
}

TEST(Util_ColorMatch_EnsureReadable, DarkColorIsLeftAloneForWhiteText)
{
	ASSERT_TRUE(SameRgb(EnsureReadable({ 32, 32, 32 }, true, 3.0), { 32, 32, 32 }));
}

TEST(Util_ColorMatch_EnsureReadable, WhiteIsDarkenedOnlyAsMuchAsNeeded)
{
	const auto out = EnsureReadable({ 255, 255, 255 }, true, 3.0);
	ASSERT_GE(Contrast(Luminance(out), 1.0), 3.0);
	ASSERT_GT(out.R, 120);
}

TEST(Util_ColorMatch_EnsureReadable, BlackIsLightenedForBlackText)
{
	const auto out = EnsureReadable({ 0, 0, 0 }, false, 3.0);
	ASSERT_GE(Contrast(Luminance(out), 0.0), 3.0);
}

TEST(Util_ColorMatch_EnsureReadable, DarkeningKeepsHue)
{
	const auto out = EnsureReadable({ 120, 200, 255 }, true, 3.0);
	ASSERT_GT(out.B, out.G);
	ASSERT_GT(out.G, out.R);
}

TEST(Util_ColorMatch_EnsureReadable, ContrastOfOneDisablesClamp)
{
	ASSERT_TRUE(SameRgb(EnsureReadable({ 255, 255, 255 }, true, 1.0), { 255, 255, 255 }));
}

TEST(Util_ColorMatch_DividerColor, LighterOnDarkDarkerOnLight)
{
	ASSERT_GT(Luminance(DividerColor({ 14, 14, 14 })), Luminance({ 14, 14, 14 }));
	ASSERT_LT(Luminance(DividerColor({ 240, 240, 240 })), Luminance({ 240, 240, 240 }));
}

TEST(Util_ColorMatch_EaseOut, StartsAtZeroEndsAtOneAndClamps)
{
	ASSERT_DOUBLE_EQ(EaseOut(0.0), 0.0);
	ASSERT_DOUBLE_EQ(EaseOut(1.0), 1.0);
	ASSERT_DOUBLE_EQ(EaseOut(-1.0), 0.0);
	ASSERT_DOUBLE_EQ(EaseOut(2.0), 1.0);
	ASSERT_GT(EaseOut(0.5), 0.5); // ease-out is ahead of linear halfway through
}

TEST(Util_ColorMatch_Blend, BlendsAllChannelsIncludingAlpha)
{
	const Color from { 0, 100, 200, 0 };
	const Color to { 200, 100, 0, 255 };
	const auto mid = Blend(from, to, 0.5);
	ASSERT_EQ(mid.R, 100);
	ASSERT_EQ(mid.G, 100);
	ASSERT_EQ(mid.B, 100);
	ASSERT_EQ(mid.A, 128);
	ASSERT_EQ(Blend(from, to, 0.0).A, 0);
	ASSERT_EQ(Blend(from, to, 1.0).A, 255);
}

TEST(Util_ColorMatch_DividerColor, IsSubtle)
{
	const auto d = DividerColor({ 14, 14, 14 });
	ASSERT_LT(d.R, 60);
}
