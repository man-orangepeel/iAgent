# Guide de migration — Depuis un assistant IA existant vers iAgent

> Ce guide suppose que vous avez déjà complété l'installation de base
> (voir `docs/install/guide-installation.md`).
>
> Durée estimée : 1-2 heures (selon la complexité de votre configuration existante).

---

## Vue d'ensemble

La migration se fait en 6 étapes :

1. **Auditer** votre assistant existant
2. **Inventorier** les composants à migrer
3. **Migrer** les fichiers d'identité et personnaliser la configuration
4. **Migrer** les composants LLM
5. **Valider** que tout fonctionne
6. **Couper** l'ancien système

---

## Étape 1 — Auditer votre assistant existant

Vous devez d'abord comprendre ce que contient votre assistant actuel.
Claude Code peut faire cet audit pour vous.

### Ce qu'il faut identifier

Demandez à Claude Code (ou faites-le vous-même) de lire et documenter :

- **Fichiers d'identité** : personnalité, contexte utilisateur, mémoire
  (souvent nommés IDENTITY.md, SOUL.md, USER.md, MEMORY.md ou équivalent)
- **Configuration** : fichier de config principal (JSON, YAML, etc.)
- **Agents/tâches** : scripts Python ou autres qui exécutent des actions
  (heartbeat, rédaction, veille, etc.)
- **Workflows automatisés** : CRON jobs, LaunchAgents, services planifiés
- **Dépendances externes** : APIs utilisées (Gemini, GPT, Tavily, Brave, etc.),
  credentials, bibliothèques
- **Données d'état** : fichiers de session, mémoire persistante, déduplication

### Livrable attendu

Un document résumant :
- L'architecture générale (dossiers, fichiers, rôle de chaque composant)
- Les services actifs (CRON, hooks, agents)
- Les dépendances externes (APIs, credentials, bibliothèques)
- Les points d'attention (fichiers volumineux, configurations inhabituelles)

Sauvegardez ce document — c'est votre référence pour la suite.

---

## Étape 2 — Inventorier les composants

À partir de l'audit, classez chaque composant dans une de ces catégories :

| Action | Signification | Exemple |
|--------|---------------|---------|
| **CONSERVER** | Code Python fonctionnel, aucune migration nécessaire | Scripts utilitaires sans appel LLM |
| **REMPLACER_LLM** | Garder la logique, remplacer l'appel LLM par Claude CLI | Agent rédacteur, heartbeat LLM |
| **RÉÉCRIRE** | Dépend d'une infrastructure absente dans iAgent | Gateway Node.js, webhooks custom |
| **SUPPRIMER** | Fonctionnalité inutilisée ou redondante | Validations obsolètes, code mort |

### Format recommandé

Créez un tableau à 5 colonnes :

```markdown
| Composant | Rôle actuel | Moteur actuel | Action iAgent | Priorité |
|-----------|-------------|---------------|---------------|----------|
| heartbeat | Surveillance | Gemini API    | REMPLACER_LLM | P1       |
| gateway   | Telegram     | Node.js       | RÉÉCRIRE      | P1       |
| rédacteur | Newsletter   | GPT-4         | REMPLACER_LLM | P2       |
| archive   | Nettoyage    | Python pur    | CONSERVER      | P3       |
```

Identifiez également :
- Les vices de sécurité à corriger (tokens en clair, permissions trop larges)
- Les dépendances critiques (LaunchAgents, paths Python, ports)

**Validez ce tableau avant de continuer.** C'est la feuille de route de votre migration.

---

## Étape 3 — Migrer les fichiers d'identité

### 3a. Fichiers d'identité (personnalité)

Copiez vos fichiers d'identité existants dans `~/.iagent/identity/` :

```bash
# Adaptez les chemins selon votre ancien assistant
cp ~/ancien-assistant/IDENTITY.md ~/.iagent/identity/IDENTITY.md
cp ~/ancien-assistant/SOUL.md ~/.iagent/identity/SOUL.md
cp ~/ancien-assistant/USER.md ~/.iagent/identity/USER.md
# etc.
```

**Important :** éditez ensuite chaque fichier pour :
- Remplacer les mentions de Gemini, GPT ou autre LLM par Claude Code CLI
- Supprimer les références à l'ancien gateway ou framework
- Mettre à jour les chemins de fichiers vers `~/.iagent/`
- Vérifier que le format est compatible avec iAgent
  (voir les fichiers `identity/*.md` actuels pour référence)

### 3b. Projets métier

Si vous avez des projets métier (newsletter, veille, pipeline de contenu, etc.),
deux options :

**Option 1 — Projet intégré à iAgent :**
```bash
mkdir -p ~/.iagent/projects/mon-projet/{agents,prompts,state,logs}
cp ~/ancien-assistant/projets/mon-projet/agents/*.py ~/.iagent/projects/mon-projet/agents/
```

**Option 2 — Projet séparé (recommandé si autonome) :**
```bash
mkdir -p ~/mon-projet/{agents,prompts,state,logs}
cp ~/ancien-assistant/projets/mon-projet/agents/*.py ~/mon-projet/agents/
```
Les agents du projet importent `core.*` depuis iAgent via `sys.path`.

### 3c. Données d'état

Si vous avez des fichiers d'état (déduplication, mémoire, sessions) :
```bash
# Adaptez selon votre structure
cp ~/ancien-assistant/data/state.json ~/.iagent/data/
```

### 3d. Personnaliser CLAUDE.md

Éditez `~/.iagent/CLAUDE.md` (créé à l'installation via `identity/CLAUDE-template.md`).

Si ce n'est pas déjà fait, remplacez chaque `[À REMPLACER]` :
- **Nom du projet** : le nom de votre agent
- **Compte macOS** : votre nom d'utilisateur (`whoami`)
- **Chemin absolu** : `/Users/VOTRE_USER/.iagent`
- **Python path** : `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
- **Langue** : votre langue de travail

Puis ajoutez les éléments spécifiques à votre migration :
- Les décisions architecturales issues du tableau de migration (étape 2)
- Les problèmes connus spécifiques à votre configuration
- Les composants migrés et leur statut (CONSERVER, REMPLACER_LLM, etc.)

### 3e. Vérifier iagent.json

Le fichier `~/.iagent/config/iagent.json` est **pré-configuré dans le repo — aucune
modification manuelle nécessaire** dans la plupart des cas.

Points importants pour la migration :
- `python_path` pointe vers `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` —
  vérifiez que ce chemin existe sur votre machine (`ls -la` sur ce chemin)
- `gateway.tools` inclut `Write` et `Edit` — **requis** pour que l'agent puisse
  écrire ses fichiers de configuration lors du BOOTSTRAP. Ne pas retirer ces outils.
- `gateway.timeout` à 180s — nécessaire pour l'écriture des fichiers identity
  lors de la première conversation

Référence complète : voir `docs/install/guide-installation.md`, étape 7.

---

## Étape 4 — Migrer les composants LLM

Pour chaque composant classé **REMPLACER_LLM** dans votre tableau :

1. Identifiez l'appel LLM actuel (Gemini, GPT, Groq, etc.)
2. Remplacez-le par un appel à `core/claude_runner.py` :

```python
from core.claude_runner import run

response = run(
    prompt="Votre prompt ici",
    context_files=["identity/IDENTITY.md", "identity/SOUL.md"],
    timeout=60
)

if response.success:
    print(response.text)
else:
    print(f"Erreur : {response.error}")
```

3. Testez chaque composant migré individuellement
4. Vérifiez que le résultat est comparable à l'ancien système

> **Conseil :** migrez les composants P1 d'abord, validez, puis passez aux P2.
> Ne migrez pas tout en une seule fois.

---

## Étape 5 — Valider

### Diagnostic complet

```bash
cd ~/.iagent
bash scripts/doctor.sh
```

**Résultat attendu : 17/17 ✓** — Le diagnostic vérifie 17 points (environnement,
fichiers, services, connectivité, heartbeat, sécurité, sauvegarde).
Mode rapide (sans appels réseau) : `bash scripts/doctor.sh --quick` → 14/14 attendu.

Pour le détail des 17 vérifications, voir `docs/install/guide-installation.md`, étape 10.

### Audit de sécurité

```bash
bash scripts/security-audit.sh --fix
```

**Résultat attendu : 0 critique, 0 élevé — posture ACCEPTABLE.**
L'audit vérifie 10 catégories (permissions fichiers, secrets exposés, isolation,
injection de prompts, exfiltration, authentification, logging, dépendances, réseau,
configuration).

Le flag `--fix` corrige automatiquement les permissions (chmod). Autres options :
```bash
bash scripts/security-audit.sh --json       # sortie JSON
bash scripts/security-audit.sh --category 3 # une seule catégorie
```

Pour le détail des 10 catégories, voir `docs/install/guide-installation.md`, étape 11.

### Test Telegram

Envoyez un message à votre bot et vérifiez :
- Réponse reçue avec le ton attendu
- Bootstrap chargé (identité correcte)
- Session persistante (2e message sans re-bootstrap)

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
1. Envoyer « Bonjour » → l'agent doit répondre avec l'identité migrée
2. Envoyer `/brief` → brief matinal avec agenda et mails
3. Envoyer un vocal → transcription puis réponse
4. Envoyer `/doctor` → diagnostic santé

### Test des composants migrés

Pour chaque composant REMPLACER_LLM migré, exécutez-le manuellement
et comparez le résultat avec l'ancien système.

---

## Étape 6 — Couper l'ancien système

Une fois la validation complète :

1. **Arrêter les services de l'ancien assistant** :
```bash
# Adaptez selon votre ancien système
launchctl unload ~/Library/LaunchAgents/com.ancien-assistant.*.plist
# ou : arrêter le service Node.js, CRON, etc.
```

2. **Ne pas supprimer immédiatement** — gardez l'ancien dossier pendant
   2 semaines minimum en cas de besoin de référence

3. **Révoquer les clés API obsolètes** (Gemini, Groq, OpenAI, Tavily, etc.)
   si vous ne les utilisez plus ailleurs

4. **Archiver** (optionnel) :
```bash
mv ~/ancien-assistant ~/ancien-assistant_archived_$(date +%Y%m%d)
```

---

## En cas de problème

Si un composant migré ne fonctionne pas :

1. Vérifiez les logs : `tail -50 ~/.iagent/logs/runner.log`
2. Testez le composant en isolation :
   ```python
   python3 -c "from core.claude_runner import run; r = run('test', timeout=30); print(r)"
   ```
3. Comparez avec le comportement original dans votre ancien assistant
4. Consultez les erreurs fréquentes dans `docs/install/guide-installation.md`

---

## Références utiles

Le guide d'installation (`docs/install/guide-installation.md`) contient des sections
complémentaires qui restent pertinentes après migration :

- **Brief matinal** — fonctionnement et personnalisation du `/brief`
- **Skills disponibles** — Gmail, Calendar, Drive, Whisper, Documents
- **Commandes de maintenance** — logs, redémarrage, diagnostic rapide
- **Erreurs fréquentes** — table des erreurs courantes et solutions
- **Rotation des tokens en urgence** — procédure si un token est compromis
- **Sécurité** — principes de sécurité d'iAgent
