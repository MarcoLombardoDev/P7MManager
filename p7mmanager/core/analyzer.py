# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Reading a .p7m from disk and saying everything that can be said about it.

This is the layer the interface and the command line both call: give it a
path, get back an :class:`Analysis` that is safe to display — every failure
mode is a field on the result rather than an exception, because a queue of
five hundred files must not stop at the first damaged one.

Two container encodings are handled. Most .p7m files are raw DER; those from
some PEC providers arrive base64-encoded, with or without PEM banner lines,
and are decoded transparently. When the CMS structure cannot be read at all,
the file is still searched for an embedded PDF, which is what the shell
scripts this tool replaces did for every file.
"""

from __future__ import annotations

import base64
import binascii
import datetime as _dt
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import payload as payload_module
from .cms import CmsError, SignedData, parse_signed_data
from .payload import PayloadKind
from .verify import verify_signed_data

__all__ = [
    "Analysis",
    "ContainerEncoding",
    "Outcome",
    "analyse",
    "analyse_bytes",
    "decode_container",
    "MAX_FILE_BYTES",
]

# Refuse to load anything absurd into memory; a signed document is rarely
# larger and the message is clearer than a MemoryError.
MAX_FILE_BYTES = 512 * 1024 * 1024

MAX_NESTING = 8

_PEM_BLOCK = re.compile(
    rb"-----BEGIN [A-Z0-9 #]+-----(?P<body>.*?)-----END [A-Z0-9 #]+-----", re.S
)
_BASE64_ONLY = re.compile(rb"^[A-Za-z0-9+/=\s]+$")


class ContainerEncoding(str, Enum):
    DER = "DER"
    PEM = "PEM"
    BASE64 = "Base64"
    RAW = "none"

    @property
    def label(self) -> str:
        return self.value


class Outcome(str, Enum):
    """How an analysis, or an extraction, ended."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

    @property
    def is_failure(self) -> bool:
        return self is Outcome.ERROR


@dataclass
class Analysis:
    """Everything known about one container."""

    path: Path
    size: int = 0
    encoding: ContainerEncoding = ContainerEncoding.DER
    layers: list[SignedData] = field(default_factory=list)
    payload: bytes | None = None
    payload_kind: PayloadKind | None = None
    payload_name: str | None = None
    recovered_by_scan: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    # -- derived views ------------------------------------------------
    @property
    def signed_data(self) -> SignedData | None:
        """The outermost SignedData, which is the one users mean."""
        return self.layers[0] if self.layers else None

    @property
    def innermost(self) -> SignedData | None:
        return self.layers[-1] if self.layers else None

    @property
    def nesting(self) -> int:
        return len(self.layers)

    @property
    def signers(self) -> list:
        return [signer for layer in self.layers for signer in layer.signers]

    @property
    def signature_count(self) -> int:
        return len(self.signers)

    @property
    def detached(self) -> bool:
        return bool(self.layers) and self.layers[-1].detached

    @property
    def payload_size(self) -> int:
        return len(self.payload) if self.payload else 0

    @property
    def has_payload(self) -> bool:
        return bool(self.payload)

    @property
    def signing_time(self) -> _dt.datetime | None:
        times = [s.signing_time for s in self.signers if s.signing_time]
        return min(times) if times else None

    @property
    def integrity(self) -> bool | None:
        """True when every signer that could be checked matched."""
        results = [s.digest_matches for s in self.signers if s.digest_matches is not None]
        if not results:
            return None
        return all(results)

    @property
    def signatures_valid(self) -> bool | None:
        results = [s.signature_valid for s in self.signers if s.signature_valid is not None]
        if not results:
            return None
        return all(results)

    @property
    def outcome(self) -> Outcome:
        if self.error:
            return Outcome.ERROR
        if self.integrity is False or self.signatures_valid is False:
            return Outcome.ERROR
        if self.warnings or self.recovered_by_scan or not self.has_payload:
            return Outcome.WARNING
        return Outcome.OK

    @property
    def summary(self) -> str:
        """One line for the queue's status column."""
        if self.error:
            return self.error
        if self.detached and not self.has_payload:
            return "detached signature: no document enclosed"
        parts = []
        if self.payload_kind is not None:
            parts.append(self.payload_kind.label)
        if self.signature_count:
            parts.append(
                "1 signature" if self.signature_count == 1 else f"{self.signature_count} signatures"
            )
        if self.recovered_by_scan:
            parts.append("recovered by scanning")
        return " · ".join(parts) or "no content"


def decode_container(data: bytes) -> tuple[bytes, ContainerEncoding]:
    """Return the DER bytes of a container and how they were encoded."""
    if data[:1] == b"\x30":
        return data, ContainerEncoding.DER

    match = _PEM_BLOCK.search(data)
    if match:
        try:
            return base64.b64decode(match.group("body"), validate=False), ContainerEncoding.PEM
        except (binascii.Error, ValueError):
            pass

    sample = data[:4096]
    if sample.strip() and _BASE64_ONLY.match(sample):
        try:
            decoded = base64.b64decode(b"".join(data.split()), validate=False)
        except (binascii.Error, ValueError):
            decoded = b""
        if decoded[:1] == b"\x30":
            return decoded, ContainerEncoding.BASE64

    return data, ContainerEncoding.RAW


def _scan_for_pdf(data: bytes) -> bytes | None:
    """The fallback the original scripts used: cut from %PDF to the last %%EOF."""
    start = data.find(b"%PDF")
    if start < 0:
        return None
    end = data.rfind(b"%%EOF")
    if end > start:
        return data[start : end + 5]
    return data[start:]


def analyse_bytes(data: bytes, name: str = "document.p7m", verify: bool = True) -> Analysis:
    """Analyse an in-memory container. ``name`` only shapes the output name."""
    started = time.perf_counter()
    analysis = Analysis(path=Path(name), size=len(data))

    if not data:
        analysis.error = "empty file"
        analysis.elapsed_ms = (time.perf_counter() - started) * 1000
        return analysis

    der, encoding = decode_container(data)
    analysis.encoding = encoding

    current = der
    for depth in range(MAX_NESTING):
        try:
            signed = parse_signed_data(current)
        except CmsError as exc:
            if depth == 0:
                recovered = _scan_for_pdf(data)
                if recovered:
                    analysis.recovered_by_scan = True
                    analysis.payload = recovered
                    analysis.warnings.append(
                        f"signature structure unreadable ({exc}); "
                        "PDF recovered by scanning the file's bytes"
                    )
                else:
                    analysis.error = str(exc)
            break

        if verify:
            verify_signed_data(signed)
        analysis.layers.append(signed)

        if signed.content is None:
            analysis.warnings.append(
                "detached signature: the signed document is not enclosed"
            )
            break

        kind = payload_module.identify(signed.content)
        if kind is payload_module.P7M and depth + 1 < MAX_NESTING:
            current = signed.content
            continue
        analysis.payload = signed.content
        break
    else:  # pragma: no cover - only reachable past MAX_NESTING
        analysis.warnings.append("nested envelopes beyond the supported depth")

    if analysis.payload is not None:
        analysis.payload_kind = payload_module.identify(analysis.payload)
        analysis.payload_name = payload_module.output_name(
            Path(name), analysis.payload_kind
        )
        if analysis.payload_kind is payload_module.BINARY:
            analysis.warnings.append("content type not recognised")

    for layer in analysis.layers:
        for signer in layer.signers:
            if signer.certificate is not None and signer.signing_time is not None:
                if signer.certificate.is_valid_at(signer.signing_time) is False:
                    analysis.warnings.append(
                        f"the certificate of {signer.display_name} was not valid "
                        "at the time of signing"
                    )
            elif signer.certificate is None:
                analysis.warnings.append(
                    "the signer's certificate is not enclosed"
                )

    analysis.elapsed_ms = (time.perf_counter() - started) * 1000
    return analysis


def analyse(path: str | Path, verify: bool = True) -> Analysis:
    """Analyse a file on disk. Every failure is reported on the result."""
    file_path = Path(path)
    started = time.perf_counter()
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        analysis = Analysis(path=file_path, error=f"file not accessible: {exc.strerror}")
        analysis.elapsed_ms = (time.perf_counter() - started) * 1000
        return analysis

    if size > MAX_FILE_BYTES:
        analysis = Analysis(path=file_path, size=size)
        analysis.error = f"file too large ({size / 1024 / 1024:.0f} MB)"
        return analysis

    try:
        data = file_path.read_bytes()
    except OSError as exc:
        analysis = Analysis(path=file_path, size=size)
        analysis.error = f"read failed: {exc.strerror}"
        return analysis

    analysis = analyse_bytes(data, name=file_path.name, verify=verify)
    analysis.path = file_path
    return analysis
