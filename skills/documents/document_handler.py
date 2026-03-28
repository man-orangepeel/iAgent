# -*- coding: utf-8 -*-
"""
document_handler.py — Skill Documents pour iAgent.

Extraction de texte depuis PDF et DOCX via CLI subprocess :
  - PDF  : pdftotext (poppler, brew install poppler)
  - DOCX : textutil (macOS natif)

Pas de bibliothèque Python requise — tout passe par subprocess.

Workflow :
  1. Reçoit un chemin vers un fichier document
  2. Détecte le type par extension
  3. Extrait le contenu texte via CLI
  4. Retourne le contenu pour traitement par Claude
  5. Stockage optionnel dans data/workspace/<projet>/
"""
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("iagent.documents")
_IAGENT_DIR = Path(__file__).resolve().parent.parent.parent
_WORKSPACE = _IAGENT_DIR / "data" / "workspace"

# Binaires
_PDFTOTEXT_BIN = "/usr/local/bin/pdftotext"
_TEXTUTIL_BIN = "/usr/bin/textutil"

# Limite contexte sécurisée
MAX_CHARS_TO_CLAUDE = 40_000

# Extensions supportées
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


# ── Extracteurs ──────────────────────────────────────────────────

def _extract_pdf(path: Path) -> dict:
    """Extrait le texte d'un PDF via pdftotext (poppler)."""
    try:
        result = subprocess.run(
            [_PDFTOTEXT_BIN, "-layout", str(path), "-"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:200]
            return {"success": False, "text": "", "error": f"pdftotext erreur : {stderr}"}

        text = result.stdout.strip()
        # Compter les pages (séparateur form-feed)
        pages = text.count("\f") + 1 if text else 0
        return {"success": True, "text": text, "meta": {"type": "pdf", "pages": pages}}

    except subprocess.TimeoutExpired:
        return {"success": False, "text": "", "error": "Timeout extraction PDF (60s)"}
    except FileNotFoundError:
        return {"success": False, "text": "", "error": "pdftotext absent — brew install poppler"}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


def _extract_docx(path: Path) -> dict:
    """Extrait le texte d'un DOCX/DOC via textutil (macOS natif)."""
    try:
        result = subprocess.run(
            [_TEXTUTIL_BIN, "-convert", "txt", "-stdout", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:200]
            return {"success": False, "text": "", "error": f"textutil erreur : {stderr}"}

        text = result.stdout.strip()
        paragraphs = len([p for p in text.split("\n") if p.strip()])
        return {"success": True, "text": text, "meta": {"type": "docx", "paragraphs": paragraphs}}

    except subprocess.TimeoutExpired:
        return {"success": False, "text": "", "error": "Timeout extraction DOCX (60s)"}
    except FileNotFoundError:
        return {"success": False, "text": "", "error": "textutil absent (devrait être natif macOS)"}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


# ── Routage par extension ────────────────────────────────────────

_EXTRACTORS = {
    ".pdf":  _extract_pdf,
    ".docx": _extract_docx,
    ".doc":  _extract_docx,
}


# ── Interface principale ─────────────────────────────────────────

def extract(file_path: Path) -> dict:
    """
    Extrait le contenu texte d'un fichier document.

    Returns :
        {
            "success": bool,
            "text": str,         # contenu extrait (tronqué si trop long)
            "truncated": bool,
            "meta": dict,        # type, pages/paragraphs
            "error": str,
        }
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    extractor = _EXTRACTORS.get(suffix)

    if not extractor:
        return {
            "success": False, "text": "", "truncated": False,
            "meta": {}, "error": f"Format non supporté : {suffix}. "
                                 f"Formats acceptés : {', '.join(SUPPORTED_EXTENSIONS)}",
        }

    if not path.exists():
        return {
            "success": False, "text": "", "truncated": False,
            "meta": {}, "error": f"Fichier introuvable : {path}",
        }

    result = extractor(path)
    if not result["success"]:
        return {
            "success": False, "text": "", "truncated": False,
            "meta": {}, "error": result["error"],
        }

    text = result["text"]
    chars_original = len(text)
    truncated = chars_original > MAX_CHARS_TO_CLAUDE

    if truncated:
        text = (text[:MAX_CHARS_TO_CLAUDE]
                + f"\n\n[... contenu tronqué — {chars_original} chars total]")
        _logger.warning("Contenu tronqué : %d → %d chars", chars_original, MAX_CHARS_TO_CLAUDE)

    meta = result.get("meta", {})
    meta["chars_original"] = chars_original

    _logger.info(
        "Extraction OK | %s | %s | %d chars%s",
        path.name, meta.get("type", "?"), chars_original,
        " (tronqué)" if truncated else "",
    )

    return {
        "success": True,
        "text": text,
        "truncated": truncated,
        "meta": meta,
        "error": "",
    }


def save_to_workspace(file_path: Path, project_name: str, new_name: Optional[str] = None) -> Path:
    """
    Déplace un fichier depuis tmp/ vers data/workspace/<project>/.
    Retourne le nouveau chemin.
    """
    dest_dir = _WORKSPACE / project_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = new_name or Path(file_path).name
    dest_path = dest_dir / dest_name
    shutil.move(str(file_path), str(dest_path))
    _logger.info("Fichier stocké dans workspace : %s", dest_path)
    return dest_path


def cleanup(file_path: Path) -> None:
    """Supprime un fichier temporaire."""
    try:
        Path(file_path).unlink(missing_ok=True)
        _logger.debug("Supprimé : %s", file_path)
    except Exception as e:
        _logger.warning("Erreur cleanup %s : %s", file_path, e)
