# -*- coding: utf-8 -*-
"""
morning_brief.py — Envoi quotidien du brief matinal à 7h45.

Workflow :
  1. Nettoyer les renotify_mails lus (via gog)
  2. Récupérer l'agenda du jour (gog calendar)
  3. Récupérer les mails non lus 7j (gog gmail)
  4. Formater et envoyer via Telegram
  5. Mettre à jour tracking.json (awaiting_response: true)

Déclenché par : com.iagent.morning_brief.plist (07h45)
Ou manuellement : python3 tasks/morning_brief.py
Ou via /brief dans Telegram
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

_IAGENT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_IAGENT_DIR))

from core.env_loader import load_env, require_env
from core.utils.brief_parser import format_brief_message
from skills.telegram.telegram_client import get_alerts_client

_logger = logging.getLogger("iagent.morning_brief")
_TRACKING = _IAGENT_DIR / "projects" / "personal_assistant" / "state" / "tracking.json"


def _load_tracking() -> dict:
    """Charge le fichier de suivi."""
    try:
        return json.loads(_TRACKING.read_text())
    except Exception:
        return {
            "date": "", "awaiting_response": False,
            "brief_snapshot": {"events": [], "unread_mails": []},
            "reminders": [], "renotify_mails": [],
        }


def _save_tracking(data: dict) -> None:
    """Sauvegarde le fichier de suivi."""
    _TRACKING.parent.mkdir(parents=True, exist_ok=True)
    _TRACKING.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _run_gog(args: list, timeout: int = 30) -> dict:
    """Exécute une commande gog et retourne le JSON parsé."""
    try:
        result = subprocess.run(
            ["gog"] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()[:200]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout gog"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON invalide : {e}"}
    except Exception as e:
        return {"error": str(e)}


def _get_events() -> list:
    """
    Récupère les événements du jour via gog calendar.
    Exclut les événements déjà passés et les événements journée entière.
    """
    raw = _run_gog(["calendar", "list", "--all", "--days", "1", "--json"])
    if "error" in raw:
        _logger.error("gog calendar : %s", raw["error"])
        return []

    now = datetime.now()
    events = []
    num = 1

    # Structure gog : {"events": [{summary, start: {dateTime|date}, id, ...}]}
    items = raw.get("events", [])
    for item in items:
        start = item.get("start", {})
        # Événement avec heure précise (pas journée entière)
        dt_str = start.get("dateTime", "")
        if not dt_str:
            continue  # Journée entière → ignorer

        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            dt_local = dt.astimezone().replace(tzinfo=None)

            # Exclure les événements passés
            if dt_local < now:
                continue

            events.append({
                "num": num,
                "title": item.get("summary", "Sans titre"),
                "time": dt_local.strftime("%H:%M"),
                "datetime": dt_local.isoformat(),
                "id": item.get("id", f"evt_{num}"),
            })
            num += 1
        except Exception as e:
            _logger.warning("Événement ignoré : %s", e)

    return events


def _get_unread_mails(existing_renotify_ids: set) -> list:
    """
    Récupère les mails non lus des 7 derniers jours via gog gmail.
    Exclut les mails déjà dans renotify_mails.
    """
    raw = _run_gog([
        "gmail", "search", "is:unread newer_than:7d",
        "--max", "20", "--json",
    ])
    if "error" in raw:
        _logger.error("gog gmail : %s", raw["error"])
        return []

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    mails = []
    idx = 0

    # Structure gog : {"threads": [{id, date, from, subject, labels, ...}]}
    # gog retourne les plus récents en premier — conserver cet ordre (plus récent → plus ancien)
    items = list(raw.get("threads", []))
    for item in items:
        if idx >= len(letters):
            break
        mail_id = item.get("id", "")
        if mail_id in existing_renotify_ids:
            continue
        mails.append({
            "letter": letters[idx],
            "subject": item.get("subject", "Sans objet")[:80],
            "from": item.get("from", "?")[:40],
            "id": mail_id,
        })
        idx += 1

    return mails


def _check_mail_read(thread_id: str) -> bool:
    """
    Vérifie si un thread est lu via gog gmail thread.
    L'ID stocké est un thread ID (retourné par gog gmail search).
    Retourne True si lu (ou introuvable → considéré traité).
    """
    raw = _run_gog(["gmail", "thread", thread_id, "--json"])
    if "error" in raw:
        return True  # Introuvable → considéré traité
    # Structure gog : {"thread": {"messages": [{labelIds: [...]}]}}
    messages = raw.get("thread", {}).get("messages", [])
    if not messages:
        return True
    label_ids = messages[0].get("labelIds", [])
    return "UNREAD" not in label_ids


def _clean_renotify_mails(renotify_mails: list) -> tuple[list, list]:
    """
    Vérifie chaque mail en renotify : supprime les lus et ceux > 7 jours.
    """
    today = date.today()
    kept = []
    removed = []

    for m in renotify_mails:
        added = date.fromisoformat(m.get("added_date", str(today)))
        days_old = (today - added).days

        if days_old > 7:
            _logger.info("Renotify expiré (>7j) : %s", m["subject"])
            removed.append(m)
            continue

        if _check_mail_read(m["id"]):
            _logger.info("Mail lu → supprimé du renotify : %s", m["subject"])
            removed.append(m)
            continue

        m.setdefault("notified_dates", [])
        if str(today) not in m["notified_dates"]:
            m["notified_dates"].append(str(today))
        kept.append(m)

    return kept, removed


def _send_telegram(text: str) -> bool:
    """Envoie un message Telegram via le skill telegram (requests)."""
    try:
        client = get_alerts_client()
        result = client.send_message(text)
        return result.get("ok", False)
    except Exception as e:
        _logger.error("Telegram send error : %s", e)
        return False


def run_brief() -> None:
    """Point d'entrée principal — exécuté à 7h45 ou via /brief."""
    load_env()
    _logger.info("Morning brief démarré")
    tracking = _load_tracking()

    # 1. Nettoyer les renotify_mails lus
    renotify_mails, removed = _clean_renotify_mails(
        tracking.get("renotify_mails", [])
    )
    if removed:
        _logger.info("%d mail(s) supprimé(s) du renotify", len(removed))

    # 2. IDs déjà en renotify
    existing_ids = {m["id"] for m in renotify_mails}

    # 3. Récupérer agenda et mails frais
    events = _get_events()
    unread_mails = _get_unread_mails(existing_ids)

    _logger.info(
        "%d événement(s), %d mail(s) non lus, %d renotify actif(s)",
        len(events), len(unread_mails), len(renotify_mails),
    )

    # 4. Formater et envoyer
    message = format_brief_message(events, unread_mails, renotify_mails)
    sent = _send_telegram(message)

    if not sent:
        _logger.error("Échec envoi brief Telegram")
        return

    # 5. Mettre à jour tracking.json
    tracking.update({
        "date": str(date.today()),
        "awaiting_response": True,
        "brief_snapshot": {
            "events": events,
            "unread_mails": unread_mails,
        },
        "renotify_mails": renotify_mails,
        "reminders": [
            r for r in tracking.get("reminders", [])
            if not r.get("sent", False)
        ],
    })
    _save_tracking(tracking)
    _logger.info("Brief envoyé, awaiting_response=True")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(message)s",
    )
    run_brief()
