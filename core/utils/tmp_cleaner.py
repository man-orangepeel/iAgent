# -*- coding: utf-8 -*-
"""
tmp_cleaner.py — Purge automatique des fichiers temporaires.

Appelé au démarrage du gateway et du heartbeat.
Supprime les fichiers de tmp/ plus vieux que max_age_hours.
"""
import logging
from pathlib import Path
from datetime import datetime, timedelta

_logger = logging.getLogger("iagent.tmp_cleaner")
_IAGENT_DIR = Path(__file__).resolve().parent.parent.parent


def purge_tmp(max_age_hours: int = 24) -> dict:
    """
    Supprime les fichiers temporaires plus vieux que max_age_hours.

    Returns:
        {"deleted": int, "freed_mb": float, "errors": int}
    """
    tmp_dir = _IAGENT_DIR / "tmp"
    if not tmp_dir.exists():
        return {"deleted": 0, "freed_mb": 0.0, "errors": 0}

    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    deleted = 0
    freed_bytes = 0
    errors = 0

    for f in tmp_dir.rglob("*"):
        if not f.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                size = f.stat().st_size
                f.unlink()
                deleted += 1
                freed_bytes += size
                _logger.debug("Purgé : %s (%.1f KB)", f.name, size / 1024)
        except Exception as e:
            _logger.warning("Erreur purge %s : %s", f.name, e)
            errors += 1

    freed_mb = freed_bytes / (1024 * 1024)
    if deleted > 0:
        _logger.info(
            "Purge tmp : %d fichier(s) supprimé(s), %.2f MB libérés",
            deleted, freed_mb,
        )
    return {"deleted": deleted, "freed_mb": freed_mb, "errors": errors}
