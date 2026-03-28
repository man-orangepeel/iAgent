<!-- SENTINEL:TOOLS-G7H8 -->
# TOOLS.md — Notes locales iAgent · v3.0

## Outils Bash disponibles en session Telegram

Tu as accès à Bash. Utilise ces commandes directement :
- **`gog gmail ...`** → lire emails, chercher, marquer lu
- **`gog calendar ...`** → événements calendrier
- **`iagent doctor`** → diagnostic santé
- **`iagent security`** → audit sécurité
- **`iagent logs <nom>`** → dernières lignes d'un log

Quand l'utilisateur demande ses emails, son agenda, un diagnostic → **exécute la commande Bash immédiatement**, ne dis pas "je n'ai pas accès".

---

**Python actif :** python3 (adapter selon ton système)
Sur macOS avec Python.org : `/Library/Frameworks/Python.framework/Versions/3.X/bin/python3`

**Moteur LLM :** Claude Code CLI (`claude -p`) via `core/claude_runner.py`.
Pas de clé API — auth OAuth forfait Max.

---

## Exécution LLM — claude_runner.py

Tous les appels LLM passent par `core/claude_runner.py` :

```python
from core.claude_runner import run as claude_run
response = claude_run("Mon prompt", context_files=["identity/IDENTITY.md"], timeout=60)
```

**Règles d'optimisation financière :**
- Injecter UNIQUEMENT les fichiers contexte nécessaires (jamais toute l'identity)
- Un seul appel groupé par génération
- Timeout max : 60s pour la production
- Logger durée et nb de chars injectés (voir `logs/runner.log`)

---

## Telegram — envoi direct

```python
# Via le skill telegram (tokens depuis .env)
from skills.telegram.telegram_client import send_message, send_photo, send_poll
send_message("Texte")
send_photo("https://...", caption="Légende")
send_poll("?", ["Oui", "Non", "Peut-être"])

# DM alertes opérateur
send_message("Alerte : ...", chat_id=IAGENT_CHAT_ID)
```

---

## Credentials — Inventaire

Tous dans `~/.iagent/.env`.

| Credential | Variable `.env` | Utilisé ? |
|---|---|---|
| Telegram bot token | `IAGENT_BOT_TOKEN` | ✅ Gateway |
| Telegram chat ID   | `IAGENT_CHAT_ID`   | ✅ Alertes |
| ntfy topic | `NTFY_TOPIC` | ✅ Notifications push |
| WebSearch | natif Claude CLI | ✅ Recherche web (via run_with_search) |
| gog OAuth | `credentials/gog/oauth.json` | ✅ Gmail/Calendar |

---

## Planification — LaunchAgents macOS

iAgent utilise `launchd` (natif macOS), pas de CRON ni de gateway Node.js.

```bash
# Vérifier les agents actifs
launchctl list | grep iagent
```

---

## Dispatcher iagent — Opérations internes

Toutes les opérations internes passent par `iagent`.
**Disponible en session Telegram** via `Bash(iagent:*)`.

```bash
iagent doctor --quick       # Diagnostic santé rapide
iagent doctor               # Diagnostic complet (17 checks)
iagent security             # Audit sécurité (35 checks)
iagent heartbeat --dry-run  # Simuler un heartbeat
iagent logs telegram        # 20 dernières lignes log Telegram
iagent logs runner          # 20 dernières lignes log runner
```

---

## gog — Accès Gmail, Calendar, Drive

Binaire : `/usr/local/bin/gog`
Compte : [À configurer]
**Disponible en session Telegram** via `Bash(gog:*)`.

```bash
gog gmail search "is:unread newer_than:7d" --max 5 --json
gog gmail get <message_id> --json
gog gmail messages modify <message_id> --remove UNREAD
gog calendar list --all --days 7
```

---

## Skills — Statut

| Skill | Commande | Statut |
|-------|----------|--------|
| gog (Gmail/Calendar/Drive) | `gog ...` | ✅ Actif |
| iagent (opérations internes) | `iagent ...` | ✅ Actif |
| telegram (skills/) | via Python | ✅ Actif |
| ntfy (skills/) | via Python | ✅ Actif |
| whisper (skills/) | via gateway vocal | ✅ Actif |
| documents (PDF/DOCX) | via gateway document | ✅ Actif |
| morning brief | cron 7h45 + /brief | ✅ Actif |
| reminder | cron 15min | ✅ Actif |

---

## Whisper — Transcription audio

Modèle : base (local via brew, ~150MB, ~30s/min audio sur CPU)
Formats : .ogg (Telegram), .wav, .mp3
Purge auto : fichiers tmp supprimés après 24h

Comportement :
- Envoyer un message vocal → transcrit automatiquement, traité comme texte
- Dire "transcris" puis envoyer vocal → retourne aussi le texte brut

---

## Documents — Extraction PDF, DOCX

Outils CLI : pdftotext (poppler via brew), textutil (macOS natif)
Formats : .pdf, .docx, .doc
Limite : 40 000 caractères envoyés à Claude (tronqué si plus)
Stockage : caption "stocke dans <projet>" → data/workspace/<projet>/
Purge auto : fichiers tmp supprimés après 24h

Comportement :
- Envoyer un document → extrait le texte, analyse par Claude
- Ajouter un caption → utilisé comme instruction ("résume ce PDF", "traduis ce document")
- Caption "stocke dans projet-x" → sauvegarde dans workspace + analyse

---

## Morning Brief — Brief quotidien 7h45

Cron : com.iagent.morning_brief.plist (7h45)
Commande Telegram : /brief (re-analyse complète)
Données : projects/personal_assistant/state/tracking.json

Contenu :
- Rappels actifs (mails re-notifiés non lus)
- Agenda du jour (gog calendar, hors événements passés)
- Mails non lus 7j (gog gmail)

Réponse au brief (numéros/lettres) :
- Chiffres → rappel événement (défaut 1h, ou -Nmin : "3-15")
- Lettres → mail à re-notifier chaque matin jusqu'à lu

---

## Reminder — Rappels toutes les 15min

Cron : com.iagent.reminder.plist (StartInterval 900s)
Silencieux si rien à envoyer.
Envoie les rappels événements dus depuis tracking.json.

---

### Ajouter un nouveau skill

1. Installer le binaire (ex: `brew install ...`)
2. Créer le module dans `skills/<nom>/`
3. Documenter les commandes dans cette section
4. Redémarrer gateway : `launchctl unload/load ~/Library/LaunchAgents/com.iagent.telegram.plist`
