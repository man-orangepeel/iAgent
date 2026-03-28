# -*- coding: utf-8 -*-
"""
whisper_client.py — Skill Whisper pour iAgent.

Transcription audio locale via le CLI `whisper` (brew install openai-whisper).
Pas de clé API requise — tout est local.

Workflow :
  1. Reçoit un chemin vers un fichier audio (.ogg, .wav, .mp3...)
  2. Appelle `whisper` en subprocess avec --model base et --output_format json
  3. Parse le résultat JSON pour extraire le texte
  4. Nettoie les fichiers temporaires

Modèle : "base" (~150MB, ~30s sur CPU Intel i5 pour 1min audio)
Note : sur machine avec GPU, utiliser "turbo" (large-v3-turbo) pour de meilleures performances.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("iagent.whisper")

# Binaire whisper installé via brew
_WHISPER_BIN = "/usr/local/bin/whisper"

# Modèle par défaut — "base" pour CPU Intel i5 (turbo recommandé si GPU disponible)
_DEFAULT_MODEL = "base"


def transcribe(
    audio_path: Path,
    model: str = _DEFAULT_MODEL,
    cleanup: bool = True,
) -> dict:
    """
    Transcrit un fichier audio en texte via le CLI whisper.

    Args:
        audio_path : chemin vers le fichier audio (.ogg, .wav, .mp3...)
        model      : modèle whisper (tiny, base, small, medium, large)
        cleanup    : supprimer les fichiers temporaires après transcription

    Returns:
        {
            "success": bool,
            "text": str,           # texte transcrit
            "language": str,       # langue détectée ("fr", "en"...)
            "error": str           # si success=False
        }
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        return {"success": False, "text": "", "language": "", "error": f"Fichier introuvable : {audio_path}"}

    output_dir = audio_path.parent
    _logger.info("Transcription : %s (modèle=%s)", audio_path.name, model)

    try:
        result = subprocess.run(
            [
                _WHISPER_BIN,
                str(audio_path),
                "--model", model,
                "--output_format", "json",
                "--output_dir", str(output_dir),
                "--fp16", "False",       # CPU Intel — pas de GPU
                "--language", "French",  # Optimisation : forcer français (95% des vocaux)
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max — marge pour vocaux longs (5-7 min)
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:200]
            _logger.error("whisper erreur (code %d) : %s", result.returncode, stderr)
            return {"success": False, "text": "", "language": "", "error": f"whisper erreur : {stderr}"}

        # Lire le JSON de sortie
        json_path = audio_path.with_suffix(".json")
        if not json_path.exists():
            # Essayer avec le nom complet (whisper ajoute parfois le suffixe)
            json_candidates = list(output_dir.glob(f"{audio_path.stem}*.json"))
            json_path = json_candidates[0] if json_candidates else None

        if not json_path or not json_path.exists():
            # Fallback : parser stdout
            text = result.stdout.strip()
            _logger.info("Transcription OK (stdout) | %d chars", len(text))
            return {"success": True, "text": text, "language": "fr", "error": ""}

        data = json.loads(json_path.read_text(encoding="utf-8"))
        text = data.get("text", "").strip()
        language = data.get("language", "fr")

        _logger.info("Transcription OK | lang=%s | %d chars", language, len(text))

        return {"success": True, "text": text, "language": language, "error": ""}

    except subprocess.TimeoutExpired:
        _logger.error("whisper timeout (300s)")
        return {"success": False, "text": "", "language": "", "error": "Timeout transcription (300s)"}
    except FileNotFoundError:
        _logger.error("whisper CLI introuvable — installer avec : brew install openai-whisper")
        return {"success": False, "text": "", "language": "", "error": "whisper CLI absent"}
    except Exception as e:
        _logger.error("Erreur transcription : %s", e)
        return {"success": False, "text": "", "language": "", "error": str(e)}
    finally:
        if cleanup:
            _cleanup_files(audio_path, output_dir)


def _cleanup_files(audio_path: Path, output_dir: Path) -> None:
    """Supprime les fichiers temporaires générés par whisper."""
    stem = audio_path.stem
    for ext in [".json", ".txt", ".srt", ".vtt", ".tsv"]:
        for f in output_dir.glob(f"{stem}*{ext}"):
            try:
                f.unlink()
                _logger.debug("Supprimé : %s", f.name)
            except Exception:
                pass
    # Supprimer le fichier audio source
    if audio_path.exists():
        try:
            audio_path.unlink()
            _logger.debug("Supprimé : %s", audio_path.name)
        except Exception:
            pass
