# Migration — Depuis un assistant IA existant vers iAgent

> Vous avez déjà un assistant IA (OpenClaw, custom, autre) et vous
> voulez passer à iAgent ? Ce dossier vous guide dans la migration.

## Prérequis

**Avant de commencer la migration, complétez d'abord l'installation de base :**

1. Suivez le parcours [docs/install/](../install/) en entier
2. Vérifiez que `bash scripts/doctor.sh` passe sans erreur
3. Revenez ici pour les étapes spécifiques à la migration

## Ce que fait la migration

La migration transforme votre installation iAgent de base en un remplacement
complet de votre ancien assistant. Elle :

- Audite votre assistant existant pour identifier ce qui doit être conservé, remplacé ou supprimé
- Migre vos fichiers d'identité et vos workflows métier
- Remplace les appels LLM existants (Gemini, GPT, etc.) par Claude Code CLI
- Valide que tout fonctionne avant de couper l'ancien système

## Par où commencer

### Option A — Vous suivez le guide vous-même
Ouvrez [guide-migration.md](guide-migration.md) et suivez les étapes une par une.

### Option B — Vous laissez Claude Code faire le maximum
1. Ouvrez Claude Code dans le terminal
2. Donnez-lui le fichier [runbook-migration.md](runbook-migration.md) comme instruction
3. Claude Code audite votre ancien assistant, produit les livrables, vous validez à chaque checkpoint

## Fichiers dans ce dossier

| Fichier | Rôle |
|---------|------|
| `guide-migration.md` | Guide pas-à-pas pour un humain |
| `runbook-migration.md` | Blocs de commandes pour Claude Code |
