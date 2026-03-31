# [À REMPLACER: Nom du projet] — Contexte permanent

<!-- Ce fichier est lu automatiquement par Claude Code et par l'agent via gateway.
     Personnalisez chaque section [À REMPLACER] avec vos informations. -->

## Situation

[À REMPLACER: Description du projet]. Moteur : Claude Code CLI (forfait Pro ou Max, 0 API).
Déployé sur [À REMPLACER: compte macOS], dossier `[À REMPLACER: chemin absolu]`.

## Règles absolues

- Ne jamais lire/afficher de secrets (tokens, credentials, clés API) — ex : `.env`, `*.key`, `*.pem`
- Projet 100% autonome — aucune dépendance externe
- Fichiers identity dans `identity/` = contexte bootstrap, à lire et utiliser
- Données dans `data/`
- Les projets métier vivent dans `projects/<nom>/`
- Python path : [À REMPLACER: résultat de `which python3`]
- Langue : [À REMPLACER: français / anglais / autre]

## Instructions d'exécution

Tu as accès à Bash et WebSearch. Exécute directement, ne dis jamais "je n'ai pas accès".

| Demande | Commande |
|---|---|
| emails, inbox, Gmail | `gog gmail search "<critères>" --max N --json` |
| agenda, calendrier | `gog calendar list --days N` |
| doctor, diagnostic | `[À REMPLACER: nom] doctor --quick` |
| sécurité, audit | `[À REMPLACER: nom] security` |
| logs | `[À REMPLACER: nom] logs telegram` |

Si tu hésites entre parler et exécuter → exécute.

## Phases du projet
<!-- Adaptez les phases selon votre projet -->
- [ ] Phase 1 : [À REMPLACER: description]
- [ ] Phase 2 : [À REMPLACER: description]
- [ ] Phase 3 : [À REMPLACER: description]

## Phase en cours

[À REMPLACER: Phase actuelle]

## Décisions architecturales prises (ne pas rediscuter)
<!-- Ajoutez ici les décisions validées au fur et à mesure -->
- Sessions Telegram : `--resume` natif Claude CLI. Réinitialisation par double condition : TTL ET taille. Paramètres dans config.

## Optimisation financière — Règles d'appel Claude CLI

- Injecter UNIQUEMENT les fichiers contexte nécessaires par cas d'usage
- Un seul appel groupé par génération (pas N appels séparés)
- Timeout max : 60s pour les appels de production
- Logger durée et nb de chars injectés à chaque appel

## Problèmes connus / blocages actifs
<!-- Mettre à jour au fur et à mesure -->

---

## Claude Code VSC — Protocole développeur

Au début de chaque nouvelle session Claude Code (VS Code) ou après un compactage mémoire :
1. Lire ce fichier + `DEVLOG.md`
2. Résumer en 3 lignes : où on en est, ce qui est fait, prochaine action
3. Attendre validation avant de continuer
