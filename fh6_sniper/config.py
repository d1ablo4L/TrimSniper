"""Configuration dataclass and JSON load/save."""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class Config:
    window_title: str = "Forza Horizon 6"
    resolution: tuple = (1920, 1080)
    match_threshold: float = 0.80
    # lime UI colour in HSV — usato solo dalla utility largest_lime_bbox,
    # NON più dal rilevamento Conferma/SOLD (ora universale SDR+HDR).
    lime_hsv_lower: tuple = (32, 110, 110)
    lime_hsv_upper: tuple = (52, 255, 255)
    # key timing in ms (min, max), randomised per press
    key_hold_ms: tuple = (20, 45)
    between_keys_ms: tuple = (20, 55)
    poll_interval_ms: tuple = (40, 90)
    buyout_select_delay_ms: int = 0
    moving_background: bool = True
    # timeouts in seconds
    timeout_results_s: float = 12.0
    timeout_outcome_s: float = 25.0
    timeout_claim_s: float = 20.0
    timeout_generic_s: float = 10.0
    loop_pace_s: float = 0.15
    # auto-stop
    auto_stop_enabled: bool = True
    max_cars: int = 1
    max_minutes: float = 180.0
    # behaviour
    collect_after_buyout: bool = True
    notify_sound: bool = True
    notify_toast: bool = True
    # paths
    log_path: str = "logs/purchases.csv"
    template_dir: str = "templates"
    # global hotkeys (pynput format)
    hotkey_start_stop: str = "<f8>"
    hotkey_panic: str = "<f9>"


_TUPLE_FIELDS = {
    name for name, f in Config.__dataclass_fields__.items()
    if isinstance(f.default, tuple)
}


def load_config(path=DEFAULT_CONFIG_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        cfg = Config()
        save_config(cfg, path)
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in _TUPLE_FIELDS:
        if key in data and isinstance(data[key], list):
            data[key] = tuple(data[key])
    known = set(Config.__dataclass_fields__)
    cfg = Config(**{k: v for k, v in data.items() if k in known})
    for key, value in data.items():
        if key not in known:
            setattr(cfg, key, value)
    if not known.issubset(data.keys()):
        save_config(cfg, path)
    return cfg


def save_config(cfg: Config, path=DEFAULT_CONFIG_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    declared = set(Config.__dataclass_fields__)
    for key, value in cfg.__dict__.items():
        if key not in declared:
            data[key] = value
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
