"""Macchina a stati dello sniper e wrapper GameIO usato dai test."""
from __future__ import annotations
import logging
import random
import time
from . import actions, capture, vision
from .vision import Screen

log = logging.getLogger("fh6.sniper")


def _names(screens) -> str:
    return "{" + ", ".join(sorted(s.name for s in screens)) + "}"


class GameIO:
    """Connessione tra cattura + visione + input. Sostituibile per i test.

    Le funzioni di rilevamento colore (confirm_highlighted, card_sold,
    first_buyable_slot) usano il nuovo sistema universale di vision.py
    basato su luminosità e saturazione relativa: non richiedono parametri
    HSV specifici per SDR o HDR, quindi GameIO non ha più bisogno di
    distinguere le due modalità.
    """

    def __init__(self, cfg, templates):
        self.cfg = cfg
        self.templates = templates
        self._last_screen = None

    def screen(self, targets=None) -> Screen:
        """Identifica lo schermo corrente."""
        if (targets is not None and self._last_screen is not None
                and self._last_screen != Screen.UNKNOWN):
            targets = targets | {self._last_screen}
        frame = capture.grab_screen(self.cfg.window_title)
        result = vision.identify_screen(
            frame, self.templates, self.cfg.match_threshold, targets=targets)
        if result != self._last_screen:
            log.info("schermo -> %s", result.name)
            self._last_screen = result
        return result

    def focused(self) -> bool:
        return capture.is_game_focused(self.cfg.window_title)

    def confirm_highlighted(self) -> bool:
        """True se il pulsante Conferma è evidenziato (SDR, HDR, qualsiasi display)."""
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.is_confirm_highlighted(frame)

    def card_sold(self) -> bool:
        """True se la prima card mostra il timbro SOLD (SDR, HDR, qualsiasi display)."""
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.is_card_sold(frame)

    def first_buyable_slot(self) -> int:
        """Primo slot acquistabile, 0 se tutti venduti (SDR, HDR, qualsiasi display)."""
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.first_buyable_slot(frame)

    def press(self, name: str, times: int = 1) -> None:
        log.info("premi %s%s", name, f" x{times}" if times > 1 else "")
        actions.tap_key(name, times,
                        self.cfg.key_hold_ms, self.cfg.between_keys_ms)


class Sniper:
    """Gestisce il loop della casa d'aste tramite un GameIO."""

    def __init__(self, io, cfg, clock=time.monotonic, sleeper=time.sleep,
                 on_purchase=None, on_status=None, on_stats=None):
        self.io = io
        self.cfg = cfg
        self.clock = clock
        self.sleeper = sleeper
        self.on_purchase = on_purchase
        self.on_status = on_status
        self.on_stats = on_stats
        self.cars_bought    = 0
        self.searches       = 0
        self.failed_buyouts = 0
        self.started_at     = None
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def _status(self, text: str) -> None:
        log.info("[stato] %s", text)
        if self.on_status:
            self.on_status(text)

    def _emit_stats(self) -> None:
        if self.on_stats:
            self.on_stats(self.searches, self.cars_bought,
                          self.failed_buyouts)

    def _poll_delay(self) -> None:
        lo, hi = self.cfg.poll_interval_ms
        self.sleeper(random.uniform(lo, hi) / 1000.0)

    def _guard_focus(self) -> None:
        if self.io.focused():
            return
        self._status("In pausa: FH6 non in primo piano")
        while not self.io.focused():
            if self._stop:
                return
            self.sleeper(0.5)

    def _press(self, name: str, times: int = 1) -> None:
        self._guard_focus()
        if self._stop:
            return
        self.io.press(name, times)

    def wait_for(self, screens: set, timeout: float):
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if self._stop:
                return None
            before = self.clock()
            self._guard_focus()
            if self._stop:
                return None
            deadline += self.clock() - before
            current = self.io.screen(targets=screens)
            if current in screens:
                log.info("attesa %s -> %s", _names(screens), current.name)
                return current
            self._poll_delay()
        log.info("attesa %s -> TIMEOUT dopo %.0fs", _names(screens), timeout)
        return None

    def _press_until(self, key, from_screen, targets,
                     settle: float = 0.7, reach: float = 8.0,
                     attempts: int = 4):
        inner_targets = targets | {from_screen}
        for _ in range(attempts):
            if self._stop:
                return None
            self._press(key)
            deadline = self.clock() + settle
            while self.clock() < deadline:
                if self._stop:
                    return None
                s = self.io.screen(targets=inner_targets)
                if s in targets:
                    return s
                if s != from_screen:
                    return self.wait_for(targets, reach)
                self._poll_delay()
        return None

    def _goto_search_config(self) -> bool:
        s = self.io.screen()
        for _ in range(10):
            if self._stop:
                return False
            if s == Screen.SEARCH_CONFIG:
                return True
            if s == Screen.AH_LANDING:
                return self._enter_search_from_landing(known=s)
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._press("esc")
            s = self._await_settle(prev=s)
        self._status("Perso: avvia il bot nella Casa d'Aste")
        return False

    def _enter_search_from_landing(self, known=None) -> bool:
        self._status("Apertura Ricerca Aste")
        for attempt in range(1, 5):
            if self._stop:
                return False
            s = known if known is not None else self.io.screen()
            known = None
            log.info("entra_ricerca tentativo %d: schermo=%s", attempt, s.name)
            if s == Screen.SEARCH_CONFIG:
                return True
            if s == Screen.UNKNOWN:
                self.sleeper(0.6)
                continue
            if s != Screen.AH_LANDING:
                self._press("esc")
                self.sleeper(0.3)
                continue
            self.sleeper(0.2)
            self._press("enter")
            if self.wait_for({Screen.SEARCH_CONFIG}, 0.9) is not None:
                return True
        log.info("entra_ricerca: abbandonato dopo 4 tentativi")
        return False

    def _navigate_to_confirm(self) -> bool:
        for _ in range(12):
            if self._stop:
                return False
            if self.io.confirm_highlighted():
                return True
            self._press("down")
        return self.io.confirm_highlighted()

    def _recover(self) -> str:
        unknown_streak = 0
        s = self.io.screen()
        for _ in range(14):
            if self._stop:
                return "recover_failed"
            if s in (Screen.SEARCH_CONFIG, Screen.AH_LANDING):
                log.info("recupero: raggiunto %s", s.name)
                return "recovered"
            if s == Screen.UNKNOWN:
                unknown_streak += 1
                if unknown_streak >= 4:
                    self._press("esc")
                    unknown_streak = 0
                    s = self._await_settle(prev=s)
                    continue
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            unknown_streak = 0
            self._press("esc")
            s = self._await_settle(prev=s)
        log.info("recupero: abbandonato")
        return "recover_failed"

    def _await_settle(self, prev, timeout: float = 1.2):
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if self._stop:
                return Screen.UNKNOWN
            self._poll_delay()
            s = self.io.screen()
            if s != Screen.UNKNOWN and s != prev:
                return s
        return Screen.UNKNOWN

    def _back_to_landing(self, known=None) -> None:
        s = known if known is not None else self.io.screen()
        for _ in range(6):
            if self._stop:
                return
            if s == Screen.AH_LANDING:
                return
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._press("esc")
            s = self._await_settle(prev=s)

    def _escape_player_options(self) -> str:
        self._status("Annuncio già venduto, salto")
        for _ in range(6):
            if self._stop:
                return "recover_failed"
            if self.io.screen() == Screen.AH_LANDING:
                return "no_cars"
            self._press("esc")
            self.sleeper(0.6)
        return "no_cars"

    def _collect(self) -> None:
        self._status("Ritiro dell'auto in corso")
        if self._press_until("y", Screen.RESULTS_HAS_CARS,
                             {Screen.AUCTION_OPTIONS}) is None:
            return
        if self._press_until("enter", Screen.AUCTION_OPTIONS,
                             {Screen.CLAIM_CAR}) is None:
            return
        deadline = self.clock() + self.cfg.timeout_claim_s
        while self.clock() < deadline:
            if self._stop:
                return
            s = self.io.screen()
            if s == Screen.CLAIM_CAR:
                self._press("enter")
                self.sleeper(1.0)
            elif s == Screen.UNKNOWN:
                self.sleeper(0.3)
            else:
                return

    def run_once(self) -> str:
        log.info("--- run_once ---")
        cfg = self.cfg
        if not self._goto_search_config():
            return "recover_failed"

        self._status("Ricerca in corso")
        if not self._navigate_to_confirm():
            return self._recover()
        result = self._press_until(
            "enter", Screen.SEARCH_CONFIG,
            {Screen.RESULTS_HAS_CARS, Screen.RESULTS_EMPTY})
        if result is not Screen.RESULTS_HAS_CARS:
            self._back_to_landing(known=result)
            return "no_cars"

        slot = self.io.first_buyable_slot()
        if slot == 0:
            self._status("Tutti gli annunci venduti, salto")
            self._back_to_landing(known=result)
            return "no_cars"

        self._status("Auto trovata, acquisto immediato")
        for _ in range(slot - 1):
            self._press("down")

        if slot > 1 and self.io.first_buyable_slot() != slot:
            self._status("Annuncio venduto durante la navigazione, salto")
            self._back_to_landing(known=result)
            return "no_cars"

        seen = self._press_until(
            "y", Screen.RESULTS_HAS_CARS,
            {Screen.AUCTION_OPTIONS, Screen.PLAYER_OPTIONS})
        if seen == Screen.PLAYER_OPTIONS:
            return self._escape_player_options()
        if seen is None:
            return self._recover()

        self._press("down")
        if cfg.buyout_select_delay_ms:
            self.sleeper(cfg.buyout_select_delay_ms / 1000.0)
        self._press("enter")
        seen = self.wait_for({Screen.BUY_OUT, Screen.PLAYER_OPTIONS}, 2.5)
        if seen == Screen.PLAYER_OPTIONS:
            return self._escape_player_options()
        if seen is None:
            return self._recover()

        outcome = None
        for _ in range(4):
            if self._stop:
                return self._recover()
            self._press("enter")
            seen = self.wait_for(
                {Screen.BUYOUT_PROGRESS,
                 Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED}, 0.7)
            if seen in (Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED):
                outcome = seen
                break
            if seen == Screen.BUYOUT_PROGRESS:
                outcome = self.wait_for(
                    {Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED},
                    cfg.timeout_outcome_s)
                break
        if outcome is None:
            return self._recover()

        self._press("enter")

        if outcome == Screen.BUYOUT_FAILED:
            self._back_to_landing()
            return "failed"

        if cfg.collect_after_buyout:
            self._collect()
        self._back_to_landing()
        return "bought"

    def _auto_stop_reached(self) -> bool:
        cfg = self.cfg
        if not cfg.auto_stop_enabled:
            return False
        if self.cars_bought >= cfg.max_cars:
            return True
        elapsed_min = (self.clock() - self.started_at) / 60.0
        return elapsed_min >= cfg.max_minutes

    def run(self) -> str:
        self.started_at = self.clock()
        log.info("=== sniper avviato ===")
        self._status("In esecuzione")
        while not self._stop:
            if self._auto_stop_reached():
                self._status("Limite auto-stop raggiunto")
                return "auto_stop"
            self._guard_focus()
            if self._stop:
                break
            t0 = self.clock()
            outcome = self.run_once()
            log.info("esito run_once: %s", outcome)
            self.searches += 1
            if outcome == "recover_failed":
                self._emit_stats()
                self._status("Fermato: impossibile recuperare")
                return "recover_failed"
            if outcome == "failed":
                self.failed_buyouts += 1
            if outcome == "bought":
                self.cars_bought += 1
                loop_s = self.clock() - t0
                self._status(f"Acquistata/e {self.cars_bought} auto")
                if self.on_purchase:
                    self.on_purchase(loop_s, self.cars_bought)
            self._emit_stats()
            self.sleeper(self.cfg.loop_pace_s)
        self._status("Fermato")
        return "stopped"
