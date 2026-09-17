# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Turning a finished queue into something that can be filed or audited.

A run over a few hundred containers is usually evidence of something, so the
report carries what an auditor would ask for — who signed, when, whether the
content still matches the digest — and not only whether a file was written.

CSV is written with a UTF-8 BOM because these reports get opened in Excel on
Windows, which otherwise mangles every accented name in the signer column.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from .. import APP_NAME, __version__
from .jobs import Job

__all__ = ["COLUMNS", "row_for", "write_csv", "write_json", "as_dicts"]

COLUMNS: Sequence[str] = (
    "file",
    "folder",
    "size",
    "state",
    "message",
    "encoding",
    "content_type",
    "payload_bytes",
    "signatures",
    "signers",
    "signed_on",
    "digest_algorithm",
    "integrity",
    "signature_check",
    "certificate_subject",
    "certificate_issuer",
    "certificate_serial",
    "certificate_valid_from",
    "certificate_valid_until",
    "timestamps",
    "output",
    "warnings",
)


def _isoformat(value: _dt.datetime | None) -> str:
    return value.isoformat(sep=" ", timespec="seconds") if value else ""


def _tristate(value: bool | None) -> str:
    if value is None:
        return "not checked"
    return "ok" if value else "FAILED"


def row_for(job: Job) -> dict[str, object]:
    """One flat record per queued file."""
    row: dict[str, object] = dict.fromkeys(COLUMNS, "")
    row["file"] = job.path.name
    row["folder"] = str(job.path.parent)
    row["size"] = job.size
    row["state"] = job.state.value
    row["message"] = job.message
    row["signatures"] = 0

    result = job.result
    if result is None:
        return row

    analysis = result.analysis
    row["encoding"] = analysis.encoding.value
    row["payload_bytes"] = analysis.payload_size
    row["signatures"] = analysis.signature_count
    row["integrity"] = _tristate(analysis.integrity)
    row["signature_check"] = _tristate(analysis.signatures_valid)
    row["warnings"] = " | ".join(analysis.warnings)
    row["output"] = str(result.output_path) if result.output_path else ""
    if analysis.payload_kind is not None:
        row["content_type"] = analysis.payload_kind.label

    signers = analysis.signers
    row["signers"] = " | ".join(signer.display_name for signer in signers)
    row["signed_on"] = " | ".join(
        _isoformat(signer.signing_time) for signer in signers if signer.signing_time
    )
    row["digest_algorithm"] = " | ".join(
        sorted({signer.digest_algorithm for signer in signers if signer.digest_algorithm})
    )
    row["timestamps"] = " | ".join(
        _isoformat(stamp.generated)
        for signer in signers
        for stamp in signer.timestamps
        if stamp.generated
    )

    certificates = [signer.certificate for signer in signers if signer.certificate]
    if certificates:
        first = certificates[0]
        row["certificate_subject"] = str(first.subject)
        row["certificate_issuer"] = str(first.issuer)
        row["certificate_serial"] = first.serial_hex
        row["certificate_valid_from"] = _isoformat(first.not_before)
        row["certificate_valid_until"] = _isoformat(first.not_after)
    return row


def as_dicts(jobs: Iterable[Job]) -> list[dict[str, object]]:
    return [row_for(job) for job in jobs]


def write_csv(jobs: Iterable[Job], path: str | Path, delimiter: str = ";") -> Path:
    """Write a semicolon-separated report, which is what Excel expects here."""
    target = Path(path)
    rows = as_dicts(jobs)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(COLUMNS), delimiter=delimiter,
                            quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    target.write_text(buffer.getvalue(), encoding="utf-8-sig")
    return target


def write_json(jobs: Iterable[Job], path: str | Path) -> Path:
    """Write the same records as JSON, with a header naming the run."""
    target = Path(path)
    document = {
        "tool": APP_NAME,
        "version": __version__,
        "generated": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": (
            "Integrity and RSA signature checks only. No trust list, no revocation "
            "check, no timestamp validation: this is not a legal validation."
        ),
        "files": as_dicts(jobs),
    }
    target.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return target
