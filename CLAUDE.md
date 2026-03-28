<!-- RUNTIME — lu par Claude CLI gateway Telegram à chaque invocation -->
## Instructions runtime — Exécution directe

Tu as accès à Bash et WebSearch. Exécute directement,
ne dis jamais "je n'ai pas accès".

| Demande | Commande |
|---|---|
| emails, inbox, Gmail | `gog gmail search "<critères>" --max N --json` |
| exemples critères | `newer_than:7d`, `is:unread`, `from:exemple.com` |
| agenda, calendrier | `gog calendar list --days N` |
| doctor, diagnostic | `iagent doctor --quick` |
| sécurité, audit | `iagent security` |
| logs | `iagent logs telegram` |

Si tu hésites entre parler et exécuter → exécute.

---

<!-- DÉVELOPPEMENT — lu par Claude Code VSC uniquement -->
# iAgent — Contexte développement

## Description
Agent IA personnel générique opéré via Telegram.
Agent personnel autonome sur macOS.

## Stack
- Python 3.14+
- Claude Code CLI (forfait Max)
- python-telegram-bot
- gog (Google OAuth)
- whisper local

## Structure
- identity/   : personnalité et contexte (À PERSONNALISER)
- core/       : moteur technique
- skills/     : gog, telegram, ntfy, whisper, documents
- gateway/    : Telegram
- tasks/      : heartbeat
- projects/   : personal_assistant (morning_brief, reminder)
- scripts/    : doctor, security-audit, iagent dispatcher

## Avant de démarrer
1. Copier .env.example → .env et remplir les variables
2. Personnaliser identity/*.md
3. bash scripts/install_launchagents.sh
4. Voir RUNBOOK.md pour le guide complet
