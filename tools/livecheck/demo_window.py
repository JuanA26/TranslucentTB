"""Maximized test window whose color cycles, so the matcher can be checked against known colors.

python prototype/demo_window.py --colors "#1e1e1e,#2b5797,#ffffff,busy" --interval 3
"busy" draws random colored blocks (the matcher should back off).
"""
import argparse
import random
import tkinter as tk


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--colors", default="#1e1e1e,#2b5797,#ffffff,busy")
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--cycles", type=int, default=1, help="times to go through the list, then close (0 = forever)")
    args = p.parse_args()
    colors = [c.strip() for c in args.colors.split(",")]

    root = tk.Tk()
    root.title("TaskbarMatch demo")
    root.state("zoomed")
    # Background-launched processes can't take focus; topmost puts it above other apps anyway.
    root.attributes("-topmost", True)
    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    step = {"i": 0}

    def show():
        i = step["i"]
        if args.cycles and i >= len(colors) * args.cycles:
            root.destroy()
            return
        c = colors[i % len(colors)]
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if c == "busy":
            rng = random.Random(1)
            canvas.configure(bg="#000000")
            for x in range(0, w, 24):
                for y in range(0, h, 24):
                    canvas.create_rectangle(x, y, x + 24, y + 24, width=0,
                                            fill="#%06x" % rng.randrange(0x1000000))
        else:
            canvas.configure(bg=c)
        canvas.create_text(w // 2, h // 2, text=f"demo color: {c}", font=("Segoe UI", 28),
                           fill="#888888")
        print("SHOW", c, flush=True)
        step["i"] = i + 1
        root.after(int(args.interval * 1000), show)

    root.after(500, show)
    root.mainloop()


if __name__ == "__main__":
    main()
