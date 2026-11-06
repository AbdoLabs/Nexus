"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    timezone: str = os.getenv("TIMEZONE", "Europe/Madrid")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    province: str = os.getenv("PROVINCE", "Madrid")
    appointment_procedure: str = os.getenv(
        "APPOINTMENT_PROCEDURE", "TOMA DE HUELLAS"
    )
    office_selection: str = os.getenv("OFFICE_SELECTION", "Cualquier oficina")
    check_interval_minutes: int = int(
        os.getenv("CHECK_INTERVAL_MINUTES", "5")
    )


settings = Settings()


def validate_settings() -> None:
    """Validate configuration values that affect monitoring safety."""
    if settings.check_interval_minutes < 5:
        raise ValueError("CHECK_INTERVAL_MINUTES must be at least 5.")
    if not settings.province.strip():
        raise ValueError("PROVINCE cannot be empty.")
    if not settings.appointment_procedure.strip():
        raise ValueError("APPOINTMENT_PROCEDURE cannot be empty.")
