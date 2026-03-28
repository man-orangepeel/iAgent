"""Détecteur heuristique de prompt injection pour emails entrants."""
import re
from typing import Optional

# Patterns haute confiance — spécifiques aux attaques prompt injection.
# Volontairement conservateurs pour éviter les faux positifs sur
# newsletters Bitcoin (ex: "execute trades", "act as your own bank").
_INJECTION_PATTERNS = [
    r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions',
    r'disregard\s+(all\s+)?(previous|prior|above)\s+instructions',
    r'forget\s+(all\s+)?(previous|prior|above)\s+instructions',
    r'override\s+(all\s+)?(previous|prior)?\s*instructions',
    r'you\s+are\s+now\s+(a|an|the)\s+\w+',   # "you are now a different agent"
    r'your\s+new\s+(instructions|role|task|system\s+prompt)\s+(are|is)',
    r'pretend\s+(you\s+are|to\s+be)',
    r'new\s+system\s+prompt\s*:',
    r'system\s+prompt\s*:',
    r'\[system\]',
    r'<\s*system\s*>',
    r'run\s+this\s+code',
    r'execute\s+this\s+(code|script|command)',
    r'download\s+this\s+file',
    r'exfiltrate',
]

# Patterns cachés (style invisible) — tentatives de cacher les injections
# dans le HTML avant nettoyage. Vérifier sur le corps brut (avant clean_email_body).
_HIDDEN_CONTENT_PATTERNS = [
    r'display\s*:\s*none',
    r'visibility\s*:\s*hidden',
    r'opacity\s*:\s*0',
    r'font-size\s*:\s*0',
    r'color\s*:\s*white',      # texte blanc sur fond blanc
    r'<!--.*?ignore.*?-->',    # commentaires HTML avec "ignore"
]

# Patterns de stéganographie textuelle — détectés sur le texte nettoyé ET le HTML brut.
# 5+ caractères Unicode invisibles consécutifs = quasi-certainement malveillant.
_TEXT_STEGANOGRAPHY_PATTERNS = [
    r'[\u200b\u200c\u200d\ufeff\u00ad]{5,}',   # zero-width / soft-hyphen en masse
    r'[\u202a-\u202e\u2066-\u2069]',            # bidirectional override (Trojan Source)
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_COMPILED_HIDDEN = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _HIDDEN_CONTENT_PATTERNS]
_COMPILED_STEG = [re.compile(p) for p in _TEXT_STEGANOGRAPHY_PATTERNS]


def detect_injection(text: str, raw_html: Optional[str] = None) -> dict:
    """
    Analyse un texte email pour détecter des tentatives de prompt injection.

    Args:
        text: Corps nettoyé (après clean_email_body) — texte envoyé au LLM
        raw_html: Corps HTML brut (optionnel) — pour détecter le contenu caché

    Returns:
        Dict avec :
            detected (bool)   : True si injection suspectée
            patterns (list)   : Patterns déclenchés
            confidence (str)  : "high" | "medium" | "none"
    """
    triggered = []

    for pattern in _COMPILED:
        if pattern.search(text):
            triggered.append(pattern.pattern)

    hidden_triggered = []
    if raw_html:
        for pattern in _COMPILED_HIDDEN:
            if pattern.search(raw_html):
                hidden_triggered.append(pattern.pattern)

    # Stéganographie Unicode — vérifiée sur le texte nettoyé ET le HTML brut
    steg_triggered = []
    for pattern in _COMPILED_STEG:
        if pattern.search(text):
            steg_triggered.append(pattern.pattern)
    if raw_html:
        for pattern in _COMPILED_STEG:
            if pattern.search(raw_html) and pattern.pattern not in steg_triggered:
                steg_triggered.append(pattern.pattern)

    detected = bool(triggered or hidden_triggered or steg_triggered)
    all_triggered = triggered + hidden_triggered + steg_triggered

    if triggered:
        confidence = "high"
    elif hidden_triggered or steg_triggered:
        confidence = "medium"
    else:
        confidence = "none"

    return {
        "detected": detected,
        "patterns": all_triggered,
        "confidence": confidence,
    }
