# Guide d'installation — iAgent

> **Durée estimée : 45–60 min** · Agent IA personnel autonome sur macOS, opéré via Telegram.

---

## Ce que vous allez obtenir

À la fin de ce guide, vous aurez :

- Un **bot Telegram** personnel qui répond à vos messages (texte, voix, documents)
- Un **brief matinal** automatique à 7h45 (agenda + emails non lus)
- Des **rappels** d'événements 15 min avant chaque rendez-vous
- Un **heartbeat** toutes les 2h (maintenance mémoire, file d'attente, proactivité)
- L'accès à **Gmail, Google Calendar et Drive** via commandes naturelles
- La **transcription vocale** locale (Whisper, aucune donnée envoyée à un tiers)
- L'extraction automatique de **documents PDF et DOCX**
- Un système de **diagnostic** (`doctor`) et d'**audit sécurité** intégrés

---

## Prérequis

### Matériel

| Élément | Minimum | Recommandé |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| RAM | 8 Go | 16 Go (Whisper turbo) |
| Disque | 2 Go libres | 5 Go |
| Processeur | Intel i5 | Apple Silicon (M1+) |

### Abonnement

| Service | Niveau | Coût |
|---|---|---|
| Anthropic (Claude) | Pro (suffisant) ou Max | 20 € / 100 € par mois |

### Logiciels à installer avant de commencer

| Logiciel | Installation | Vérification |
|---|---|---|
| **Homebrew** | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | `brew --version` |
| **Python 3.14+** | `brew install python@3.14` | `python3 --version` |
| **Node.js 18+** | `brew install node` | `node --version` |
| **ffmpeg** | `brew install ffmpeg` | `ffmpeg -version` |
| **Whisper** | `pip3 install openai-whisper` | `whisper --help` |
| **pdftotext** | `brew install poppler` | `pdftotext -v` |
| **gog** | `npm install -g @nicholasgasior/gog` | `gog --version` |

---

## Étape 1 — Créer le bot Telegram

### 1a. Créer le bot

1. Ouvrir Telegram → chercher **@BotFather**
2. Envoyer `/newbot`
3. Choisir un nom (ex. « Mon Assistant ») puis un username (ex. `mon_assistant_bot`)
4. **Copier le token** affiché (format `123456789:ABCdefGHI...`)

### 1b. Obtenir votre chat_id

1. Chercher **@userinfobot** dans Telegram
2. Envoyer `/start`
3. **Copier votre Id** (nombre entier, ex. `987654321`)

> **Sécurité** : le `chat_id` sert de filtre — seul ce compte pourra parler au bot.

---

## Étape 2 — Installer Claude Code CLI

```bash
# Installer Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# S'authentifier (ouvre le navigateur)
claude auth login
```

Vérifier :
```bash
claude --version
# Attendu : claude-code X.Y.Z
```

---

## Étape 3 — Installer iAgent

```bash
# Cloner le dépôt
git clone https://github.com/VOTRE_USER/iagent.git ~/.iagent

# Installer les dépendances Python
cd ~/.iagent
pip3 install -r requirements.txt

# Lancer l'initialisation
bash scripts/init.sh
```

`init.sh` va :
- Créer `.env` depuis `.env.example` si absent
- Créer les dossiers nécessaires (`logs/`, `tmp/`, `data/`, `projects/`)
- Créer `tracking.json` pour le brief matinal

Les fichiers `identity/` sont déjà dans le repo — ils guident
la personnalisation lors de votre première conversation Telegram.

---

## Étape 4 — Configurer les identifiants (`.env`)

Ouvrir `~/.iagent/.env` et remplir :

```bash
# Telegram
IAGENT_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
IAGENT_CHAT_ID=987654321

# Google OAuth — rempli automatiquement par gog (étape 5)
# GOG_CLIENT_ID=...
# GOG_CLIENT_SECRET=...
```

> **Ne jamais committer `.env`** — il est dans `.gitignore`.

---

## Étape 5 — Configurer Google OAuth (gog)

### 5a. Créer un projet Google Cloud

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un nouveau projet (ex. « iAgent »)
3. Activer les APIs : **Gmail API**, **Google Calendar API**, **Google Drive API**

### 5b. Créer les identifiants OAuth

1. Menu → APIs & Services → Credentials
2. Create Credentials → OAuth client ID
3. Type : **Desktop application**
4. Télécharger le fichier JSON
5. Copier `client_id` et `client_secret` dans `.env`

### 5c. Authentifier gog

```bash
# Authentification Gmail
gog gmail auth

# Authentification Calendar
gog calendar auth

# Authentification Drive (optionnel)
gog drive auth
```

Chaque commande ouvre le navigateur pour autoriser l'accès. Le token est stocké localement par gog.

**Vérifier :**
```bash
gog gmail search "newer_than:1d" --max 3
gog calendar list --days 3
```

---

## Étape 6 — Configurer CLAUDE.md

`CLAUDE.md` à la racine du projet est lu par Claude Code CLI à **chaque invocation**
(y compris en mode `--resume`). Copiez et adaptez le template :

```bash
cp ~/.iagent/identity/CLAUDE-template.md ~/.iagent/CLAUDE.md
nano ~/.iagent/CLAUDE.md
```

Remplacez chaque `[À REMPLACER]` :
- Nom du projet : le nom de votre agent
- Compte macOS : votre nom d'utilisateur (`whoami`)
- Chemin absolu : `/Users/VOTRE_USER/.iagent`
- Python path : résultat de `which python3`
- Langue : votre langue de travail

> **Les fichiers `identity/IDENTITY.md`, `SOUL.md` et `USER.md`** seront
> personnalisés automatiquement lors de votre première conversation Telegram.
> L'agent vous guide — pas besoin de les éditer manuellement.

---

## Étape 7 — Configurer `iagent.json`

Le fichier `config/iagent.json` centralise les paramètres techniques :

```json
{
  "session": {
    "ttl_hours": 4,
    "max_size_kb": 200
  },
  "heartbeat": {
    "interval_minutes": 120,
    "timeout_seconds": 60,
    "alert_on_consecutive_failures": 2
  },
  "context": {
    "max_chars": 38000,
    "warn_threshold": 0.9
  },
  "python_path": "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
  "gateway": {
    "tools": ["WebSearch", "Bash"],
    "timeout": 90
  }
}
```

**À adapter :**
- **`python_path`** : vérifier avec `which python3` (doit pointer vers Python 3.14+)
- **`session.ttl_hours`** : durée max d'une session Telegram avant rotation (défaut 4h)
- **`session.max_size_kb`** : taille max du contexte avant rotation (défaut 200 Ko)
- **Heure du brief matinal** : définie dans `launchagents/com.iagent.morning_brief.plist`
  (clés `Hour` et `Minute`). Défaut : 7h45. Pour changer l'heure, modifier la plist
  puis recharger le LaunchAgent.

---

## Étape 8 — Choisir le modèle Whisper

iAgent utilise Whisper en local pour transcrire les messages vocaux.

| Modèle | Taille | Vitesse (M1) | Vitesse (Intel) | Qualité |
|---|---|---|---|---|
| `turbo` | 809 Mo | ~3s / 30s audio | ~15s / 30s audio | Excellente |
| `base` | 142 Mo | ~1s / 30s audio | ~5s / 30s audio | Correcte |

**Recommandation :**
- **Apple Silicon (M1/M2/M3)** : utiliser `turbo` — qualité maximale, rapide
- **Intel** : utiliser `base` — `turbo` sera trop lent (>15s par message)

Le modèle est configuré dans le skill Whisper (`skills/whisper.py`). Le premier appel télécharge le modèle automatiquement.

---

## Étape 9 — Installer les LaunchAgents

Les LaunchAgents assurent le démarrage automatique des services à l'ouverture de session macOS.

```bash
bash scripts/install_launchagents.sh
```

Ce script va :
1. Copier les 4 plists dans `~/Library/LaunchAgents/`
2. Remplacer `USERNAME` par votre nom d'utilisateur macOS
3. Charger les agents via `launchctl load`

**Les 4 agents :**

| Agent | Déclencheur | Rôle |
|---|---|---|
| `com.iagent.telegram` | Au login | Gateway Telegram (bot) |
| `com.iagent.heartbeat` | Toutes les 2h | Maintenance (mémoire, queue, proactivité) |
| `com.iagent.morning_brief` | 7h45 | Brief matinal (agenda + mails) |
| `com.iagent.reminder` | Toutes les 15 min | Rappels d'événements |

**Vérifier :**
```bash
launchctl list | grep iagent
# Doit afficher les 4 agents avec un PID (ou 0 pour les agents calendar)
```

---

## Étape 10 — Diagnostic complet

```bash
bash scripts/doctor.sh
```

Le diagnostic vérifie **17 points** :

| # | Vérification | Criticité |
|---|---|---|
| 1 | Python trouvé | Bloquant |
| 2 | Version Python ≥ 3.11 | Bloquant |
| 3 | Claude CLI trouvé | Bloquant |
| 4 | Claude CLI authentifié | Bloquant |
| 5 | Dossier iAgent existe | Bloquant |
| 6 | Fichier .env existe | Bloquant |
| 7 | Variables .env requises | Bloquant |
| 8 | Dépendances Python | Bloquant |
| 9 | ffmpeg installé | Bloquant (voix) |
| 10 | Whisper installé | Bloquant (voix) |
| 11 | pdftotext installé | Warning |
| 12 | gog installé | Bloquant (Google) |
| 13 | gog Gmail auth | Bloquant (Google) |
| 14 | gog Calendar auth | Bloquant (Google) |
| 15 | LaunchAgents chargés | Warning |
| 16 | Gateway Telegram active | Warning |

**Résultat attendu : 16/16 ✓**

> Mode rapide (sans appels réseau) : `bash scripts/doctor.sh --quick`

---

## Étape 11 — Audit de sécurité

```bash
bash scripts/security-audit.sh
```

L'audit vérifie **10 catégories** basées sur OWASP LLM Top 10, MITRE ATLAS et OWASP Agentic :

| # | Catégorie | Exemples de vérifications |
|---|---|---|
| 1 | Permissions fichiers | .env en 600, credentials/ en 700 |
| 2 | Secrets exposés | Pas de tokens dans le code |
| 3 | Isolation utilisateur | Accès limité au user macOS |
| 4 | Injection de prompts | Filtrage des entrées Telegram |
| 5 | Exfiltration de données | Pas d'envoi vers des tiers |
| 6 | Authentification | chat_id vérifié, tokens valides |
| 7 | Logging | Pas de secrets dans les logs |
| 8 | Dépendances | Versions à jour, pas de CVE connue |
| 9 | Réseau | Ports, connexions sortantes |
| 10 | Configuration | Paramètres sécurisés |

**Options :**
```bash
bash scripts/security-audit.sh --fix        # corrige automatiquement (chmod)
bash scripts/security-audit.sh --json       # sortie JSON
bash scripts/security-audit.sh --category 3 # une seule catégorie
```

---

## Étape 12 — Premier contact

> **Première fois :** votre agent va se présenter et vous poser des questions
> pour configurer son identité (nom, personnalité, vos préférences).
> C'est le processus d'initialisation guidé par `identity/BOOTSTRAP.md`.
> Il mettra à jour les fichiers `identity/` lui-même et supprimera
> `BOOTSTRAP.md` une fois terminé.

Ouvrir Telegram et envoyer un message à votre bot.

**Commandes disponibles :**

| Commande | Description |
|---|---|
| `/start` | Message de bienvenue |
| `/help` | Liste des commandes |
| `/brief` | Lancer le brief matinal manuellement |
| `/doctor` | Diagnostic rapide (14 checks) |
| `/audit` | Audit de sécurité |
| Message texte | Conversation libre avec l'agent |
| Message vocal | Transcription automatique puis réponse |
| Document PDF/DOCX | Extraction du texte puis analyse |

**Test rapide :**
1. Envoyer « Bonjour » → l'agent doit répondre
2. Envoyer `/brief` → brief matinal avec agenda et mails
3. Envoyer un vocal → transcription puis réponse
4. Envoyer `/doctor` → diagnostic santé

---

## Le brief matinal

Chaque matin à 7h45, l'agent envoie automatiquement via Telegram :

```
☀️ Brief du 28 mars 2026

📅 Agenda du jour
• 09:00 – Réunion équipe (Zoom)
• 12:30 – Déjeuner avec Marc
• 16:00 – Call fournisseur

📧 Emails importants (7 derniers jours)
• [Banque] Relevé mensuel disponible
• [Client] Validation du devis #42
• [Newsletter] Bitcoin Weekly Digest

⏰ Rappels actifs
• Renouveler passeport (dans 12 jours)
• Payer facture électricité (demain)
```

Le brief est déclenché par le LaunchAgent `com.iagent.morning_brief.plist`.
Pour le lancer manuellement : `/brief` dans Telegram.

---

## Skills disponibles

| Skill | Commande | Description |
|---|---|---|
| Gmail | `gog gmail search "..." --max N` | Recherche d'emails |
| Calendar | `gog calendar list --days N` | Agenda |
| Drive | `gog drive list` | Fichiers Google Drive |
| Telegram | (automatique) | Gateway de communication |
| Whisper | (automatique) | Transcription vocale locale |
| Documents | (automatique) | Extraction PDF / DOCX |
| Doctor | `iagent doctor` | Diagnostic santé |
| Security | `iagent security` | Audit de sécurité |
| Logs | `iagent logs telegram` | Consultation des logs |

**Captions de documents** : quand vous envoyez un document avec la légende « stocke dans projets », l'agent le sauvegarde dans `data/workspace/projets/`.

---

## Commandes de maintenance

```bash
# Voir les logs Telegram en temps réel
tail -f ~/.iagent/logs/telegram.log

# Voir les logs du heartbeat
tail -f ~/.iagent/logs/heartbeat.log

# Redémarrer la gateway Telegram
launchctl kickstart -k gui/$(id -u)/com.iagent.telegram

# Arrêter tous les agents
launchctl bootout gui/$(id -u)/com.iagent.telegram
launchctl bootout gui/$(id -u)/com.iagent.heartbeat
launchctl bootout gui/$(id -u)/com.iagent.morning_brief
launchctl bootout gui/$(id -u)/com.iagent.reminder

# Relancer tous les agents
bash scripts/install_launchagents.sh

# Diagnostic rapide
bash scripts/doctor.sh --quick

# Audit sécurité avec corrections automatiques
bash scripts/security-audit.sh --fix
```

---

## Erreurs fréquentes

| Erreur | Cause probable | Solution |
|---|---|---|
| `Claude CLI not found` | CLI non installée | `curl -fsSL https://claude.ai/install.sh \| bash` |
| `Not authenticated` | Session CLI expirée | `claude auth login` |
| `IAGENT_BOT_TOKEN missing` | `.env` incomplet | Vérifier `.env` |
| `gog: command not found` | gog non installé | `npm install -g @nicholasgasior/gog` |
| `Gmail auth expired` | Token Google expiré | `gog gmail auth` |
| `Whisper model not found` | Premier lancement | Attendre le téléchargement automatique |
| `ffmpeg not found` | ffmpeg non installé | `brew install ffmpeg` |
| `Permission denied` sur `.env` | Permissions trop ouvertes | `chmod 600 ~/.iagent/.env` |
| `LaunchAgent not loaded` | Agent non chargé | `bash scripts/install_launchagents.sh` |
| `pdftotext not found` | poppler non installé | `brew install poppler` |

---

## Rotation des tokens en urgence

Si un token est compromis :

1. **Telegram** : aller sur @BotFather → `/revoke` → copier le nouveau token dans `.env`
2. **Google** : révoquer dans [Google Security](https://myaccount.google.com/permissions) → ré-authentifier avec `gog gmail auth` et `gog calendar auth`
3. **Claude** : `claude auth logout` puis `claude auth login`
5. **Redémarrer** : `launchctl kickstart -k gui/$(id -u)/com.iagent.telegram`

---

## Sécurité

- **Aucune donnée** n'est envoyée à des tiers (sauf Claude API via CLI et Google APIs via gog)
- **Whisper tourne en local** — les messages vocaux ne quittent jamais la machine
- **Le chat_id** filtre les messages — seul votre compte Telegram peut interagir
- **Les tokens** sont dans `.env` (permissions 600) et jamais dans le code
- **L'audit de sécurité** vérifie 10 catégories basées sur les standards OWASP et MITRE
- **Les logs** ne contiennent jamais de secrets (vérifié par l'audit)
- **Les sessions** sont rotées automatiquement (TTL 4h, taille max 200 Ko)
