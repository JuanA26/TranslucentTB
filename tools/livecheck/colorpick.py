"""Pure color logic: choose one color from a strip of pixels, keep taskbar text readable.

No Windows APIs here, so it can be unit-tested anywhere.
"""
from collections import Counter

RGB = tuple[int, int, int]


def pick_color(pixels: list[RGB], tolerance: int = 24) -> tuple[RGB | None, float]:
    """Return (dominant color, coverage).

    coverage is the fraction of pixels within `tolerance` (per channel) of the
    chosen color. A low coverage means the strip is busy (photo, mixed UI) and
    a single solid color would look wrong.
    """
    if not pixels:
        return None, 0.0
    # Coarse 16-level buckets per channel find the most common color family.
    buckets = Counter((r >> 4, g >> 4, b >> 4) for r, g, b in pixels)
    key = buckets.most_common(1)[0][0]
    members = [p for p in pixels if (p[0] >> 4, p[1] >> 4, p[2] >> 4) == key]
    seed = _mean(members)
    # Refine with every pixel close to the seed, so a color sitting on a bucket
    # boundary is not split in half.
    close = [p for p in pixels if _dist(p, seed) <= tolerance]
    return _mean(close), len(close) / len(pixels)


def _mean(pixels: list[RGB]) -> RGB:
    n = len(pixels)
    return tuple(round(sum(c) / n) for c in zip(*pixels))  # type: ignore[return-value]


def _dist(a: RGB, b: RGB) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def _linear(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: RGB) -> float:
    """WCAG relative luminance, 0 (black) to 1 (white)."""
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def ensure_readable(rgb: RGB, light_text: bool, min_contrast: float) -> RGB:
    """Nudge rgb toward black (white text) or white (black text) until the
    taskbar icons/clock reach min_contrast. Returns rgb unchanged if it already does."""
    text_lum = 1.0 if light_text else 0.0
    if min_contrast <= 1 or contrast(luminance(rgb), text_lum) >= min_contrast:
        return rgb
    toward = (0, 0, 0) if light_text else (255, 255, 255)
    lo, hi = 0.0, 1.0  # smallest blend factor that passes, by bisection
    for _ in range(20):
        t = (lo + hi) / 2
        if contrast(luminance(mix(rgb, toward, t)), text_lum) >= min_contrast:
            hi = t
        else:
            lo = t
    return mix(rgb, toward, hi)


def divider_color(rgb: RGB, strength: float = 0.15) -> RGB:
    """A subtle separator shade: lighter on dark colors, darker on light ones."""
    toward = (255, 255, 255) if luminance(rgb) < 0.4 else (0, 0, 0)
    return mix(rgb, toward, strength)


def parse_hex(s: str) -> RGB:
    s = s.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"expected #rrggbb, got {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def to_hex(rgb: RGB) -> str:
    return "#%02x%02x%02x" % rgb
