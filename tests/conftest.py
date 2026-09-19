# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

"""Fixtures built from real signatures.

The containers the tests run against are produced by OpenSSL at collection
time rather than committed as binary blobs: a blob cannot be re-read, and a
parser test whose input nobody can regenerate is a test nobody can change.
Where OpenSSL is missing the CMS tests skip rather than fail — the pure ASN.1
and payload tests still run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

OPENSSL = shutil.which("openssl")
requires_openssl = pytest.mark.skipif(OPENSSL is None, reason="openssl is not installed")

SUBJECT = "/C=IT/O=Prova S.p.A./CN=Marco Lombardo/serialNumber=TINIT-AAABBB80A01H501U"
SECOND_SUBJECT = "/C=IT/O=Prova S.p.A./CN=Giulia Rossi"

PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
)
XML_BYTES = b'<?xml version="1.0" encoding="UTF-8"?>\n<FatturaElettronica/>\n'


def _run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True)


def _make_identity(directory: Path, name: str, subject: str) -> tuple[Path, Path]:
    key = directory / f"{name}.key.pem"
    certificate = directory / f"{name}.cert.pem"
    _run(OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key),
         "-out", str(certificate), "-days", "365", "-nodes", "-subj", subject)
    return key, certificate


def _sign(source: Path, target: Path, key: Path, certificate: Path,
          *extra: str) -> Path:
    _run(OPENSSL, "cms", "-sign", "-in", str(source), "-signer", str(certificate),
         "-inkey", str(key), "-outform", "DER", "-binary", "-nodetach",
         "-out", str(target), *extra)
    return target


@pytest.fixture(scope="session")
def signing_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("signing")


@pytest.fixture(scope="session")
def identity(signing_dir: Path):
    if OPENSSL is None:
        pytest.skip("openssl is not installed")
    return _make_identity(signing_dir, "first", SUBJECT)


@pytest.fixture(scope="session")
def second_identity(signing_dir: Path):
    if OPENSSL is None:
        pytest.skip("openssl is not installed")
    return _make_identity(signing_dir, "second", SECOND_SUBJECT)


@pytest.fixture(scope="session")
def plain_pdf(signing_dir: Path) -> Path:
    path = signing_dir / "documento.pdf"
    path.write_bytes(PDF_BYTES)
    return path


@pytest.fixture(scope="session")
def signed_pdf(signing_dir: Path, plain_pdf: Path, identity) -> Path:
    """``documento.pdf.p7m``: one signature, DER, content enclosed."""
    key, certificate = identity
    return _sign(plain_pdf, signing_dir / "documento.pdf.p7m", key, certificate)


@pytest.fixture(scope="session")
def signed_xml(signing_dir: Path, identity) -> Path:
    key, certificate = identity
    source = signing_dir / "fattura.xml"
    source.write_bytes(XML_BYTES)
    return _sign(source, signing_dir / "fattura.xml.p7m", key, certificate)


@pytest.fixture(scope="session")
def signed_base64(signing_dir: Path, plain_pdf: Path, identity) -> Path:
    """The same signature, PEM armoured, as some PEC providers deliver it."""
    key, certificate = identity
    target = signing_dir / "base64.pdf.p7m"
    _run(OPENSSL, "cms", "-sign", "-in", str(plain_pdf), "-signer", str(certificate),
         "-inkey", str(key), "-outform", "PEM", "-binary", "-nodetach",
         "-out", str(target))
    return target


@pytest.fixture(scope="session")
def signed_detached(signing_dir: Path, plain_pdf: Path, identity) -> Path:
    key, certificate = identity
    target = signing_dir / "detached.pdf.p7m"
    _run(OPENSSL, "cms", "-sign", "-in", str(plain_pdf), "-signer", str(certificate),
         "-inkey", str(key), "-outform", "DER", "-binary", "-out", str(target))
    return target


@pytest.fixture(scope="session")
def signed_twice(signing_dir: Path, signed_pdf: Path, second_identity) -> Path:
    """Two signatures over one document, as a countersigned contract has."""
    key, certificate = second_identity
    target = signing_dir / "doppia.pdf.p7m"
    _run(OPENSSL, "cms", "-resign", "-in", str(signed_pdf), "-inform", "DER",
         "-signer", str(certificate), "-inkey", str(key), "-outform", "DER",
         "-binary", "-out", str(target))
    return target


@pytest.fixture(scope="session")
def signed_nested(signing_dir: Path, signed_pdf: Path, second_identity) -> Path:
    """A .p7m whose payload is another .p7m."""
    key, certificate = second_identity
    return _sign(signed_pdf, signing_dir / "annidato.pdf.p7m.p7m", key, certificate)


@pytest.fixture(scope="session")
def signed_sha512(signing_dir: Path, plain_pdf: Path, identity) -> Path:
    key, certificate = identity
    return _sign(plain_pdf, signing_dir / "sha512.pdf.p7m", key, certificate,
                 "-md", "sha512")


@pytest.fixture
def container_tree(tmp_path: Path, signed_pdf: Path, signed_xml: Path,
                   signed_detached: Path) -> Path:
    """A small folder tree, as a PEC export looks."""
    root = tmp_path / "posta"
    (root / "2026" / "gennaio").mkdir(parents=True)
    (root / "2026" / "febbraio").mkdir(parents=True)
    shutil.copy(signed_pdf, root / "contratto.pdf.p7m")
    shutil.copy(signed_xml, root / "2026" / "gennaio" / "fattura.xml.p7m")
    shutil.copy(signed_detached, root / "2026" / "febbraio" / "staccata.pdf.p7m")
    (root / "2026" / "lettera.txt").write_text("non è una busta")
    return root


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep settings and logs out of the real home directory."""
    monkeypatch.setenv("P7MMANAGER_HOME", str(tmp_path / "home"))
    from p7mmanager.i18n import Language, set_language

    set_language(Language.ENGLISH)
    yield
    set_language(Language.ENGLISH)


@pytest.fixture(scope="session", autouse=True)
def qt_offscreen():
    """No display on a CI runner; Qt must not try to open one."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
