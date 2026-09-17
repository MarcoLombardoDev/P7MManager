# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Recognising what came out of the envelope, and naming the file for it.

A .p7m says nothing about what it wraps, so the payload is identified by its
leading bytes. This matters for more than a label: ``fattura.xml.p7m`` should
land as ``fattura.xml`` and a container whose name lost the inner extension
should still get the right one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["PayloadKind", "identify", "output_name", "P7M_SUFFIXES"]

P7M_SUFFIXES = (".p7m", ".p7s", ".p7", ".cms")


@dataclass(frozen=True)
class PayloadKind:
    """A recognised content type: what to call it and how to name the file."""

    key: str
    label: str
    extension: str

    @property
    def is_pdf(self) -> bool:
        return self.key == "pdf"


PDF = PayloadKind("pdf", "PDF document", ".pdf")
XML = PayloadKind("xml", "XML document", ".xml")
ZIP = PayloadKind("zip", "ZIP archive", ".zip")
DOCX = PayloadKind("docx", "Word document (OOXML)", ".docx")
XLSX = PayloadKind("xlsx", "Excel workbook (OOXML)", ".xlsx")
PPTX = PayloadKind("pptx", "PowerPoint presentation (OOXML)", ".pptx")
OLE = PayloadKind("ole", "Office 97-2003 document", ".doc")
RTF = PayloadKind("rtf", "RTF document", ".rtf")
PNG = PayloadKind("png", "PNG image", ".png")
JPEG = PayloadKind("jpeg", "JPEG image", ".jpg")
TIFF = PayloadKind("tiff", "TIFF image", ".tif")
GIF = PayloadKind("gif", "GIF image", ".gif")
SEVENZIP = PayloadKind("7z", "7-Zip archive", ".7z")
RAR = PayloadKind("rar", "RAR archive", ".rar")
GZIP = PayloadKind("gzip", "GZIP archive", ".gz")
P7M = PayloadKind("p7m", "Nested signed envelope", ".p7m")
TEXT = PayloadKind("text", "Text", ".txt")
BINARY = PayloadKind("bin", "Binary data", ".bin")
EMPTY = PayloadKind("empty", "Empty", ".bin")

_MAGIC: tuple[tuple[bytes, PayloadKind], ...] = (
    (b"%PDF", PDF),
    (b"PK\x03\x04", ZIP),
    (b"PK\x05\x06", ZIP),
    (b"{\\rtf", RTF),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", OLE),
    (b"\x89PNG\r\n\x1a\n", PNG),
    (b"\xff\xd8\xff", JPEG),
    (b"II*\x00", TIFF),
    (b"MM\x00*", TIFF),
    (b"GIF8", GIF),
    (b"7z\xbc\xaf\x27\x1c", SEVENZIP),
    (b"Rar!\x1a\x07", RAR),
    (b"\x1f\x8b", GZIP),
)

_OOXML_MARKERS: tuple[tuple[bytes, PayloadKind], ...] = (
    (b"word/", DOCX),
    (b"xl/", XLSX),
    (b"ppt/", PPTX),
)


def _looks_like_xml(data: bytes) -> bool:
    head = data[:512].lstrip(b"\xef\xbb\xbf \t\r\n")
    return head.startswith(b"<?xml") or head.startswith(b"<")


def _looks_like_text(data: bytes) -> bool:
    sample = data[:2048]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
        except UnicodeDecodeError:
            return False
    printable = sum(1 for byte in sample if byte >= 0x20 or byte in (9, 10, 13))
    return bool(sample) and printable / len(sample) > 0.95


def identify(data: bytes) -> PayloadKind:
    """Name the content from its leading bytes."""
    if not data:
        return EMPTY

    for magic, kind in _MAGIC:
        if data.startswith(magic):
            if kind is ZIP:
                head = data[:4096]
                for marker, ooxml in _OOXML_MARKERS:
                    if marker in head:
                        return ooxml
            return kind

    # A nested envelope: check before the generic binary fallback.
    from .cms import looks_like_cms  # imported here to keep the import graph flat

    if looks_like_cms(data):
        return P7M

    if _looks_like_xml(data):
        return XML
    if _looks_like_text(data):
        return TEXT
    return BINARY


def strip_signature_suffix(name: str) -> str:
    """``fattura.xml.p7m`` -> ``fattura.xml``; repeated suffixes all come off."""
    stem = name
    while True:
        lowered = stem.lower()
        for suffix in P7M_SUFFIXES:
            if lowered.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        else:
            return stem


def output_name(source: Path, kind: PayloadKind) -> str:
    """The file name the extracted payload should get.

    The container's own name decides whenever it already carries the inner
    extension, because that is the name the sender chose. Only when it does
    not — ``allegato.p7m`` holding a PDF — is the detected extension added.
    """
    stem = strip_signature_suffix(source.name)
    if not stem:
        stem = source.stem or "document"
    if kind.key in ("empty", "bin") and Path(stem).suffix:
        return stem
    if Path(stem).suffix.lower() == kind.extension:
        return stem
    if kind is DOCX and Path(stem).suffix.lower() in (".doc", ".docx"):
        return stem
    if kind is XLSX and Path(stem).suffix.lower() in (".xls", ".xlsx"):
        return stem
    if kind is JPEG and Path(stem).suffix.lower() in (".jpg", ".jpeg"):
        return stem
    if kind is TIFF and Path(stem).suffix.lower() in (".tif", ".tiff"):
        return stem
    return stem + kind.extension
