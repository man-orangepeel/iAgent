# Migration depuis un assistant IA existant

Tu as OpenClaw ou un agent custom, et tu veux passer à iAgent.

## Prérequis

Complète d'abord l'installation de base ([docs/install/](../install/))
et vérifie que `bash scripts/doctor.sh` passe sans erreur.

## Avant de commencer
```bash
python3 --version   # 3.11+
node --version      # 18+
brew --version
claude --version    # Claude Code CLI + forfait Pro ou Max
bash scripts/doctor.sh --quick  # 14/14 attendu
```

Si une commande échoue ou si doctor ne passe pas, complète d'abord
l'installation de base avant de migrer.

## Ce que couvre la migration

- Audit de ton assistant existant (composants, dépendances, sécurité)
- Migration des fichiers d'identité et des workflows métier
- Remplacement des appels LLM (Gemini, GPT, etc.) par Claude Code CLI
- Validation et coupure de l'ancien système

## Deux parcours

**Guide manuel** — [guide-migration.md](guide-migration.md)
Étapes détaillées pour faire la migration toi-même.
Durée : 1–2h selon la complexité de ta configuration.

**Runbook Claude Code** — [sur demande](https://www.linkedin.com/in/manuelproquin/)
Claude Code audite ton ancien assistant, produit le tableau de migration,
exécute les actions, tu valides à chaque checkpoint.
Durée : 30–45 min.

---

### Tu préfères construire ton agent sans toucher au code ?

Si tu veux les bénéfices d'un assistant IA sans gérer l'infrastructure,
le [AI Chief of Staff Bootcamp](https://aichiefofstaffbootcamp.netlify.app/)
t'accompagne en 4 semaines pour déployer tes propres agents sur ta façon
de travailler — sans prérequis technique.