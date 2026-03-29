# Note technique — Installation de Whisper OpenAI sur macOS

**Destination** : Claude Code (extension VS Code ou CLI) pour installation autonome.
**Source** : configuration iAgent.
**Date** : 2026-03-29.

---

## 1. Qu'est-ce que Whisper dans iAgent ?

Whisper est un modèle de transcription vocale open-source d'OpenAI, exécuté **100% en local** (aucune API, aucune clé). Il convertit les messages vocaux Telegram (.ogg) en texte, qui est ensuite traité par Claude.

**Chemin du skill** : `skills/whisper/whisper_client.py`
**Binaire attendu** : `/usr/local/bin/whisper` (Intel) ou `/opt/homebrew/bin/whisper` (Apple Silicon)
**Cache des modèles** : `~/.cache/whisper/` (téléchargement automatique au premier appel)
**Dossier temporaire audio** : `tmp/audio/`

---

## 2. Prérequis système

| Composant | Requis | Vérification |
|-----------|--------|-------------|
| macOS | 13+ (Ventura ou plus) | `sw_vers` |
| Python | 3.8+ | `python3 --version` |
| Homebrew | installé | `brew --version` |
| pip3 | installé | `pip3 --version` |
| ffmpeg | installé (dépendance whisper) | `ffmpeg -version` |
| Espace disque | ~500 Mo minimum (modèle base + dépendances) | — |

**Important** : ne JAMAIS utiliser `/usr/bin/python3` (Apple system Python). Utiliser le Python installé via brew ou python.org :
```
/Library/Frameworks/Python.framework/Versions/3.x/bin/python3
```

---

## 3. Installation pas à pas

### Étape 1 — Installer ffmpeg (si absent)

```bash
brew install ffmpeg
```

Whisper en dépend pour décoder les fichiers audio (.ogg, .mp3, .wav, etc.).

### Étape 2 — Installer openai-whisper via Homebrew

```bash
brew install openai-whisper
```

Cela installe le CLI `whisper` dans `/usr/local/bin/whisper` (Intel) ou `/opt/homebrew/bin/whisper` (Apple Silicon).

**Alternative pip** (si brew échoue ou si on veut une version plus récente) :
```bash
pip3 install -U openai-whisper
```

### Étape 3 — Vérifier l'installation

```bash
whisper --help | head -1
```

**Attendu** : une ligne d'usage s'affiche.

Si `whisper` n'est pas trouvé dans le PATH, vérifier :
```bash
which whisper
# Si absent, essayer :
brew list openai-whisper --verbose | grep bin
```

### Étape 4 — Créer le dossier temporaire audio (si absent)

```bash
mkdir -p tmp/audio
```

### Étape 5 — Tester une transcription

```bash
# Générer un fichier audio de test (silence 3s)
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 3 -q:a 9 -acodec libvorbis /tmp/test_whisper.ogg -y

# Transcrire
whisper /tmp/test_whisper.ogg --model base --output_format json --fp16 False --language French --output_dir /tmp/

# Vérifier la sortie
cat /tmp/test_whisper.json
```

**Attendu** : un JSON avec `"text"`, `"language"`.

Nettoyage :
```bash
rm -f /tmp/test_whisper.{ogg,json,txt,srt,vtt,tsv}
```

---

## 4. Configuration dans iAgent

Le fichier de configuration est `skills/whisper/whisper_client.py`. Les variables clés :

```python
# Chemin du binaire
_WHISPER_BIN = "/usr/local/bin/whisper"
# Sur Apple Silicon (M1/M2/M3/M4), modifier en :
# _WHISPER_BIN = "/opt/homebrew/bin/whisper"

# Modèle par défaut
_DEFAULT_MODEL = "base"
```

### Adapter le binaire à l'architecture

| Architecture | Chemin binaire brew |
|---|---|
| Intel (x86_64) | `/usr/local/bin/whisper` |
| Apple Silicon (arm64) | `/opt/homebrew/bin/whisper` |

Pour détecter automatiquement :
```bash
uname -m
# x86_64 → Intel
# arm64  → Apple Silicon
```

### Adapter `--fp16` à la machine

| Machine | `--fp16` | Raison |
|---------|----------|--------|
| CPU Intel (pas de GPU) | `False` | Pas de support FP16 sans GPU |
| Apple Silicon avec MPS | `False` | PyTorch MPS ne supporte pas FP16 pour whisper |
| NVIDIA GPU (CUDA) | `True` (par défaut) | Accélération GPU native |

---

## 5. Choix du modèle

| Modèle | Taille disque | RAM | Vitesse CPU | Vitesse GPU | Qualité FR | Vocal max (timeout 300s) |
|--------|--------------|-----|-------------|-------------|-----------|--------------------------|
| `tiny` | 75 Mo | 150 Mo | ~10x realtime | ~100x | Faible | ~50 min |
| **`base`** | **150 Mo** | **300 Mo** | **~1x realtime** | **~30x** | **Correct** | **~4-5 min** |
| `small` | 500 Mo | 1 Go | ~0.3x realtime | ~15x | Bon | ~1.5-2 min |
| `medium` | 1.5 Go | 2.5 Go | ~0.1x realtime | ~8x | Tres bon | ~30s (CPU) |
| `turbo` | 800 Mo | 1.5 Go | Trop lent CPU | ~25x | Excellent | GPU recommande |

**Recommandation** :
- **Intel sans GPU** : `base` (bon compromis vitesse/qualité)
- **Apple Silicon (M1+)** : `turbo` (excellent via accélération MPS)
- **NVIDIA GPU** : `turbo` ou `large-v3`

Pour changer :
```python
# Dans skills/whisper/whisper_client.py :
_DEFAULT_MODEL = "turbo"   # Apple Silicon / GPU
_DEFAULT_MODEL = "base"    # Intel CPU seul (défaut)
```

Le modèle se télécharge automatiquement dans `~/.cache/whisper/` lors du premier appel.

---

## 6. Intégration dans iAgent

### Flux de données

```
Utilisateur → message vocal Telegram (.ogg)
    → gateway/telegram_gateway.py
    → télécharge .ogg dans tmp/audio/
    → appelle whisper_transcribe(ogg_path, cleanup=True)
    → skills/whisper/whisper_client.py
    → subprocess: whisper fichier.ogg --model base --output_format json --fp16 False --language French
    → parse JSON → extrait texte
    → nettoie fichiers temporaires (.json, .txt, .srt, .vtt, .tsv, .ogg)
    → retourne texte transcrit → traité par Claude comme message texte
```

### Arguments CLI utilisés

```bash
whisper <fichier_audio> \
  --model base \
  --output_format json \
  --output_dir <dossier_parent_du_fichier> \
  --fp16 False \
  --language French
```

| Argument | Valeur | Raison |
|----------|--------|--------|
| `--model` | `base` | Compromis vitesse/qualité sur CPU |
| `--output_format` | `json` | Parsing programmatique |
| `--output_dir` | `tmp/audio/` | Meme dossier que le source |
| `--fp16` | `False` | Pas de GPU |
| `--language` | `French` | 95% des vocaux sont en français, évite la détection auto |

### Dry-run / diagnostic

Le gateway Telegram inclut un check whisper dans son dry-run :
```bash
python3 gateway/telegram_gateway.py --dry-run
```

Sortie attendue :
```
Whisper : ✅ (disponible)
```

---

## 7. Dépannage

| Problème | Diagnostic | Solution |
|----------|-----------|----------|
| `whisper: command not found` | `which whisper` | `brew install openai-whisper` |
| `FileNotFoundError` dans les logs | Le binaire n'est pas au chemin configuré | Vérifier `which whisper` et adapter `_WHISPER_BIN` |
| Timeout 300s dépassé | Audio trop long pour le modèle/CPU | Passer à `tiny` ou limiter la durée des vocaux |
| `RuntimeError: CUDA not available` | Normal sur Mac sans NVIDIA | S'assurer que `--fp16 False` est bien passé |
| Modèle ne se télécharge pas | Problème réseau ou disque plein | Vérifier espace disque et connectivité, `ls ~/.cache/whisper/` |
| Transcription vide ou mauvaise | Mauvaise langue détectée | `--language French` force le français |
| `No module named 'whisper'` | Installation pip cassée | `pip3 install -U openai-whisper` |

---

## 8. Résumé des commandes d'installation

```bash
# 1. Prérequis
brew install ffmpeg

# 2. Whisper
brew install openai-whisper

# 3. Vérification
whisper --help | head -1
which whisper

# 4. Dossier audio
mkdir -p tmp/audio

# 5. Test fonctionnel (optionnel)
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 3 -q:a 9 -acodec libvorbis /tmp/test_whisper.ogg -y
whisper /tmp/test_whisper.ogg --model base --output_format json --fp16 False --language French --output_dir /tmp/
cat /tmp/test_whisper.json
rm -f /tmp/test_whisper.{ogg,json,txt,srt,vtt,tsv}

# 6. Dry-run iAgent
python3 gateway/telegram_gateway.py --dry-run
```

---

## 9. Fichiers impliqués (référence rapide)

| Fichier | Role |
|---------|------|
| `skills/whisper/whisper_client.py` | Module Python — appel subprocess + parsing |
| `gateway/telegram_gateway.py` | Intégration — réception vocaux, appel transcribe |
| `config/kintoun.json` | Config générale (tmp.audio_dir) |
| `~/.cache/whisper/` | Cache des modèles téléchargés |
| `tmp/audio/` | Stockage temporaire des fichiers audio |
