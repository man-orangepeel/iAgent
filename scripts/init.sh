#!/bin/bash
# init.sh — Initialisation workspace iAgent
# Crée .env depuis .env.example si absent
# Crée les dossiers nécessaires
# Les fichiers identity/*.md sont déjà dans le repo — ne pas les écraser

set -e
IAGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$IAGENT_DIR"

echo "=== Initialisation iAgent ==="

# 1. Créer .env depuis .env.example si absent
if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env
    echo "✓  Créé : .env (à remplir)"
else
    echo "⏭  .env existe déjà — ignoré"
fi

# 2. Créer les dossiers nécessaires
mkdir -p logs tmp/audio tmp/documents data/memory \
         projects/personal_assistant/state
echo "✓  Dossiers créés"

# 3. Créer tracking.json si absent
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
echo "4. Adapter CLAUDE.md : cp identity/CLAUDE-template.md CLAUDE.md"
echo "5. Vérifier : python3 gateway/telegram_gateway.py --dry-run"
echo "6. Démarrer et envoyer un premier message — l'agent guide la suite"
