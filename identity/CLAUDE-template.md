# [À REMPLACER: Nom du projet] — Contexte permanent pour Claude Code

<!-- Ce fichier est lu automatiquement par Claude Code au début de chaque session.
     Personnalisez chaque section [À REMPLACER] avec vos informations. -->

## Situation
<!-- Décrivez votre projet en une phrase -->
[À REMPLACER: Description du projet]. Moteur : Claude Code CLI (forfait Pro ou Max, 0 API).
Déployé sur [À REMPLACER: compte macOS], dossier `[À REMPLACER: chemin absolu]`.

## Règles absolues
- Ne jamais lire/afficher `.env`, `credentials/`, `identity/`
- Projet 100% autonome — fichiers identity dans `identity/`, données dans `data/`
- Les projets métier vivent dans `projects/<nom>/`
- Python path : [À REMPLACER: résultat de `which python3`]
- Langue : [À REMPLACER: français / anglais / autre]

## Phases du projet
<!-- Adaptez les phases selon votre projet -->
- [ ] Phase 1 : [À REMPLACER: description]
- [ ] Phase 2 : [À REMPLACER: description]
- [ ] Phase 3 : [À REMPLACER: description]

## Phase en cours
[À REMPLACER: Phase actuelle]

## Décisions architecturales prises (ne pas rediscuter)
<!-- Ajoutez ici les décisions validées au fur et à mesure -->
- `--bare` incompatible avec auth OAuth (Pro/Max) — utiliser `--tools ""` + `--no-session-persistence`
- Sessions Telegram : `--resume` natif Claude CLI. Réinitialisation par double condition : TTL ET taille. Paramètres dans `config/iagent.json`.

## Optimisation financière — Règles d'appel Claude CLI
- Injecter UNIQUEMENT les fichiers contexte nécessaires par cas d'usage
- Un seul appel groupé par génération (pas N appels séparés)
- Timeout max : 60s pour les appels de production
- Logger durée et nb de chars injectés à chaque appel

## Problèmes connus / blocages actifs
<!-- Mettre à jour au fur et à mesure -->

---

## Documentation — Règle permanente

Après chaque phase terminée :
1. Mettre à jour les cases `[ ]` ci-dessus
2. Mettre à jour "Phase en cours"
3. Ajouter une entrée dans `DEVLOG.md`
4. Ajouter une entrée dans `docs/install/guide-installation.md` ou `DEVLOG.md`

---

## Ouverture de session — Protocole obligatoire

Au début de chaque nouvelle session ou après un compactage mémoire :
1. Lire ce fichier + `DEVLOG.md`
2. Résumer en 3 lignes : où on en est, ce qui est fait, prochaine action
3. Attendre validation avant de continuer
