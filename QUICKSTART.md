# Démarrage rapide — iAgent

> Tu viens de voir le projet et tu veux tester ?
> Suis ces 4 étapes — ensuite Claude Code fait le reste.

---

## Étape 1 — Installer VS Code

VS Code est l'éditeur de code depuis lequel tu vas piloter l'installation.

1. Télécharger depuis [code.visualstudio.com](https://code.visualstudio.com/)
2. Ouvrir le fichier téléchargé et suivre l'installation
3. Lancer VS Code

## Étape 2 — Installer l'extension Claude Code

Claude Code est l'assistant IA qui va exécuter l'installation à ta place.

1. Dans VS Code, ouvrir le terminal intégré :
   `Menu → Terminal → New Terminal`
2. Coller et exécuter cette commande :
```bash
npm install -g @anthropic-ai/claude-code
```
3. Quand c'est terminé, vérifier :
```bash
claude --version
```
   Doit afficher un numéro de version.

> **Prérequis :** Node.js doit être installé.
> Si la commande échoue : télécharger Node.js depuis
> [nodejs.org](https://nodejs.org/) (version LTS), puis relancer.

## Étape 3 — Cloner le repo iAgent

"Cloner" = télécharger le projet sur ton Mac.

Dans le terminal VS Code :
```bash
git clone https://github.com/man-orangepeel/iagent ~/.iagent
cd ~/.iagent
```

## Étape 4 — Lancer l'installation

Toujours dans le terminal VS Code, colle cette commande :
```bash
claude "Lis intégralement le fichier docs/install/runbook-install.md, \
annonce ton plan en listant les 6 phases et les 4 étapes où tu auras \
besoin de moi, puis attends ma validation avant de commencer."
```

Claude Code lit le runbook, t'explique ce qu'il va faire, et attend ton go.
**À partir de là, suis ses instructions.**

---

> **Bloqué quelque part ?**
> Envoie un message sur [LinkedIn](https://www.linkedin.com/in/manuelproquin/)
> en précisant l'étape où tu es bloqué.
