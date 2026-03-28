# RUNBOOK — Guide d'installation iAgent
> Document payant — ne pas distribuer

## Table des matières
1. Prérequis système
2. Installation Claude Code CLI
3. Création du bot Telegram
4. Configuration Google OAuth (gog)
5. Installation iAgent
6. Configuration .env
7. Personnalisation identity/
8. Démarrage et vérification
9. LaunchAgents (démarrage automatique)
10. Commandes disponibles
11. Dépannage

## 1. Prérequis système

### macOS
- macOS 12 Monterey ou supérieur
- Python 3.11+ : [instructions]
- Homebrew : [instructions]
- ffmpeg : `brew install ffmpeg`

### Compte Anthropic
- Forfait Max requis (claude.ai/upgrade)
- Installer Claude Code CLI :
  `curl -fsSL https://claude.ai/install.sh | bash`
- S'authentifier : `claude auth login`

## 2. Création du bot Telegram

1. Ouvrir Telegram → chercher @BotFather
2. `/newbot` → suivre les instructions
3. Copier le token dans `.env` → `TELEGRAM_BOT_TOKEN_KINTO_UN`
4. Obtenir ton chat_id via @userinfobot
5. Copier dans `.env` → `TELEGRAM_CHAT_ID_ALERTES`

## 3. Configuration Google OAuth (gog)

[À compléter — instructions gog auth login]

## 4. Installation iAgent
```bash
git clone https://github.com/man-orangepeel/iagent ~/.iagent
cd ~/.iagent
pip install -r requirements.txt
cp .env.example .env
# Remplir .env
```

## 5-11. [À compléter]

---
*Version 1.0 — 2026-03-28*
