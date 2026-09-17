# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Turning what the user dropped in — files, folders, a whole tree — into a list.

Folders are the normal case: a PEC export is a directory of hundreds of
containers. Scanning is kept separate from the queue so it can run before
anything is enqueued and report how many files it found.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .payload import P7M_SUFFIXES

__all__ = ["scan", "iter_containers", "is_container"]


def is_container(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in P7M_SUFFIXES


def iter_containers(root: Path, recursive: bool = True) -> Iterator[Path]:
    """Yield every container under ``root``, skipping what cannot be read."""
    if root.is_file():
        if is_container(root):
            yield root
        return
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_dir():
                if recursive and not entry.is_symlink():
                    yield from iter_containers(entry, recursive)
            elif is_container(entry):
                yield entry
        except OSError:  # pragma: no cover - permissions, vanished files
            continue


def scan(
    paths: Iterable[str | Path],
    recursive: bool = True,
    include_all_files: bool = False,
) -> list[Path]:
    """Collect containers from a mix of files and folders, de-duplicated.

    ``include_all_files`` adds files whose extension is not a signature one:
    the user pointed at them explicitly, so they are taken at their word.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    def remember(candidate: Path) -> None:
        try:
            key = candidate.resolve()
        except OSError:  # pragma: no cover - unreachable network paths
            key = candidate
        if key not in seen:
            seen.add(key)
            found.append(candidate)

    for item in paths:
        path = Path(item).expanduser()
        if path.is_dir():
            for container in iter_containers(path, recursive):
                remember(container)
        elif path.is_file() and (include_all_files or is_container(path)):
            remember(path)
    return found
