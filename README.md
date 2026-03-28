# iAgent — Agent IA personnel via Telegram

Un agent IA autonome opéré via Telegram, propulsé par
Claude Code CLI. Chaîne des skills (web, email, calendrier,
fichiers, audio) à la demande, sans interface graphique.

## Ce que iAgent fait

- **Conversation** : répond à tes questions, cherche sur le web
- **Email** : lit et résume tes mails Gmail (non lus, par critères)
- **Calendrier** : consulte ton agenda Google
- **Fichiers** : lit et analyse PDF, DOCX
- **Audio** : transcrit tes messages vocaux Telegram
- **Brief matinal** : résumé agenda + mails à 7h45
- **Rappels** : notifications avant événements

## Stack technique

| Composant | Technologie |
|---|---|
| LLM | Claude Code CLI (forfait Max — 0 API payante) |
| Interface | Telegram (polling) |
| Email/Calendar | gog CLI (Google OAuth) |
| Transcription | Whisper local |
| Documents | pdfplumber, python-docx |
| Notifications | ntfy.sh |

## Installation rapide
```bash
git clone https://github.com/man-orangepeel/iagent ~/.iagent
cd ~/.iagent
pip install -r requirements.txt
cp .env.example .env
# Remplir .env avec tes credentials
# Voir RUNBOOK.md pour le guide complet
```

## Prérequis

- macOS (testé sur macOS 14+)
- Python 3.11+
- Claude Code CLI avec forfait Max
  `curl -fsSL https://claude.ai/install.sh | bash`
- Compte Telegram + bot créé via @BotFather
- gog CLI (Google OAuth — Gmail, Calendar, Drive)
  Voir RUNBOOK.md section 3 pour l'installation
- ffmpeg (pour Whisper) : `brew install ffmpeg`

## Personnalisation

Modifier les fichiers `identity/` pour définir
la personnalité et le contexte de ton agent.
Voir `identity/IDENTITY.md` pour commencer.

## Monétisation / Support

- **RUNBOOK.md** (guide installation complet) : [lien]
- **Accompagnement migration** : [contact]

---

*Construit avec Claude Code CLI — zéro dépendance API payante.*
