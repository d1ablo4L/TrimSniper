"""Log CSV degli acquisti e notifiche sonore/toast."""
from __future__ import annotations
import csv
import datetime as dt
from pathlib import Path


def log_purchase(log_path, outcome: str, loop_seconds: float,
                 total: int) -> None:
    """Aggiunge una riga al CSV degli acquisti. Scrive l'intestazione se nuovo."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                ["timestamp", "esito", "secondi_ciclo", "totale_acquistati"])
        writer.writerow([
            dt.datetime.now().isoformat(timespec="seconds"),
            outcome, f"{loop_seconds:.1f}", total,
        ])


def notify_success(car_count: int, sound: bool, toast: bool) -> None:
    """Beep + toast Windows dopo un acquisto riuscito."""
    if sound:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
    if toast:
        try:
            from win11toast import toast as show_toast
            show_toast("FH6 Sniper",
                       f"Auto acquistata ({car_count} questa sessione)")
        except Exception:
            pass
