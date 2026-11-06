"""Nexus monitoring entry point.

The appointment portal adapter is intentionally not implemented yet.
Running this module validates configuration and reports readiness; it does
not query the Spanish appointment portal or claim that appointments were found.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import settings, validate_settings

logger = logging.getLogger(__name__)


def run_check() -> None:
    """Run one scaffold check."""
    validate_settings()
    logger.info(
        "Nexus scaffold ready at %s | province=%s | procedure=%s | office=not preselected",
        datetime.now(timezone.utc).isoformat(),
        settings.province,
        settings.appointment_procedure,
    )
    logger.warning(
        "No appointment search was performed: portal adapter is pending."
    )


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_check()


if __name__ == "__main__":
    main()
