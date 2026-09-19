# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

"""Recognising the payload, and naming the file it becomes."""

from __future__ import annotations

from pathlib import Path

import pytest

from p7mmanager.core import payload

from .conftest import PDF_BYTES, XML_BYTES, requires_openssl


@pytest.mark.parametrize(
    "data, expected",
    [
        (PDF_BYTES, "pdf"),
        (XML_BYTES, "xml"),
        (b"\xef\xbb\xbf<?xml version='1.0'?><a/>", "xml"),
        (b"PK\x03\x04" + b"\x00" * 20 + b"word/document.xml", "docx"),
        (b"PK\x03\x04" + b"\x00" * 20 + b"xl/workbook.xml", "xlsx"),
        (b"PK\x03\x04" + b"\x00" * 40, "zip"),
        (b"{\\rtf1\\ansi", "rtf"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, "png"),
        (b"\xff\xd8\xff\xe0", "jpeg"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
        (b"", "empty"),
        (b"una nota di testo, niente di piu'", "text"),
        (b"\x00\x01\x02\x03\xff\xfe", "bin"),
    ],
)
def test_identify(data, expected):
    assert payload.identify(data).key == expected


@requires_openssl
def test_a_nested_container_is_recognised_as_such(signed_pdf):
    assert payload.identify(signed_pdf.read_bytes()).key == "p7m"


@pytest.mark.parametrize(
    "name, kind, expected",
    [
        ("fattura.xml.p7m", payload.XML, "fattura.xml"),
        ("contratto.pdf.p7m", payload.PDF, "contratto.pdf"),
        ("CONTRATTO.PDF.P7M", payload.PDF, "CONTRATTO.PDF"),
        ("allegato.p7m", payload.PDF, "allegato.pdf"),
        ("doppio.p7m.p7m", payload.PDF, "doppio.pdf"),
        ("firma.p7s", payload.PDF, "firma.pdf"),
        ("foto.jpeg.p7m", payload.JPEG, "foto.jpeg"),
        ("relazione.doc.p7m", payload.DOCX, "relazione.doc"),
        ("senza-nome.p7m", payload.BINARY, "senza-nome.bin"),
    ],
)
def test_output_name(name, kind, expected):
    assert payload.output_name(Path(name), kind) == expected
