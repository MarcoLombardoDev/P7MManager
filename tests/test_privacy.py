# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The claim the README makes about privacy, checked rather than asserted.

A .p7m holds a contract, an invoice, a court document — things people are not
free to hand to a third party, and often not legally allowed to. The README
says the documents never leave the machine; these tests are what make that
sentence something other than marketing, and what would fail if a future change
quietly added a call home.
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "p7mmanager"

#: Standard-library modules that reach the network. urllib is not here: only
#: urllib.parse is used, for percent-encoding a mailto: subject line, and that
#: is checked separately below.
NETWORK_MODULES = {
    "socket",
    "ssl",
    "http",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "xmlrpc",
    "webbrowser",
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
}


def _imports(path: Path) -> list[tuple[str, int]]:
    """Every module a file imports, as (dotted name, line)."""
    found: list[tuple[str, int]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def test_nothing_in_the_package_imports_a_network_module():
    offenders = [
        f"{path.relative_to(ROOT)}:{line}: {module}"
        for path in sorted(PACKAGE.rglob("*.py"))
        for module, line in _imports(path)
        if module.split(".")[0] in NETWORK_MODULES
    ]
    assert not offenders, "the application must not reach the network:\n" + "\n".join(
        offenders
    )


def test_urllib_is_only_used_for_percent_encoding():
    """urllib.parse is text handling; urllib.request is the network."""
    for path in sorted(PACKAGE.rglob("*.py")):
        for module, line in _imports(path):
            if module.split(".")[0] != "urllib":
                continue
            assert module == "urllib.parse", (
                f"{path.relative_to(ROOT)}:{line}: only urllib.parse is allowed"
            )


def test_no_qt_networking_either():
    """Qt ships QtNetwork in the bundle because QtCore links it; the
    application must still never use it."""
    for path in sorted(PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "QtNetwork" not in text, f"{path.relative_to(ROOT)} uses QtNetwork"
        assert "QNetworkAccessManager" not in text


def test_nothing_phones_home_on_start_or_update():
    """No telemetry, no analytics, no crash reporter, no update check."""
    suspicious = ("telemetry", "analytics", "sentry", "posthog", "mixpanel",
                  "check_for_updates", "phone_home")
    for path in sorted(PACKAGE.rglob("*.py")):
        lowered = path.read_text(encoding="utf-8").lower()
        for word in suspicious:
            # "no telemetry" in a docstring is the promise, not a breach of it.
            occurrences = [
                line for line in lowered.splitlines()
                if word in line and not line.lstrip().startswith(("#", "*", '"', "'"))
                and "no " + word not in line
            ]
            assert not occurrences, f"{path.relative_to(ROOT)}: {word} in {occurrences}"


@pytest.fixture
def no_network(monkeypatch):
    """Make the network unusable, the way an air-gapped machine would."""

    def refuse(*args, **kwargs):
        raise AssertionError("the engine tried to open a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    return refuse


def test_a_container_is_analysed_with_the_network_unusable(no_network, tmp_path):
    """The engine's answer must not depend on anything outside this machine.

    It is also why the verdicts are worded as they are: a tool that checked
    revocation would have to ask an authority, and this one never asks anyone.
    """
    from .conftest import OPENSSL

    if OPENSSL is None:
        pytest.skip("openssl is not installed")

    import shutil
    import subprocess

    key, certificate = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key),
         "-out", str(certificate), "-days", "30", "-nodes", "-subj", "/CN=Prova"],
        check=True, capture_output=True,
    )
    document = tmp_path / "documento.pdf"
    document.write_bytes(b"%PDF-1.4\ntrailer<</Root 1 0 R>>\n%%EOF\n")
    container = tmp_path / "documento.pdf.p7m"
    subprocess.run(
        ["openssl", "cms", "-sign", "-in", str(document), "-signer", str(certificate),
         "-inkey", str(key), "-outform", "DER", "-binary", "-nodetach",
         "-out", str(container)],
        check=True, capture_output=True,
    )
    assert shutil.which("openssl")

    from p7mmanager.core.extractor import extract

    result = extract(container)

    assert result.written is True
    assert result.analysis.integrity is True
    assert result.analysis.signatures_valid is True


def test_the_readme_only_promises_what_holds():
    """The privacy section must not claim the tool is a web page, or that it
    catches more than it does."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "never leave" in readme.lower() or "never leaves" in readme.lower()
    for wrong in ("in your browser", "JavaScript", "upload your file", "our servers"):
        assert wrong.lower() not in readme.lower(), (
            f"{wrong!r} describes a web service; this is a desktop application"
        )
