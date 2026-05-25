"""Entry point: wires config, templates, sniper, overlay, and hotkeys."""
from __future__ import annotations
import logging
import sys
import threading
from pynput import keyboard
from . import capture, notifier, paths, vision
from .config import load_config
from .overlay import Overlay
from .sniper import GameIO, Sniper


def _setup_logging():
    log_path = paths.app_dir() / "logs" / "sniper.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(message)s", "%H:%M:%S")
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root = logging.getLogger("fh6")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    if sys.stderr is not None:          # no console under --windowed exe
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    return log_path


def main() -> None:
    log_path = _setup_logging()
    logging.getLogger("fh6").info("FH6 Sniper starting (log: %s)", log_path)
    cfg = load_config(paths.app_dir() / "config.json")
    templates = vision.load_templates(
        paths.app_dir() / cfg.template_dir,
        moving_background=cfg.moving_background)
    io = GameIO(cfg, templates)
    overlay = Overlay(
        hide_from_capture=not getattr(cfg, "overlay_capturable", False))

    state = {
        "sniper": None,
        "thread": None,
        # display-side running totals - accumulate across stop/start cycles
        # so the overlay's BOUGHT / SEARCHES / FAILS don't reset every run.
        "display": {"searches": 0, "bought": 0, "fails": 0},
        # last raw values seen from the current Sniper - used to compute
        # deltas (new Sniper instances start their internal counters at 0).
        "last_bot_stats": (0, 0, 0),
    }
    purchase_log = paths.app_dir() / cfg.log_path

    def on_purchase(loop_seconds, total):
        notifier.log_purchase(purchase_log, "bought", loop_seconds, total)
        notifier.notify_success(total, cfg.notify_sound, cfg.notify_toast)

    def on_stats(searches, bought, fails):
        last_s, last_b, last_f = state["last_bot_stats"]
        d = state["display"]
        d["searches"] += max(0, searches - last_s)
        d["bought"]   += max(0, bought   - last_b)
        d["fails"]    += max(0, fails    - last_f)
        state["last_bot_stats"] = (searches, bought, fails)
        overlay.set_stats(d["searches"], d["bought"], d["fails"])

    def start():
        if state["thread"] and state["thread"].is_alive():
            return
        capture.focus_window(cfg.window_title)
        state["last_bot_stats"] = (0, 0, 0)        # new Sniper, fresh deltas
        sniper = Sniper(io, cfg, on_purchase=on_purchase,
                        on_status=overlay.set_status,
                        on_stats=on_stats)

        def _run_safe():
            try:
                sniper.run()
            except Exception:
                logging.getLogger("fh6.main").exception(
                    "sniper thread crashed")
                try:
                    overlay.set_status("Crashed: see sniper.log")
                except Exception:
                    pass

        thread = threading.Thread(target=_run_safe, daemon=True)
        state["sniper"], state["thread"] = sniper, thread
        thread.start()

    def stop():
        if state["sniper"]:
            state["sniper"].request_stop()

    def toggle():
        if state["thread"] and state["thread"].is_alive():
            stop()
        else:
            start()

    hotkeys = keyboard.GlobalHotKeys({
        cfg.hotkey_start_stop: toggle,
        cfg.hotkey_panic: stop,
    })
    hotkeys.start()

    overlay.on_toggle(toggle)
    overlay.set_status("Idle")
    try:
        overlay.run()
    finally:
        stop()
        hotkeys.stop()


if __name__ == "__main__":
    main()
