#!/bin/bash
# security-audit.sh — Audit de sécurité iAgent
# Basé sur : iAgent security audit,OWASP LLM Top 10 2025,
#            MITRE ATLAS Threat Model, OWASP Agentic Top 10 2025
#
# Usage :
#   bash scripts/security-audit.sh              # audit complet
#   bash scripts/security-audit.sh --fix        # applique les corrections sans risque (chmod)
#   bash scripts/security-audit.sh --json       # sortie JSON pour intégration
#   bash scripts/security-audit.sh --category 3 # une seule catégorie

set -uo pipefail

# ── Variables globales ────────────────────────────
IAGENT_DIR="$HOME/.iagent"
ENV_FILE="$HOME/.iagent/.env"
PYTHON_PATH=$(which python3 2>/dev/null || echo "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3")
CRITICAL=0; HIGH=0; MEDIUM=0; LOW=0; OK_COUNT=0
FIX=false; JSON_MODE=false; CATEGORY=0
JSON_ITEMS=""

# ── Parsing arguments ────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --fix)      FIX=true ;;
        --json)     JSON_MODE=true ;;
        --category) CATEGORY="$2"; shift ;;
        --help|-h)
            echo "Usage : bash scripts/security-audit.sh [--fix] [--json] [--category N]"
            echo "  --fix        Applique les corrections sans risque (chmod uniquement)"
            echo "  --json       Sortie JSON pour intégration"
            echo "  --category N Exécute uniquement la catégorie N (1-10)"
            exit 0 ;;
        *) echo "Option inconnue : $1"; exit 1 ;;
    esac
    shift
done

# ── Fonctions utilitaires ────────────────────────

get_perms() {
    # Compatible macOS (BSD stat) et Linux (GNU stat)
    stat -f %Lp "$1" 2>/dev/null || stat -c %a "$1" 2>/dev/null || echo "000"
}

audit() {
    local level="$1" label="$2" detail="${3:-}" fix_cmd="${4:-}"
    if ! $JSON_MODE; then
        case "$level" in
            CRITICAL) printf "  🔴 [CRITIQUE] %-45s %s\n" "$label" "${detail:+→ $detail}"
                      CRITICAL=$((CRITICAL+1)) ;;
            HIGH)     printf "  🟠 [ÉLEVÉ]    %-45s %s\n" "$label" "${detail:+→ $detail}"
                      HIGH=$((HIGH+1)) ;;
            MEDIUM)   printf "  🟡 [MOYEN]    %-45s %s\n" "$label" "${detail:+→ $detail}"
                      MEDIUM=$((MEDIUM+1)) ;;
            LOW)      printf "  🔵 [FAIBLE]   %-45s %s\n" "$label" "${detail:+→ $detail}"
                      LOW=$((LOW+1)) ;;
            OK)       printf "  ✓             %-45s %s\n" "$label" "${detail:+($detail)}"
                      OK_COUNT=$((OK_COUNT+1)) ;;
            INFO)     printf "  ℹ             %-45s %s\n" "$label" "${detail:-}" ;;
        esac
    else
        case "$level" in
            CRITICAL) CRITICAL=$((CRITICAL+1)) ;;
            HIGH)     HIGH=$((HIGH+1)) ;;
            MEDIUM)   MEDIUM=$((MEDIUM+1)) ;;
            LOW)      LOW=$((LOW+1)) ;;
            OK)       OK_COUNT=$((OK_COUNT+1)) ;;
        esac
        # En mode JSON, n'accumuler que les problèmes (pas OK ni INFO)
        if [ "$level" != "OK" ] && [ "$level" != "INFO" ]; then
            local sev_lower=$(echo "$level" | tr '[:upper:]' '[:lower:]')
            local escaped_label=$(echo "$label" | sed 's/"/\\"/g')
            local escaped_detail=$(echo "$detail" | sed 's/"/\\"/g')
            JSON_ITEMS="${JSON_ITEMS}{\"severity\":\"${sev_lower}\",\"label\":\"${escaped_label}\",\"detail\":\"${escaped_detail}\"},"
        fi
    fi
    # Auto-fix si --fix et commande fournie
    if [ "$level" != "OK" ] && [ "$level" != "INFO" ] && [ -n "$fix_cmd" ] && $FIX; then
        eval "$fix_cmd" 2>/dev/null && ! $JSON_MODE && echo "     ↳ Corrigé automatiquement"
    fi
}

section() {
    local num="$1" title="$2"
    if [ "$CATEGORY" -ne 0 ] && [ "$CATEGORY" -ne "$num" ]; then
        return 1
    fi
    $JSON_MODE || { echo; echo "══ $num. $title ══════════════════════════════════"; }
    return 0
}

# ── En-tête ───────────────────────────────────────
if ! $JSON_MODE; then
    echo "=== iAgent Security Audit ==="
    echo "    OWASP LLM Top 10 2025 · MITRE ATLAS · iAgent Security Model"
    echo "    $(date '+%Y-%m-%d %H:%M')"
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 1 — Credentials & Token Security
# ══════════════════════════════════════════════════
if section 1 "Credentials & Token Security"; then

    # 1a. Permissions .env
    if [ -f "$ENV_FILE" ]; then
        PERM=$(get_perms "$ENV_FILE")
        OTHER=${PERM: -1}
        if [ "$OTHER" -gt 0 ]; then
            audit CRITICAL "Permissions .env" "mode $PERM (world-readable)" "chmod 600 \"$ENV_FILE\""
        elif [ "${PERM}" != "600" ] && [ "${PERM}" != "400" ]; then
            audit MEDIUM "Permissions .env" "mode $PERM (recommandé: 600)" "chmod 600 \"$ENV_FILE\""
        else
            audit OK "Permissions .env" "mode $PERM"
        fi
    else
        audit HIGH "Permissions .env" "fichier .env introuvable"
    fi

    # 1b. Tokens dans les logs
    TOKEN_HITS=$(grep -rcE "[0-9]{8,10}:[A-Za-z0-9_-]{35}" "$IAGENT_DIR/logs/" 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}')
    if [ "$TOKEN_HITS" -gt 0 ]; then
        audit CRITICAL "Tokens dans les logs" "$TOKEN_HITS occurrence(s) détectée(s)"
    else
        audit OK "Tokens dans les logs" "aucun token exposé"
    fi

    # 1c. Tokens hardcodés dans le code Python
    # Exclusions : variables lisant depuis l'environnement, commentaires, placeholders
    HARD_TOKENS=$(grep -rE "(TOKEN|API_KEY|SECRET|PASSWORD)\s*=\s*['\"][A-Za-z0-9_\-]{15,}" \
        --include="*.py" \
        "$IAGENT_DIR/core/" "$IAGENT_DIR/projects/" "$IAGENT_DIR/skills/" \
        "$IAGENT_DIR/tasks/" "$IAGENT_DIR/gateway/" 2>/dev/null | \
        grep -vE "os\.getenv|environ\[|load_env|env_loader|#.*example|#.*placeholder|replace_with|your_token|your_key|TODO|FIXME|test_|_test\." | \
        wc -l | tr -d ' ')
    if [ "$HARD_TOKENS" -gt 0 ]; then
        FILES=$(grep -rlE "(TOKEN|API_KEY|SECRET|PASSWORD)\s*=\s*['\"][A-Za-z0-9_\-]{15,}" \
            --include="*.py" \
            "$IAGENT_DIR/core/" "$IAGENT_DIR/projects/" "$IAGENT_DIR/skills/" \
            "$IAGENT_DIR/tasks/" "$IAGENT_DIR/gateway/" 2>/dev/null | \
            grep -vE "test_|_test\." | xargs -I{} basename {} 2>/dev/null | tr '\n' ' ')
        audit CRITICAL "Tokens hardcodés dans le code" "fichiers : $FILES"
    else
        audit OK "Tokens hardcodés dans le code" "aucun"
    fi

    # 1d. Clés API inutilisées dans .env
    if [ -f "$ENV_FILE" ]; then
        OLD_KEYS=""
        for KEY in GEMINI_API_KEY GROQ_API_KEY NVIDIA_API_KEY OPENAI_API_KEY KIMI_API_KEY; do
            grep -q "^${KEY}=" "$ENV_FILE" 2>/dev/null && OLD_KEYS="$OLD_KEYS $KEY"
        done
        if [ -n "$OLD_KEYS" ]; then
            audit HIGH "Clés API inutilisées dans .env" "$OLD_KEYS"
        else
            audit OK "Clés API inutilisées dans .env" "aucune clé obsolète"
        fi
    fi

    # 1e. Permissions dossier .iagent
    DIR_PERM=$(get_perms "$IAGENT_DIR")
    DIR_OTHER=${DIR_PERM: -1}
    if [ "$DIR_OTHER" -gt 0 ]; then
        audit MEDIUM "Permissions dossier .iagent" "mode $DIR_PERM (recommandé: 700)" "chmod 700 \"$IAGENT_DIR\""
    else
        audit OK "Permissions dossier .iagent" "mode $DIR_PERM"
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 2 — Prompt Injection Defense
# ══════════════════════════════════════════════════
if section 2 "Prompt Injection Defense"; then

    DETECTOR="$IAGENT_DIR/core/utils/injection_detector.py"

    # 2a. injection_detector présent
    if [ -f "$DETECTOR" ]; then
        audit OK "injection_detector présent" "core/utils/injection_detector.py"
    else
        audit CRITICAL "injection_detector absent" "fichier manquant"
    fi

    # 2b. injection_detector activé dans gateway
    GW_IMPORT=$(grep -c "from core.utils.injection_detector import" "$IAGENT_DIR/gateway/telegram_gateway.py" 2>/dev/null)
    GW_CALL=$(grep -c "detect_injection" "$IAGENT_DIR/gateway/telegram_gateway.py" 2>/dev/null)
    if [ "$GW_IMPORT" -ge 1 ] && [ "$GW_CALL" -ge 2 ]; then
        audit OK "injection_detector activé dans gateway" "import + $GW_CALL appels"
    else
        audit CRITICAL "injection_detector non activé dans gateway" "import=$GW_IMPORT appels=$GW_CALL"
    fi

    # 2c. Patterns injection dans bootstrap et prompts
    # Vérifier ligne par ligne pour éviter les faux positifs dus au contexte
    SUSPECT=0
    PATTERNS="ignore previous instructions|disregard instructions|new persona|you are now|act as if|override your|forget your instructions|ignore your system|jailbreak"

    for dir in "$IAGENT_DIR/identity" "$IAGENT_DIR/projects"; do
        [ -d "$dir" ] || continue
        while IFS= read -r line; do
            # Exclure les lignes qui parlent DE l'injection dans un contexte défensif
            echo "$line" | grep -qiE \
              "signaler|bloquer|détecter|reject|injection|arrêt|interdit|NE PAS|NEVER|do not|prevent|defend|warning|alert|sécurité" \
              && continue
            SUSPECT=$((SUSPECT+1))
        done < <(grep -rihE "$PATTERNS" "$dir/" 2>/dev/null)
    done

    if [ "$SUSPECT" -gt 0 ]; then
        audit CRITICAL "Patterns injection dans identity/projects" \
            "$SUSPECT ligne(s) suspecte(s) — vérifier manuellement"
    else
        audit OK "Identity/projects propres" "aucun pattern d'injection"
    fi

    # 2d. TokenFilter actif sur les logs Telegram
    GW="$IAGENT_DIR/gateway/telegram_gateway.py"
    if [ -f "$GW" ]; then
        TF=$(grep -cE "_TokenFilter|addFilter" "$GW" 2>/dev/null)
        if [ "$TF" -ge 2 ]; then
            audit OK "TokenFilter actif" "masquage tokens dans les logs"
        else
            audit MEDIUM "TokenFilter absent ou incomplet" "tokens potentiellement loggués"
        fi
    fi

    # 2e. Contenu prompt non loggué dans claude_runner
    RUNNER="$IAGENT_DIR/core/claude_runner.py"
    if [ -f "$RUNNER" ]; then
        LOG_CONTENT=$(grep -cE "log.*(prompt|response|result|stdout)" "$RUNNER" 2>/dev/null)
        if [ "$LOG_CONTENT" -eq 0 ]; then
            audit OK "Isolation logs runner" "prompts/réponses non loggués"
        else
            audit MEDIUM "Contenu potentiellement loggué" "vérifier claude_runner.py"
        fi
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 3 — Bootstrap Integrity
# ══════════════════════════════════════════════════
if section 3 "Bootstrap Integrity"; then

    BOOTSTRAP_DIR="$IAGENT_DIR/identity"

    # 3a. Permissions world-writable
    WW=$(find "$BOOTSTRAP_DIR" -type f \( -perm -002 -o -perm -020 \) 2>/dev/null | wc -l | tr -d ' ')
    if [ "$WW" -gt 0 ]; then
        audit HIGH "Bootstrap world-writable" "$WW fichier(s)" "chmod -R og-w \"$BOOTSTRAP_DIR\""
    else
        audit OK "Permissions identity" "aucun fichier world-writable"
    fi

    # 3b. Cohérence identité (pas de fuite vers ancien stack)
    # Exclure : négations ("pas de"), historique ("remplacé", "archivé"), noms d'outils ("openai-whisper")
    LEAKS=$(grep -riE "gemini|node\.js|openai|gpt-[34]" "$BOOTSTRAP_DIR/"*.md 2>/dev/null \
        | grep -ivE "pas de|remplacé|archivé|ancien|openai-whisper" | wc -l | tr -d ' ')
    if [ "$LEAKS" -gt 0 ]; then
        FILES=$(grep -riE "gemini|node\.js|openai|gpt-[34]" "$BOOTSTRAP_DIR/"*.md 2>/dev/null \
            | grep -ivE "pas de|remplacé|archivé|ancien|openai-whisper" | sed 's/:.*//;s/.*\///' | sort -u | tr '\n' ' ')
        audit MEDIUM "Références ancien stack dans identity" "$FILES"
    else
        audit OK "Cohérence identité identity" "aucune référence Gemini/OpenAI/Node.js"
    fi

    # 3c. Budget bootstrap (taille contexte telegram_session)
    if [ -f "$IAGENT_DIR/core/context_builder.py" ]; then
        CTX_SIZE=$("$PYTHON_PATH" -c "
import sys; sys.path.insert(0, '$IAGENT_DIR')
from core.context_builder import build
ctx = build('telegram_session')
print(len(ctx))
" 2>/dev/null || echo "0")
        if [ "$CTX_SIZE" -gt 36000 ]; then
            audit HIGH "Budget bootstrap dépassé" "${CTX_SIZE} chars (limite 38000, seuil critique 36000)"
        elif [ "$CTX_SIZE" -gt 30000 ]; then
            audit LOW "Budget bootstrap élevé" "${CTX_SIZE} chars (79%+ du budget)"
        elif [ "$CTX_SIZE" -gt 0 ]; then
            audit OK "Budget identity" "${CTX_SIZE} chars"
        else
            audit INFO "Budget identity" "impossible à calculer"
        fi
    fi

    # 3d. Fichiers bootstrap sous contrôle de version
    if git -C "$IAGENT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        DIRTY=$(git -C "$IAGENT_DIR" diff HEAD -- identity/ 2>/dev/null | wc -l | tr -d ' ')
        if [ "$DIRTY" -gt 0 ]; then
            audit LOW "Bootstrap modifié (non commité)" "git diff détecte des changements"
        else
            audit OK "Bootstrap sous contrôle de version" "aucune modification non commitée"
        fi
    else
        audit INFO "Contrôle de version identity" "git non initialisé"
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 4 — Channel Access Control
# ══════════════════════════════════════════════════
if section 4 "Channel Access Control"; then

    GW="$IAGENT_DIR/gateway/telegram_gateway.py"

    # 4a. Whitelist Telegram stricte
    if [ -f "$GW" ]; then
        HAS_AUTH=$(grep -cE "_is_authorized|whitelist" "$GW" 2>/dev/null)
        HAS_WILD=$(grep -cE 'whitelist.*[*]|chat_id\s*=\s*["\x27][*]|"[*]"' "$GW" 2>/dev/null)
        if [ "$HAS_AUTH" -ge 1 ] && [ "$HAS_WILD" -eq 0 ]; then
            audit OK "Whitelist Telegram stricte" "pas de wildcard"
        elif [ "$HAS_WILD" -gt 0 ]; then
            audit CRITICAL "Whitelist contient un wildcard" "tous les expéditeurs acceptés"
        else
            audit CRITICAL "Whitelist absente" "aucune vérification d'expéditeur"
        fi
    else
        audit CRITICAL "telegram_gateway.py manquant" "impossible de vérifier la whitelist"
    fi

    # 4b. Rejet silencieux (pas de réponse aux non-autorisés)
    if [ -f "$GW" ]; then
        # Vérifie que le return est après le check d'autorisation sans send_message
        SILENT=$(grep -A2 "not _is_authorized\|non autorisé" "$GW" 2>/dev/null | grep -c "return")
        if [ "$SILENT" -ge 1 ]; then
            audit OK "Rejet silencieux" "pas de réponse aux non-autorisés"
        else
            audit HIGH "Réponse aux non-autorisés" "confirme l'existence du bot"
        fi
    fi

    # 4c. Isolation session par chat_id
    SM="$IAGENT_DIR/core/session_manager.py"
    if [ -f "$SM" ]; then
        ISOLATION=$(grep -cE "chat_id" "$SM" 2>/dev/null)
        if [ "$ISOLATION" -ge 3 ]; then
            audit OK "Isolation session par chat_id" "UUID distinct par expéditeur"
        else
            audit HIGH "Isolation session insuffisante" "vérifier session_manager.py"
        fi
    else
        audit HIGH "session_manager.py manquant" "impossible de vérifier l'isolation"
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 5 — Excessive Agency / Tool Abuse
# ══════════════════════════════════════════════════
if section 5 "Excessive Agency / Tool Abuse"; then

    RUNNER="$IAGENT_DIR/core/claude_runner.py"

    # 5a. --tools "" actif (isolation Claude)
    if [ -f "$RUNNER" ]; then
        TOOLS_EMPTY=$(grep -c '"--tools", ""' "$RUNNER" 2>/dev/null)
        if [ "$TOOLS_EMPTY" -ge 1 ]; then
            audit OK '--tools "" actif' "Claude ne peut pas exécuter de code"
        else
            audit CRITICAL '--tools "" absent' "Claude a accès aux outils système"
        fi
    else
        audit CRITICAL "claude_runner.py manquant" "impossible de vérifier l'isolation"
    fi

    # 5b. --output-format json
    if [ -f "$RUNNER" ]; then
        JSON_FMT=$(grep -c '"--output-format", "json"' "$RUNNER" 2>/dev/null)
        if [ "$JSON_FMT" -ge 1 ]; then
            audit OK "--output-format json actif" "réponses structurées"
        else
            audit MEDIUM "--output-format json absent" "sortie texte brut"
        fi
    fi

    # 5c. Pas d'écriture dans context_builder
    CB="$IAGENT_DIR/core/context_builder.py"
    if [ -f "$CB" ]; then
        WRITES=$(grep -cE 'write_text|write_bytes|open\(.*"w"|open\(.*"a"' "$CB" 2>/dev/null)
        if [ "$WRITES" -eq 0 ]; then
            audit OK "context_builder en lecture seule" "pas d'écriture dans identity"
        else
            audit CRITICAL "context_builder peut écrire" "risque de memory poisoning (ASI06)"
        fi
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 6 — Rate Limiting & Resource Exhaustion
# ══════════════════════════════════════════════════
if section 6 "Rate Limiting & Resource Exhaustion"; then

    RUNNER="$IAGENT_DIR/core/claude_runner.py"
    HB="$IAGENT_DIR/tasks/heartbeat.py"
    GW="$IAGENT_DIR/gateway/telegram_gateway.py"

    # 6a. Timeout configuré sur les appels Claude CLI
    if [ -f "$RUNNER" ]; then
        TIMEOUT=$(grep -cE "timeout" "$RUNNER" 2>/dev/null)
        if [ "$TIMEOUT" -ge 2 ]; then
            audit OK "Timeout configuré" "présent dans run() et run_session()"
        else
            audit HIGH "Timeout manquant" "risque de service gelé"
        fi
    fi

    # 6b. Protection boucle heartbeat
    if [ -f "$HB" ]; then
        ANTI_LOOP=$(grep -cE "lastChecks|monotonic" "$HB" 2>/dev/null)
        if [ "$ANTI_LOOP" -ge 2 ]; then
            audit OK "Protection boucle heartbeat" "rotation par timestamp"
        else
            audit MEDIUM "Protection boucle insuffisante" "risque de boucle d'erreur"
        fi
    fi

    # 6c. Whitelist vérifiée AVANT appel LLM
    if [ -f "$GW" ]; then
        # Chercher l'appel _is_authorized (pas la définition) et l'appel run_session (pas l'import)
        LINE_AUTH=$(grep -n "if.*_is_authorized\|if not _is_authorized" "$GW" 2>/dev/null | head -1 | cut -d: -f1)
        LINE_LLM=$(grep -n "= run_session\|response.*run_session" "$GW" 2>/dev/null | head -1 | cut -d: -f1)
        if [ -n "$LINE_AUTH" ] && [ -n "$LINE_LLM" ]; then
            if [ "$LINE_AUTH" -lt "$LINE_LLM" ]; then
                audit OK "Whitelist vérifiée avant appel LLM" "ligne $LINE_AUTH < $LINE_LLM"
            else
                audit CRITICAL "Whitelist vérifiée APRÈS appel LLM" "consommation de tokens par inconnus"
            fi
        else
            audit MEDIUM "Vérification ordre whitelist/LLM" "impossible à déterminer"
        fi
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 7 — Session Security
# ══════════════════════════════════════════════════
if section 7 "Session Security"; then

    RUNNER="$IAGENT_DIR/core/claude_runner.py"

    # 7a. --no-session-persistence en mode one-shot
    if [ -f "$RUNNER" ]; then
        NO_PERSIST=$(grep -c "no-session-persistence" "$RUNNER" 2>/dev/null)
        if [ "$NO_PERSIST" -ge 1 ]; then
            audit OK "--no-session-persistence (one-shot)" "sessions jetables"
        else
            audit MEDIUM "--no-session-persistence absent" "sessions one-shot écrites sur disque"
        fi
    fi

    # 7b. Permissions ~/.claude/
    if [ -d "$HOME/.claude" ]; then
        CLAUDE_PERM=$(get_perms "$HOME/.claude")
        CLAUDE_OTHER=${CLAUDE_PERM: -1}
        if [ "$CLAUDE_OTHER" -gt 0 ]; then
            audit HIGH "Permissions ~/.claude/" "mode $CLAUDE_PERM (world-readable)" "chmod 700 \"$HOME/.claude\""
        else
            audit OK "Permissions ~/.claude/" "mode $CLAUDE_PERM"
        fi
    fi

    # 7c. Taille sessions accumulées
    if [ -d "$HOME/.claude/projects" ]; then
        SESSION_MB=$(du -sm "$HOME/.claude/projects" 2>/dev/null | awk '{print $1}')
        if [ "${SESSION_MB:-0}" -gt 500 ]; then
            audit MEDIUM "Sessions accumulées" "${SESSION_MB} Mo (> 500 Mo)"
        elif [ "${SESSION_MB:-0}" -gt 100 ]; then
            audit LOW "Sessions accumulées" "${SESSION_MB} Mo (> 100 Mo)"
        else
            audit OK "Sessions accumulées" "${SESSION_MB:-0} Mo"
        fi
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 8 — Network Exposure
# ══════════════════════════════════════════════════
if section 8 "Network Exposure"; then

    GW="$IAGENT_DIR/gateway/telegram_gateway.py"

    # 8a. Telegram en mode polling (pas webhook)
    if [ -f "$GW" ]; then
        POLLING=$(grep -c "run_polling" "$GW" 2>/dev/null)
        WEBHOOK=$(grep -ciE "webhook|set_webhook" "$GW" 2>/dev/null)
        if [ "$POLLING" -ge 1 ] && [ "$WEBHOOK" -eq 0 ]; then
            audit OK "Mode polling actif" "aucun port exposé"
        elif [ "$WEBHOOK" -gt 0 ]; then
            audit HIGH "Webhook détecté" "endpoint HTTP exposé sur internet"
        else
            audit MEDIUM "Mode réseau indéterminé" "vérifier telegram_gateway.py"
        fi
    fi

    # 8b. Ports Python ouverts sur interface publique
    PY_PORTS=$(lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -i python | grep -v "127.0.0.1\|::1\|\[::1\]" | wc -l | tr -d ' ')
    if [ "$PY_PORTS" -gt 0 ]; then
        audit CRITICAL "Port Python public ouvert" "$PY_PORTS processus"
    else
        audit OK "Aucun port Python public" "pas d'exposition réseau"
    fi

    # 8c. mDNS/Bonjour
    MDNS=$(grep -rlE "mdns|bonjour|zeroconf|avahi" --include="*.py" "$IAGENT_DIR/" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MDNS" -gt 0 ]; then
        audit LOW "Publication mDNS détectée" "service annoncé sur le réseau local"
    else
        audit INFO "Pas de publication mDNS" ""
    fi
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 9 — Supply Chain
# ══════════════════════════════════════════════════
if section 9 "Supply Chain"; then

    # 9a. Dépendances pip à jour
    PTB_OUTDATED=$(pip3 list --outdated 2>/dev/null | grep -c "python-telegram-bot" || true)
    if [ "$PTB_OUTDATED" -gt 0 ]; then
        audit LOW "python-telegram-bot obsolète" "mise à jour disponible"
    else
        audit OK "python-telegram-bot à jour" ""
    fi

    # 9b. Imports tiers minimaux
    UNEXPECTED=$("$PYTHON_PATH" -c "
import ast, pathlib, sys
# Modules stdlib Python (liste partielle mais suffisante)
STDLIB = {
    'abc','argparse','ast','asyncio','base64','collections','configparser',
    'copy','csv','ctypes','dataclasses','datetime','email','enum','functools',
    'glob','hashlib','html','http','importlib','inspect','io','itertools',
    'json','logging','math','multiprocessing','operator','os','pathlib',
    'locale',
    'pickle','platform','plistlib','posixpath','pprint','queue','random',
    're','shutil','signal','socket','sqlite3','ssl','string','struct',
    'subprocess','sys','tempfile','textwrap','threading','time','traceback',
    'typing','unittest','urllib','uuid','warnings','xml','zipfile'
}
ALLOWED_THIRD = {'telegram', 'requests'}
INTERNAL = {'core', 'agents', 'tasks', 'gateway', 'projects', 'skills'}
root = pathlib.Path('$IAGENT_DIR')
unexpected = set()
for d in ['core','agents','tasks','gateway']:
    for f in (root / d).rglob('*.py'):
        try:
            tree = ast.parse(f.read_text())
        except: continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split('.')[0]
                    if top not in STDLIB and top not in ALLOWED_THIRD and top not in INTERNAL:
                        unexpected.add(top)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split('.')[0]
                if top not in STDLIB and top not in ALLOWED_THIRD and top not in INTERNAL:
                    unexpected.add(top)
if unexpected:
    print(' '.join(sorted(unexpected)))
" 2>/dev/null || echo "")
    if [ -n "$UNEXPECTED" ]; then
        audit MEDIUM "Imports tiers inattendus" "$UNEXPECTED"
    else
        audit OK "Imports tiers minimaux" "uniquement telegram + requests"
    fi

    # 9c. Intégrité hash fichiers critiques
    INTEGRITY="$IAGENT_DIR/data/integrity.json"
    HASH_RESULT=$("$PYTHON_PATH" -c "
import hashlib, json, pathlib, sys
root = pathlib.Path('$IAGENT_DIR')
files = [
    'core/claude_runner.py', 'core/session_manager.py',
    'gateway/telegram_gateway.py', 'tasks/heartbeat.py'
]
current = {}
for f in files:
    p = root / f
    if p.exists():
        current[f] = hashlib.sha256(p.read_bytes()).hexdigest()
integrity = root / 'data' / 'integrity.json'
if integrity.exists():
    baseline = json.loads(integrity.read_text())
    changed = [f for f in files if current.get(f) != baseline.get(f)]
    if changed:
        print('CHANGED:' + ' '.join(changed))
    else:
        print('OK')
else:
    integrity.write_text(json.dumps(current, indent=2))
    print('CREATED')
" 2>/dev/null || echo "ERROR")
    case "$HASH_RESULT" in
        OK)      audit OK "Intégrité fichiers critiques" "hash conforme à la baseline" ;;
        CREATED) audit INFO "Baseline intégrité créée" "data/integrity.json initialisé" ;;
        CHANGED*) audit MEDIUM "Hash modifié" "${HASH_RESULT#CHANGED:}" ;;
        *)       audit LOW "Vérification intégrité" "impossible (erreur Python)" ;;
    esac
fi

# ══════════════════════════════════════════════════
# CATÉGORIE 10 — Incident Response Readiness
# ══════════════════════════════════════════════════
if section 10 "Incident Response Readiness"; then

    # 10a. Backup git présent et récent
    if git -C "$IAGENT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        LAST_COMMIT=$(git -C "$IAGENT_DIR" log -1 --format="%ar" 2>/dev/null)
        DAYS_AGO=$(git -C "$IAGENT_DIR" log -1 --format="%ct" 2>/dev/null)
        NOW=$(date +%s)
        DIFF_DAYS=$(( (NOW - DAYS_AGO) / 86400 ))
        if [ "$DIFF_DAYS" -gt 7 ]; then
            audit LOW "Dernier commit ancien" "$LAST_COMMIT"
        else
            audit OK "Backup git récent" "$LAST_COMMIT"
        fi
    else
        audit MEDIUM "Pas de contrôle de version" "git non initialisé"
    fi

    # 10b. Procédure de rotation des tokens documentée
    ROT=$(grep -ciE "rotation|révoquer|revoke|urgence" "$IAGENT_DIR/docs/install/guide-installation.md" 2>/dev/null || echo 0)
    if [ "$ROT" -gt 0 ]; then
        audit OK "Procédure rotation documentée" "$ROT mention(s)"
    else
        audit LOW "Procédure rotation absente" "ajouter dans docs/install/guide-installation.md"
    fi

    # 10c. Logs disponibles pour audit
    LOGS_OK=0; LOGS_TOTAL=3
    for LOG in runner.log heartbeat.log telegram.log; do
        [ -s "$IAGENT_DIR/logs/$LOG" ] && LOGS_OK=$((LOGS_OK+1))
    done
    if [ "$LOGS_OK" -eq "$LOGS_TOTAL" ]; then
        audit OK "Logs disponibles" "$LOGS_OK/$LOGS_TOTAL non vides"
    elif [ "$LOGS_OK" -gt 0 ]; then
        audit LOW "Logs partiels" "$LOGS_OK/$LOGS_TOTAL non vides"
    else
        audit LOW "Logs vides ou absents" "aucun log exploitable"
    fi
fi

# ══════════════════════════════════════════════════
# RÉSUMÉ
# ══════════════════════════════════════════════════
TOTAL_ISSUES=$((CRITICAL + HIGH + MEDIUM + LOW))
TOTAL_CHECKS=$((TOTAL_ISSUES + OK_COUNT))

if $JSON_MODE; then
    # Retirer la virgule finale des items JSON
    JSON_ITEMS="${JSON_ITEMS%,}"
    cat <<ENDJSON
{
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "critical": $CRITICAL,
  "high": $HIGH,
  "medium": $MEDIUM,
  "low": $LOW,
  "passed": $OK_COUNT,
  "total": $TOTAL_CHECKS,
  "checks": [$JSON_ITEMS]
}
ENDJSON
else
    echo
    echo "════════════════════════════════════════════════"
    [ "$CRITICAL" -gt 0 ] && echo "🔴 $CRITICAL critique(s)  — corriger IMMÉDIATEMENT"
    [ "$HIGH" -gt 0 ]     && echo "🟠 $HIGH élevé(s)        — corriger dans les 24h"
    [ "$MEDIUM" -gt 0 ]   && echo "🟡 $MEDIUM moyen(s)       — planifier cette semaine"
    [ "$LOW" -gt 0 ]      && echo "🔵 $LOW faible(s)        — amélioration optionnelle"
    echo "✓  $OK_COUNT/$TOTAL_CHECKS vérifications passées"
    echo
    if [ "$CRITICAL" -eq 0 ] && [ "$HIGH" -eq 0 ]; then
        echo "Posture : ACCEPTABLE — aucun risque immédiat"
    elif [ "$CRITICAL" -eq 0 ]; then
        echo "Posture : ATTENTION — risques élevés à corriger"
    else
        echo "Posture : RISQUE — corriger les critiques avant toute utilisation"
    fi
    echo
fi

exit $(( (CRITICAL + HIGH) > 0 ? 1 : 0 ))
