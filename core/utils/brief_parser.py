# -*- coding: utf-8 -*-
"""
brief_parser.py — Parser et formatage pour le morning brief.

Format de réponse attendu (flexible) :
  Chiffres seuls     : "1", "1 2", "1, 2"
  Chiffre-délai      : "3-15" (event 3, rappel 15min avant)
  Lettres majuscules : "A", "A B", "A, B, C"
  Mix                : "1, 3-15, A, C"

Non reconnu → None (message normal, pas une réponse brief)
"""
import html as html_mod
import re
from datetime import date
from typing import Optional

# Token valide : chiffre seul, chiffre-délai, ou lettre (majuscule ou minuscule)
_TOKEN_PATTERN = re.compile(r"^(?:\d+(?:-\d+)?|[A-Za-z])$")
_SEPARATORS = re.compile(r"[\s,;]+")


def parse_brief_response(text: str) -> Optional[dict]:
    """
    Parse une réponse au morning brief.

    Returns :
        None si le texte n'est pas une réponse brief valide.
        dict avec clés "events" et "mails" si valide.

    Exemples :
        "1, 3-15, 4-60, A, C" →
            {"events": [{"num": 1, "delay_min": 60}, {"num": 3, "delay_min": 15},
                        {"num": 4, "delay_min": 60}],
             "mails": ["A", "C"]}
        "bitcoin" → None
    """
    text = text.strip()
    if not text:
        return None

    tokens = _SEPARATORS.split(text)
    if not tokens:
        return None

    # Tous les tokens doivent être valides
    for token in tokens:
        if not _TOKEN_PATTERN.match(token):
            return None

    events = []
    mails = []

    for token in tokens:
        if re.match(r"^\d+-\d+$", token):
            num, delay = token.split("-")
            events.append({"num": int(num), "delay_min": int(delay)})
        elif re.match(r"^\d+$", token):
            events.append({"num": int(token), "delay_min": 60})
        elif re.match(r"^[A-Za-z]$", token):
            mails.append(token.upper())

    if not events and not mails:
        return None

    return {"events": events, "mails": mails}


def format_brief_message(
    events: list,
    unread_mails: list,
    renotify_mails: list,
) -> str:
    """
    Formate le message brief Telegram en HTML.

    Args :
        events       : liste de dicts {num, title, time}
        unread_mails : liste de dicts {letter, subject, from}
        renotify_mails : liste de dicts {subject, from, notified_dates}
    """
    import locale
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        pass  # Fallback si locale absente
    today = date.today().strftime("%A %d %B %Y").capitalize()
    lines = [
        f"☁️ {today} — on fait le point.",
    ]

    # Numérotation continue pour les mails (après les events)
    next_letter_idx = 0
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Agenda
    lines.append("")
    if events:
        lines.append("📅 <b>Agenda</b>")
        for e in events:
            lines.append(f"  {e['num']}. {e['time']} — {html_mod.escape(e['title'])}")
    else:
        lines.append("📅 <b>Agenda</b> — rien aujourd'hui")

    # Mails non lus (nouveaux)
    lines.append("")
    if unread_mails:
        lines.append(f"📬 <b>Nouveaux mails non lus</b>")
        for m in unread_mails:
            sender = html_mod.escape(m["from"])
            subject = html_mod.escape(m["subject"])
            lines.append(f"  {m['letter']}. {sender}")
            lines.append(f"      <i>{subject}</i>")
            next_letter_idx = max(next_letter_idx, letters.index(m["letter"]) + 1)
    else:
        lines.append("📬 <b>Mails</b> — aucun nouveau mail non lu")

    # Rappels mails (re-notifiés)
    if renotify_mails:
        lines.append("")
        lines.append("👀 <b>Rappel mails non lus</b>")
        for m in renotify_mails:
            days = len(m.get("notified_dates", []))
            letter = letters[next_letter_idx] if next_letter_idx < len(letters) else "?"
            next_letter_idx += 1
            sender = html_mod.escape(m["from"])
            subject = html_mod.escape(m["subject"])
            lines.append(f"  {letter}. {sender} — J+{days}")
            lines.append(f"      <i>{subject}</i>")

    # Instructions réponse
    if events or unread_mails or renotify_mails:
        lines.append("")
        lines.append("──────────────────")
        lines.append("🤝 Tu veux un rappel ? Réponds :")

        if events and len(events) >= 3:
            e1, e2, e3 = events[0]["num"], events[1]["num"], events[2]["num"]
            lines.append(
                f"<code>{e1}, {e2}, {e3}-30</code>"
                f" → rappel 1h avant pour {e1} et {e2},"
                f" 30min avant pour {e3}"
            )
        elif events and len(events) == 2:
            e1, e2 = events[0]["num"], events[1]["num"]
            lines.append(
                f"<code>{e1}, {e2}-30</code>"
                f" → rappel 1h avant pour {e1},"
                f" 30min avant pour {e2}"
            )
        elif events:
            lines.append(
                f"<code>{events[0]['num']}</code>"
                " → rappel 1h avant (ou -Nmin)"
            )
        if unread_mails:
            sample = ", ".join(m["letter"] for m in unread_mails[:3])
            lines.append(
                f"<code>{sample}</code>"
                f" → relance pour {sample} demain matin"
                " si toujours non lus"
            )

    return "\n".join(lines)
