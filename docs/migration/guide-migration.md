# Guide de migration — OpenClaw vers iAgent

> Ce guide suppose que vous avez déjà complété l'installation de base
> (voir `docs/install/guide-installation.md`).
>
> Durée estimée : 1-2 heures (selon la complexité de votre OpenClaw).

---

## Vue d'ensemble

La migration se fait en 4 étapes :

1. **Auditer** votre OpenClaw existant
2. **Inventorier** les composants à migrer
3. **Migrer** les fichiers et personnaliser la configuration
4. **Valider** et couper l'ancien système

---

## Étape 1 — Auditer votre OpenClaw

Vous devez d'abord comprendre ce que contient votre OpenClaw. Claude Code peut faire cet audit pour vous.

### Ce qu'il faut lire

Demandez à Claude Code (ou lisez vous-même) :

```
Lis les fichiers suivants de mon OpenClaw et produis un rapport d'architecture :
- ~/.openclaw/openclaw.json (sans afficher les tokens)
- ~/.openclaw/cron/jobs.json
- ~/.openclaw/workspace/IDENTITY.md
- ~/.openclaw/workspace/SOUL.md
- ~/.openclaw/workspace/MEMORY.md
- ~/.openclaw/workspace/AGENTS.md
- ~/.openclaw/workspace/TOOLS.md
- ~/.openclaw/workspace/COMMUNICATION.md
- ~/.openclaw/workspace/QUEUE.md
- ~/.openclaw/workspace/HEARTBEAT.md
- Tous les fichiers Python dans ~/.openclaw/workspace/tasks/
- Tous les fichiers Python dans ~/.openclaw/workspace/agents/
- ~/.openclaw/hooks/ (tous les fichiers)
```

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
| **CONSERVER** | Code Python fonctionnel, aucune migration nécessaire | Scripts utilitaires sans LLM |
| **REMPLACER_LLM** | Garder la logique, remplacer l'appel Gemini/GPT par Claude CLI | Agent rédacteur, heartbeat LLM |
| **RÉÉCRIRE** | Dépend du gateway Node.js OpenClaw, à recoder en Python | Gateway Telegram, CRON jobs |
| **SUPPRIMER** | Fonctionnalité inutilisée ou redondante | Validations obsolètes |

### Format recommandé

Créez un tableau à 5 colonnes :

```markdown
| Composant | Rôle actuel | Moteur actuel | Action iAgent | Priorité |
|-----------|-------------|---------------|------------------|----------|
| ... | ... | ... | ... | P1/P2/P3 |
```

Identifiez également :
- Les vices de sécurité à corriger (tokens en clair, permissions trop larges)
- Les dépendances critiques (LaunchAgents, paths Python, ports)

**Validez ce tableau avant de continuer.** C'est la feuille de route de votre migration.

---

## Étape 3 — Migrer les fichiers

### 3a. Fichiers bootstrap (identité)

Copiez vos fichiers bootstrap existants dans `~/.iagent/identity/` :

```bash
# Exemple — adaptez selon votre audit
cp ~/.openclaw/workspace/IDENTITY.md ~/.iagent/identity/
cp ~/.openclaw/workspace/SOUL.md ~/.iagent/identity/
cp ~/.openclaw/workspace/USER.md ~/.iagent/identity/
# etc.
```

**Important :** éditez ensuite chaque fichier pour :
- Remplacer les mentions de Gemini/GPT par Claude
- Supprimer les références au gateway Node.js
- Mettre à jour les chemins de fichiers

### 3b. Projets métier (ex: OrangePeel Flow)

Les projets métier vivent dans leur propre dossier, séparés de iAgent :

```bash
# Exemple : extraction d'un projet dans son propre répertoire
mkdir -p ~/.orangepeel_flow/{agents,prompts,state,logs}
cp ~/.openclaw/workspace/projects/orangepeel_flow/agents/*.py ~/.orangepeel_flow/agents/
cp ~/.openclaw/workspace/projects/orangepeel_flow/prompts/*.txt ~/.orangepeel_flow/prompts/
cp ~/.openclaw/workspace/projects/orangepeel_flow/state/*.json ~/.orangepeel_flow/state/
```

Les agents du projet importent `core.*` depuis iAgent via `sys.path`.

### 3c. Données d'état

Si vous avez des fichiers d'état (déduplication, mémoire) :

```bash
cp ~/.openclaw/workspace/projects/*/state/state.json ~/.orangepeel_flow/state/
```

### 3d. Personnaliser CLAUDE.md

Éditez `~/.iagent/CLAUDE.md` (déjà créé à l'installation) pour ajouter :
- Les décisions architecturales de votre migration (section "Décisions architecturales")
- Les problèmes connus spécifiques à votre configuration
- Les phases spécifiques de votre migration (à la place des phases génériques)

### 3e. Personnaliser iagent.json

Éditez `~/.iagent/config/iagent.json` pour ajuster :
- `python_path` : résultat de `which python3` sur votre machine
- `session.ttl_hours` : durée avant réinitialisation de session Telegram
- `session.max_size_kb` : taille max du fichier de session
- `heartbeat.interval_minutes` : fréquence du heartbeat

---

## Étape 4 — Migrer les composants LLM

Pour chaque composant classé **REMPLACER_LLM** dans votre tableau :

1. Identifiez l'appel LLM actuel (Gemini, GPT, etc.)
2. Remplacez-le par un appel à `core/claude_runner.py` :

```python
from core.claude_runner import run

response = run(
    prompt="Votre prompt ici",
    context_files=["identity/IDENTITY.md", "identity/SOUL.md"],
    timeout=60
)
```

3. Testez chaque composant migré individuellement

---

## Étape 5 — Valider

### Diagnostic complet

```bash
cd ~/.iagent
bash scripts/doctor.sh
```

### Audit de sécurité

```bash
bash scripts/security-audit.sh
```

### Test Telegram

Envoyez un message à votre bot et vérifiez :
- Réponse reçue avec le ton attendu
- Bootstrap chargé (identité correcte)
- Session persistante (2e message sans re-bootstrap)

---

## Étape 6 — Couper l'ancien système

Une fois la validation complète :

1. **Arrêter les services OpenClaw** :
```bash
launchctl unload ~/Library/LaunchAgents/com.openclaw.*.plist
```

2. **Ne pas supprimer immédiatement** — gardez `~/.openclaw/` pendant 1-2 semaines en cas de besoin de référence

3. **Révoquer les clés API obsolètes** (Gemini, Groq, etc.) si vous ne les utilisez plus

---

## En cas de problème

Si un composant migré ne fonctionne pas :

1. Vérifiez les logs : `cat ~/.iagent/logs/runner.log`
2. Testez le composant en isolation : `python3 -c "from agents.xxx import run; print(run({...}))"`
3. Comparez avec le comportement original dans OpenClaw
4. Consultez les erreurs fréquentes dans `docs/install/guide-installation.md`
