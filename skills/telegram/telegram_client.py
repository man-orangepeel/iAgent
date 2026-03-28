# -*- coding: utf-8 -*-
"""
telegram_client.py — Client Telegram pour iAgent.

Gère l'envoi de messages, photos et sondages via l'API Telegram Bot.

Usage :
    from skills.telegram.telegram_client import get_alerts_client
    client = get_alerts_client()
    client.send_message("Texte")
"""
import time
from typing import Optional, List, Dict
from urllib.parse import urlparse

import requests


class TelegramClient:
    """Client minimal pour l'API Telegram Bot avec retry."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.session = requests.Session()

    def _request(self, method: str, payload: Dict, max_retries: int = 3) -> Dict:
        """Requête API avec retry et backoff exponentiel."""
        url = f"{self.base_url}/{method}"
        for attempt in range(max_retries):
            try:
                response = self.session.post(url, json=payload, timeout=30)
                if not response.ok:
                    print(f"⚠️ Telegram {response.status_code} — {response.text[:300]}")
                response.raise_for_status()
                result = response.json()
                if result.get("ok"):
                    return result
                print(f"⚠️ Telegram API : {result.get('description')}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return result
            except Exception as e:
                print(f"⚠️ Telegram erreur (tentative {attempt + 1}) : {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"ok": False, "description": "Max retries exceeded"}

    def send_message(self, text: str, chat_id: Optional[str] = None,
                     parse_mode: str = "HTML") -> Dict:
        """Envoie un message texte. Fallback sans formatage si erreur parse."""
        if len(text) > 4096:
            text = text[:4093] + "..."
        target = chat_id or self.chat_id
        payload: Dict = {"chat_id": target, "text": text, "disable_web_page_preview": False}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            return self._request("sendMessage", payload)
        except Exception:
            if parse_mode:
                payload.pop("parse_mode", None)
                return self._request("sendMessage", payload)
            raise

    def send_photo(self, photo_url: str, caption: Optional[str] = None) -> Dict:
        """Envoie une photo par URL (http/https uniquement)."""
        scheme = urlparse(photo_url).scheme
        if scheme not in ("http", "https"):
            raise ValueError(f"Schéma non autorisé : {scheme!r}")
        payload: Dict = {"chat_id": self.chat_id, "photo": photo_url}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"
        return self._request("sendPhoto", payload)

    def send_poll(self, question: str, options: List[str],
                  is_anonymous: bool = True) -> Dict:
        """Envoie un sondage (2-10 options)."""
        if len(options) < 2 or len(options) > 10:
            raise ValueError("Sondage : 2-10 options requises")
        if len(question) > 255:
            question = question[:252] + "..."
        clean = [{"text": str(o).strip()[:100]} for o in options[:10] if str(o).strip()]
        if len(clean) < 2:
            raise ValueError(f"Sondage : < 2 options valides ({len(clean)})")
        payload = {
            "chat_id": self.chat_id,
            "question": question,
            "options": clean,
            "is_anonymous": is_anonymous,
            "allows_multiple_answers": False,
        }
        return self._request("sendPoll", payload)

    def stop_poll(self, message_id: int) -> Dict:
        """Clôture un sondage. Retourne {'ok': False, 'already_closed': True} si déjà clos."""
        response = self.session.post(
            f"{self.base_url}/stopPoll",
            json={"chat_id": self.chat_id, "message_id": message_id},
            timeout=30,
        )
        result = response.json()
        if not response.ok and response.status_code == 400:
            return {"ok": False, "already_closed": True, "description": result.get("description", "")}
        response.raise_for_status()
        return result

    def get_me(self) -> Dict:
        """Vérifie que le bot est opérationnel."""
        return self._request("getMe", {})

    def health_check(self) -> bool:
        """Vérifie la connectivité."""
        try:
            return self.get_me().get("ok", False)
        except Exception:
            return False



def get_alerts_client() -> TelegramClient:
    """Client bot iAgent (alertes opérateur DM)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from core.env_loader import load_env, require_env
    load_env()
    return TelegramClient(
        bot_token=require_env("IAGENT_BOT_TOKEN"),
        chat_id=require_env("IAGENT_CHAT_ID"),
    )
