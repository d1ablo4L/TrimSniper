"""Overlay di stato sempre in primo piano — tema ROG TrimSniper."""
from __future__ import annotations
import ctypes
import time
import tkinter as tk

# ── Palette ROG ─────────────────────────────────────────────────────────────
# Sfondo: gradiente simulato dal nero puro verso il rosso scuro profondo.
# Ogni sezione ha una tonalità leggermente più calda di quella precedente.
_BORDER   = "#FF0028"   # bordo esterno 1 px — rosso ROG pieno
_BG_HDR   = "#020000"   # header (quasi nero)
_BG       = "#080000"   # corpo principale
_BG_MID   = "#0c0000"   # zona status / pulsante
_BG_BOT   = "#160000"   # footer (rosso scuro più caldo)
_CARD     = "#0e0000"   # card statistiche

_DIVIDER  = "#2a0000"   # separatori
_ROG      = "#FF0028"   # rosso ROG — colore accento primario
_ROG_DIM  = "#c40020"   # ROG leggermente smorzato (hover stop)
_TEXT     = "#f4f4f6"   # testo bianco
_DIM      = "#7a3535"   # testo dimmed rosso-grigio
_FAINT    = "#3a0e0e"   # testo molto tenue (etichette card)
_AMBER    = "#f0a83c"   # stato in pausa
_RED_STAT = "#ff4060"   # contatore FALLITI
_STOP     = "#b80000"   # pulsante ferma
_STOP_HV  = "#8f0000"   # hover ferma
_START_HV = "#cc001e"   # hover avvia

# Parole nei messaggi di stato che portano in stato "fermo"
_STOPPED_WORDS = ("inattivo", "fermato", "auto-stop", "perso",
                  "impossibile", "crash", "in pausa")


class Overlay:
    """HUD di stato Tk con tema ROG. run() blocca sul loop principale di Tk."""

    def __init__(self, hide_from_capture: bool = True):
        self.root = tk.Tk()
        self.root.title("TrimSniper V1.0.0")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        # Il background del root è il rosso ROG → crea un sottile bordo colorato
        self.root.configure(bg=_BORDER)

        self._status_var   = tk.StringVar(value="Inattivo")
        self._bought_var   = tk.StringVar(value="0")
        self._searches_var = tk.StringVar(value="0")
        self._fails_var    = tk.StringVar(value="0")
        self._time_var     = tk.StringVar(value="00:00")
        self._active  = False
        self._started = None
        self._drag    = (0, 0)
        self._btn_base  = _ROG
        self._btn_hover = _START_HV

        self._build()
        self.root.update_idletasks()
        # +1 px per il bordo ROG su ogni lato
        w = 344 + 2
        h = self.root.winfo_reqheight()
        self.root.geometry(f"{w}x{h}+24+24")
        if hide_from_capture:
            self._exclude_from_capture()
        self._tick()

    # ── Escludi dalla cattura ──────────────────────────────────────────────
    def _exclude_from_capture(self):
        """Nasconde l'overlay dalla cattura schermo (WDA_EXCLUDEFROMCAPTURE)."""
        try:
            user32 = ctypes.windll.user32
            hwnd   = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd   = parent
                parent = user32.GetParent(hwnd)
            user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception:
            pass

    # ── Layout ─────────────────────────────────────────────────────────────
    def _build(self):
        root = self.root

        # Contenitore interno: 1 px di padding rispetto al bordo ROG del root
        inner = tk.Frame(root, bg=_BG_HDR)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Striscia accent in cima (dentro il contenitore) ─────────────
        tk.Frame(inner, bg=_ROG, height=3).pack(fill="x")

        # ── Header: titolo + dot + chiudi ───────────────────────────────
        header = tk.Frame(inner, bg=_BG_HDR)
        header.pack(fill="x", padx=16, pady=(13, 0))

        self._dot = tk.Label(header, text="●", bg=_BG_HDR, fg=_DIM,
                             font=("Segoe UI", 9))
        self._dot.pack(side="left")

        # Titolo principale
        title_frame = tk.Frame(header, bg=_BG_HDR)
        title_frame.pack(side="left", padx=(6, 0))
        tk.Label(title_frame, text="TrimSniper", bg=_BG_HDR, fg=_ROG,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(title_frame, text=" V1.0.0", bg=_BG_HDR, fg=_TEXT,
                 font=("Segoe UI", 10)).pack(side="left")

        close = tk.Label(header, text="✕", bg=_BG_HDR, fg=_DIM,
                         font=("Segoe UI", 11), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.root.destroy())
        close.bind("<Enter>", lambda _e: close.config(fg=_ROG))
        close.bind("<Leave>", lambda _e: close.config(fg=_DIM))

        # Firma autore sotto il titolo
        tk.Label(inner, text="Creato da d1ablo", bg=_BG_HDR, fg=_FAINT,
                 font=("Segoe UI", 7)).pack(anchor="w", padx=36, pady=(1, 0))

        # Drag sull'header e sulla firma
        for w in (header, self._dot, title_frame, inner):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        # ── Separatore ──────────────────────────────────────────────────
        sep = tk.Frame(inner, bg=_DIVIDER, height=1)
        sep.pack(fill="x", padx=16, pady=(12, 0))

        # ── Stato ───────────────────────────────────────────────────────
        status_bg = tk.Frame(inner, bg=_BG_MID)
        status_bg.pack(fill="x")
        self._status = tk.Label(
            status_bg, textvariable=self._status_var,
            bg=_BG_MID, fg=_ROG,
            font=("Segoe UI", 12, "bold"), anchor="center",
            justify="center", wraplength=300, height=2)
        self._status.pack(fill="x", padx=16, pady=(10, 0))

        # ── Card statistiche ─────────────────────────────────────────────
        self._build_stats(inner)

        # ── Pulsante AVVIA / FERMA ───────────────────────────────────────
        btn_wrap = tk.Frame(inner, bg=_BG_MID)
        btn_wrap.pack(fill="x", padx=16, pady=(13, 0))
        self._btn = tk.Button(
            btn_wrap, text="AVVIA", font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", height=2)
        self._btn.pack(fill="x")
        self._btn.bind("<Enter>",
                       lambda _e: self._btn.config(bg=self._btn_hover))
        self._btn.bind("<Leave>",
                       lambda _e: self._btn.config(bg=self._btn_base))
        self._set_button(running=False)

        # ── Footer con hotkey ────────────────────────────────────────────
        footer = tk.Frame(inner, bg=_BG_BOT)
        footer.pack(fill="x")
        tk.Label(footer,
                 text="F8  avvia / ferma          F9  emergenza",
                 bg=_BG_BOT, fg=_DIM,
                 font=("Segoe UI", 8)).pack(pady=(11, 14))

    def _build_stats(self, parent):
        card = tk.Frame(parent, bg=_CARD)
        card.pack(fill="x", padx=16, pady=(12, 0))
        cells = (
            ("ACQUISTATI", self._bought_var,   _ROG),
            ("RICERCHE",   self._searches_var,  _TEXT),
            ("FALLITI",    self._fails_var,      _RED_STAT),
            ("ATTIVO",     self._time_var,       _TEXT),
        )
        for i, (caption, var, color) in enumerate(cells):
            if i:
                tk.Frame(card, bg=_DIVIDER, width=1).pack(
                    side="left", fill="y", pady=10)
            cell = tk.Frame(card, bg=_CARD)
            cell.pack(side="left", expand=True, fill="both")
            tk.Label(cell, textvariable=var, bg=_CARD, fg=color,
                     font=("Segoe UI", 15, "bold")).pack(pady=(11, 0))
            tk.Label(cell, text=caption, bg=_CARD, fg=_FAINT,
                     font=("Segoe UI", 7)).pack(pady=(2, 11))

    # ── Drag ───────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        self.root.geometry(
            f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    # ── Logica pulsante ────────────────────────────────────────────────────
    def _set_button(self, running: bool):
        if running:
            text, base, hover, fg = "FERMA", _STOP, _STOP_HV, "#ffffff"
        else:
            text, base, hover, fg = "AVVIA", _ROG,  _START_HV, "#ffffff"
        self._btn_base, self._btn_hover = base, hover
        self._btn.config(text=text, bg=base, fg=fg,
                         activebackground=hover, activeforeground=fg)

    # ── Logica stato ───────────────────────────────────────────────────────
    @staticmethod
    def _state_of(text: str) -> str:
        low = text.lower()
        if "in pausa" in low:
            return "paused"
        if any(w in low for w in _STOPPED_WORDS):
            return "stopped"
        return "running"

    def _apply_status(self, text: str):
        self._status_var.set(text)
        state = self._state_of(text)
        dot_color  = {"running": _ROG, "paused": _AMBER, "stopped": _DIM}[state]
        text_color = {"running": _ROG, "paused": _AMBER, "stopped": _DIM}[state]
        self._dot.config(fg=dot_color)
        self._status.config(fg=text_color)
        running = state != "stopped"
        self._set_button(running)
        if running and self._started is None:
            self._started = time.monotonic()
            self._time_var.set("00:00")
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

    # ── API pubblica ───────────────────────────────────────────────────────
    def set_status(self, text: str):
        """Aggiornamento stato thread-safe."""
        try:
            self.root.after(0, self._apply_status, text)
        except RuntimeError:
            pass

    def set_stats(self, searches: int, bought: int, fails: int):
        """Aggiornamento statistiche thread-safe."""
        try:
            self.root.after(0, self._apply_stats, searches, bought, fails)
        except RuntimeError:
            pass

    def on_toggle(self, callback):
        """Collega il pulsante AVVIA/FERMA a un callback."""
        self._btn.config(command=callback)

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
