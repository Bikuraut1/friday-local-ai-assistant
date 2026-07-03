from __future__ import annotations

import math
import random
import time
import tkinter as tk
from pathlib import Path


ROOT = Path("D:/Friday")
LOG_PATH = ROOT / "logs" / "wake-listener.log"
TITLE = "FRIDAY"


class FridayVisualizer:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(TITLE)
        self.root.geometry("360x130+40+80")
        self.root.configure(bg="#090d10")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        self.phase = 0.0
        self.mode = "starting"
        self.last_log_size = 0
        self.drag_x = 0
        self.drag_y = 0

        self.container = tk.Frame(self.root, bg="#090d10", highlightthickness=1, highlightbackground="#27313a")
        self.container.pack(fill="both", expand=True)

        self.header = tk.Frame(self.container, bg="#0f151a", height=34)
        self.header.pack(fill="x")
        self.header.bind("<ButtonPress-1>", self.start_drag)
        self.header.bind("<B1-Motion>", self.drag)

        self.title = tk.Label(
            self.header,
            text="FRIDAY",
            fg="#edf2f4",
            bg="#0f151a",
            font=("Segoe UI", 11, "bold"),
        )
        self.title.pack(side="left", padx=12)
        self.title.bind("<ButtonPress-1>", self.start_drag)
        self.title.bind("<B1-Motion>", self.drag)

        self.close = tk.Button(
            self.header,
            text="x",
            command=self.root.destroy,
            fg="#9aa8b2",
            bg="#0f151a",
            activeforeground="#ffffff",
            activebackground="#19232b",
            relief="flat",
            width=3,
            cursor="hand2",
        )
        self.close.pack(side="right", padx=6)

        self.status = tk.Label(
            self.container,
            text="Starting voice core",
            fg="#9aa8b2",
            bg="#090d10",
            font=("Segoe UI", 9),
        )
        self.status.pack(anchor="w", padx=13, pady=(9, 0))

        self.canvas = tk.Canvas(self.container, width=334, height=58, bg="#090d10", highlightthickness=0)
        self.canvas.pack(padx=13, pady=(2, 10))

        self.root.after(80, self.tick)

    def start_drag(self, event) -> None:
        self.drag_x = event.x
        self.drag_y = event.y

    def drag(self, event) -> None:
        x = self.root.winfo_x() + event.x - self.drag_x
        y = self.root.winfo_y() + event.y - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def read_log_mode(self) -> None:
        if not LOG_PATH.exists():
            return
        try:
            size = LOG_PATH.stat().st_size
            if size == self.last_log_size:
                return
            self.last_log_size = size
            text = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-2500:].lower()
        except Exception:
            return

        if "listening..." in text:
            self.mode = "listening"
        elif "stt(" in text or "llm:" in text or "router:" in text:
            self.mode = "thinking"
        elif "friday:" in text or "tts+playback" in text or "startup greeting" in text:
            self.mode = "speaking"
        elif "wake listener armed" in text:
            self.mode = "armed"
        elif "wake word detected" in text:
            self.mode = "awake"

    def mode_label(self) -> str:
        return {
            "starting": "Starting voice core",
            "armed": "Standing by - say Hey Jarvis",
            "awake": "Wake detected",
            "listening": "Listening",
            "thinking": "Thinking",
            "speaking": "Speaking",
        }.get(self.mode, "Online")

    def mode_color(self) -> str:
        return {
            "starting": "#9aa8b2",
            "armed": "#57c7ff",
            "awake": "#f2c94c",
            "listening": "#33d17a",
            "thinking": "#b48cff",
            "speaking": "#57c7ff",
        }.get(self.mode, "#57c7ff")

    def amplitude(self) -> float:
        return {
            "starting": 0.20,
            "armed": 0.26,
            "awake": 0.62,
            "listening": 0.85,
            "thinking": 0.46,
            "speaking": 0.75,
        }.get(self.mode, 0.32)

    def draw_wave(self) -> None:
        self.canvas.delete("all")
        color = self.mode_color()
        amp = self.amplitude()
        width = 334
        height = 58
        center = height / 2
        bars = 34
        gap = 4
        bar_width = (width - (bars - 1) * gap) / bars

        for index in range(bars):
            wave = math.sin(self.phase + index * 0.55)
            pulse = math.sin(self.phase * 0.55 + index * 0.17)
            jitter = random.uniform(-0.05, 0.05)
            normalized = abs(wave * 0.72 + pulse * 0.28) + jitter
            bar_height = max(5, min(height - 8, 7 + normalized * amp * 48))
            x1 = index * (bar_width + gap)
            x2 = x1 + bar_width
            y1 = center - bar_height / 2
            y2 = center + bar_height / 2
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="", width=0)

        self.canvas.create_oval(width - 18, 6, width - 8, 16, fill=color, outline="")

    def tick(self) -> None:
        self.read_log_mode()
        self.status.configure(text=self.mode_label(), fg=self.mode_color())
        self.draw_wave()
        self.phase += 0.28 if self.mode in {"listening", "speaking", "awake"} else 0.16
        self.root.after(80, self.tick)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    FridayVisualizer().run()
