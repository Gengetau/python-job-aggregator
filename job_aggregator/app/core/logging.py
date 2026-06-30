"""Structured logging helpers."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure a compact console logger for local development."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
