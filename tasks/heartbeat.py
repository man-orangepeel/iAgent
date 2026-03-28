# -*- coding: utf-8 -*-
"""
heartbeat.py — Orchestrateur heartbeat iAgent.

Toutes les 2h (via LaunchAgent), exécute une catégorie LLM en rotation.
Catégories : queue_work, soul_evil, memory_distill, proactive.

Usage :
    python3 tasks/heartbeat.py                          # rotation automatique
    python3 tasks/heartbeat.py --force-category soul_evil  # forcer une catégorie
    python3 tasks/heartbeat.py --dry-run                # afficher sans exécuter
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

_IAGENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_IAGENT_DIR))

from core.claude_runner import run as claude_run
from core.context_builder import build as build_context
from core.env_loader import load_env, require_env
from core.config import get_config

# --- Chemins ---
_STATE_FILE = _IAGENT_DIR / "data" / "memory" / "heartbeat-state.json"
_MEMORY_DIR = _IAGENT_DIR / "data" / "memory"
_IDENTITY_DIR = _IAGENT_DIR / "identity"

# Ordre de priorité si égalité de timestamps
_CATEGORIES = ["queue_work", "soul_evil", "memory_distill", "proactive"]

# Mapping catégorie → profil context_builder
_CONTEXT_MAP = {
    "queue_work":      "heartbeat_queue",
    "soul_evil":       "heartbeat_soul",
    "memory_distill":  "heartbeat_memory",
    "proactive":       "heartbeat_proactive",
}

_SILENCE = "SILENCE"


# --- État heartbeat ---

def _load_state() -> dict:
    if not _STATE_FILE.exists():
        return {"lastChecks": {c: 0 for c in _CATEGORIES}}
    return json.loads(_STATE_FILE.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    import tempfile, os
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=_STATE_FILE.parent)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, _STATE_FILE)


def _pick_category(state: dict) -> str:
    checks = state.get("lastChecks", {})
    return min(_CATEGORIES, key=lambda c: (checks.get(c, 0), _CATEGORIES.index(c)))


# --- Prompts par catégorie ---

def _prompt_queue_work() -> str:
    queue = (_IDENTITY_DIR / "QUEUE.md").read_text(encoding="utf-8")
    return (
        f"Lis QUEUE.md ci-dessous.\n"
        f"Si une tâche commence par [APPROVED], décris précisément ce qu'il faut faire.\n"
        f"Si aucune tâche [APPROVED] → réponds exactement \"{_SILENCE}\".\n"
        f"IMPORTANT : ne JAMAIS exécuter une tâche sans [APPROVED].\n\n"
        f"--- QUEUE.md ---\n{queue}"
    )


def _prompt_soul_evil() -> str:
    return (
        f"Tu es iAgent. Relis SOUL.md fourni en contexte.\n"
        f"Analyse s'il y a eu une dérive comportementale récente.\n"
        f"Vérifie : ton direct et concis ? Priorité financière respectée ? "
        f"Flatteries ou validations sans challenge ?\n"
        f"Si aucune dérive → réponds exactement \"{_SILENCE}\".\n"
        f"Si dérive → décris-la en 3 lignes max."
    )


def _prompt_memory_distill() -> str:
    logs = _read_recent_logs(days=3)
    if not logs:
        return f"Aucun log récent trouvé. Réponds exactement \"{_SILENCE}\"."
    return (
        f"Voici MEMORY.md (en contexte) et les logs des 3 derniers jours.\n"
        f"Si les logs contiennent des décisions ou faits importants absents de MEMORY.md, "
        f"propose un patch concis (lignes à ajouter).\n"
        f"Si rien de nouveau → réponds exactement \"{_SILENCE}\".\n\n"
        f"--- Logs récents ---\n{logs}"
    )


def _prompt_proactive() -> str:
    return (
        f"Tu es iAgent. En te basant sur USER.md, MEMORY.md et HEARTBEAT.md "
        f"fournis en contexte, y a-t-il une opportunité proactive à signaler à l'utilisateur ?\n"
        f"(maintenance, optimisation, rappel, tâche oubliée)\n"
        f"Si opportunité → 3 lignes max. Sinon → exactement \"{_SILENCE}\"."
    )


_PROMPT_FN = {
    "queue_work": _prompt_queue_work,
    "soul_evil": _prompt_soul_evil,
    "memory_distill": _prompt_memory_distill,
    "proactive": _prompt_proactive,
}


# --- Utilitaires ---

def _read_recent_logs(days: int = 3) -> str:
    parts = []
    today = datetime.now()
    for delta in range(days):
        day = today - timedelta(days=delta)
        log_file = _MEMORY_DIR / f"{day.strftime('%Y-%m-%d')}.md"
        if log_file.exists():
            parts.append(f"--- {log_file.name} ---\n{log_file.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def _send_alert(message: str) -> bool:
    try:
        import requests
        load_env()
        token = require_env("IAGENT_BOT_TOKEN")
        chat_id = require_env("IAGENT_CHAT_ID")
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000], "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"⚠️ Alerte Telegram échouée : {e}", file=sys.stderr)
        return False


def _log_memory(category: str, text: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")
    log_file = _MEMORY_DIR / f"{today}.md"
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text(f"# {today} — Logs heartbeat\n\n", encoding="utf-8")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"## {now} [{category}]\n{text.strip()}\n\n")


# --- Exécution ---

def run_heartbeat(category: str = None, dry_run: bool = False) -> dict:
    state = _load_state()
    selected = category or _pick_category(state)
    if selected not in _CATEGORIES:
        return {"error": f"Catégorie inconnue : {selected}"}

    context = build_context(_CONTEXT_MAP[selected])
    prompt = _PROMPT_FN[selected]()

    print(f"🫀 [{selected}] contexte={len(context)} chars, prompt={len(prompt)} chars")

    if dry_run:
        print(f"   DRY-RUN — pas d'appel LLM")
        return {"category": selected, "context_chars": len(context), "dry_run": True}

    # Contexte via context_builder (source unique de vérité)
    context_str = build_context(_CONTEXT_MAP[selected])
    cfg = get_config().get("heartbeat", {})
    timeout = cfg.get("timeout_seconds", 60)
    # Passer le contexte via un fichier temporaire pour --system-prompt
    import tempfile, os
    fd, ctx_file = tempfile.mkstemp(suffix=".md", dir=_MEMORY_DIR)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(context_str)
        response = claude_run(prompt, context_files=[ctx_file], timeout=timeout)
    finally:
        os.unlink(ctx_file)

    if not response.success:
        msg = f"❌ Heartbeat {selected} échoué : {response.error}"
        print(msg, file=sys.stderr)
        state.setdefault("lastChecks", {})[selected] = int(time.time() * 1000)
        _save_state(state)
        return {"category": selected, "error": response.error, "duration_ms": response.duration_ms}

    is_silence = response.text.strip().upper().startswith(_SILENCE)

    if is_silence:
        print(f"🤫 [{selected}] → SILENCE ({response.duration_ms}ms)")
    else:
        print(f"📢 [{selected}] → résultat ({len(response.text)} chars, {response.duration_ms}ms)")
        _log_memory(selected, response.text)
        _send_alert(f"🫀 *Heartbeat [{selected}]*\n\n{response.text[:1800]}")

    state.setdefault("lastChecks", {})[selected] = int(time.time() * 1000)
    _save_state(state)

    return {
        "category": selected,
        "silence": is_silence,
        "duration_ms": response.duration_ms,
        "result": response.text if not is_silence else None,
    }


# --- CLI ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heartbeat iAgent")
    parser.add_argument("--force-category", choices=_CATEGORIES, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_heartbeat(category=args.force_category, dry_run=args.dry_run)
    if "error" in result:
        print(f"ERREUR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    elif result.get("dry_run"):
        print(f"→ Catégorie: {result['category']}, contexte: {result['context_chars']} chars")
    elif result.get("silence"):
        print("SILENCE")
    else:
        print(result.get("result", ""))
