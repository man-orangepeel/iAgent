# -*- coding: utf-8 -*-
"""
ntfy_client.py — Client ntfy pour notifications push iAgent.

AVERTISSEMENT SÉCURITÉ :
  ntfy.sh est public. Un topic sans auth est lisible par tous.
  Désactivé par défaut (enabled=False).

Usage :
    from skills.ntfy.ntfy_client import NtfyClient
    client = NtfyClient(enabled=True)
    client.notify("Message", title="Titre")
"""
import os
from typing import Optional

import requests


def _safe_header(text: str) -> str:
    """Supprime les caractères non encodables en latin-1 (contrainte headers HTTP)."""
    return text.encode("latin-1", errors="ignore").decode("latin-1").strip()


class NtfyClient:
    """Client ntfy désactivé par défaut."""

    def __init__(self, topic: Optional[str] = None,
                 base_url: str = "https://ntfy.sh",
                 enabled: bool = False):
        self.topic = topic or os.getenv("NTFY_TOPIC")
        self.base_url = base_url
        self.enabled = enabled
        if self.enabled and self.base_url == "https://ntfy.sh":
            print("⚠️ ntfy activé sur ntfy.sh public — vérifier l'authentification du topic")

    def notify(self, message: str, title: Optional[str] = None,
               tags: Optional[list] = None, priority: str = "default") -> bool:
        """Envoie une notification si activé. Retourne True si envoyée."""
        if not self.enabled or not self.topic:
            return False
        headers: dict = {"Priority": priority}
        if title:
            headers["Title"] = _safe_header(title)
        if tags:
            headers["Tags"] = ",".join(tags)
        try:
            resp = requests.post(
                f"{self.base_url}/{self.topic}",
                data=message.encode("utf-8"),
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ ntfy erreur : {e}")
            return False

    def notify_success(self, subject: str) -> bool:
        return self.notify(f"✅ {subject}", title="iAgent", tags=["white_check_mark"])

    def notify_error(self, error: str) -> bool:
        return self.notify(f"❌ {error}", title="iAgent — Erreur", tags=["warning"], priority="high")
