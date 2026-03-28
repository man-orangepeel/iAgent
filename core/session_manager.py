# -*- coding: utf-8 -*-
"""
session_manager.py — Gestion des sessions Telegram persistantes.

Stocke le mapping chat_id → session_id dans data/sessions.json.
Réinitialisation automatique si les DEUX conditions sont remplies :
  - (now - last_active) > TTL_HOURS
  - taille JSONL > MAX_SIZE_KB
Réinitialisation manuelle via force_reset().

Usage :
    from core.session_manager import get_or_create_session, force_reset
    session_id, is_new, info = get_or_create_session("CHAT_ID")
"""
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from core.config import get_config

_IAGENT_DIR = Path(__file__).resolve().parent.parent
_SESSIONS_FILE = _IAGENT_DIR / "data" / "sessions.json"

# Chemin des sessions Claude CLI
_CLAUDE_SESSIONS_DIR = (
    Path.home() / ".claude" / "projects"
    / str(_IAGENT_DIR).replace("/", "-").lstrip("-")
)


def _load_sessions() -> dict:
    if not _SESSIONS_FILE.exists():
        return {}
    return json.loads(_SESSIONS_FILE.read_text(encoding="utf-8"))


def _save_sessions(data: dict) -> None:
    _SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=_SESSIONS_FILE.parent)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SESSIONS_FILE)


def _session_jsonl_size_kb(session_id: str) -> float:
    """Taille du fichier session JSONL. Cherche dans plusieurs emplacements possibles."""
    # Chemin principal (calculé)
    jsonl = _CLAUDE_SESSIONS_DIR / f"{session_id}.jsonl"
    if jsonl.exists():
        return jsonl.stat().st_size / 1024
    # Fallback : chercher dans les sous-dossiers de ~/.claude/projects/
    claude_projects = Path.home() / ".claude" / "projects"
    if claude_projects.exists():
        for d in claude_projects.iterdir():
            if d.is_dir() and "iAgent" in d.name:
                candidate = d / f"{session_id}.jsonl"
                if candidate.exists():
                    return candidate.stat().st_size / 1024
    return 0.0


def _check_auto_reset(session: dict) -> str | None:
    """
    Vérifie si une session doit être réinitialisée automatiquement.
    Retourne un message explicatif si oui, None sinon.
    """
    cfg = get_config().get("session", {})
    ttl_hours = cfg.get("ttl_hours", 4)
    max_size_kb = cfg.get("max_size_kb", 200)

    last_active = datetime.fromisoformat(session.get("last_active", "2000-01-01"))
    inactive_delta = datetime.now() - last_active
    inactive = inactive_delta > timedelta(hours=ttl_hours)
    size_kb = _session_jsonl_size_kb(session["session_id"])
    oversized = size_kb > max_size_kb

    if inactive and oversized:
        hours = round(inactive_delta.total_seconds() / 3600, 1)
        return (
            f"Session réinitialisée automatiquement "
            f"(inactive depuis {hours}h, taille {size_kb:.0f} KB)"
        )
    return None


def _create_session(sessions: dict, chat_id: str) -> str:
    """Crée une nouvelle session et sauvegarde."""
    new_id = str(uuid.uuid4())
    sessions[chat_id] = {
        "session_id": new_id,
        "created": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
    }
    _save_sessions(sessions)
    return new_id


def get_or_create_session(chat_id: str) -> tuple[str, bool, str | None]:
    """
    Retourne (session_id, is_new_session, info_message).

    info_message est non-None quand la session a été réinitialisée
    automatiquement (double condition TTL ET taille) — à afficher à l'utilisateur.
    """
    sessions = _load_sessions()
    existing = sessions.get(chat_id)

    if existing:
        reset_reason = _check_auto_reset(existing)
        if reset_reason:
            new_id = _create_session(sessions, chat_id)
            return new_id, True, reset_reason
        return existing["session_id"], False, None

    # Première session pour ce chat
    new_id = _create_session(sessions, chat_id)
    return new_id, True, None


def force_reset(chat_id: str) -> str:
    """
    Réinitialise manuellement la session d'un chat (commande /reset).
    Retourne le nouveau session_id.
    """
    sessions = _load_sessions()
    new_id = _create_session(sessions, chat_id)
    return new_id


def update_session_activity(chat_id: str, session_id: str) -> None:
    """Met à jour last_active après chaque échange."""
    sessions = _load_sessions()
    if chat_id in sessions:
        sessions[chat_id]["last_active"] = datetime.now().isoformat()
        _save_sessions(sessions)
