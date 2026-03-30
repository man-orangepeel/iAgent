# QUICKSTART — iAgent

> Suis ces étapes dans l'ordre.
> À l'étape 5, Claude Code prend le relais.

---

## Ce que tu fais (étapes 1–5)

### Étape 1 — Compte Anthropic + forfait Pro ou Max

1. Créer un compte sur [claude.ai](https://claude.ai)
2. Souscrire au forfait **Pro** (20€/mois) ou Max
   → C'est le cerveau de ton agent. Aucun autre abonnement IA, ou paiement d'une API n'est nécessaire.

### Étape 2 — Installer VS Code

1. Télécharger depuis [code.visualstudio.com](https://code.visualstudio.com/)
2. Installer et lancer

### Étape 3 — Installer l'extension Claude Code dans VS Code

1. Dans VS Code, ouvrir le panneau **Extensions** (icône dans la barre verticale gauche)
2. Chercher `Claude Code`
3. Cliquer **Install**

### Étape 4 — Ouvrir ce fichier dans VS Code

Dans VS Code, ouvrir le dossier où tu as enregistré le fichier :
   `File → Open Folder` (sélectionne le dossier)


### Étape 5 — Donner les instructions à Claude Code

1. Ouvre le tchat avec Claude (logo en haut à droite)
2. Dans le chat, choisis le mode "Ask before edit" (en bas à droite)
3. Dis à Claude :
`Lis le fichier QUICKSTART.md qui est dans ce dossier et suis les instructions de la section CE QUE FAIT CLAUDE.`

**À partir de là, Claude Code prend le relais. Suis ses instructions.**

---

## Ce que fait Claude (étapes 6–9)

> *Cette section est à destination de Claude Code — pas à lire par l'utilisateur.*

### Étape 6 — Vérifier et installer Node.js

```bash
node --version 2>/dev/null || echo "ABSENT"
```

Si absent :
- Informer l'utilisateur
- Lui demander de télécharger Node.js LTS depuis [nodejs.org](https://nodejs.org/)
- Attendre confirmation avant de continuer

### Étape 7 — Installer Claude Code CLI

Installer dans `~/.npm-global` (chemin attendu par les LaunchAgents et le runtime iAgent) :

```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
npm install -g @anthropic-ai/claude-code
```

Ajouter `~/.npm-global/bin` au PATH de façon permanente :

```bash
# Détecter le shell et ajouter au bon fichier de config
SHELL_RC="$HOME/.zshrc"
[ "$SHELL" = "/bin/bash" ] && SHELL_RC="$HOME/.bashrc"
grep -q '\.npm-global' "$SHELL_RC" 2>/dev/null || echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> "$SHELL_RC"
export PATH="$HOME/.npm-global/bin:$PATH"
```

Vérifier l'installation :
```bash
~/.npm-global/bin/claude --version
```

Guider l'utilisateur pour l'authentification OAuth (lien à ouvrir dans le navigateur) :
```bash
~/.npm-global/bin/claude auth login
```

Vérifier :
```bash
~/.npm-global/bin/claude auth status 2>&1 | grep loggedIn
# Doit afficher "loggedIn": true
```

### Étape 8 — Choisir l'emplacement et cloner le repo

Demander à l'utilisateur :
> "Où veux-tu installer iAgent ? L'emplacement par défaut est `~/.iagent/`.
> Tu peux choisir un autre dossier. Confirme ou indique un chemin."

Attendre la réponse, puis :

```bash
IAGENT_DIR="${RÉPONSE_UTILISATEUR:-$HOME/.iagent}"
git clone https://github.com/man-orangepeel/iagent "$IAGENT_DIR"
cd "$IAGENT_DIR"
echo "✓ Repo cloné dans : $IAGENT_DIR"
```
Puis aide l'utilisateur à ajouter le nouveau dossier dans l'explorateur VSC, à rouvrir sur QUICKSTART.md (celui du dossier), et à fermer le dossier qu'il avait initialement ouvert (contenant le 1er QUICKSTART)

### Étape 9 — Vérifier la présence du runbook et orienter

```bash
RUNBOOK="$IAGENT_DIR/docs/install/runbook-install.md"
[ -f "$RUNBOOK" ] && echo "RUNBOOK_PRESENT" || echo "RUNBOOK_ABSENT"
```

**Si le runbook est présent :**

Demander à l'utilisateur :
> "Tu as le runbook. Deux options pour continuer :
> - **Automatique** : je gère l'installation grâce au runbook, tu valides les étapes clés (recommandé)
> - **Manuel** : tu suis le guide pas à pas toi-même → `docs/install/guide-installation.md`
> Quelle option tu choisis ?"

Si automatique → dire à Claude Code dans le chat :
> "Lis intégralement `docs/install/runbook-install.md` et exécute-le."

Si manuel → informer :
> "Ouvre `docs/install/guide-installation.md` et suis les étapes.
> Je reste disponible si tu as des questions."

---

**Si le runbook est absent :**

Demander à l'utilisateur :
> "Je ne trouve pas le runbook d'installation automatisée dans le repo.
> Trois options :
> - **Manuel** : tu suis le guide pas à pas → `docs/install/guide-installation.md`
> - **Obtenir le runbook** : rends-toi sur [orangepeel-iagent.fr](https://www.orangepeel-iagent.fr)
>   pour recevoir le runbook par email, puis enregistre-le ici : `docs/install/runbook-install.md`
>   et dis-moi quand c'est fait.
> - **Sans toucher au code ? Plus puissant ? Et sur mesure ?** : le [AI Chief of Staff Bootcamp](https://aichiefofstaffbootcamp.netlify.app/) (Neon&Slate)
>   t'accompagne en 4 semaines pour déployer tes propres agents IA — emails, réunions, notes,
>   to-do, production de contenu — sans prérequis technique.
> Quelle option tu choisis ?"

Si l'utilisateur revient avec le runbook → reprendre à l'étape 9.

Si manuel → informer :
> "Ouvre `docs/install/guide-installation.md` et suis les étapes.
> Je reste disponible si tu as des questions."

---

> **Bloqué quelque part ?**
> [linkedin.com/in/manuelproquin](https://www.linkedin.com/in/manuelproquin/)