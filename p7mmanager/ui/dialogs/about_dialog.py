# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""About P7M Manager: what it is, which version, and under what terms.

The window carries the copyright line along the bottom at all times; this box
is where the rest goes — the versions a bug report needs, and the two claims
that must never drift apart: the software is free under AGPL-3.0, and what it
reports about a signature is not a legal validation.
"""

from __future__ import annotations

import sys
from urllib.parse import quote

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ... import (
    APP_AUTHOR,
    APP_COPYRIGHT_YEAR,
    APP_NAME,
    APP_SUBTITLE,
    CONTACT_EMAIL,
    LICENSING_SUBJECT,
    __version__,
)
from ...i18n import tr

__all__ = ["AboutDialog"]


def _qt_version() -> str:
    try:
        from PySide6.QtCore import qVersion

        return f"Qt {qVersion()}"
    except Exception:  # pragma: no cover - defensive
        return "Qt"


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{tr('About')} {APP_NAME}")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(APP_NAME, self)
        title.setStyleSheet("font-size: 26px; font-weight: 700; color: #2c3e50;")
        layout.addWidget(title)

        subtitle = QLabel(tr(APP_SUBTITLE), self)
        subtitle.setObjectName("hint")
        layout.addWidget(subtitle)

        # The engine is standard library, so the only versions worth naming in
        # a bug report are the interpreter's and Qt's.
        versions = QLabel(
            f"{tr('Version {version}').format(version=__version__)}\n"
            f"Python {sys.version.split()[0]} · {_qt_version()}",
            self,
        )
        versions.setObjectName("hint")
        layout.addWidget(versions)

        copyright_line = QLabel(
            f"© {APP_COPYRIGHT_YEAR} {APP_AUTHOR}", self
        )
        layout.addWidget(copyright_line)

        disclaimer = QLabel(
            tr(
                "This tool checks integrity and, for RSA, the signature itself. It is "
                "not a legal validation: it has no trust list, does not check "
                "revocation and does not validate timestamps against an authority."
            ),
            self,
        )
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        licence = QLabel(
            tr(
                "P7M Manager is free software released under the GNU Affero General "
                "Public License, version 3 or later. It works entirely offline: no "
                "account, no server, no telemetry."
            ),
            self,
        )
        licence.setWordWrap(True)
        layout.addWidget(licence)

        link = QLabel(
            f"{tr('Commercial licensing')}: "
            f'<a href="mailto:{CONTACT_EMAIL}?subject={quote(LICENSING_SUBJECT)}">'
            f"{CONTACT_EMAIL}</a>",
            self,
        )
        link.setTextFormat(Qt.TextFormat.RichText)
        # Opened through QDesktopServices rather than setOpenExternalLinks, so a
        # machine with no mail client fails quietly instead of raising; the
        # address stays readable on screen either way.
        link.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        layout.addWidget(link)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        # Qt translates its standard buttons only where its own translations
        # are installed, which a frozen build need not carry.
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr("Close"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
