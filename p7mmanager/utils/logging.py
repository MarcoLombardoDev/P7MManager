# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""One rotating log file, so a bug report can arrive with evidence."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import ensure_dir, log_dir

__all__ = ["setup_logging", "log_file"]

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def log_file():
    return log_dir() / "p7mmanager.log"


def setup_logging(level: str | int = logging.INFO) -> None:
    """Log to stderr and to a capped file; never fail to start over logging."""
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    try:
        ensure_dir(log_dir())
        rotating = RotatingFileHandler(
            log_file(), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        rotating.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(rotating)
    except OSError:  # pragma: no cover - read-only or unwritable home
        root.debug("No writable log directory; logging to the console only")
