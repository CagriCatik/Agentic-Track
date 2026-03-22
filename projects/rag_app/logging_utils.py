"""Shared logging configuration for the RAG application."""

from __future__ import annotations

import logging
import os

_CONFIGURED = False


def configure_logging(level_name: str | None = None) -> int:
    global _CONFIGURED

    resolved_name = (level_name or os.getenv("RAG_LOG_LEVEL", "INFO")).strip().upper()
    level = getattr(logging, resolved_name, logging.INFO)

    if not _CONFIGURED:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
        _CONFIGURED = True
    else:
        logging.getLogger().setLevel(level)

    for noisy_logger in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    return level
