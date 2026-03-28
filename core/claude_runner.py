# -*- coding: utf-8 -*-
"""
claude_runner.py — Moteur principal iAgent : appel Claude Code CLI via subprocess.

Aucune clé API requise — utilise l'auth OAuth du compte (forfait Max).

Fonctions disponibles :
    run()                      — appel one-shot sans outils (--tools "")
    run_with_search()          — appel one-shot avec WebSearch (--tools "WebSearch")
    run_session()              — session persistante sans outils
    run_session_with_search()  — session persistante avec WebSearch

Usage en tant que module :
    from core.claude_runner import run, run_with_search
    result = run("Mon prompt", context_files=["identity/IDENTITY.md"])

Usage en ligne de commande :
    python3 core/claude_runner.py --prompt "Mon prompt" --context-files fichier1.md
"""
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# --- Configuration ---

_IAGENT_DIR = Path(__file__).resolve().parent.parent
_LOG_DIR = _IAGENT_DIR / "logs"
_LOG_FILE = _LOG_DIR / "runner.log"
_MAX_CONTEXT_CHARS = 38_000  # Marge de sécurité sur budget 40k
_DEFAULT_TIMEOUT = 60        # Règle optimisation financière : 60s max en production
_CLAUDE_BIN = "claude"       # Doit être dans le PATH


# --- Config gateway (chargée une seule fois au démarrage) ---

def _load_gateway_config() -> dict:
    """Charge la config gateway une seule fois."""
    try:
        import json
        cfg_file = _IAGENT_DIR / "config" / "iagent.json"
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            return cfg.get("gateway", {})
    except Exception:
        pass
    # Fallback sécurisé : WebSearch uniquement
    return {"tools": ["WebSearch"], "allowed_patterns": ["WebSearch"], "timeout": 90}

_GATEWAY_CFG = _load_gateway_config()
_GATEWAY_TOOLS = _GATEWAY_CFG.get("tools", ["WebSearch"])
_GATEWAY_TIMEOUT = _GATEWAY_CFG.get("timeout", 90)


# --- Logging ---

def _setup_logger() -> logging.Logger:
    """Configure le logger runner (rotation 1 Mo, 3 fichiers)."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("iagent.runner")
    if not logger.handlers:
        handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

_logger = _setup_logger()


# --- Modèle de réponse ---

@dataclass
class ClaudeResponse:
    """Réponse structurée d'un appel Claude Code CLI."""
    text: str = ""
    success: bool = False
    error: Optional[str] = None
    duration_ms: int = 0


# --- Construction du contexte ---

def _build_context(context_files: list[str]) -> tuple[str, int]:
    """
    Lit et concatène les fichiers contexte.

    Returns:
        (contexte_concaténé, nombre_total_de_chars)
    Tronque avec warning si le total dépasse _MAX_CONTEXT_CHARS.
    """
    parts = []
    for filepath in context_files:
        path = Path(filepath)
        if not path.exists():
            _logger.warning("Fichier contexte introuvable : %s", filepath)
            continue
        content = path.read_text(encoding="utf-8")
        parts.append(f"--- {path.name} ---\n{content}")

    result = "\n\n".join(parts)
    total_chars = len(result)

    if total_chars > _MAX_CONTEXT_CHARS:
        _logger.warning(
            "Contexte tronqué : %d → %d chars", total_chars, _MAX_CONTEXT_CHARS
        )
        result = result[:_MAX_CONTEXT_CHARS]

    return result, total_chars


# --- Fonction principale ---

def run(
    prompt: str,
    context_files: Optional[list[str]] = None,
    max_tokens: int = 4096,
    timeout: int = _DEFAULT_TIMEOUT,
    model: Optional[str] = None,
) -> ClaudeResponse:
    """
    Appelle Claude Code CLI en mode non-interactif.

    Args:
        prompt: Le texte du prompt utilisateur.
        context_files: Liste de chemins vers des fichiers à injecter en contexte.
        max_tokens: Non utilisé directement (Claude CLI gère en interne), conservé pour compatibilité API.
        timeout: Durée max en secondes avant kill du process.
        model: Modèle à utiliser (None = défaut Claude Code).

    Returns:
        ClaudeResponse avec le texte, succès/échec, erreur éventuelle et durée.
    """
    # Construire la commande
    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--no-session-persistence",
        "--tools", "",
    ]

    if model:
        cmd += ["--model", model]

    # Injecter le contexte via --system-prompt
    context_chars = 0
    if context_files:
        context, context_chars = _build_context(context_files)
        if context:
            cmd += ["--system-prompt", context]

    # Mesurer le temps
    start = time.monotonic()

    try:
        # Le prompt passe via stdin (requis quand --tools "" est utilisé)
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
            _logger.error(
                "ERR | %dms | %dchars | %s", duration_ms, context_chars, error_msg
            )
            return ClaudeResponse(
                error=error_msg, duration_ms=duration_ms
            )

        # Parser la sortie JSON
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            _logger.error(
                "ERR | %dms | %dchars | JSON invalide : %s", duration_ms, context_chars, e
            )
            return ClaudeResponse(
                error=f"JSON invalide : {e}", duration_ms=duration_ms
            )

        # Vérifier le statut
        if data.get("is_error"):
            error_msg = data.get("result", "Erreur inconnue")
            _logger.error(
                "ERR | %dms | %dchars | %s", duration_ms, context_chars, error_msg
            )
            return ClaudeResponse(
                text=error_msg, error=error_msg, duration_ms=duration_ms
            )

        # Succès
        text = data.get("result", "")
        _logger.info("OK | %dms | %dchars", duration_ms, context_chars)
        return ClaudeResponse(
            text=text, success=True, duration_ms=duration_ms
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("ERR | %dms | %dchars | TIMEOUT", duration_ms, context_chars)
        return ClaudeResponse(
            error="TIMEOUT", duration_ms=duration_ms
        )
    except FileNotFoundError:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error(
            "ERR | %dms | %dchars | Claude CLI introuvable dans le PATH",
            duration_ms, context_chars,
        )
        return ClaudeResponse(
            error="Claude CLI introuvable dans le PATH", duration_ms=duration_ms
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error(
            "ERR | %dms | %dchars | %s", duration_ms, context_chars, e
        )
        return ClaudeResponse(
            error=str(e), duration_ms=duration_ms
        )


# --- Mode session (gateway Telegram) ---

def run_session(
    prompt: str,
    session_id: str,
    is_new_session: bool,
    bootstrap_context: str = "",
    timeout: int = _DEFAULT_TIMEOUT,
) -> ClaudeResponse:
    """
    Appelle Claude Code CLI dans une session persistante.

    Args:
        prompt: Le texte du message utilisateur.
        session_id: UUID de la session.
        is_new_session: True = premier message (injecte bootstrap via --system-prompt).
        bootstrap_context: Contexte bootstrap (utilisé seulement si is_new_session=True).
        timeout: Durée max en secondes.

    Returns:
        ClaudeResponse avec le texte, succès/échec, erreur éventuelle et durée.
    """
    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--tools", "",
    ]

    context_chars = 0
    if is_new_session:
        cmd += ["--session-id", session_id]
        if bootstrap_context:
            cmd += ["--system-prompt", bootstrap_context]
            context_chars = len(bootstrap_context)
    else:
        cmd += ["--resume", session_id]

    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
            _logger.error(
                "ERR | %dms | session=%s | %dchars | %s",
                duration_ms, session_id[:8], context_chars, error_msg,
            )
            return ClaudeResponse(error=error_msg, duration_ms=duration_ms)

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            _logger.error(
                "ERR | %dms | session=%s | %dchars | JSON invalide",
                duration_ms, session_id[:8], context_chars,
            )
            return ClaudeResponse(error=f"JSON invalide : {e}", duration_ms=duration_ms)

        if data.get("is_error"):
            error_msg = data.get("result", "Erreur inconnue")
            _logger.error(
                "ERR | %dms | session=%s | %dchars | %s",
                duration_ms, session_id[:8], context_chars, error_msg,
            )
            return ClaudeResponse(text=error_msg, error=error_msg, duration_ms=duration_ms)

        text = data.get("result", "")
        _logger.info(
            "OK | %dms | session=%s | %dchars",
            duration_ms, session_id[:8], context_chars,
        )
        return ClaudeResponse(text=text, success=True, duration_ms=duration_ms)

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("ERR | %dms | session=%s | TIMEOUT", duration_ms, session_id[:8])
        return ClaudeResponse(error="TIMEOUT", duration_ms=duration_ms)
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("ERR | %dms | session=%s | %s", duration_ms, session_id[:8], e)
        return ClaudeResponse(error=str(e), duration_ms=duration_ms)


# --- Mode gateway (WebSearch + skills autorisés) ---


def run_with_search(
    prompt: str,
    context_files: Optional[list[str]] = None,
    timeout: int = _GATEWAY_TIMEOUT,
    model: Optional[str] = None,
) -> ClaudeResponse:
    """
    Appel Claude CLI avec outils gateway (config-driven).

    Outils disponibles définis dans config/iagent.json → gateway.tools
    Patterns autorisés dans gateway.allowed_patterns

    Log format : SEARCH_OK/SEARCH_ERR
    """
    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--no-session-persistence",
        "--permission-mode", "bypassPermissions",
    ]
    # Tools = filtre dur (seuls ces outils existent pour Claude)
    cmd += ["--tools"] + _GATEWAY_TOOLS

    if model:
        cmd += ["--model", model]

    context_chars = 0
    if context_files:
        context, context_chars = _build_context(context_files)
        if context:
            cmd += ["--system-prompt", context]

    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
            _logger.error("SEARCH_ERR | %dms | %dchars | %s", duration_ms, context_chars, error_msg)
            return ClaudeResponse(error=error_msg, duration_ms=duration_ms)

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            _logger.error("SEARCH_ERR | %dms | %dchars | JSON invalide", duration_ms, context_chars)
            return ClaudeResponse(error=f"JSON invalide : {e}", duration_ms=duration_ms)

        if data.get("is_error"):
            error_msg = data.get("result", "Erreur inconnue")
            _logger.error("SEARCH_ERR | %dms | %dchars | %s", duration_ms, context_chars, error_msg)
            return ClaudeResponse(text=error_msg, error=error_msg, duration_ms=duration_ms)

        text = data.get("result", "")
        _logger.info("SEARCH_OK | %dms | %dchars", duration_ms, context_chars)
        return ClaudeResponse(text=text, success=True, duration_ms=duration_ms)

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("SEARCH_ERR | %dms | %dchars | TIMEOUT", duration_ms, context_chars)
        return ClaudeResponse(error="TIMEOUT", duration_ms=duration_ms)
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("SEARCH_ERR | %dms | %dchars | %s", duration_ms, context_chars, e)
        return ClaudeResponse(error=str(e), duration_ms=duration_ms)


def run_session_with_search(
    prompt: str,
    session_id: str,
    is_new_session: bool,
    bootstrap_context: str = "",
    timeout: int = _GATEWAY_TIMEOUT,
) -> ClaudeResponse:
    """
    Session persistante avec outils gateway (config-driven).

    Utilisé par le gateway Telegram — Claude décide quels outils utiliser.
    """
    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    # Tools = filtre dur (seuls ces outils existent pour Claude)
    cmd += ["--tools"] + _GATEWAY_TOOLS

    context_chars = 0
    if is_new_session:
        cmd += ["--session-id", session_id]
        if bootstrap_context:
            cmd += ["--system-prompt", bootstrap_context]
            context_chars = len(bootstrap_context)
    else:
        cmd += ["--resume", session_id]

    start = time.monotonic()

    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or f"Exit code {proc.returncode}"
            _logger.error(
                "SEARCH_ERR | %dms | session=%s | %dchars | %s",
                duration_ms, session_id[:8], context_chars, error_msg,
            )
            return ClaudeResponse(error=error_msg, duration_ms=duration_ms)

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            _logger.error(
                "SEARCH_ERR | %dms | session=%s | JSON invalide",
                duration_ms, session_id[:8],
            )
            return ClaudeResponse(error=f"JSON invalide : {e}", duration_ms=duration_ms)

        if data.get("is_error"):
            error_msg = data.get("result", "Erreur inconnue")
            _logger.error(
                "SEARCH_ERR | %dms | session=%s | %dchars | %s",
                duration_ms, session_id[:8], context_chars, error_msg,
            )
            return ClaudeResponse(text=error_msg, error=error_msg, duration_ms=duration_ms)

        text = data.get("result", "")
        _logger.info(
            "SEARCH_OK | %dms | session=%s | %dchars",
            duration_ms, session_id[:8], context_chars,
        )
        return ClaudeResponse(text=text, success=True, duration_ms=duration_ms)

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("SEARCH_ERR | %dms | session=%s | TIMEOUT", duration_ms, session_id[:8])
        return ClaudeResponse(error="TIMEOUT", duration_ms=duration_ms)
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        _logger.error("SEARCH_ERR | %dms | session=%s | %s", duration_ms, session_id[:8], e)
        return ClaudeResponse(error=str(e), duration_ms=duration_ms)


# --- Mode CLI ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Appel Claude Code CLI depuis iAgent"
    )
    parser.add_argument("--prompt", required=True, help="Texte du prompt")
    parser.add_argument(
        "--context-files", nargs="*", default=[],
        help="Fichiers à injecter en contexte"
    )
    parser.add_argument(
        "--timeout", type=int, default=_DEFAULT_TIMEOUT,
        help=f"Timeout en secondes (défaut : {_DEFAULT_TIMEOUT})"
    )
    parser.add_argument("--model", default=None, help="Modèle Claude à utiliser")
    args = parser.parse_args()

    result = run(
        args.prompt,
        context_files=args.context_files or None,
        timeout=args.timeout,
        model=args.model,
    )

    if result.success:
        print(result.text)
    else:
        print(f"ERREUR: {result.error}", file=sys.stderr)
        sys.exit(1)
