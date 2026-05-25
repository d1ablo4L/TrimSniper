"""Always-on-top status overlay for the sniper."""
from __future__ import annotations
import ctypes
import time
import tkinter as tk

_BG       = "#15161a"
_CARD     = "#1e1f25"
_DIVIDER  = "#2e2f37"
_LIME     = "#c6f000"
_TEXT     = "#f4f4f6"
_DIM      = "#83858f"
_FAINT    = "#5c5e68"
_AMBER    = "#f0a83c"
_RED      = "#e2685f"
_STOP     = "#e0524b"
_STOP_HV  = "#c43f39"
_START_HV = "#b0d800"

_STOPPED_WORDS = ("idle", "stopped", "auto-stop", "lost", "could not", "crashed")


class Overlay:
    """Tk status HUD. run() blocks on the tk main loop."""

    def __init__(self, hide_from_capture: bool = True):
        self.root = tk.Tk()
        self.root.title("FH6 Sniper")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg=_BG)

        self._status_var = tk.StringVar(value="Idle")
        self._bought_var = tk.StringVar(value="0")
        self._searches_var = tk.StringVar(value="0")
        self._fails_var = tk.StringVar(value="0")
        self._time_var = tk.StringVar(value="00:00")
        self._active = False
        self._started = None
        self._drag = (0, 0)
        self._btn_base = _LIME
        self._btn_hover = _START_HV

        self._build()
        self.root.update_idletasks()
        self.root.geometry(f"344x{self.root.winfo_reqheight()}+24+24")
        if hide_from_capture:
            self._exclude_from_capture()
        self._tick()

    def _exclude_from_capture(self):
        """Hide the overlay from screen capture (WDA_EXCLUDEFROMCAPTURE)."""
        try:
            user32 = ctypes.windll.user32
            hwnd = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd = parent
                parent = user32.GetParent(hwnd)
            user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception:
            pass

    def _build(self):
        root = self.root
        tk.Frame(root, bg=_LIME, height=3).pack(fill="x")

        header = tk.Frame(root, bg=_BG)
        header.pack(fill="x", padx=18, pady=(15, 0))
        self._dot = tk.Label(header, text="●", bg=_BG, fg=_DIM,
                             font=("Segoe UI", 10))
        self._dot.pack(side="left")
        brand = tk.Label(header, text="  FH6", bg=_BG, fg=_LIME,
                         font=("Segoe UI", 11, "bold"))
        brand.pack(side="left")
        name = tk.Label(header, text=" SNIPER", bg=_BG, fg=_TEXT,
                        font=("Segoe UI", 11, "bold"))
        name.pack(side="left")
        close = tk.Label(header, text="✕", bg=_BG, fg=_DIM,
                         font=("Segoe UI", 11), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.root.destroy())
        close.bind("<Enter>", lambda _e: close.config(fg=_TEXT))
        close.bind("<Leave>", lambda _e: close.config(fg=_DIM))
        for w in (header, self._dot, brand, name):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        tk.Frame(root, bg=_DIVIDER, height=1).pack(
            fill="x", padx=18, pady=(14, 0))

        self._status = tk.Label(
            root, textvariable=self._status_var, bg=_BG, fg=_LIME,
            font=("Segoe UI", 13), anchor="center", justify="center",
            wraplength=300, height=2)
        self._status.pack(fill="x", padx=18, pady=(11, 0))

        self._build_stats(root)

        self._btn = tk.Button(
            root, text="START", font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, highlightthickness=0, cursor="hand2",
            height=2)
        self._btn.pack(fill="x", padx=18, pady=(14, 0))
        self._btn.bind("<Enter>",
                       lambda _e: self._btn.config(bg=self._btn_hover))
        self._btn.bind("<Leave>",
                       lambda _e: self._btn.config(bg=self._btn_base))
        self._set_button(running=False)

        tk.Label(root, text="F8  start / stop          F9  panic",
                 bg=_BG, fg=_DIM, font=("Segoe UI", 8)).pack(pady=(12, 15))

    def _build_stats(self, root):
        card = tk.Frame(root, bg=_CARD)
        card.pack(fill="x", padx=18, pady=(13, 0))
        cells = (("BOUGHT", self._bought_var, _LIME),
                 ("SEARCHES", self._searches_var, _TEXT),
                 ("FAILS", self._fails_var, _RED),
                 ("UPTIME", self._time_var, _TEXT))
        for i, (caption, var, color) in enumerate(cells):
            if i:
                tk.Frame(card, bg=_DIVIDER, width=1).pack(
                    side="left", fill="y", pady=12)
            cell = tk.Frame(card, bg=_CARD)
            cell.pack(side="left", expand=True, fill="both")
            tk.Label(cell, textvariable=var, bg=_CARD, fg=color,
                     font=("Segoe UI", 15, "bold")).pack(pady=(12, 0))
            tk.Label(cell, text=caption, bg=_CARD, fg=_FAINT,
                     font=("Segoe UI", 8)).pack(pady=(2, 12))

    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        self.root.geometry(
            f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _set_button(self, running: bool):
        if running:
            text, base, hover, fg = "STOP", _STOP, _STOP_HV, "#ffffff"
        else:
            text, base, hover, fg = "START", _LIME, _START_HV, _BG
        self._btn_base, self._btn_hover = base, hover
        self._btn.config(text=text, bg=base, fg=fg,
                         activebackground=hover, activeforeground=fg)

    @staticmethod
    def _state_of(text: str) -> str:
        low = text.lower()
        if "paused" in low:
            return "paused"
        if any(w in low for w in _STOPPED_WORDS):
            return "stopped"
        return "running"

    def _apply_status(self, text: str):
        self._status_var.set(text)
        state = self._state_of(text)
        self._dot.config(
            fg={"running": _LIME, "paused": _AMBER, "stopped": _DIM}[state])
        self._status.config(
            fg={"running": _LIME, "paused": _AMBER, "stopped": _DIM}[state])
        running = state != "stopped"
        self._set_button(running)
        if running and self._started is None:    # first ever start, init timer
            self._started = time.monotonic()
            self._time_var.set("00:00")
        # Stats (bought / searches / fails) accumulate across stop/start
        # cycles and only clear when the overlay is closed.
        self._active = running

    def _apply_stats(self, searches: int, bought: int, fails: int):
        self._searches_var.set(str(searches))
        self._bought_var.set(str(bought))
        self._fails_var.set(str(fails))

    def _tick(self):
        if self._active and self._started is not None:
            m, s = divmod(int(time.monotonic() - self._started), 60)
            self._time_var.set(f"{m:02d}:{s:02d}")
        try:
            self.root.after(1000, self._tick)
        except RuntimeError:
            pass

    def set_status(self, text: str):
        """Thread-safe status update."""
        try:
            self.root.after(0, self._apply_status, text)
        except RuntimeError:
            pass

    def set_stats(self, searches: int, bought: int, fails: int):
        """Thread-safe stats update."""
        try:
            self.root.after(0, self._apply_stats, searches, bought, fails)
        except RuntimeError:
            pass

    def on_toggle(self, callback):
        """Wire the START/STOP button to a callback."""
        self._btn.config(command=callback)

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
