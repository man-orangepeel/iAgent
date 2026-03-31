# iAgent — Agent IA personnel, 100% sous ton contrôle

Inspiré d'OpenClaw — sans les dépendances, sans les frais API, sans le code fermé.

**→ [Démarrage rapide — 5 étapes pour commencer](QUICKSTART.md)**

> Construit de zéro en Python pur, sans framework, sans dépendance externe —
> architecture, sécurité, documentation et déploiement réalisés en autonomie.


---

## Pourquoi iAgent plutôt qu'OpenClaw ?

OpenClaw est excellent. iAgent s'en inspire directement — même philosophie d'agent
personnalisé, mémorisable, extensible. Mais avec des différences structurelles :

| | OpenClaw | iAgent |
|---|---|---|
| **LLM** | Multi-modèles (Gemini, GPT, Claude…) | Claude — via ton forfait Pro/Max existant |
| **Coût LLM** | Clés API payantes à l'usage | Zéro — inclus dans l'abonnement |
| **Code** | Fermé (app macOS + Node.js) | 100% ouvert, Python pur, lisible |
| **Données** | Transitent par les serveurs OpenClaw | Restent sur ta machine |
| **Dépendances** | Node.js, npm, gateway propriétaire | Python + Claude CLI |
| **Sécurité** | Surface d'attaque étendue | Périmètre minimal, auditable ligne par ligne |
| **Personnalisation** | Via l'interface OpenClaw | Directement dans les fichiers |

Si tu utilises déjà Claude Pro ou Max : iAgent ne te coûte rien de plus.

---

## Ce que ça fait

- **Conversation** — répond, cherche sur le web, exécute des tâches Bash
- **Email & calendrier** — lit Gmail et Google Calendar à la demande (gog CLI)
- **Documents** — extrait et analyse PDF, DOCX
- **Audio** — transcrit les messages vocaux Telegram (Whisper local)
- **Brief matinal** — agenda + mails non lus chaque matin à 7h45, avec rappels configurables
- **Automatisation** — LaunchAgents macOS, heartbeat 2h, tâches planifiées

---

## Stack

| Composant | Technologie |
|---|---|
| LLM | Claude Code CLI (forfait Pro ou Max) |
| Interface | Telegram (polling, zéro webhook exposé) |
| Email / Calendar | gog CLI (Google OAuth) |
| Transcription | Whisper local |
| Documents | pdftotext (poppler), textutil (macOS natif) |
| Runtime | Python 3.11+, zéro Node.js |

---

## Architecture
```
~/.iagent/
├── core/          — moteur Claude CLI, sessions, contexte, env
├── gateway/       — Telegram (polling, whitelist, MD→HTML, vocal, documents)
├── skills/        — gog, telegram, whisper, documents
├── projects/      — personal_assistant (brief, reminder) + projets métier
├── identity/      — personnalité, mémoire, outils (fichiers Markdown)
├── tasks/         — heartbeat autonome
└── config/        — iagent.json
```

L'agent lit ses propres fichiers `identity/` à chaque session.
Il les met à jour lui-même. La mémoire persiste entre les conversations.

---

## Santé et sécurité

iAgent embarque deux outils de diagnostic pensés pour la production :

**`doctor.sh`** — 17 vérifications au démarrage et à tout moment :
état de l'auth Claude, credentials, LaunchAgents, budget contexte,
cohérence de configuration, appel Claude réel, backup git.
```bash
bash scripts/doctor.sh           # complet (~15s)
bash scripts/doctor.sh --quick   # sans appel réseau (~1s)
```

**`security-audit.sh`** — 35 checks en 10 catégories :
credentials & tokens, prompt injection, accès Telegram,
excessive agency, sessions, exposition réseau, supply chain.
```bash
bash scripts/security-audit.sh         # audit complet
bash scripts/security-audit.sh --fix   # corrige les permissions
```

Exit code `0` = posture acceptable. Exit code `1` = au moins un point critique ou élevé.
Fréquence recommandée : à chaque modification de configuration.

---

## Personnalisation et évolutivité

Au premier message Telegram, l'agent guide la configuration de son identité
via une conversation interactive. Il écrit dans ses propres fichiers, supprime
le script de bootstrap une fois terminé.

Extensible par conception :
- **Nouveaux skills** → `skills/<nom>/` + entrée dans `identity/TOOLS.md`
- **Projets métier** → `projects/<nom>/` (pipeline, veille, newsletter, automation)
- **Nouvelles tâches planifiées** → LaunchAgents macOS + entrée dans le heartbeat

---

## Installation

Deux parcours :

- **From scratch** → [docs/install/](docs/install/)
- **Migration depuis OpenClaw** → [docs/migration/](docs/migration/)

Chaque parcours : guide manuel complet (public) + runbook Claude Code automatisé (sur demande).

**Prérequis :** macOS 14+, Python 3.11+, Claude Code CLI (Pro ou Max), compte Telegram, compte Google.
Tout est couvert étape par étape dans les guides.

---

## Support & Documentation

### Installation from scratch
- Guide manuel : [docs/install/guide-installation.md](docs/install/guide-installation.md)
- Runbook Claude Code automatisé : [sur demande](https://www.linkedin.com/in/manuelproquin/)

### Migration depuis OpenClaw
- Guide migration : [docs/migration/guide-migration.md](docs/migration/guide-migration.md)
- Runbook Claude Code automatisé : [sur demande](https://www.linkedin.com/in/manuelproquin/)

### Tu préfères construire ton assistant IA sans toucher au code ?
Le [AI Chief of Staff Bootcamp](https://aichiefofstaffbootcamp.netlify.app/) (Neon&Slate)
t'accompagne en 4 semaines pour déployer tes propres agents IA sur ta façon de travailler —
emails, réunions, notes, to-do, production de contenu — sans prérequis technique.

---

*Code ouvert. Données chez toi. Zéro dépendance API payante.*