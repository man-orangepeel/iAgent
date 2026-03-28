# -*- coding: utf-8 -*-
"""
context_builder.py — Assemblage du contexte identity par cas d'usage.

Chaque use_case définit les fichiers identity minimaux nécessaires.
Le contexte est concaténé et prêt à être passé à --system-prompt.

Usage :
    from core.context_builder import build
    context = build("heartbeat_soul")  # → contenu de SOUL.md uniquement
"""
import logging
from pathlib import Path
from core.config import get_config

_IAGENT_DIR = Path(__file__).resolve().parent.parent
_IDENTITY_DIR = _IAGENT_DIR / "identity"

_logger = logging.getLogger("iagent.context_builder")

# --- Profils : fichiers identity par cas d'usage ---
_PROFILES: dict[str, list[str]] = {
    "heartbeat_soul":      ["SOUL.md"],
    "heartbeat_memory":    ["MEMORY.md", "AGENTS.md"],
    "heartbeat_queue":     ["QUEUE.md", "AGENTS.md", "COMMUNICATION.md"],
    "heartbeat_proactive": ["USER.md", "MEMORY.md", "HEARTBEAT.md"],
    "telegram_session":    ["IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md",
                            "AGENTS.md", "TOOLS.md", "COMMUNICATION.md", "QUEUE.md"],
}


def build(use_case: str) -> str:
    """
    Retourne le contexte concaténé pour un cas d'usage donné.

    Args:
        use_case: Clé du profil (ex: "heartbeat_soul", "telegram_session").

    Returns:
        Chaîne prête pour --system-prompt.

    Raises:
        ValueError: si use_case inconnu.
    """
    if use_case not in _PROFILES:
        raise ValueError(
            f"use_case inconnu : {use_case!r}. "
            f"Disponibles : {', '.join(_PROFILES.keys())}"
        )

    files = _PROFILES[use_case]
    if not files:
        _logger.info("%s | 0 fichiers | 0 chars", use_case)
        return ""

    parts = []
    for name in files:
        path = _IDENTITY_DIR / name
        if not path.exists():
            _logger.warning("Fichier identity introuvable : %s", path)
            continue
        parts.append(f"--- {name} ---\n{path.read_text(encoding='utf-8')}")

    result = "\n\n".join(parts)
    total = len(result)

    cfg = get_config().get("context", {})
    max_chars = cfg.get("max_chars", 38_000)
    warn_ratio = cfg.get("warn_threshold", 0.9)
    warn_threshold = int(max_chars * warn_ratio)

    if total > max_chars:
        _logger.warning("%s | TRONQUÉ %d → %d chars", use_case, total, max_chars)
        result = result[:max_chars]
        total = max_chars
    elif total > warn_threshold:
        _logger.warning("%s | %d fichiers | %d chars (proche limite)", use_case, len(files), total)
    else:
        _logger.info("%s | %d fichiers | %d chars", use_case, len(files), total)

    return result
