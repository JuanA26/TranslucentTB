"""Live check: open a maximized demo window cycling known colors and screenshot only the
taskbar area for each. Writes PNGs + a summary to the output folder. Whatever is painting
the taskbar (TranslucentBarImproved) must already be running.

python tools/livecheck/verify_live.py OUT_DIR [--colors "#1e1e1e,#2b5797,busy"]
"""
import argparse
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

import win32
from colorpick import ensure_readable, pick_color, to_hex

HERE = Path(__file__).resolve().parent


def write_png(path: Path, bgra: bytes, w: int, h: int) -> None:
    rows = b"".join(b"\x00" + bytes(
        v for i in range(y * w * 4, (y + 1) * w * 4, 4) for v in (bgra[i + 2], bgra[i + 1], bgra[i]))
        for y in range(h))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def hex_to_rgb(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--colors", default="#1e1e1e,#2b5797,#ffffff,busy")
    p.add_argument("--interval", type=float, default=3.0)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    win32.make_dpi_aware()

    bar = next(b for b in win32.find_taskbars() if b.hwnd and b.edge == "bottom")
    l, t, r, b = bar.rect
    shot = (l, t - 40, r, b)  # taskbar + 40 px of app above it
    light = win32.taskbar_uses_light_text()

    colors = [c.strip() for c in args.colors.split(",")]
    demo = subprocess.Popen([sys.executable, str(HERE / "demo_window.py"), "--colors", args.colors,
                             "--interval", str(args.interval)], stdout=subprocess.PIPE, text=True)
    lines = []
    try:
        for c in colors:
            line = demo.stdout.readline().strip()  # "SHOW <color>"
            assert line == f"SHOW {c}", line
            time.sleep(args.interval * 0.6)  # let sampling + fade settle
            raw, w, h = win32.capture_raw(shot)
            name = c.lstrip("#")
            write_png(args.out / f"taskbar_{name}.png", raw, w, h)
            # Dominant color of the taskbar band only (rows 40..), skipping icons/text.
            px = [(raw[i + 2], raw[i + 1], raw[i]) for y in range(40, h) for i in range(y * w * 4, (y + 1) * w * 4, 16)]
            got, cov = pick_color(px, tolerance=6)
            expect = "-" if c == "busy" else to_hex(ensure_readable(hex_to_rgb(c), light, 3.0))
            i = (40 * w + 200) * 4  # taskbar's top row, left of the icons: where a divider would be
            top = (raw[i + 2], raw[i + 1], raw[i])
            lines.append(f"demo {c:8s} expected taskbar {expect:8s} got {to_hex(got)} ({cov:.0%} of taskbar), top row {to_hex(top)}")
            print(lines[-1], flush=True)
    finally:
        demo.wait(timeout=args.interval + 5)
    (args.out / "summary.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
