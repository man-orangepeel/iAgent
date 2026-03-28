# -*- coding: utf-8 -*-
"""
config.py — Chargement de config/iagent.json.

Usage :
    from core.config import get_config
    cfg = get_config()
    timeout = cfg["heartbeat"]["timeout_seconds"]
"""
import json
from pathlib import Path

_IAGENT_DIR = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _IAGENT_DIR / "config" / "iagent.json"

_cache: dict | None = None


def get_config() -> dict:
    """Charge et cache la configuration. Relecture si le fichier change."""
    global _cache
    if _cache is None:
        if not _CONFIG_FILE.exists():
            return {}
        _cache = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    return _cache
