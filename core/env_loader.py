# -*- coding: utf-8 -*-
"""
env_loader.py — Chargement des variables d'environnement depuis un fichier .env.

Chemin unique : ~/.iagent/.env
Configurable via la variable d'environnement IAGENT_ENV_PATH.
Aucun fallback — FileNotFoundError si absent.

Usage :
    from core.env_loader import load_env, require_env
    load_env()
"""
import os
from pathlib import Path


# --- Chemin configurable ---
# Priorité : variable d'environnement > défaut iAgent
_IAGENT_ENV = Path.home() / ".iagent" / ".env"


def _resolve_env_path() -> Path:
    """Détermine le chemin .env à utiliser."""
    explicit = os.environ.get("IAGENT_ENV_PATH")
    if explicit:
        return Path(explicit)
    return _IAGENT_ENV


ENV_PATH: Path = _resolve_env_path()


def load_env(env_path: Path | str | None = None) -> int:
    """
    Charge un fichier .env dans os.environ.

    Args:
        env_path: Chemin vers le fichier .env. Si None, utilise ENV_PATH.

    Returns:
        Nombre de variables injectées.

    Raises:
        FileNotFoundError: si le fichier .env est absent.

    Note:
        os.environ.setdefault ne remplace JAMAIS une variable déjà définie.
        Le runtime a priorité sur le fichier .env.
    """
    target = Path(env_path) if env_path else ENV_PATH
    if not target.exists():
        raise FileNotFoundError(
            f"Fichier .env absent : {target}\n"
            f"Créer ce fichier avec les variables requises.\n"
            f"Voir docs/install/guide-installation.md"
        )
    count = 0
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.setdefault(k, v) == v:
                count += 1
    return count


def require_env(key: str) -> str:
    """
    Retourne os.environ[key] ou lève ValueError.

    À appeler après load_env(). Fail fast si un credential manque.
    """
    val = os.environ.get(key)
    if not val:
        raise ValueError(
            f"Credential manquant : {key}\n"
            f"Vérifier {ENV_PATH} ou les variables d'environnement du runtime."
        )
    return val
