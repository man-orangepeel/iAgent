# Guide d'installation — iAgent

> **Durée estimée : 45–60 min** · Agent IA personnel autonome sur macOS, opéré via Telegram.

---

## Ce que vous allez obtenir

À la fin de ce guide, vous aurez :

- Un **bot Telegram** personnel qui répond à vos messages (texte, voix, documents)
- Un **brief matinal** sur demande (`/brief`) ou planifiable manuellement
- Des **rappels** d'événements configurables via Telegram
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
| **Python 3.14+** | Télécharger et installer depuis [python.org/downloads](https://www.python.org/downloads/) — utiliser le package macOS (`.pkg`), pas brew | `python3 --version` |
| **Node.js 18+** | `brew install node` | `node --version` |
| **ffmpeg** | `brew install ffmpeg` | `ffmpeg -version` |
| **Whisper** | `brew install openai-whisper` | `whisper --help` |
| **pdftotext** | `brew install poppler` | `pdftotext -v` |
| **gog** | `brew install gogcli` | `gog --version` |

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
# Configurer npm global (évite sudo)
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.zshrc
export PATH=~/.npm-global/bin:$PATH

# Installer Claude Code CLI
npm install -g @anthropic-ai/claude-code

# S'authentifier (ouvre le navigateur)
~/.npm-global/bin/claude auth login
```

Vérifier :
```bash
~/.npm-global/bin/claude --version
# Attendu : numéro de version
~/.npm-global/bin/claude auth status 2>&1 | grep loggedIn
# Attendu : "loggedIn": true
```

---

## Étape 3 — Installer iAgent

```bash
# Cloner le dépôt
git clone https://github.com/man-orangepeel/iagent ~/.iagent

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
```

> **Ne jamais committer `.env`** — il est dans `.gitignore`.

---

## Étape 5 — Configurer Google OAuth (gog)

### 5a. Créer un projet Google Cloud

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un nouveau projet (ex. « iAgent »)
3. Activer les APIs : **Gmail API**, **Google Calendar API**, **Google Drive API**

### 5b. Configurer l'écran de consentement OAuth

1. Menu (☰) → **APIs et services** → **Google Auth Platform**
2. Si non configuré → cliquer sur **Premiers Pas**
3. Nom de l'application : `iAgent`, adresse email : votre Gmail
4. **Cible** : sélectionner **Externe**
5. Dans la page **Audience** → **Utilisateurs test** → **Add user** → votre adresse Gmail → **Enregistrer**

### 5c. Créer les identifiants OAuth

1. Menu → **APIs & Services** → **Identifiants**
2. **+ Créer des identifiants** → **ID client OAuth**
3. Type : **Application de bureau**
4. Nom : `iAgent` → **Créer**
5. Cliquer sur **Télécharger le JSON** — conserver ce fichier pour l'étape suivante

> **Note :** gog gère ses credentials dans `~/Library/Application Support/gogcli/` — rien à copier dans `.env`.

### 5d. Authentifier gog

```bash
# Injecter le fichier JSON téléchargé (adapter le nom du fichier)
gog auth credentials set ~/Downloads/<nom-du-fichier>.json

# Générer l'URL d'autorisation
gog auth add <VOTRE_EMAIL> --remote --step 1 --services gmail,calendar,drive
```

Copier l'URL `auth_url` affichée dans votre navigateur. Google demandera votre connexion et vos autorisations. **Votre navigateur affichera une erreur `127.0.0.1 n'autorise pas la connexion` — c'est normal.** Copier l'URL complète de la barre d'adresse (commence par `http://127.0.0.1:...`) et la coller dans le terminal :

```bash
echo "<URL_COPIÉE>" | gog auth add <VOTRE_EMAIL> --manual --services gmail,calendar,drive

# Configurer le compte par défaut
grep -q 'GOG_ACCOUNT' ~/.zshrc || echo 'export GOG_ACCOUNT=<VOTRE_EMAIL>' >> ~/.zshrc
export GOG_ACCOUNT=<VOTRE_EMAIL>
```

**Vérifier :**
```bash
gog auth status
gog gmail search "newer_than:1d" --max 1 --json | head -5
gog calendar list --all --days 1 --json | head -5
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
- Python path : `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
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
    "tools": ["WebSearch", "Bash", "Write", "Edit"],
    "timeout": 180
  }
}
```

**Ce fichier est pré-configuré dans le repo — aucune modification manuelle nécessaire.**
- `python_path` pointe vers Python 3.14 (framework macOS)
- `gateway.tools` inclut `Write` et `Edit` — requis pour que l'agent puisse écrire ses fichiers de configuration lors du BOOTSTRAP
- `gateway.timeout` à 180s — nécessaire pour l'écriture des fichiers identity lors de la première conversation

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
1. Copier les 2 plists dans `~/Library/LaunchAgents/`
2. Remplacer `USERNAME` par votre nom d'utilisateur macOS
3. Charger les agents via `launchctl load`

**Les 2 agents installés :**

| Agent | Déclencheur | Rôle |
|---|---|---|
| `com.iagent.telegram` | Au login, permanent | Gateway Telegram (bot) |
| `com.iagent.heartbeat` | Toutes les 2h | Maintenance (mémoire, surveillance) |

> Le brief matinal et les rappels sont déclenchés par la gateway Telegram (commande `/brief`) — pas par des LaunchAgents séparés.

**Vérifier :**
```bash
launchctl list | grep iagent
# Doit afficher com.iagent.heartbeat et com.iagent.telegram avec un PID
```

---

## Étape 10 — Diagnostic complet

```bash
bash scripts/doctor.sh
```

Le diagnostic vérifie **17 points** :

| # | Vérification | Criticité |
|---|---|---|
| 1 | Claude CLI trouvé | Bloquant |
| 2 | Python trouvé | Bloquant |
| 3 | Dossiers critiques existent | Bloquant |
| 4 | Fichiers BOOTSTRAP présents | Bloquant |
| 5 | iagent.json valide | Bloquant |
| 6 | Variables .env requises | Bloquant |
| 7 | python-telegram-bot installé | Bloquant |
| 8 | ffmpeg installé | Bloquant (voix) |
| 9 | Whisper installé | Bloquant (voix) |
| 10 | pdftotext installé | Warning |
| 11 | gog installé | Bloquant (Google) |
| 12 | gog Gmail auth | Bloquant (Google) |
| 13 | gog Calendar auth | Bloquant (Google) |
| 14 | LaunchAgent heartbeat chargé | Warning |
| 15 | LaunchAgent telegram chargé | Warning |
| 16 | Gateway Telegram active | Warning |
| 17 | Drift de configuration | Warning |

**Résultat attendu : 17/17 ✓**

> Mode rapide (sans appels réseau) : `bash scripts/doctor.sh --quick`

---

## Étape 11 — Audit de sécurité

```bash
bash scripts/security-audit.sh --fix
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
| `/brief` | Lancer le brief matinal manuellement |
| `/doctor` | Diagnostic rapide |
| `/audit` | Audit de sécurité |
| `/reset` | Réinitialiser la session (nouveau bootstrap) |
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

Envoyez `/brief` dans Telegram pour recevoir le brief à la demande. Exemple de contenu :

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

Pour lancer le brief : `/brief` dans Telegram.
Pour l'automatiser à une heure fixe, voir la plist `launchagents/com.iagent.morning_brief.plist` (installation manuelle, non incluse dans le script de base).

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
| `gog: command not found` | gog non installé | `brew install gogcli` |
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
