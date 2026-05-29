"""Keyboard input with randomized timing."""
from __future__ import annotations
import random
import time
from pynput.keyboard import Key, Controller

_DEFAULT_KEYBOARD = Controller()

KEY_MAP = {
    "enter": Key.enter,
    "esc": Key.esc,
    "up": Key.up,
    "down": Key.down,
    "y": "y",
}


def _rand_seconds(ms_range) -> float:
    return random.uniform(ms_range[0], ms_range[1]) / 1000.0


def press_key(name, key_hold_ms, between_keys_ms,
              keyboard=_DEFAULT_KEYBOARD, sleep=time.sleep) -> None:
    """Press one key with a randomized hold and post-press gap."""
    key = KEY_MAP[name]
    keyboard.press(key)
    sleep(_rand_seconds(key_hold_ms))
    keyboard.release(key)
    sleep(_rand_seconds(between_keys_ms))


def tap_key(name, times, key_hold_ms, between_keys_ms,
            keyboard=_DEFAULT_KEYBOARD, sleep=time.sleep) -> None:
    """Press a key `times` times."""
    for _ in range(times):
        press_key(name, key_hold_ms, between_keys_ms, keyboard, sleep)
