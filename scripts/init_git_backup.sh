#!/bin/bash
# init_git_backup.sh — Initialise la sauvegarde git de iAgent
# Crée un .gitignore sécurisé avant de commiter

set -e
cd ~/.iagent

if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Git déjà initialisé."
    exit 0
fi

# Créer .gitignore AVANT git init
cat > .gitignore << 'EOF'
# Credentials — NE JAMAIS commiter
.env
*.env
credentials/
identity/
*.pem
*.key

# Logs — trop volumineux et rotatifs
logs/*.log
logs/*.log.*

# Sessions et données runtime
data/sessions.json
data/memory/heartbeat-state.json
data/memory/*.md

# Intégrité (régénéré au runtime)
data/integrity.json

# Claude CLI local
.claude/

# Cache Python
__pycache__/
*.pyc
*.pyo

# macOS
.DS_Store
.Spotlight-V100
.Trashes
EOF

git init
git add .
git commit -m "init: iAgent backup initial"
echo
echo "✓ Backup git initialisé."
echo "  Pousser vers un dépôt PRIVÉ uniquement :"
echo "  git remote add origin <url-depot-prive>"
echo "  git push -u origin main"
