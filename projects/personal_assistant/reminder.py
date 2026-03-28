# -*- coding: utf-8 -*-
"""
reminder.py — Cron toutes les 15min.

Vérifie tracking.json et envoie les rappels dus.
Silencieux si rien à envoyer.

Déclenché par : com.iagent.reminder.plist (StartInterval 900s)
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_IAGENT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_IAGENT_DIR))

from core.env_loader import load_env
from skills.telegram.telegram_client import get_alerts_client

_logger = logging.getLogger("iagent.reminder")
_TRACKING = _IAGENT_DIR / "projects" / "personal_assistant" / "state" / "tracking.json"


def _load_tracking() -> dict:
    try:
        return json.loads(_TRACKING.read_text())
    except Exception:
        return {"reminders": []}


def _save_tracking(data: dict) -> None:
    _TRACKING.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _send_telegram(text: str) -> bool:
    """Envoie un message Telegram via le skill telegram (requests)."""
    try:
        client = get_alerts_client()
        result = client.send_message(text)
        return result.get("ok", False)
    except Exception as e:
        _logger.error("Telegram error : %s", e)
        return False


def run_reminders() -> None:
    """Vérifie et envoie les rappels dus."""
    load_env()

    tracking = _load_tracking()
    reminders = tracking.get("reminders", [])
    now = datetime.now()
    modified = False

    for reminder in reminders:
        if reminder.get("sent", False):
            continue

        notify_at_str = reminder.get("notify_at", "")
        if not notify_at_str:
            continue

        try:
            notify_at = datetime.fromisoformat(notify_at_str)
        except ValueError:
            continue

        if now >= notify_at:
            # Calculer le délai restant réel
            event_dt_str = reminder.get("event_datetime", "")
            delay_note = ""
            if event_dt_str:
                try:
                    event_dt = datetime.fromisoformat(event_dt_str)
                    minutes_left = int((event_dt - now).total_seconds() / 60)
                    if minutes_left > 0:
                        delay_note = f" (dans {minutes_left} min)"
                    else:
                        delay_note = " (maintenant)"
                except Exception:
                    pass

            title = reminder.get("title", "Événement")
            time_str = reminder.get("time", "")
            message = (
                f"⏰ <b>Rappel</b> : {title}"
                f"{f' à {time_str}' if time_str else ''}"
                f"{delay_note}"
            )

            sent = _send_telegram(message)
            if sent:
                reminder["sent"] = True
                modified = True
                _logger.info("Rappel envoyé : %s", title)
            else:
                _logger.error("Échec envoi rappel : %s", title)

    if modified:
        # Nettoyer les reminders envoyés
        tracking["reminders"] = [
            r for r in reminders if not r.get("sent", False)
        ]
        _save_tracking(tracking)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(message)s",
    )
    run_reminders()
