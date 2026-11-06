"""Telegram notification helper."""

from __future__ import annotations

import logging

import requests

from .config import settings

logger = logging.getLogger(__name__)


def send_telegram_message(message: str) -> bool:
    """Send a Telegram message when credentials are configured.

    Returns False if Telegram has not been configured or the API request fails.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram is not configured; notification skipped.")
        return False

    url = (
        "https://api.telegram.org/bot"
        f"{settings.telegram_bot_token}/sendMessage"
    )
    try:
        response = requests.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": message},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("ok"))
    except (requests.RequestException, ValueError):
        logger.exception("Telegram notification failed.")
        return False
