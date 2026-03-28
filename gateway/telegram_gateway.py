# -*- coding: utf-8 -*-
"""
telegram_gateway.py — Gateway Telegram iAgent.

Reçoit les messages Telegram de l'utilisateur, les route vers claude_runner.run_session_with_search(),
renvoie la réponse. Sessions persistantes (bootstrap une seule fois).
WebSearch activé — Claude décide si une recherche est nécessaire.

Commandes :
    /audit — Audit de sécurité iAgent
    /brief — Re-analyse complète et envoi du morning brief
    /doctor — Diagnostic rapide iAgent
    /reset — Réinitialise la session Claude (nouveau bootstrap)

Usage :
    python3 gateway/telegram_gateway.py              # démarrage normal
    python3 gateway/telegram_gateway.py --dry-run     # vérification config
"""
import argparse
import logging
import re
import sys
from pathlib import Path

# Empêcher les logs httpx/httpcore d'afficher les URLs (contiennent le token bot)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_IAGENT_DIR = Path(__file__).resolve().parent.parent

# Filtre pour masquer les tokens Telegram dans tous les logs
_TOKEN_PATTERN = re.compile(r"[0-9]{8,10}:[A-Za-z0-9_-]{35}")


class _TokenFilter(logging.Filter):
    """Masque les tokens Telegram dans les messages de log."""
    def filter(self, record):
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = _TOKEN_PATTERN.sub("[TOKEN_MASQUÉ]", record.msg)
        return True

sys.path.insert(0, str(_IAGENT_DIR))

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from core.claude_runner import run_session_with_search
from core.context_builder import build as build_context
from core.env_loader import load_env, require_env
from core.session_manager import (
    get_or_create_session, force_reset, update_session_activity,
)
from core.utils.tmp_cleaner import purge_tmp
from skills.whisper.whisper_client import transcribe as whisper_transcribe
from skills.documents.document_handler import (
    extract as doc_extract, save_to_workspace as doc_save,
    cleanup as doc_cleanup, SUPPORTED_EXTENSIONS as DOC_EXTENSIONS,
)
from core.utils.brief_parser import parse_brief_response
from projects.personal_assistant.morning_brief import run_brief as _run_morning_brief
import json as _json

_logger = logging.getLogger("iagent.gateway")
_TRACKING = _IAGENT_DIR / "projects" / "personal_assistant" / "state" / "tracking.json"
_MAX_MSG_LEN = 4000
_TMP_AUDIO_DIR = _IAGENT_DIR / "tmp" / "audio"
_TMP_DOC_DIR = _IAGENT_DIR / "tmp" / "documents"

_WELCOME_MSG = "🐉☁️ Nouvelle session — iAgent prêt."


def _table_to_pre(table_lines: list[str]) -> str:
    """Convertit des lignes de table Markdown en bloc <pre> avec bordures."""
    import html as html_mod
    rows = []
    header_idx = -1
    for i, line in enumerate(table_lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Détecter la ligne séparateur (|---|---|) → marque l'en-tête
        if cells and all(re.match(r"^[-:]+$", c) for c in cells):
            header_idx = i - 1
            continue
        rows.append(cells)
    if not rows:
        return ""
    # Largeur max par colonne
    n_cols = max(len(r) for r in rows)
    widths = [0] * n_cols
    for row in rows:
        for j, cell in enumerate(row):
            if j < n_cols:
                widths[j] = max(widths[j], len(cell))
    # Ligne séparateur
    sep = "┼".join("─" * (w + 2) for w in widths)
    sep_top = "┬".join("─" * (w + 2) for w in widths)
    sep_bot = "┴".join("─" * (w + 2) for w in widths)
    # Formater
    formatted = ["┌" + sep_top + "┐"]
    for i, row in enumerate(rows):
        parts = []
        for j in range(n_cols):
            cell = row[j] if j < len(row) else ""
            parts.append(" " + cell.ljust(widths[j]) + " ")
        formatted.append("│" + "│".join(parts) + "│")
        # Séparateur après l'en-tête (row 0 si header détecté)
        if header_idx >= 0 and i == 0:
            formatted.append("├" + sep + "┤")
    formatted.append("└" + sep_bot + "┘")
    return "<pre>" + html_mod.escape("\n".join(formatted)) + "</pre>"


def _md_to_html(text: str) -> str:
    """Convertit le Markdown de Claude en HTML Telegram."""
    import html as html_mod

    # 1. Extraire les tables Markdown → <pre> aligné
    table_blocks = []
    def _collect_table(m):
        table_blocks.append(_table_to_pre(m.group(0).strip().split("\n")))
        return f"\x00TABLE{len(table_blocks)-1}\x00"
    text = re.sub(
        r"(?:^[ \t]*\|.+\|[ \t]*\n?){2,}",
        _collect_table, text, flags=re.MULTILINE,
    )

    # 2. Extraire les blocs de code
    code_blocks = []
    def _save_block(m):
        code_blocks.append(m.group(1))
        return f"\x00CODEBLOCK{len(code_blocks)-1}\x00"
    text = re.sub(r"```(?:\w*\n)?(.*?)```", _save_block, text, flags=re.DOTALL)
    inline_codes = []
    def _save_inline(m):
        inline_codes.append(m.group(1))
        return f"\x00INLINE{len(inline_codes)-1}\x00"
    text = re.sub(r"`([^`]+)`", _save_inline, text)

    # 3. Échapper HTML et convertir le formatage
    text = html_mod.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # 4. Restaurer les blocs protégés
    for i, block in enumerate(code_blocks):
        text = text.replace(f"\x00CODEBLOCK{i}\x00", f"<pre>{html_mod.escape(block)}</pre>")
    for i, code in enumerate(inline_codes):
        text = text.replace(f"\x00INLINE{i}\x00", f"<code>{html_mod.escape(code)}</code>")
    for i, table in enumerate(table_blocks):
        text = text.replace(f"\x00TABLE{i}\x00", table)
    return text


# --- Whitelist ---

def _load_whitelist() -> set[str]:
    load_env()
    chat_id = require_env("TELEGRAM_CHAT_ID_ALERTES")
    return {chat_id.strip()}


def _is_authorized(chat_id: str) -> bool:
    return chat_id in _load_whitelist()


# --- Tracking brief ---

def _load_tracking() -> dict:
    try:
        return _json.loads(_TRACKING.read_text())
    except Exception:
        return {"awaiting_response": False, "reminders": [], "renotify_mails": []}


def _save_tracking(data: dict) -> None:
    _TRACKING.write_text(_json.dumps(data, indent=2, ensure_ascii=False))


# --- Handler /audit ---

async def _handle_audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/audit — Audit de sécurité iAgent."""
    message = update.effective_message
    if not message:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return
    _logger.info("/audit | chat=%s", chat_id)
    await message.reply_text("🔒 Audit sécurité en cours...")
    import subprocess
    result = subprocess.run(
        ["bash", "scripts/security-audit.sh"],
        capture_output=True, text=True, timeout=60,
        cwd=str(_IAGENT_DIR),
    )
    output = (result.stdout + result.stderr).strip()
    # Tronquer si trop long, envoyer en chunks
    for i in range(0, len(output), 4000):
        await message.reply_text(output[i:i+4000])


# --- Handler /brief ---

async def _handle_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/brief — Re-analyse complète et envoi du morning brief."""
    message = update.effective_message
    if not message:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return
    _logger.info("/brief | chat=%s", chat_id)
    await message.reply_text("🔄 Analyse en cours...")
    try:
        _run_morning_brief()
    except Exception as e:
        _logger.error("/brief erreur : %s", e)
        await message.reply_text(f"⚠️ Erreur lors du brief : {e}")


# --- Handler /doctor ---

async def _handle_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/doctor — Diagnostic rapide iAgent."""
    message = update.effective_message
    if not message:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return
    _logger.info("/doctor | chat=%s", chat_id)
    await message.reply_text("🩺 Diagnostic en cours...")
    import subprocess
    result = subprocess.run(
        ["bash", "scripts/doctor.sh", "--quick"],
        capture_output=True, text=True, timeout=30,
        cwd=str(_IAGENT_DIR),
    )
    output = (result.stdout + result.stderr).strip()
    # Envoyer tel quel (texte brut, pas de HTML)
    await message.reply_text(output[:4000])


# --- Handler /reset ---

async def _handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return
    _logger.info("/reset | chat=%s", chat_id)
    new_id = force_reset(chat_id)
    bootstrap = build_context("telegram_session")
    response = run_session_with_search(
        prompt="Tu viens d'être réinitialisé. Présente-toi brièvement (2 lignes max).",
        session_id=new_id,
        is_new_session=True,
        bootstrap_context=bootstrap,
        timeout=90,
    )
    await message.reply_text(_WELCOME_MSG)
    if response.success:
        try:
            await message.reply_text(_md_to_html(response.text), parse_mode="HTML")
        except Exception:
            await message.reply_text(response.text)
    else:
        await message.reply_text("⚠️ Session réinitialisée mais erreur au bootstrap.")
    update_session_activity(chat_id, new_id)


# --- Traitement réponse brief ---

async def _process_brief_response(message, parsed: dict, tracking: dict) -> None:
    """Configure les rappels à partir d'une réponse brief valide."""
    from datetime import datetime, timedelta, date

    snapshot = tracking.get("brief_snapshot", {})
    events_map = {e["num"]: e for e in snapshot.get("events", [])}
    mails_map = {m["letter"]: m for m in snapshot.get("unread_mails", [])}

    new_reminders = []
    confirmed_events = []
    confirmed_mails = []

    # Traiter les événements
    for ev in parsed.get("events", []):
        event = events_map.get(ev["num"])
        if not event:
            continue
        try:
            event_dt = datetime.fromisoformat(event["datetime"])
            notify_at = event_dt - timedelta(minutes=ev["delay_min"])
            now = datetime.now()
            imminent = notify_at <= now

            if imminent:
                notify_at = now

            new_reminders.append({
                "type": "event",
                "title": event["title"],
                "time": event["time"],
                "event_datetime": event["datetime"],
                "notify_at": notify_at.isoformat(),
                "delay_min": ev["delay_min"],
                "sent": False,
            })
            delay_str = f"{ev['delay_min']}min" if ev["delay_min"] != 60 else "1h"
            note = " — imminent, rappel dans ~15min" if imminent else ""
            confirmed_events.append(f"  • {event['time']} {event['title']} (-{delay_str}{note})")
        except Exception as e:
            _logger.warning("Reminder event %d : %s", ev["num"], e)

    # Traiter les mails
    renotify = tracking.get("renotify_mails", [])
    existing_ids = {m["id"] for m in renotify}
    today = str(date.today())

    for letter in parsed.get("mails", []):
        mail = mails_map.get(letter)
        if not mail:
            continue
        if mail["id"] not in existing_ids:
            renotify.append({
                "id": mail["id"],
                "subject": mail["subject"],
                "from": mail["from"],
                "added_date": today,
                "notified_dates": [today],
            })
        confirmed_mails.append(f"  • {mail['subject']} ({mail['from']})")

    # Mettre à jour tracking
    tracking["awaiting_response"] = False
    tracking["reminders"] = tracking.get("reminders", []) + new_reminders
    tracking["renotify_mails"] = renotify
    _save_tracking(tracking)

    # Confirmer à l'utilisateur
    lines = ["✅ <b>Rappels configurés</b>"]
    if confirmed_events:
        lines.append("")
        lines.append("⏰ <b>Événements</b>")
        lines.extend(confirmed_events)
    if confirmed_mails:
        lines.append("")
        lines.append("📬 <b>Mails (rappel demain matin)</b>")
        lines.extend(confirmed_mails)
    if not confirmed_events and not confirmed_mails:
        lines = ["✅ Aucun rappel configuré."]

    try:
        await message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception:
        await message.reply_text("\n".join(lines))


# --- Handler messages ---

async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    chat_id = str(message.chat_id)
    user_text = message.text.strip()
    if not _is_authorized(chat_id):
        _logger.warning("Message ignoré — chat_id %s non autorisé", chat_id)
        return
    _logger.info("Message reçu | chat=%s | %d chars", chat_id, len(user_text))

    # Intercepter les réponses au morning brief
    tracking = _load_tracking()
    if tracking.get("awaiting_response", False):
        parsed = parse_brief_response(user_text)
        if parsed is not None:
            await _process_brief_response(message, parsed, tracking)
            return
        # Message non structuré → clore la fenêtre brief, continuer vers Claude
        tracking["awaiting_response"] = False
        _save_tracking(tracking)

    # Détecter si le message demande une transcription du prochain vocal
    text_lower = user_text.lower()
    if any(w in text_lower for w in ("transcri", "retranscri", "donne-moi le texte")):
        context.chat_data["wants_transcript"] = True

    await message.reply_text("Reçu ☁️")
    await _process_text_with_claude(message, chat_id, user_text)


async def _send_response(message, html_text: str) -> None:
    """Envoie la réponse Claude en chunks HTML avec fallback texte brut."""
    while html_text:
        chunk = html_text[:_MAX_MSG_LEN]
        html_text = html_text[_MAX_MSG_LEN:]
        try:
            await message.reply_text(chunk, parse_mode="HTML")
        except Exception:
            await message.reply_text(chunk)


async def _process_text_with_claude(
    message, chat_id: str, user_text: str, *, timeout: int = 90
) -> None:
    """Traite un texte (tapé, transcrit ou extrait d'un document) via Claude CLI."""
    session_id, is_new, reset_info = get_or_create_session(chat_id)
    if reset_info:
        await message.reply_text(f"⚠️ {reset_info}")
    if is_new:
        await message.reply_text(_WELCOME_MSG)

    bootstrap = build_context("telegram_session") if is_new else ""
    prompt = user_text if is_new else f"[Outils actifs: gog, iagent, WebSearch]\n\n{user_text}"

    response = run_session_with_search(
        prompt=prompt,
        session_id=session_id,
        is_new_session=is_new,
        bootstrap_context=bootstrap,
        timeout=timeout,
    )

    if not response.success:
        await message.reply_text(f"⚠️ Erreur : {response.error}")
        return

    await _send_response(message, _md_to_html(response.text))
    update_session_activity(chat_id, session_id)
    _logger.info(
        "Réponse envoyée | chat=%s | session=%s | %dms | new=%s",
        chat_id, session_id[:8], response.duration_ms, is_new,
    )


# --- Handler document ---

async def _handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reçoit un fichier document Telegram (PDF, DOCX).
    Extrait le texte via CLI subprocess, traite via Claude.
    """
    message = update.effective_message
    if not message or not message.document:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return

    doc = message.document
    file_name = doc.file_name or f"fichier_{doc.file_id}"
    suffix = Path(file_name).suffix.lower()

    # Vérifier format supporté
    if suffix not in DOC_EXTENSIONS:
        await message.reply_text(
            f"⚠️ Format non supporté : {suffix}\n"
            f"Formats acceptés : PDF, DOCX"
        )
        return

    _logger.info("Document reçu | chat=%s | %s | %d bytes", chat_id, file_name, doc.file_size or 0)
    await message.reply_text(f"📄 Lecture de {file_name}...")

    # Télécharger dans tmp/documents/
    _TMP_DOC_DIR.mkdir(parents=True, exist_ok=True)
    try:
        tg_file = await context.bot.get_file(doc.file_id)
    except Exception as e:
        await message.reply_text(f"⚠️ Impossible de télécharger le fichier : {e}")
        return
    tmp_path = _TMP_DOC_DIR / f"{doc.file_unique_id}_{file_name}"
    await tg_file.download_to_drive(str(tmp_path))

    # Extraire le contenu
    extraction = doc_extract(tmp_path)
    if not extraction["success"]:
        await message.reply_text(f"⚠️ Erreur de lecture : {extraction['error']}")
        doc_cleanup(tmp_path)
        return

    if not extraction["text"].strip():
        await message.reply_text("⚠️ Ce document semble ne contenir que des images — pas de texte extractible.")
        doc_cleanup(tmp_path)
        return

    # Détecter instruction de stockage dans le caption
    caption = (message.caption or "").strip()
    store_project = None
    store_match = re.search(r"(?:stock[eé]|sauvegarde)\s+dans\s+(\S+)", caption, re.IGNORECASE)
    if store_match:
        store_project = store_match.group(1)
        doc_save(tmp_path, store_project)
        await message.reply_text(f"✅ Fichier stocké dans workspace/{store_project}/")

    # Construire le prompt pour Claude
    meta = extraction["meta"]
    meta_str = ", ".join(f"{k}={v}" for k, v in meta.items())
    instruction = caption if caption and not store_match else "Fais un résumé structuré de ce document."
    truncated_note = " (contenu partiel — fichier trop long)" if extraction["truncated"] else ""

    prompt = (
        f"[Document reçu : {file_name}{truncated_note}]\n"
        f"[Métadonnées : {meta_str}]\n\n"
        f"Instruction : {instruction}\n\n"
        f"{'='*40}\n"
        f"{extraction['text']}\n"
        f"{'='*40}"
    )

    await _process_text_with_claude(message, chat_id, prompt, timeout=120)

    # Nettoyer si pas stocké
    if not store_project:
        doc_cleanup(tmp_path)

    _logger.info("Document traité | chat=%s | %s | %d chars | store=%s",
                 chat_id, file_name, meta.get("chars_original", 0), store_project)


# --- Handler vocal ---

async def _handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reçoit un message vocal Telegram.
    Transcrit via whisper, traite comme un message texte.
    """
    message = update.effective_message
    if not message or not message.voice:
        return
    chat_id = str(message.chat_id)
    if not _is_authorized(chat_id):
        return

    _logger.info("Vocal reçu | chat=%s | %ds", chat_id, message.voice.duration)
    await message.reply_text("🎙️ Transcription en cours...")

    # Télécharger le fichier vocal
    _TMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    voice = message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = _TMP_AUDIO_DIR / f"{voice.file_unique_id}.ogg"
    await file.download_to_drive(str(ogg_path))

    # Transcrire
    result = whisper_transcribe(ogg_path, cleanup=True)
    if not result["success"]:
        await message.reply_text(f"⚠️ Erreur transcription : {result['error']}")
        return

    transcribed_text = result["text"]
    _logger.info(
        "Vocal transcrit | chat=%s | lang=%s | %d chars",
        chat_id, result["language"], len(transcribed_text),
    )

    if not transcribed_text.strip():
        await message.reply_text("🔇 Audio vide ou inaudible.")
        return

    # Détecter si l'utilisateur veut la transcription explicitement
    wants_transcript = context.chat_data.get("wants_transcript", False)
    if wants_transcript:
        await message.reply_text(f"📝 <i>{transcribed_text}</i>", parse_mode="HTML")
        context.chat_data["wants_transcript"] = False
        return  # Transcription seule — pas de traitement Claude

    # Traiter comme message texte normal avec contexte vocal
    prefixed = f"[Message vocal transcrit] {transcribed_text}"
    await _process_text_with_claude(message, chat_id, prefixed)


# --- Démarrage ---

def start_gateway() -> None:
    load_env()
    purge_tmp(max_age_hours=24)
    token = require_env("TELEGRAM_BOT_TOKEN_KINTO_UN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("audit", _handle_audit))
    app.add_handler(CommandHandler("brief", _handle_brief))
    app.add_handler(CommandHandler("doctor", _handle_doctor))
    app.add_handler(CommandHandler("reset", _handle_reset))
    app.add_handler(MessageHandler(filters.Document.ALL, _handle_document))
    app.add_handler(MessageHandler(filters.VOICE, _handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    # Enregistrer le menu de commandes côté Telegram (ordre alphabétique)
    async def _post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("audit", "Audit de sécurité"),
            BotCommand("brief", "Morning brief"),
            BotCommand("doctor", "Diagnostic rapide"),
            BotCommand("reset", "Réinitialiser la session"),
        ])

    app.post_init = _post_init
    print("🚀 Gateway Telegram iAgent démarré (WebSearch + Whisper + Documents + Brief)")
    print(f"   Whitelist : {_load_whitelist()}")
    app.run_polling(drop_pending_updates=True)


def dry_run() -> None:
    load_env()
    token = require_env("TELEGRAM_BOT_TOKEN_KINTO_UN")
    whitelist = _load_whitelist()
    bootstrap = build_context("telegram_session")
    print("=== Gateway Telegram iAgent — Dry Run ===")
    print(f"Token : {'✅' if len(token) > 20 else '❌'} ({len(token)} chars)")
    print(f"Whitelist : {whitelist}")
    print(f"Bootstrap : {len(bootstrap)} chars")
    print(f"Mode : WebSearch activé (run_session_with_search)")
    import shutil
    whisper_ok = shutil.which("whisper") is not None
    print(f"Whisper : {'✅' if whisper_ok else '❌'} ({'disponible' if whisper_ok else 'absent'})")
    pdftotext_ok = shutil.which("pdftotext") is not None
    textutil_ok = shutil.which("textutil") is not None
    print(f"Documents : pdftotext={'✅' if pdftotext_ok else '❌'} textutil={'✅' if textutil_ok else '❌'}")
    tracking_ok = _TRACKING.exists()
    print(f"Brief : tracking={'✅' if tracking_ok else '❌'}")
    print("=== Config OK ===")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().addFilter(_TokenFilter())
    parser = argparse.ArgumentParser(description="Gateway Telegram iAgent")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        dry_run()
    else:
        start_gateway()
