# Note technique — Installation de Claude CLI pour iAgent

> Destinée à Claude Code (extension VS Code) pour qu'il puisse installer et configurer
> Claude CLI de manière stable sur toutes les sessions shell et LaunchAgents macOS.

---

## 1. Vue d'ensemble

**Claude CLI** (`@anthropic-ai/claude-code`) est le moteur de iAgent. Chaque interaction
(Telegram, heartbeat, brief matinal, rappels) passe par un `subprocess.run(["claude", ...])`.

La stabilité dépend de **trois invariants** :
1. Le binaire `claude` est découvrable via `which claude` dans **tout contexte d'exécution**
2. L'authentification OAuth est valide (pas de clé API — forfait Pro/Max)
3. Le PATH est identique dans le shell interactif ET dans les LaunchAgents

---

## 2. Installation du package npm

### 2.1 Prérequis

- **Node.js 18+** (installé via nvm ou directement)
- **npm** avec préfixe global configuré sur `~/.npm-global`

### 2.2 Configuration du préfixe npm global

```bash
# Vérifier le préfixe actuel
npm config get prefix

# Si ce n'est pas ~/.npm-global, le configurer :
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
```

**Pourquoi `~/.npm-global` ?** Les LaunchAgents macOS ne chargent PAS le profil shell
(pas de `.zshrc`, pas de nvm). Il faut un chemin **absolu et stable** vers le binaire.
Le chemin nvm (`~/.nvm/versions/node/vXX/bin/`) change à chaque `nvm use` — inutilisable
pour les services launchd.

### 2.3 Installation

```bash
npm install -g @anthropic-ai/claude-code
```

### 2.4 Vérification

```bash
which claude
# Attendu : /Users/USERNAME/.npm-global/bin/claude

claude --version
# Attendu : X.Y.Z (Claude Code)

# Vérifier le symlink
ls -la ~/.npm-global/bin/claude
# → ../lib/node_modules/@anthropic-ai/claude-code/cli.js
```

---

## 3. Authentification OAuth

iAgent utilise l'authentification OAuth (forfait Pro ou Max), **pas de clé API**.

```bash
claude auth login
# Suivre le lien dans le navigateur, autoriser l'accès
```

### 3.1 Vérification

```bash
claude auth status
# Doit afficher "loggedIn": true
```

### 3.2 Piège critique : `--bare` est incompatible avec OAuth

Le flag `--bare` désactive le keychain macOS → "Not logged in".

**Solution iAgent** (utilisée dans `core/claude_runner.py`) :
```bash
# Au lieu de --bare :
echo "prompt" | claude -p --output-format json --no-session-persistence --tools ""
```

- `--tools ""` → désactive tous les outils (équivalent fonctionnel de --bare)
- `--no-session-persistence` → pas d'écriture session sur disque
- stdin pour le prompt → contrainte technique quand `--tools ""` est actif

---

## 4. Stabilité PATH — Le point critique

### 4.1 Le problème

macOS a **trois contextes d'exécution** avec des PATH différents :

| Contexte | Fichier lu | PATH inclut nvm ? | PATH inclut npm-global ? |
|---|---|---|---|
| Terminal interactif (zsh) | `~/.zshrc` | Oui (via nvm.sh) | Oui (`export PATH=~/.npm-global/bin:$PATH`) |
| VS Code terminal | `~/.zshrc` | Oui | Oui |
| **LaunchAgent (launchd)** | **Aucun** | **Non** | **Non (sauf si déclaré dans le plist)** |

Les LaunchAgents iAgent (heartbeat, telegram, brief, reminder) tournent sous launchd.
Sans configuration explicite, `claude` est introuvable → `FileNotFoundError`.

### 4.2 La solution : PATH explicite dans chaque plist

Chaque fichier `.plist` dans `~/.iagent/launchagents/` déclare le PATH complet :

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>HOME</key>
    <string>/Users/USERNAME</string>
    <key>PATH</key>
    <string>/Users/USERNAME/.iagent/scripts:/Users/USERNAME/.npm-global/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin</string>
</dict>
```

> **Note :** Remplacer `USERNAME` par votre nom d'utilisateur macOS (`whoami`).

**Décomposition du PATH plist :**

| Segment | Rôle |
|---|---|
| `/Users/USERNAME/.iagent/scripts` | Scripts iAgent (gog, iagent, doctor) |
| `/Users/USERNAME/.npm-global/bin` | **Binaire `claude`** — chemin stable hors nvm |
| `/Library/Frameworks/Python.framework/Versions/3.14/bin` | Python 3.14 (chemin absolu) |
| `/usr/local/bin:/usr/bin:/bin` | Utilitaires système (git, curl, etc.) |

### 4.3 Pourquoi ne PAS utiliser le chemin nvm

nvm installe Node dans `~/.nvm/versions/node/v22.x.x/bin/`. Ce chemin :
- Change à chaque `nvm install` ou `nvm use`
- N'est activé que via `source ~/.nvm/nvm.sh` (absent de launchd)
- Casserait silencieusement les LaunchAgents après une mise à jour Node

Le préfixe `~/.npm-global` est **découplé de la version Node** : le symlink
`~/.npm-global/bin/claude → ../lib/node_modules/@anthropic-ai/claude-code/cli.js`
reste valide tant que le package est installé, quelle que soit la version Node active.

### 4.4 Configuration shell (`~/.zshrc`)

Ajouter dans `~/.zshrc` :
```bash
export PATH=~/.npm-global/bin:$PATH

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

L'ordre est important : `~/.npm-global/bin` est ajouté **avant** nvm. Ainsi même si
nvm installe un autre `claude` dans son arbre, c'est le global stable qui prime.

---

## 5. Les 4 patterns d'invocation Claude CLI

iAgent utilise Claude CLI via `core/claude_runner.py` avec 4 fonctions :

### 5.1 `run()` — One-shot sans outils (heartbeat, tâches)

```bash
echo "<prompt>" | claude -p \
    --output-format json \
    --no-session-persistence \
    --tools "" \
    [--system-prompt "<contexte>"] \
    [--model <modèle>]
```
- Timeout : 60s
- Pas de session, pas d'outils
- Usage : heartbeat (soul_evil, memory_distill, queue_work, proactive)

### 5.2 `run_with_search()` — One-shot avec WebSearch

```bash
echo "<prompt>" | claude -p \
    --output-format json \
    --no-session-persistence \
    --permission-mode bypassPermissions \
    --tools WebSearch Bash \
    [--system-prompt "<contexte>"]
```
- Timeout : 90s (config gateway)
- Outils définis dans `config/iagent.json → gateway.tools`

### 5.3 `run_session()` — Session persistante sans outils

```bash
# Première interaction (nouvelle session) :
echo "<prompt>" | claude -p \
    --output-format json \
    --tools "" \
    --session-id <UUID> \
    --system-prompt "<bootstrap>"

# Interactions suivantes (reprise) :
echo "<prompt>" | claude -p \
    --output-format json \
    --tools "" \
    --resume <UUID>
```
- Session TTL : 4h ET taille > 200KB → auto-reset (double condition)
- Tracking : `data/sessions.json` (chat_id → session_id)

### 5.4 `run_session_with_search()` — Session + WebSearch (gateway Telegram)

```bash
# Première interaction :
echo "<prompt>" | claude -p \
    --output-format json \
    --permission-mode bypassPermissions \
    --tools WebSearch Bash \
    --session-id <UUID> \
    --system-prompt "<bootstrap>"

# Reprises :
echo "<prompt>" | claude -p \
    --output-format json \
    --permission-mode bypassPermissions \
    --tools WebSearch Bash \
    --resume <UUID>
```
- C'est le mode principal du gateway Telegram
- Claude décide seul quand utiliser WebSearch ou Bash

### 5.5 Format de sortie

Toutes les invocations utilisent `--output-format json`. Réponse parsée :
```python
data = json.loads(proc.stdout)
text = data.get("result", "")           # Réponse textuelle
is_error = data.get("is_error", False)  # True si erreur Claude
```

---

## 6. LaunchAgents — Les 4 services

| Plist | Fonction | Déclenchement | Restart |
|---|---|---|---|
| `com.iagent.telegram` | Gateway Telegram | Au boot | `KeepAlive: true` (respawn) |
| `com.iagent.heartbeat` | Tâches autonomes | Toutes les 2h | `StartInterval: 7200` |
| `com.iagent.morning_brief` | Brief matinal | Cron 7h45 | Non |
| `com.iagent.reminder` | Rappels agenda | Toutes les 15min | Non |

### 6.1 Installation des LaunchAgents

```bash
cd ~/.iagent
bash scripts/install_launchagents.sh
```

### 6.2 Vérification

```bash
launchctl list | grep iagent
# Doit afficher les 4 services (ou au minimum 2 : heartbeat + telegram)
```

### 6.3 Rechargement après modification

```bash
# Un seul service :
launchctl unload ~/Library/LaunchAgents/com.iagent.telegram.plist
launchctl load ~/Library/LaunchAgents/com.iagent.telegram.plist

# Ou redémarrage forcé :
launchctl kickstart -k gui/$(id -u)/com.iagent.telegram
```

---

## 7. Mise à jour de Claude CLI

```bash
npm update -g @anthropic-ai/claude-code
claude --version  # Vérifier la nouvelle version
```

Après mise à jour :
1. Le symlink `~/.npm-global/bin/claude` reste inchangé (pointe toujours vers cli.js)
2. Les LaunchAgents n'ont PAS besoin d'être rechargés
3. L'auth OAuth reste valide
4. Lancer `iagent doctor --quick` pour confirmer

---

## 8. Diagnostic

### 8.1 Quick check

```bash
# Le binaire est-il trouvable ?
which claude

# L'auth fonctionne-t-elle ?
claude auth status

# Test d'appel réel (consomme 1 appel) :
echo "Dis bonjour" | claude -p --output-format json --tools ""

# Diagnostic complet iAgent :
cd ~/.iagent && bash scripts/doctor.sh
```

### 8.2 Erreurs fréquentes

| Symptome | Cause | Solution |
|---|---|---|
| `claude: command not found` (terminal) | PATH ne contient pas `~/.npm-global/bin` | Ajouter `export PATH=~/.npm-global/bin:$PATH` dans `~/.zshrc` |
| `claude: command not found` (LaunchAgent) | PATH plist ne contient pas `~/.npm-global/bin` | Corriger le plist + `launchctl unload/load` |
| `Not logged in` | OAuth expiré ou `--bare` utilisé | `claude auth login` |
| `FileNotFoundError` (Python) | `claude` absent du PATH subprocess | Vérifier PATH dans le plist du service concerné |
| JSON invalide en sortie | Claude CLI a crashé ou version incompatible | `npm update -g @anthropic-ai/claude-code` |
| TIMEOUT (60s/90s) | Prompt trop lourd ou réseau lent | Vérifier la taille du contexte injecté |

### 8.3 Checks du doctor pertinents pour Claude CLI

- **Check #1** : Claude CLI installé et authentifié
- **Check #14** : Python absolu + `claude` dans le PATH des plists
- **Check #15** : Appel OAuth réel (pas juste `loggedIn: true`)

---

## 9. Résumé des fichiers critiques

| Fichier | Rôle |
|---|---|
| `~/.npm-global/bin/claude` | Symlink vers le binaire Claude CLI |
| `~/.npm-global/lib/node_modules/@anthropic-ai/claude-code/` | Package installé |
| `~/.zshrc` | PATH shell interactif (`~/.npm-global/bin`) |
| `~/.iagent/launchagents/*.plist` | PATH LaunchAgents (même segment) |
| `~/.iagent/core/claude_runner.py` | Moteur d'invocation (4 fonctions) |
| `~/.iagent/config/iagent.json` | Timeouts, outils gateway, config sessions |
| `~/.iagent/scripts/doctor.sh` | Diagnostic (17 checks dont 3 pour Claude CLI) |

---

## 10. Checklist d'installation complète

```
[ ] Node.js 18+ installé (via nvm ou direct)
[ ] npm prefix configuré sur ~/.npm-global
[ ] export PATH=~/.npm-global/bin:$PATH dans ~/.zshrc
[ ] npm install -g @anthropic-ai/claude-code
[ ] claude auth login (OAuth, navigateur)
[ ] which claude → ~/.npm-global/bin/claude
[ ] claude --version → numéro affiché
[ ] claude auth status → loggedIn: true
[ ] PATH ~/.npm-global/bin dans chaque fichier .plist
[ ] iagent doctor → checks 1, 14, 15 en vert
```
