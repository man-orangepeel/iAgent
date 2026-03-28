# docs/install/ — Documentation d'installation iAgent

Ce dossier contient tout le nécessaire pour installer iAgent depuis zéro.

## Deux parcours d'installation

| Parcours | Fichier | Public | Durée |
|---|---|---|---|
| **Manuel** | [guide-installation.md](guide-installation.md) | Humain (pas à pas) | 45–60 min |
| **Automatisé** | [runbook-install.md](runbook-install.md) | Claude Code (exécution assistée) | 20–30 min |

### Parcours manuel (recommandé pour une première installation)

Suivez [guide-installation.md](guide-installation.md) étape par étape.
Chaque étape inclut les commandes à exécuter et les vérifications attendues.

### Parcours automatisé (pour utilisateurs avancés)

Donnez [runbook-install.md](runbook-install.md) à Claude Code :
```
claude --resume "Lis docs/install/runbook-install.md et exécute l'installation"
```
Claude Code exécutera les étapes `[AUTO]` et vous guidera pour les étapes `[MANUEL]`.

---

## Prérequis rapides

Avant de commencer, vérifiez que vous avez :

```bash
# macOS 12+
sw_vers

# Homebrew
brew --version

# Python 3.14+
python3 --version

# Node.js 18+
node --version

# Abonnement Anthropic Pro ou Max actif
claude --version
```

Si une commande échoue, consultez la section « Prérequis » du guide d'installation.

---

## Fichiers dans ce dossier

| Fichier | Description |
|---|---|
| `README.md` | Ce fichier (orientation) |
| `guide-installation.md` | Guide complet pas à pas (12 étapes) |
| `runbook-install.md` | Runbook pour installation assistée par Claude Code (6 phases) |
