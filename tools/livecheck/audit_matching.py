"""Exercise PDF edge transitions, mixed content, and maximize/restore on the real taskbar.

Run before AND after installing a build:
  python tools/livecheck/audit_matching.py OUT_DIR
Opens only owned test windows; saves cropped taskbar PNGs and a JSON report.
Exit status is nonzero when the taskbar does not match the expected surface.
"""
import argparse
import json
import tkinter as tk
from pathlib import Path

import win32
from colorpick import ensure_readable, pick_color, to_hex
from verify_live import write_png


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    win32.make_dpi_aware()
    bars = [b for b in win32.find_taskbars() if b.edge == "bottom"]
    if not bars:
        parser.error("No visible bottom taskbar; run on the interactive desktop with auto-hide off.")
    bar = bars[0]
    light = win32.taskbar_uses_light_text()
    results = []
    root = tk.Tk()
    root.title("Taskbar color audit - background app")
    root.configure(bg="#2b5797")
    root.attributes("-topmost", True)
    root.state("zoomed")
    app = tk.Toplevel(root)
    app.title("Taskbar color audit - PDF and mixed content")
    app.attributes("-topmost", True)
    app.state("zoomed")
    canvas = tk.Canvas(app, highlightthickness=0, bg="#262626")
    canvas.pack(fill="both", expand=True)

    def paint(kind):
        app.deiconify()
        app.state("zoomed")
        app.lift()
        # Maximizing is asynchronous. Paint after Windows has resized the client.
        root.after(200, lambda: draw(kind))

    def draw(kind):
        canvas.delete("all")
        canvas.configure(bg="#262626")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if kind.startswith("pdf"):
            # Same margins, with the document either reaching the taskbar or
            # ending just above it: exactly the abrupt transition in the report.
            bottom = h if kind == "pdf_page_at_edge" else h - 24
            canvas.create_rectangle(w * .18, 0, w * .91, bottom, fill="white", width=0)
        elif kind == "thin_edge":
            canvas.create_rectangle(0, h - 3, w, h, fill="#ff00ff", width=0)
        elif kind == "mixed":
            canvas.configure(bg="#204060")
            canvas.create_rectangle(w // 2, 0, w, h, fill="#c08040", width=0)
        elif kind == "white":
            canvas.configure(bg="white")

    stages = [
        ("pdf_page_at_edge", lambda: paint("pdf_page_at_edge"), (38, 38, 38)),
        ("pdf_page_above_edge", lambda: paint("pdf_page_above_edge"), (38, 38, 38)),
        ("pdf_page_at_edge_again", lambda: paint("pdf_page_at_edge"), (38, 38, 38)),
        ("thin_edge", lambda: paint("thin_edge"), (38, 38, 38)),
        ("mixed", lambda: paint("mixed"), (112, 96, 80)),
        ("white", lambda: paint("white"), (255, 255, 255)),
        ("minimized_over_blue", lambda: app.iconify(), (43, 87, 151)),
        ("restored_maximized", lambda: paint("pdf_page_at_edge"), (38, 38, 38)),
        ("restored_normal_over_blue", lambda: (app.state("normal"), app.geometry("800x500+80+80")), (43, 87, 151)),
        ("maximized_again", lambda: paint("pdf_page_at_edge"), (38, 38, 38)),
    ]

    def capture_stage(index):
        name, _, color = stages[index]
        l, t, r, b = bar.rect
        raw, w, h = win32.capture_raw((l, t - 260, r, b))
        write_png(args.out / f"{index:02}_{name}.png", raw, w, h)
        pixels = [(raw[i + 2], raw[i + 1], raw[i])
                  for y in range(264, h) for i in range(y * w * 4, (y + 1) * w * 4, 16)]
        got, coverage = pick_color(pixels, tolerance=6)
        expected = ensure_readable(color, light, 3.0)
        error = max(abs(a - b) for a, b in zip(got, expected))
        passed = error <= 8 and coverage >= .70
        results.append(dict(stage=name, expected=to_hex(expected), actual=to_hex(got),
                            coverage=round(coverage, 3), passed=passed))
        print(f"{'PASS' if passed else 'FAIL'} {name}: expected {to_hex(expected)}, "
              f"actual {to_hex(got)} ({coverage:.0%})", flush=True)
        next_stage(index + 1)

    def next_stage(index):
        if index == len(stages):
            (args.out / "report.json").write_text(json.dumps(results, indent=2) + "\n")
            root.destroy()
            return
        stages[index][1]()
        root.after(2200, lambda: capture_stage(index))

    root.after(700, lambda: next_stage(0))
    try:
        root.mainloop()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
    return 0 if len(results) == len(stages) and all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
