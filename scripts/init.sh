#!/bin/bash
# init.sh — Initialisation workspace iAgent
# Copie les templates identity/*.template.md → fichiers live
# Crée .env depuis .env.example si absent
# Crée les dossiers nécessaires

set -e
IAGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$IAGENT_DIR"

echo "=== Initialisation iAgent ==="

# 1. Copier les templates identity/
for f in IDENTITY SOUL USER MEMORY; do
    template="identity/${f}.template.md"
    target="identity/${f}.md"
    if [ ! -f "$template" ]; then
        echo "⚠  Template absent : $template"
        continue
    fi
    if [ -f "$target" ]; then
        LINES=$(wc -l < "$target" | tr -d ' ')
        if [ "$LINES" -gt 5 ]; then
            echo "⏭  $target existe et semble personnalisé — ignoré"
            continue
        fi
    fi
    cp "$template" "$target"
    echo "✓  Créé : $target"
done

# 2. Créer .env depuis .env.example si absent
if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "✓  Créé : .env (à remplir)"
else
    echo "⏭  .env existe déjà — ignoré"
fi

# 3. Créer les dossiers nécessaires
mkdir -p logs tmp/audio tmp/documents data/memory \
         projects/personal_assistant/state
echo "✓  Dossiers créés"

# 4. Créer tracking.json si absent
TRACKING="projects/personal_assistant/state/tracking.json"
if [ ! -f "$TRACKING" ]; then
    printf '{"date":"","awaiting_response":false,"brief_snapshot":{"events":[],"unread_mails":[]},"reminders":[],"renotify_mails":[]}' \
        > "$TRACKING"
    echo "✓  Créé : $TRACKING"
fi

echo ""
echo "=== Prochaines étapes ==="
echo "1. Remplir .env (IAGENT_BOT_TOKEN + IAGENT_CHAT_ID)"
echo "2. Authentifier Claude : claude auth login"
echo "3. Authentifier gog : gog auth login"
echo "4. Personnaliser identity/IDENTITY.md, SOUL.md, USER.md"
echo "5. Adapter CLAUDE.md : cp identity/CLAUDE-template.md CLAUDE.md"
echo "6. Vérifier : python3 gateway/telegram_gateway.py --dry-run"
