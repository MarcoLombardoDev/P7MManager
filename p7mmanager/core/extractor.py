# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Writing the extracted document out, without ever touching the original.

The container is only ever read. The payload is written to a temporary file in
the destination folder and renamed into place, so an interrupted run leaves
either the complete file or nothing — never a half-written PDF that looks
extracted.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .analyzer import Analysis, Outcome, analyse

__all__ = [
    "Conflict",
    "Destination",
    "ExtractionSettings",
    "ExtractionResult",
    "extract",
]


class Conflict(str, Enum):
    """What to do when the output file already exists."""

    RENAME = "rename"
    OVERWRITE = "overwrite"
    SKIP = "skip"


class Destination(str, Enum):
    """Where extracted documents go."""

    BESIDE_SOURCE = "beside"
    SINGLE_FOLDER = "folder"
    MIRROR_TREE = "mirror"


@dataclass
class ExtractionSettings:
    """Everything the extraction step needs to decide, in one object."""

    destination: Destination = Destination.BESIDE_SOURCE
    output_dir: Path | None = None
    root_dir: Path | None = None
    conflict: Conflict = Conflict.RENAME
    verify: bool = True
    analyse_only: bool = False

    def target_dir(self, source: Path) -> Path:
        source = source.resolve()
        if self.destination is Destination.BESIDE_SOURCE or self.output_dir is None:
            return source.parent
        base = Path(self.output_dir)
        if self.destination is Destination.MIRROR_TREE and self.root_dir is not None:
            try:
                relative = source.parent.relative_to(Path(self.root_dir).resolve())
            except ValueError:
                relative = Path()
            return base / relative
        return base


@dataclass
class ExtractionResult:
    """The outcome of one file: its analysis plus what was written."""

    analysis: Analysis
    output_path: Path | None = None
    written: bool = False
    skipped: bool = False
    analysis_only: bool = False
    message: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def source(self) -> Path:
        return self.analysis.path

    @property
    def outcome(self) -> Outcome:
        """Red for a failure, amber for anything the user should look at."""
        if self.analysis.outcome is Outcome.ERROR:
            return Outcome.ERROR
        if self.analysis_only:
            return self.analysis.outcome
        if self.skipped or not self.written:
            return Outcome.WARNING
        return self.analysis.outcome


def _unique_path(target: Path) -> Path:
    """``fattura.pdf`` -> ``fattura (2).pdf`` for the first free number."""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for counter in range(2, 10000):
        candidate = target.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return candidate
    raise OSError("too many files with the same name in the destination folder")


def _write_atomically(target: Path, data: bytes) -> None:
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex[:8]}.part")
    try:
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def extract(
    source: str | Path,
    settings: ExtractionSettings | None = None,
    analysis: Analysis | None = None,
) -> ExtractionResult:
    """Analyse ``source`` and write its payload out.

    Pass ``analysis`` to reuse a result already computed for this file.
    """
    settings = settings or ExtractionSettings()
    path = Path(source)
    analysis = analysis or analyse(path, verify=settings.verify)
    result = ExtractionResult(analysis=analysis, warnings=list(analysis.warnings))

    if analysis.error:
        result.message = analysis.error
        return result

    if settings.analyse_only:
        result.analysis_only = True
        result.message = analysis.summary
        return result

    if not analysis.has_payload or analysis.payload_name is None:
        result.message = (
            "detached signature: nothing to extract"
            if analysis.detached
            else "no extractable content"
        )
        return result

    try:
        directory = settings.target_dir(path)
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        result.message = f"destination folder unusable: {exc.strerror}"
        return result

    target = directory / analysis.payload_name
    if target.resolve() == path.resolve():
        target = directory / f"{target.stem} (extracted){target.suffix}"

    if target.exists():
        if settings.conflict is Conflict.SKIP:
            result.skipped = True
            result.output_path = target
            result.message = "already there: skipped"
            return result
        if settings.conflict is Conflict.RENAME:
            try:
                target = _unique_path(target)
            except OSError as exc:
                result.message = str(exc)
                return result

    try:
        _write_atomically(target, analysis.payload)
    except OSError as exc:
        result.message = f"write failed: {exc.strerror or exc}"
        return result

    result.output_path = target
    result.written = True
    result.message = analysis.summary
    return result
