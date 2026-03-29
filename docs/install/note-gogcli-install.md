# Note technique — Installation de GOG CLI pour iAgent

> Destinée à Claude Code (extension VS Code) pour qu'il puisse installer et configurer
> GOG CLI (Google OAuth Gateway) sur une nouvelle machine.

---

## 1. Vue d'ensemble

**GOG CLI** (`gogcli`) est l'outil qui donne à iAgent l'accès à Gmail, Calendar et Drive.
Chaque brief matinal, chaque recherche d'email, chaque consultation d'agenda passe par un
`subprocess.run(["gog", ...])`.

**Point clé : GOG gère ses propres credentials en dehors du repo iAgent.**
Rien dans `.env`, rien dans `credentials/`, rien dans le dossier `~/.iagent/`.

---

## 2. Architecture des credentials — Les 2 secrets

GOG fonctionne avec **deux secrets**, stockés dans **deux emplacements distincts** :

| Secret | Contenu | Emplacement | Permissions |
|--------|---------|-------------|-------------|
| **OAuth Client** | `client_id` + `client_secret` (app Google Cloud) | `~/Library/Application Support/gogcli/credentials.json` | `600` |
| **Refresh Token** | Token OAuth utilisateur (accès Gmail/Calendar/Drive) | **macOS Keychain** (`login.keychain-db`) | Chiffré par le système |

### 2.1 Le credentials.json (OAuth Client)

Fichier de 152 octets contenant les identifiants de l'application Google Cloud :
```json
{
  "client_id": "XXXXXXX.apps.googleusercontent.com",
  "client_secret": "GOCSPX-XXXXXXX"
}
```

- Généré depuis la [Google Cloud Console](https://console.cloud.google.com/)
- Stocké par GOG dans `~/Library/Application Support/gogcli/credentials.json`
- **N'est PAS un secret utilisateur** — c'est l'identité de l'application OAuth

### 2.2 Le refresh token (Keychain)

Le token qui autorise l'accès effectif au compte Google :
```
Keychain : ~/Library/Keychains/login.keychain-db
Service  : gogcli
Account  : token:default:<email>
```

- Chiffré par macOS — jamais visible en clair sur le disque
- Géré automatiquement par GOG (rotation, refresh)
- Survit aux redémarrages et mises à jour de GOG

### 2.3 Le compte par défaut (variable d'environnement)

```bash
# Dans ~/.zshrc
export GOG_ACCOUNT=votre.email@gmail.com
```

Évite de passer `-a email@gmail.com` à chaque commande.

---

## 3. Pourquoi il n'y a RIEN dans `.env` ni dans `credentials/`

| Ce qu'on pourrait croire | La réalité |
|---|---|
| Les tokens Google sont dans `.env` | Non — `.env` ne contient que les tokens **Telegram** |
| Il faut un dossier `credentials/` | Non — GOG utilise `~/Library/Application Support/gogcli/` |
| Il faut configurer GOG dans iAgent | Non — GOG est un outil système autonome, comme `git` |

**Analogie :** GOG est à Google ce que `git` est à GitHub. On l'installe, on l'authentifie
une fois, et tous les projets y accèdent via la ligne de commande.

---

## 4. Comment iAgent utilise GOG

### 4.1 Invocation unique : subprocess

```python
# projects/personal_assistant/morning_brief.py
def _run_gog(args: list, timeout: int = 30) -> dict:
    result = subprocess.run(
        ["gog"] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    return json.loads(result.stdout)
```

### 4.2 Commandes utilisées

| Contexte | Commande |
|----------|----------|
| Brief matinal — agenda | `gog calendar list --all --days 1 --json` |
| Brief matinal — mails | `gog gmail search "is:unread newer_than:7d" --max 20 --json` |
| Brief — vérifier lecture | `gog gmail thread <thread_id> --json` |
| Session Telegram — ad hoc | `gog gmail search "<critères>" --max N --json` |
| Session Telegram — agenda | `gog calendar list --all --days N` |

### 4.3 Chaîne de résolution au runtime

```
subprocess.run(["gog", "gmail", "search", ...])
    │
    ├─ 1. Shell résout "gog" → /usr/local/bin/gog (Homebrew)
    ├─ 2. GOG lit GOG_ACCOUNT → ~/.zshrc (ou variable d'env du plist)
    ├─ 3. GOG lit credentials.json → ~/Library/Application Support/gogcli/
    ├─ 4. GOG récupère le refresh token → macOS Keychain
    ├─ 5. GOG échange refresh → access token (API Google OAuth)
    └─ 6. GOG appelle l'API Google (Gmail/Calendar/Drive)
```

---

## 5. Installation from scratch

### Étape 1 — Installer GOG CLI

```bash
brew install gogcli
```

**Vérification :**
```bash
gog --version
# Attendu : v0.11.0+ (ou plus récent)

which gog
# Attendu : /usr/local/bin/gog
```

### Étape 2 — Créer les credentials OAuth (Google Cloud Console)

> Cette étape nécessite un accès à [console.cloud.google.com](https://console.cloud.google.com/).
> C'est la seule étape manuelle qui requiert un navigateur.

1. **Créer un projet** Google Cloud (ou utiliser un projet existant)
2. **Activer les APIs** :
   - Gmail API
   - Google Calendar API
   - Google Drive API
3. **Configurer l'écran de consentement** OAuth (type "Externe" ou "Interne")
4. **Créer un OAuth 2.0 Client ID** :
   - Type d'application : **Desktop**
   - Nom : `gogcli` (ou tout autre nom)
5. **Télécharger le JSON** — bouton "Télécharger JSON" à côté du client créé

### Étape 3 — Injecter le credentials.json dans GOG

```bash
gog auth credentials set /chemin/vers/credentials.json
```

GOG copie le fichier dans `~/Library/Application Support/gogcli/credentials.json`
avec les permissions `600`.

**Vérification :**
```bash
gog auth credentials list
# CLIENT   PATH
# default  /Users/<user>/Library/Application Support/gogcli/credentials.json
```

### Étape 4 — Autoriser le compte Google

```bash
gog auth add votre.email@gmail.com --services "gmail,calendar,drive"
```

GOG ouvre un navigateur → page de consentement Google → autoriser.
Le refresh token est automatiquement stocké dans le **Keychain macOS**.

**Options utiles :**
- `--manual` : flow sans ouverture automatique du navigateur (copier-coller l'URL)
- `--remote` : flow pour machine sans navigateur (serveur distant)
- `--force-consent` : forcer un nouveau consentement (utile si token invalide)
- `--readonly` : scopes en lecture seule (plus restrictif)

**Vérification :**
```bash
gog auth status
# credentials_exists  true
# account             votre.email@gmail.com
```

### Étape 5 — Configurer le compte par défaut

```bash
echo 'export GOG_ACCOUNT=votre.email@gmail.com' >> ~/.zshrc
source ~/.zshrc
```

### Étape 6 — Tester

```bash
# Gmail
gog gmail search "newer_than:1d" --max 1 --json

# Calendar
gog calendar list --all --days 1 --json
```

---

## 6. Stabilité PATH — LaunchAgents

GOG est dans `/usr/local/bin/gog` (Homebrew). Ce chemin est **déjà dans le PATH
des LaunchAgents iAgent** :

```xml
<!-- Extrait d'un plist iAgent (com.iagent.*) -->
<key>PATH</key>
<string>...:/usr/local/bin:/usr/bin:/bin</string>
```

Contrairement à Claude CLI (qui nécessite `~/.npm-global/bin`), GOG est dans
`/usr/local/bin` — un chemin standard que launchd connaît. **Aucune configuration
plist spécifique n'est requise pour GOG.**

---

## 7. Diagnostic

### 7.1 Quick check

```bash
# Le binaire est-il trouvable ?
which gog

# Les credentials existent-ils ?
gog auth credentials list

# Le compte est-il autorisé ?
gog auth status

# Test d'appel réel (consomme un appel API Google) :
gog gmail search "newer_than:1d" --max 1 --json
```

### 7.2 Erreurs fréquentes

| Symptôme | Cause | Solution |
|---|---|---|
| `gog: command not found` | GOG pas installé | `brew install gogcli` |
| `no credentials found` | credentials.json absent | `gog auth credentials set <fichier>` |
| `token not found` | Pas autorisé ou token expiré | `gog auth add email --services "gmail,calendar,drive"` |
| `403 Forbidden` | API non activée dans Google Cloud | Activer l'API dans la console Google Cloud |
| `invalid_grant` | Refresh token révoqué | `gog auth add email --force-consent` |
| `timeout gog` (iAgent) | Réseau lent ou API Google indisponible | Réessayer ; vérifier la connexion internet |
| `JSON invalide` (iAgent) | GOG a écrit sur stderr | Vérifier `gog ... 2>&1` pour voir l'erreur |

### 7.3 Vérifier le Keychain

```bash
# Lister les entrées GOG dans le Keychain (sans afficher les secrets) :
security find-generic-password -l "gogcli" 2>/dev/null | grep -E "svce|acct"
# svce = "gogcli"
# acct = "token:default:votre.email@gmail.com"
```

---

## 8. Différence avec les credentials Telegram

| Aspect | Telegram | GOG (Google) |
|--------|----------|-------------|
| Où est le secret | `~/.iagent/.env` | macOS Keychain |
| Format | Token en clair (variable d'env) | Refresh token chiffré (Keychain) |
| Géré par | iAgent (`env_loader.py`) | GOG CLI (autonome) |
| Rotation | Manuelle (BotFather → .env) | Automatique (GOG refresh le token) |
| Backup | Sauvegarder `.env` | Ré-autoriser (`gog auth add`) |
| Dans le repo | Oui (`.env`, gitignored) | Non — entièrement externe |

---

## 9. Résumé des fichiers critiques

| Fichier | Rôle |
|---|---|
| `/usr/local/bin/gog` | Binaire GOG CLI (Homebrew) |
| `~/Library/Application Support/gogcli/credentials.json` | OAuth client (app Google Cloud) |
| `~/Library/Application Support/gogcli/keyring/` | Répertoire keyring (vide — tokens dans Keychain) |
| `~/Library/Keychains/login.keychain-db` | Refresh token chiffré |
| `~/.zshrc` (export GOG_ACCOUNT) | Compte Google par défaut |
| `~/.iagent/projects/personal_assistant/morning_brief.py` | Consommateur principal (`_run_gog()`) |

---

## 10. Checklist d'installation complète

```
[ ] brew install gogcli
[ ] gog --version → v0.11.0+
[ ] which gog → /usr/local/bin/gog
[ ] Projet Google Cloud créé avec APIs activées (Gmail, Calendar, Drive)
[ ] OAuth Client ID créé (type Desktop) + JSON téléchargé
[ ] gog auth credentials set credentials.json
[ ] gog auth credentials list → client "default" affiché
[ ] gog auth add email@gmail.com --services "gmail,calendar,drive"
[ ] gog auth status → credentials_exists: true
[ ] export GOG_ACCOUNT=email@gmail.com dans ~/.zshrc
[ ] gog gmail search "newer_than:1d" --max 1 --json → résultat JSON
[ ] gog calendar list --all --days 1 --json → résultat JSON
```
