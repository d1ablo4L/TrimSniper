"""Screen identification: template matching e rilevamento universale SDR/HDR."""
from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
import cv2
import numpy as np


class Screen(Enum):
    UNKNOWN = auto()
    SEARCH_CONFIG = auto()
    RESULTS_HAS_CARS = auto()
    RESULTS_EMPTY = auto()
    AUCTION_OPTIONS = auto()
    PLAYER_OPTIONS = auto()
    BUY_OUT = auto()
    BUYOUT_PROGRESS = auto()
    BUYOUT_SUCCESS = auto()
    BUYOUT_FAILED = auto()
    CLAIM_CAR = auto()
    AH_LANDING = auto()


TEMPLATE_SCREENS: dict[str, Screen] = {
    "search.png": Screen.SEARCH_CONFIG,
    "auction_details.png": Screen.RESULTS_HAS_CARS,
    "no_auctions.png": Screen.RESULTS_EMPTY,
    "auction_options.png": Screen.AUCTION_OPTIONS,
    "player_options.png": Screen.PLAYER_OPTIONS,
    "buy_out.png": Screen.BUY_OUT,
    "buy_out_bgoff.png": Screen.BUY_OUT,
    "buy_out_progress.png": Screen.BUYOUT_PROGRESS,
    "buy_out_progress_bgoff.png": Screen.BUYOUT_PROGRESS,
    "buyout_successful.png": Screen.BUYOUT_SUCCESS,
    "buyout_failed.png": Screen.BUYOUT_FAILED,
    "claim_car.png": Screen.CLAIM_CAR,
    "ah_landing.png": Screen.AH_LANDING,
}


# ── Utility HSV (mantenuta per compatibilità) ─────────────────────────────────
def lime_mask(bgr: np.ndarray, lower, upper) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))


def largest_lime_bbox(bgr, lower, upper):
    """Bounding box della più grande regione lime a forma di banner, o None."""
    mask = lime_mask(bgr, lower, upper)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 2000:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if h <= 0 or w / h < 4.0:
            continue
        if area > best_area:
            best_area = area
            best = (x, y, w, h)
    return best


# ── Template matching ─────────────────────────────────────────────────────────
def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def match_template(scene: np.ndarray, template: np.ndarray) -> float:
    """Miglior punteggio NCC del template nella scena. 0.0 se il template è troppo grande."""
    s, t = _gray(scene), _gray(template)
    if t.shape[0] > s.shape[0] or t.shape[1] > s.shape[1]:
        return 0.0
    result = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


_DOWNSCALED_TEMPLATES: dict[int, np.ndarray] = {}


def _small(tmpl: np.ndarray) -> np.ndarray:
    key = id(tmpl)
    cached = _DOWNSCALED_TEMPLATES.get(key)
    if cached is None:
        cached = _downscale(tmpl)
        _DOWNSCALED_TEMPLATES[key] = cached
    return cached


def load_templates(template_dir, moving_background: bool = True) -> dict:
    """Carica ogni template di rilevamento in scala di grigi.
    Lancia FileNotFoundError se un template obbligatorio manca.

    Il matching avviene sempre su frame normalizzati a 1920×1080, quindi
    i template a 1080p funzionano per qualsiasi risoluzione di gioco.
    """
    out = {}
    for name in TEMPLATE_SCREENS:
        is_bgoff = name.endswith("_bgoff.png")
        if moving_background and is_bgoff:
            continue
        if not moving_background and _has_bgoff_variant(name):
            continue
        path = Path(template_dir) / name
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"template mancante: {path}")
        gray = _gray(img)
        out[name] = gray
        _DOWNSCALED_TEMPLATES[id(gray)] = _downscale(gray)
    return out


def _has_bgoff_variant(name: str) -> bool:
    if name.endswith("_bgoff.png"):
        return False
    sibling = name[:-len(".png")] + "_bgoff.png"
    return sibling in TEMPLATE_SCREENS


_RESULTS_PRIORITY = ("auction_details.png", "no_auctions.png")
_MATCH_SCALE = 0.5


def _downscale(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, None, fx=_MATCH_SCALE, fy=_MATCH_SCALE,
                      interpolation=cv2.INTER_AREA)


TEMPLATE_REGIONS = {
    "search.png":                (472, 223, 1448, 471),
    "auction_details.png":       (889,  64, 1920, 294),
    "no_auctions.png":           (1113, 434, 1706, 690),
    "auction_options.png":       (546, 276, 1374, 526),
    "player_options.png":        (580, 230, 1340, 486),
    "buy_out.png":               (520, 470, 1400, 620),
    "buy_out_bgoff.png":         (520, 470, 1400, 620),
    "buy_out_progress.png":      (520, 470, 1400, 620),
    "buy_out_progress_bgoff.png":(520, 470, 1400, 620),
    "buyout_successful.png":     (539, 334, 1374, 612),
    "buyout_failed.png":         (546, 378, 1374, 631),
    "claim_car.png":             (538, 359, 1374, 615),
    "ah_landing.png":            (16,   89,  387, 291),
}

_FULL_RES_TEMPLATES = {
    "buy_out.png", "buy_out_bgoff.png",
    "buy_out_progress.png", "buy_out_progress_bgoff.png",
}


def screen_scores(scene_bgr, templates: dict, targets=None) -> dict:
    """Punteggio di matching per template, crop-regione.
    Il matching in scala di grigi è già indipendente da SDR/HDR e risoluzione.
    """
    if targets is not None:
        wanted = set(_RESULTS_PRIORITY)
        wanted |= {n for n, scr in TEMPLATE_SCREENS.items() if scr in targets}
        templates = {n: t for n, t in templates.items() if n in wanted}
    gray = _gray(scene_bgr)
    h, w = gray.shape[:2]
    scores = {}
    for name, tmpl in templates.items():
        region = TEMPLATE_REGIONS.get(name)
        if region:
            x1, y1, x2, y2 = region
            crop = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            crop = gray
        if name in _FULL_RES_TEMPLATES:
            scores[name] = match_template(crop, tmpl)
        else:
            scores[name] = match_template(_downscale(crop), _small(tmpl))
    return scores


def identify_screen(scene_bgr, templates: dict, threshold: float,
                    targets=None) -> Screen:
    scores = screen_scores(scene_bgr, templates, targets=targets)
    for name in _RESULTS_PRIORITY:
        if scores.get(name, 0.0) >= threshold:
            return TEMPLATE_SCREENS[name]
    best_screen, best_score = Screen.UNKNOWN, threshold
    for name, score in scores.items():
        if score >= best_score:
            best_screen, best_score = TEMPLATE_SCREENS[name], score
    return best_screen


# ── Rilevamento pulsante Conferma ─────────────────────────────────────────────
CONFIRM_ROW = (548, 714, 1372, 772)

# Soglie basate sul canale V (luminosità) invece di un hue specifico.
# Il pulsante evidenziato — lime in SDR, o qualsiasi colore brillante in HDR —
# ha sempre luminosità V significativamente maggiore dello sfondo UI scuro.
# Funziona per SDR, HDR, qualsiasi temperatura colore e gamma display.
_CONFIRM_V_THRESH  = 130   # soglia canale V: pixel "acceso"
_CONFIRM_V_COUNT   = 500   # numero minimo di pixel accesi per considerarlo evidenziato


def is_confirm_highlighted(scene_bgr, region=CONFIRM_ROW) -> bool:
    """True se il pulsante Conferma è evidenziato.

    Usa il canale V (luminosità) dell'HSV: il pulsante evidenziato è sempre
    molto più luminoso dello sfondo UI scuro, indipendentemente dal color
    space (SDR/HDR), dalla risoluzione o dalla calibrazione del display.
    Non richiede template aggiuntivi.
    """
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    v = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]
    _, bright = cv2.threshold(v, _CONFIRM_V_THRESH, 255, cv2.THRESH_BINARY)
    return int(cv2.countNonZero(bright)) > _CONFIRM_V_COUNT


# ── Rilevamento timbro SOLD ───────────────────────────────────────────────────
SOLD_STAMP_REGION = (90, 185, 300, 295)

# Approccio universale SDR/HDR: cerca pixel con alta saturazione E alta
# luminosità (colore vivace). In SDR il timbro è giallo acceso (H≈28,
# S≈255, V≈220). In HDR il tone-mapping può spostare H e abbassare S/V,
# ma il timbro rimane comunque un colore saturo e luminoso rispetto allo
# sfondo grigio-scuro della card. Non dipende dall'hue specifico.
_SOLD_S_THRESH     = 55    # saturazione minima: esclude grigi e sfondo scuro
_SOLD_V_THRESH     = 80    # luminosità minima: esclude aree in ombra
_SOLD_PIXEL_COUNT  = 800   # pixel colorati+luminosi necessari per "SOLD"

SOLD_STAMP_REGIONS = (
    SOLD_STAMP_REGION,
    (90, 387, 300, 497),
    (90, 589, 300, 699),
    (90, 791, 300, 901),
)


def is_card_sold(scene_bgr, region=SOLD_STAMP_REGION) -> bool:
    """True se la prima card mostra il timbro SOLD.

    Rileva qualsiasi colore vivace (S alta + V alta) nella regione del timbro.
    Funziona in SDR (giallo acceso) e HDR (giallo/arancio tone-mappato),
    indipendentemente da risoluzione e impostazioni display.
    """
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    hsv  = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([0, _SOLD_S_THRESH, _SOLD_V_THRESH], np.uint8),
        np.array([179, 255, 255], np.uint8))
    return int(cv2.countNonZero(mask)) > _SOLD_PIXEL_COUNT


def sold_slots(scene_bgr) -> tuple:
    """Flag SOLD per ognuno dei quattro slot risultato.
    Universale SDR/HDR: vedi is_card_sold.
    """
    hsv  = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([0, _SOLD_S_THRESH, _SOLD_V_THRESH], np.uint8),
        np.array([179, 255, 255], np.uint8))
    return tuple(int(cv2.countNonZero(mask[y1:y2, x1:x2])) > _SOLD_PIXEL_COUNT
                 for (x1, y1, x2, y2) in SOLD_STAMP_REGIONS)


def first_buyable_slot(scene_bgr) -> int:
    """Primo slot non-SOLD (indice 1), o 0 se tutti e quattro sono venduti.
    Universale SDR/HDR.
    """
    for i, sold in enumerate(sold_slots(scene_bgr), start=1):
        if not sold:
            return i
    return 0
