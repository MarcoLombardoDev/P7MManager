# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Preferences in one JSON file, written where the platform expects it.

A settings file that cannot be read is replaced by the defaults rather than
stopping the application: nothing in here is worth a failure to start.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .paths import ensure_dir, settings_file

log = logging.getLogger(__name__)

__all__ = ["Settings"]


class Settings:
    def __init__(self, path=None) -> None:
        self._path = path or settings_file()
        self._values: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        try:
            self._values = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._values = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        self._values.update(values)
        self.save()

    def save(self) -> None:
        try:
            ensure_dir(self._path.parent)
            self._path.write_text(
                json.dumps(self._values, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:  # pragma: no cover - unwritable config dir
            log.debug("Settings not saved: %s", exc)
