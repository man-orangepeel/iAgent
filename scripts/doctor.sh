#!/bin/bash
# doctor.sh v2.1 — Diagnostic santé iAgent (17 checks)
#
# Usage :
#   bash scripts/doctor.sh           # complet (17 checks)
#   bash scripts/doctor.sh --quick   # sans appels réseau (14 checks)

set -uo pipefail

IAGENT_DIR="$HOME/.iagent"
PASS=0; FAIL=0; WARN=0; SKIP=0
QUICK=false
[ "${1:-}" = "--quick" ] && QUICK=true

check() { # label, result (0=OK), detail
    if [ "$2" -eq 0 ]; then
        echo "  ✓ $1"; [ -n "${3:-}" ] && echo "    $3"; PASS=$((PASS+1))
    else
        echo "  ✗ $1"; [ -n "${3:-}" ] && echo "    $3"; FAIL=$((FAIL+1))
    fi
}
warn() { echo "  ⚠ $1"; [ -n "${2:-}" ] && echo "    $2"; WARN=$((WARN+1)); PASS=$((PASS+1)); }
skip() { echo "  ⊘ $1 (sauté — mode quick)"; SKIP=$((SKIP+1)); }

CLAUDE_PATH=$(which claude 2>/dev/null \
  || ([ -f "$HOME/.npm-global/bin/claude" ] && echo "$HOME/.npm-global/bin/claude") \
  || true)
PYTHON_PATH=$(which python3 2>/dev/null || true)
ENV_FILE="$HOME/.iagent/.env"

echo "=== iAgent Doctor v2.1 ==="
echo

# ── Environnement ──────────────────────────────
echo "── Environnement ──"

# 1. Claude CLI
if [ -n "$CLAUDE_PATH" ]; then
    CV=$("$CLAUDE_PATH" --version 2>/dev/null || echo "?")
    AUTH=$("$CLAUDE_PATH" auth status 2>/dev/null | grep -c '"loggedIn": true' || echo 0)
    [ "$AUTH" -gt 0 ] && check "Claude CLI" 0 "$CV — authentifié" \
                      || check "Claude CLI" 1 "$CV — NON authentifié (claude auth login)"
else
    check "Claude CLI" 1 "Introuvable (npm install -g @anthropic-ai/claude-code)"
fi

# 2. Python
if [ -n "$PYTHON_PATH" ]; then
    check "Python" 0 "$(python3 --version 2>/dev/null) — $PYTHON_PATH"
else
    check "Python" 1 "python3 introuvable"
fi
echo

# ── Fichiers & Configuration ───────────────────
echo "── Fichiers & Configuration ──"

# 3. Dossiers critiques
MISS=""
for d in identity skills data logs config core tasks gateway; do
    [ ! -d "$IAGENT_DIR/$d" ] && MISS="$MISS $d"
done
[ -z "$MISS" ] && check "Dossiers critiques" 0 "8/8" \
               || check "Dossiers critiques" 1 "Manquants :$MISS"

# 4. Bootstrap
BC=$(ls "$IAGENT_DIR/identity/"*.md 2>/dev/null | wc -l | tr -d ' ')
[ "$BC" -ge 9 ] && check "Bootstrap" 0 "$BC fichiers identity" \
                 || check "Bootstrap" 1 "$BC/9 (attendu: >= 9)"

# 5. Config parseable
if [ -f "$IAGENT_DIR/config/iagent.json" ]; then
    cd "$IAGENT_DIR" && python3 -c "from core.config import get_config; get_config()" 2>/dev/null \
        && check "iagent.json" 0 "Parseable" \
        || check "iagent.json" 1 "JSON invalide"
else
    check "iagent.json" 1 "Absent"
fi

# 6. Credentials
if [ -f "$ENV_FILE" ]; then
    COK=0
    for v in IAGENT_BOT_TOKEN IAGENT_CHAT_ID; do
        grep -q "^$v=" "$ENV_FILE" 2>/dev/null || COK=1
    done
    [ "$COK" -eq 0 ] && check "Credentials .env" 0 "Tokens présents ($ENV_FILE)" \
                      || check "Credentials .env" 1 "Token manquant dans $ENV_FILE"
else
    check "Credentials .env" 1 "Aucun .env trouvé"
fi

# 16. Validation valeurs config
if [ -n "$PYTHON_PATH" ] && [ -f "$IAGENT_DIR/config/iagent.json" ]; then
    CFG_RESULT=$(cd "$IAGENT_DIR" && python3 -c "
import json, os
from pathlib import Path
c = json.loads(Path('config/iagent.json').read_text())
issues = []
ttl = c.get('session',{}).get('ttl_hours',0)
if ttl <= 0: issues.append(f'session.ttl_hours={ttl}')
sz = c.get('session',{}).get('max_size_kb',0)
if sz <= 0: issues.append(f'session.max_size_kb={sz}')
t = c.get('heartbeat',{}).get('timeout_seconds',0)
if not (10<=t<=300): issues.append(f'heartbeat.timeout={t}')
mx = c.get('context',{}).get('max_chars',0)
if not (1000<=mx<=150000): issues.append(f'context.max_chars={mx}')
pp = c.get('python_path','')
if pp and not Path(pp).exists():
    real = os.popen('which python3').read().strip()
    issues.append(f'python_path introuvable (réel: {real})')
print('|'.join(issues) if issues else 'OK')
" 2>/dev/null)
    [ "$CFG_RESULT" = "OK" ] && check "Valeurs config" 0 "Cohérentes" \
                              || check "Valeurs config" 1 "$CFG_RESULT"
fi
echo

# ── Services ───────────────────────────────────
echo "── Services ──"

# 7. LaunchAgents chargés
AL=$(launchctl list 2>/dev/null | grep -c "com.iagent" || true)
AL=${AL:-0}
[ "$AL" -ge 2 ] && check "LaunchAgents" 0 "$AL/2 chargés" \
                 || check "LaunchAgents" 1 "$AL/2 (bash scripts/install_launchagents.sh)"

# 7b. Instance unique gateway (détecte les processus fantômes)
GW_COUNT=$(ps aux | grep "[t]elegram_gateway.py" | wc -l | tr -d ' ')
if [ "$GW_COUNT" -eq 1 ]; then
    check "Instance gateway" 0 "1 processus"
elif [ "$GW_COUNT" -eq 0 ]; then
    warn "Instance gateway" "Aucun processus telegram_gateway.py"
else
    check "Instance gateway" 1 "$GW_COUNT processus — tuer les doublons (ps aux | grep telegram_gateway)"
fi

# 13. Drift plists (comparaison via plistlib)
DRIFT_OK=true
for pn in com.iagent.heartbeat com.iagent.telegram; do
    SRC="$IAGENT_DIR/launchagents/${pn}.plist"
    INST="$HOME/Library/LaunchAgents/${pn}.plist"
    [ ! -f "$SRC" ] || [ ! -f "$INST" ] && continue
    DRIFT=$(python3 -c "
import plistlib, os, re
from pathlib import Path
def kv(p, normalize=False):
    try:
        text = Path(p).read_text()
        if normalize:
            text = re.sub(r'/Users/USERNAME', '/Users/' + os.environ.get('USER','USERNAME'), text)
        pl = plistlib.loads(text.encode())
        return {'program': pl.get('ProgramArguments',[]), 'path': pl.get('EnvironmentVariables',{}).get('PATH',''),
                'interval': pl.get('StartInterval',0), 'keepalive': pl.get('KeepAlive',False)}
    except: return None
s, i = kv('$SRC', normalize=True), kv('$INST')
if s is None or i is None: print('PARSE_ERROR')
elif s == i: print('OK')
else:
    diffs = [f'{k}: src={s[k]} vs inst={i.get(k)}' for k in s if s[k] != i.get(k)]
    print('DRIFT:' + ' | '.join(diffs))
" 2>/dev/null)
    case "$DRIFT" in
        OK) ;;
        DRIFT:*) DRIFT_OK=false; check "Drift $pn" 1 "${DRIFT#DRIFT:} → bash scripts/install_launchagents.sh" ;;
        *) DRIFT_OK=false; warn "Drift $pn" "Comparaison impossible" ;;
    esac
done
$DRIFT_OK && check "Drift plists" 0 "Valeurs fonctionnelles identiques"

# 14. Python absolu + claude dans PATH (via plistlib)
PLIST_OK=true
for pn in com.iagent.heartbeat com.iagent.telegram; do
    INST="$HOME/Library/LaunchAgents/${pn}.plist"
    [ ! -f "$INST" ] && continue
    PP=$(python3 -c "
import plistlib; from pathlib import Path
try:
    pl = plistlib.loads(Path('$INST').read_bytes())
    args = pl.get('ProgramArguments',[])
    print(args[0] if args else '')
except: print('')
" 2>/dev/null)
    if [ -n "$PP" ] && [ ! -f "$PP" ]; then
        check "Python plist $pn" 1 "'$PP' introuvable"; PLIST_OK=false
    fi
    if [ -n "$CLAUDE_PATH" ]; then
        CD=$(dirname "$CLAUDE_PATH")
        PLIST_PATH=$(python3 -c "
import plistlib; from pathlib import Path
try:
    pl = plistlib.loads(Path('$INST').read_bytes())
    print(pl.get('EnvironmentVariables',{}).get('PATH',''))
except: print('')
" 2>/dev/null)
        if [ -n "$PLIST_PATH" ] && ! echo "$PLIST_PATH" | grep -q "$CD"; then
            check "Claude PATH $pn" 1 "'$CD' absent du PATH plist"; PLIST_OK=false
        fi
    fi
done
$PLIST_OK && check "Paths plists" 0 "Python absolu + claude dans PATH"
echo

# ── Connectivité Telegram ──────────────────────
echo "── Connectivité Telegram ──"

# 11. Gateway probe (urllib, pas requests)
if $QUICK; then
    skip "Gateway probe"
else
    GL=$(launchctl list 2>/dev/null | grep "com.iagent.telegram" || true)
    if [ -n "$GL" ]; then
        GP=$(echo "$GL" | awk '{print $1}')
        GE=$(echo "$GL" | awk '{print $2}')
        if [ "$GP" != "-" ]; then
            if [ -n "$PYTHON_PATH" ] && [ -f "$ENV_FILE" ]; then
                API_RESULT=$(python3 -c "
import urllib.request, json, ssl
from pathlib import Path
token = None
for line in Path('$ENV_FILE').read_text().splitlines():
    if line.startswith('IAGENT_BOT_TOKEN='):
        token = line.split('=',1)[1].strip()
if not token: print('TOKEN_ABSENT'); exit()
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f'https://api.telegram.org/bot{token}/getMe'
    resp = urllib.request.urlopen(url, timeout=5, context=ctx)
    data = json.loads(resp.read())
    if data.get('ok'):
        print(f'OK:{data.get(\"result\",{}).get(\"username\",\"?\")}')
    else: print('API_ERROR')
except Exception: print('UNREACHABLE')
" 2>/dev/null)
                case "$API_RESULT" in
                    OK:*) check "Gateway probe" 0 "PID $GP — @${API_RESULT#OK:} connecté" ;;
                    TOKEN_ABSENT) check "Gateway probe" 1 "Token absent du .env" ;;
                    *) check "Gateway probe" 1 "PID $GP mais API injoignable" ;;
                esac
            else
                check "Gateway probe" 0 "PID $GP actif"
            fi
        else
            [ "$GE" = "0" ] && warn "Gateway" "Arrêté proprement (exit 0) — inactif" \
                            || check "Gateway probe" 1 "Crashé (exit $GE) — voir logs/telegram_error.log"
        fi
    else
        check "Gateway probe" 1 "Service non chargé"
    fi
fi

# 12. Fraîcheur polling
if $QUICK; then
    skip "Fraîcheur polling"
else
    TL=""
    for tf in "$IAGENT_DIR/logs/telegram_error.log" "$IAGENT_DIR/logs/telegram.log"; do
        if [ -f "$tf" ] && [ -s "$tf" ]; then TL="$tf"; break; fi
    done
    if [ -n "$TL" ]; then
        LA=$(stat -f %m "$TL" 2>/dev/null || stat -c %Y "$TL" 2>/dev/null || echo 0)
        AGE_MIN=$(( ($(date +%s) - LA) / 60 ))
        if [ "$AGE_MIN" -lt 30 ]; then
            check "Fraîcheur polling" 0 "Log actif il y a ${AGE_MIN}min"
        else
            GW_PID=$(launchctl list 2>/dev/null | grep "com.iagent.telegram" | awk '{print $1}')
            if [ -n "$GW_PID" ] && [ "$GW_PID" != "-" ]; then
                warn "Fraîcheur polling" "Log silencieux ${AGE_MIN}min (PID $GW_PID actif — normal)"
            else
                check "Fraîcheur polling" 1 "Silencieux ${AGE_MIN}min sans PID actif"
            fi
        fi
    else
        warn "Fraîcheur polling" "Log vide ou absent"
    fi
fi
echo

# ── Heartbeat ──────────────────────────────────
echo "── Heartbeat ──"

# 8. Dernier heartbeat
if [ -f "$IAGENT_DIR/data/memory/heartbeat-state.json" ] && [ -n "$PYTHON_PATH" ]; then
    HA=$(python3 -c "
import json, time
d = json.load(open('$IAGENT_DIR/data/memory/heartbeat-state.json'))
c = {k:v for k,v in d.get('lastChecks',{}).items() if k in ('queue_work','soul_evil','memory_distill','proactive')}
if not c: print(-1)
else: print(f'{(time.time()*1000-max(c.values()))/3600000:.1f}')
" 2>/dev/null)
    if [ "$HA" = "-1" ]; then check "Dernier heartbeat" 1 "Aucun enregistré"
    elif python3 -c "exit(0 if float('$HA')<3 else 1)" 2>/dev/null; then check "Dernier heartbeat" 0 "Il y a ${HA}h"
    else check "Dernier heartbeat" 1 "Il y a ${HA}h (> 3h)"
    fi
else
    check "Dernier heartbeat" 1 "heartbeat-state.json absent"
fi

# 9. Budget bootstrap
if [ -n "$PYTHON_PATH" ]; then
    BU=$(cd "$IAGENT_DIR" && python3 -c "
from core.context_builder import build
t=len(build('telegram_session')); print(f'{t} chars / 38000 ({t*100//38000}%)')
" 2>/dev/null)
    [ -n "$BU" ] && check "Budget identity" 0 "$BU" \
                  || check "Budget identity" 1 "Erreur de calcul"
fi
echo

# ── Sécurité ───────────────────────────────────
echo "── Sécurité ──"

# 10. Tokens dans les logs
TK=0
if ls "$IAGENT_DIR/logs/"*.log >/dev/null 2>&1; then
    TK=$(grep -rE "[0-9]{8,10}:[A-Za-z0-9_-]{35}" "$IAGENT_DIR/logs/"*.log 2>/dev/null | wc -l | tr -d ' ')
fi
[ "$TK" -eq 0 ] && check "Tokens dans logs" 0 "Aucune fuite" \
                 || check "Tokens dans logs" 1 "$TK occurrence(s) — nettoyer !"
echo

# ── Auth réelle (coûte ~1 token) ───────────────
echo "── Auth réelle ──"

# 15. Appel Claude réel
if $QUICK; then
    skip "Auth OAuth réelle"
else
    if [ -n "$PYTHON_PATH" ] && [ -n "$CLAUDE_PATH" ]; then
        ST=$(date +%s)
        CT=$(echo "ping" | "$CLAUDE_PATH" -p --no-session-persistence --output-format json --tools "" 2>/dev/null || echo "FAIL")
        DUR=$(( $(date +%s) - ST ))
        if echo "$CT" | grep -q '"result"'; then check "Auth OAuth réelle" 0 "Réponse en ${DUR}s"
        elif echo "$CT" | grep -qi "not logged in\|unauthorized"; then check "Auth OAuth réelle" 1 "Token expiré — claude auth login"
        elif echo "$CT" | grep -qi "rate.limit\|429"; then warn "Auth OAuth" "Rate limit actif (${DUR}s)"
        else check "Auth OAuth réelle" 1 "Échec après ${DUR}s"
        fi
    fi
fi
echo

# ── Sauvegarde ─────────────────────────────────
echo "── Sauvegarde ──"

# 17. Git
if git -C "$IAGENT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    LC=$(git -C "$IAGENT_DIR" log -1 --format="%ar" 2>/dev/null || echo "?")
    check "Backup git" 0 "Dernier commit : $LC"
else
    check "Backup git" 1 "Pas sous git"
    echo "    → bash scripts/init_git_backup.sh"
fi

# ── Résumé ─────────────────────────────────────
echo
CHECKED=$((PASS + FAIL))
TOTAL=$((CHECKED + SKIP))
if $QUICK; then
    echo "(mode quick — $SKIP check(s) sauté(s))"
fi
if [ "$FAIL" -eq 0 ]; then
    [ "$WARN" -gt 0 ] && echo "✓ $CHECKED/$CHECKED checks passés ($WARN avertissement(s))" \
                       || echo "✓ $CHECKED/$CHECKED — iAgent opérationnel"
    exit 0
else
    echo "✗ $PASS/$CHECKED checks passés — $FAIL problème(s)"
    exit 1
fi
