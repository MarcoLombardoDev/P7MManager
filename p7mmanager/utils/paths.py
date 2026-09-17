# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Where configuration, logs and bundled resources live, per platform.

Kept free of Qt so the engine and the tests can use it. Platform branching is
confined to this module, and ``P7MMANAGER_HOME`` overrides all of it — which
is what the tests set, and what a portable install on a USB stick wants.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .. import APP_NAME

__all__ = ["resources_dir", "config_dir", "log_dir", "settings_file", "ensure_dir"]


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _base(kind: str) -> Path:
    """``kind`` is one of ``config``, ``data``, ``cache``."""
    override = os.environ.get("P7MMANAGER_HOME")
    if override:
        return Path(override) / kind

    if sys.platform == "win32":
        roaming = os.environ.get("APPDATA") or str(_home() / "AppData" / "Roaming")
        local = os.environ.get("LOCALAPPDATA") or str(_home() / "AppData" / "Local")
        return Path(local if kind == "cache" else roaming) / APP_NAME
    if sys.platform == "darwin":
        if kind == "cache":
            return _home() / "Library" / "Caches" / APP_NAME
        return _home() / "Library" / "Application Support" / APP_NAME
    xdg = {
        "config": os.environ.get("XDG_CONFIG_HOME") or str(_home() / ".config"),
        "data": os.environ.get("XDG_DATA_HOME") or str(_home() / ".local" / "share"),
        "cache": os.environ.get("XDG_CACHE_HOME") or str(_home() / ".cache"),
    }[kind]
    return Path(xdg) / APP_NAME.lower().replace(" ", "-")


def resources_dir() -> Path:
    """The bundled ``resources`` folder, both frozen and from a checkout."""
    frozen = getattr(sys, "_MEIPASS", None)
    if frozen:
        return Path(frozen) / "resources"
    return Path(__file__).resolve().parent.parent.parent / "resources"


def config_dir() -> Path:
    return _base("config")


def log_dir() -> Path:
    if sys.platform == "win32":
        return _base("cache") / "logs"
    return _base("cache") / "logs"


def settings_file() -> Path:
    return config_dir() / "settings.json"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
