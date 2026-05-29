"""Path resolution that works in both source and frozen (PyInstaller) builds."""
from __future__ import annotations
import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory holding templates, config, and logs.

    Frozen exe: the folder containing the exe.
    Source: the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent
