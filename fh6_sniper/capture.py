"""Screen capture and window-focus helpers — universale per qualsiasi risoluzione."""
from __future__ import annotations
import ctypes
import logging
import time
import numpy as np
import cv2
import win32con
import win32gui

_log = logging.getLogger("fh6.capture")

# ── DPI awareness ────────────────────────────────────────────────────────────
# Obbligatorio per ottenere pixel fisici su monitor 2K/4K con Windows scaling.
# SetProcessDpiAwareness(2) = PROCESS_PER_MONITOR_DPI_AWARE (Win 8.1+).
# Fallback a SetProcessDPIAware() per Windows 7/8.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Risoluzione canonica interna. Tutti i frame vengono normalizzati a questa
# dimensione indipendentemente dalla risoluzione nativa del gioco.
# Template, regioni e soglie sono calibrati su questo valore.
CANON = (1920, 1080)
_TARGET_RATIO = 16.0 / 9.0   # rapporto d'aspetto di riferimento

_camera = None
_camera_unavailable = False
_hwnd_cache: dict = {}


# ── Crop aspect ratio ─────────────────────────────────────────────────────────
def _crop_to_16_9(frame: np.ndarray) -> np.ndarray:
    """Ritaglia il frame al rapporto 16:9 prendendo il centro dell'immagine.

    Gestisce qualsiasi aspect ratio in ingresso:
    - Più largo di 16:9 (21:9, 32:9, ultrawide…): ritaglia i lati
    - Più stretto di 16:9 (4:3, 16:10, 5:4…): ritaglia in altezza
    - Già 16:9 (con tolleranza 2 %): restituisce una view senza allocazioni

    Il crop dal centro garantisce che la UI del gioco (sempre centrata) sia
    inclusa, indipendentemente dall'aspect ratio del monitor.
    """
    h, w = frame.shape[:2]
    if h == 0:
        return frame
    actual_ratio = w / h
    if abs(actual_ratio - _TARGET_RATIO) < 0.02:   # già ≈16:9
        return frame
    if actual_ratio > _TARGET_RATIO:
        # Più largo: ritaglia la larghezza, mantieni tutta l'altezza
        new_w = int(round(h * _TARGET_RATIO))
        x0 = (w - new_w) // 2
        return frame[:, x0:x0 + new_w]
    else:
        # Più alto: ritaglia l'altezza, mantieni tutta la larghezza
        new_h = int(round(w / _TARGET_RATIO))
        y0 = (h - new_h) // 2
        return frame[y0:y0 + new_h, :]


# ── Window helpers ────────────────────────────────────────────────────────────
def find_window(title: str) -> int:
    """Restituisce l'hwnd di una finestra visibile con quel titolo, o 0."""
    cached = _hwnd_cache.get(title)
    if cached and win32gui.IsWindow(cached):
        return cached
    matches = []

    def _collect(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if win32gui.GetWindowText(hwnd).strip() == title:
                matches.append(hwnd)

    win32gui.EnumWindows(_collect, None)
    hwnd = matches[0] if matches else 0
    if hwnd:
        _hwnd_cache[title] = hwnd
    return hwnd


def client_rect(hwnd: int):
    """Restituisce (left, top, width, height) dell'area client in pixel fisici.

    Con DPI awareness attiva i valori sono pixel fisici, quindi corretti
    su qualsiasi risoluzione e impostazione di scaling di Windows.
    """
    cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
    width, height = cr - cl, cb - ct
    sx, sy = win32gui.ClientToScreen(hwnd, (cl, ct))
    return sx, sy, width, height


def using_dxgi() -> bool:
    return _camera is not None and not _camera_unavailable


def _grab_dxgi(region):
    global _camera, _camera_unavailable
    if _camera_unavailable:
        return None
    try:
        import bettercam
        if _camera is None:
            _camera = bettercam.create(output_idx=0, output_color="BGR")
        for _ in range(5):
            frame = _camera.grab(region=region) if region else _camera.grab()
            if frame is not None:
                return np.ascontiguousarray(frame)
            time.sleep(0.008)
        return None
    except Exception:
        _camera_unavailable = True
        return None


def _grab_mss(region):
    import mss
    with mss.MSS() as sct:
        if region:
            area = {"left": region[0], "top": region[1],
                    "width": region[2] - region[0],
                    "height": region[3] - region[1]}
        else:
            area = sct.monitors[1]
        shot = sct.grab(area)
        return np.ascontiguousarray(np.array(shot)[:, :, :3])


_capture_failing = False


def grab_screen(window_title: str | None = None) -> np.ndarray:
    """Cattura e restituisce un frame BGR 1920×1080 normalizzato.

    Pipeline universale:
      1. Cattura la regione fisica della finestra (DPI-aware → corretta a
         qualsiasi risoluzione: 720p, 1080p, 2K, 4K).
      2. Ritaglia al rapporto 16:9 dal centro (_crop_to_16_9) → gestisce
         ultrawide 21:9, 32:9, monitor 4:3, 16:10, ecc.
      3. Ridimensiona a CANON 1920×1080 con INTER_AREA (qualità ottimale
         per il downscale) → template e regioni sempre validi.

    Il risultato è sempre 1920×1080 BGR indipendentemente da risoluzione
    nativa, aspect ratio del monitor e backend di cattura (DXGI o mss).
    """
    global _capture_failing
    region = None
    if window_title:
        hwnd = find_window(window_title)
        if hwnd:
            x, y, w, h = client_rect(hwnd)
            if w > 0 and h > 0:
                region = (x, y, x + w, y + h)

    frame = _grab_dxgi(region)
    if frame is None:
        try:
            frame = _grab_mss(region)
        except Exception as e:
            if not _capture_failing:
                _log.warning("cattura fallita: %s", e)
                _capture_failing = True
            frame = None

    if frame is None:
        return np.zeros((CANON[1], CANON[0], 3), dtype=np.uint8)

    if _capture_failing:
        _log.info("cattura ripristinata")
        _capture_failing = False

    # Step 2: porta a 16:9 prima di ridimensionare
    frame = _crop_to_16_9(frame)

    # Step 3: normalizza a CANON
    if (frame.shape[1], frame.shape[0]) != CANON:
        frame = cv2.resize(frame, CANON, interpolation=cv2.INTER_AREA)

    return frame


def foreground_title() -> str:
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())


def is_game_focused(expected_title: str, title_getter=foreground_title) -> bool:
    return title_getter().strip() == expected_title


def focus_window(title: str) -> bool:
    """Porta la finestra indicata in primo piano. True se riuscito."""
    hwnd = find_window(title)
    if not hwnd:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
