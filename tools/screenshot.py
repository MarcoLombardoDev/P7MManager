# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Regenerate the screenshots in docs/images from the real window.

    python tools/screenshot.py

Containers are signed with OpenSSL into a temporary folder, the queue is run
against them, and the window is grabbed — so the images cannot drift away from
what the application actually draws. Run it after a change to the interface.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
)
XML = b'<?xml version="1.0" encoding="UTF-8"?>\n<FatturaElettronica versione="FPR12"/>\n'

PEOPLE = [
    ("marco", "/C=IT/O=Studio Lombardo S.r.l./CN=Marco Lombardo"
              "/serialNumber=TINIT-LMBMRC80A01F205X"),
    ("giulia", "/C=IT/O=Studio Lombardo S.r.l./CN=Giulia Bianchi"
               "/serialNumber=TINIT-BNCGLI85E45F205R"),
]


def _run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True)


def build_samples(folder: Path) -> None:
    """A folder that looks like a real batch, including the awkward cases."""
    openssl = shutil.which("openssl")
    if openssl is None:
        raise SystemExit("openssl is required to build the sample containers")

    keys = {}
    for name, subject in PEOPLE:
        key, certificate = folder / f"{name}.key", folder / f"{name}.crt"
        _run(openssl, "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key),
             "-out", str(certificate), "-days", "730", "-nodes", "-subj", subject)
        keys[name] = (key, certificate)

    documents = folder / "documenti"
    (documents / "2026").mkdir(parents=True)
    pdf = folder / "source.pdf"
    pdf.write_bytes(PDF)
    xml = folder / "source.xml"
    xml.write_bytes(XML)

    def sign(source: Path, target: Path, who: str, *extra: str) -> Path:
        key, certificate = keys[who]
        _run(openssl, "cms", "-sign", "-in", str(source), "-signer", str(certificate),
             "-inkey", str(key), "-outform", "DER", "-binary", "-nodetach",
             "-out", str(target), *extra)
        return target

    sign(pdf, documents / "contratto-fornitura.pdf.p7m", "marco")
    sign(xml, documents / "IT01234567890_00001.xml.p7m", "giulia")
    sign(pdf, documents / "2026" / "verbale-assemblea.pdf.p7m", "marco", "-md", "sha512")

    both = documents / "delibera-firmata-due-volte.pdf.p7m"
    sign(pdf, both, "marco")
    key, certificate = keys["giulia"]
    _run(openssl, "cms", "-resign", "-in", str(both), "-inform", "DER",
         "-signer", str(certificate), "-inkey", str(key), "-outform", "DER",
         "-binary", "-out", str(both))

    detached = documents / "2026" / "allegato-staccato.pdf.p7m"
    key, certificate = keys["marco"]
    _run(openssl, "cms", "-sign", "-in", str(pdf), "-signer", str(certificate),
         "-inkey", str(key), "-outform", "DER", "-binary", "-out", str(detached))

    (documents / "2026" / "danneggiato.pdf.p7m").write_bytes(
        b"\x30\x82\x04\x00 troncato durante il trasferimento"
    )


def main() -> int:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        build_samples(folder)
        home = folder / "home"
        os.environ["P7MMANAGER_HOME"] = str(home)

        from PySide6.QtWidgets import QApplication

        from p7mmanager.i18n import Language, set_language
        from p7mmanager.main import _apply_stylesheet
        from p7mmanager.ui.main_window import MainWindow

        application = QApplication.instance() or QApplication([])
        _apply_stylesheet(application)

        target_dir = ROOT / "docs" / "images"
        target_dir.mkdir(parents=True, exist_ok=True)

        for language, suffix in ((Language.ENGLISH, "en"), (Language.ITALIAN, "it")):
            set_language(language)
            window = MainWindow()
            window.resize(1560, 840)
            window.add_paths([folder / "documenti"])
            window.analyse_only_check.setChecked(True)
            window._retranslate()
            window.show()

            window._start()
            deadline = time.time() + 60
            while window.queue.is_running and time.time() < deadline:
                application.processEvents()
                time.sleep(0.01)
            for _ in range(20):
                window._drain_events()
                application.processEvents()

            window.table.selectRow(0)
            for _ in range(10):
                application.processEvents()

            path = target_dir / f"p7mmanager-{suffix}.png"
            window.grab().save(str(path))
            print(f"written {path.relative_to(ROOT)}")
            window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
