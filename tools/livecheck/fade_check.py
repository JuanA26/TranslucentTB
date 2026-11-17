"""Measure the taskbar color transition when a maximized app changes color.

Opens the demo window (dark, then red), and once it switches, samples one taskbar pixel
(left of the icons) every few ms. Prints the timeline and how long the change took.
The app painting the taskbar (TranslucentBarImproved) must already be running.

python tools/livecheck/fade_check.py [--from-color "#1e1e1e"] [--to-color "#c0392b"]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import win32
from colorpick import to_hex

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from-color", default="#1e1e1e")
    p.add_argument("--to-color", default="#c0392b")
    p.add_argument("--window", type=float, default=0.6, help="seconds to sample after the switch")
    args = p.parse_args()
    win32.make_dpi_aware()

    bar = next(b for b in win32.find_taskbars() if b.edge == "bottom")
    l, t, r, b = bar.rect
    x, y = l + 200, (t + b) // 2
    probe = (x, y, x + 1, y + 1)

    def sample():
        raw, _, _ = win32.capture_raw(probe)
        return raw[2], raw[1], raw[0]

    demo = subprocess.Popen([sys.executable, str(HERE / "demo_window.py"), "--colors",
                             f"{args.from_color},{args.to_color}", "--interval", "2"],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert demo.stdout.readline().strip() == f"SHOW {args.from_color}"
        time.sleep(1.5)
        before = sample()
        assert demo.stdout.readline().strip() == f"SHOW {args.to_color}"
        start = time.perf_counter()
        timeline = []
        while (now := time.perf_counter() - start) < args.window:
            timeline.append((now, sample()))
            time.sleep(0.004)
    finally:
        demo.wait(timeout=10)

    final = timeline[-1][1]
    changes = [(ts, c) for i, (ts, c) in enumerate(timeline) if i == 0 or c != timeline[i - 1][1]]
    print(f"before switch: {to_hex(before)}   final: {to_hex(final)}   samples: {len(timeline)}")
    for ts, c in changes:
        print(f"  {ts * 1000:6.0f} ms  {to_hex(c)}")
    moving = [ts for ts, c in changes if c != before]
    if moving:
        first = moving[0]
        settled = next(ts for ts, c in changes if c == final)
        distinct = len({c for _, c in timeline} - {before, final})
        print(f"first change at {first * 1000:.0f} ms, settled at {settled * 1000:.0f} ms, "
              f"transition {(settled - first) * 1000:.0f} ms with {distinct} in-between colors")


if __name__ == "__main__":
    main()
