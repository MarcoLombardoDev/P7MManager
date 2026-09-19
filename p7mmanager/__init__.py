# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""P7M Manager — a desktop tool for signed .p7m containers.

The package is split so that everything under :mod:`p7mmanager.core` runs
without Qt and without a display: the command line, the test-suite and the
window all drive the same engine.
"""

from __future__ import annotations

APP_NAME = "P7M Manager"
APP_SUBTITLE = "Signed containers, opened"
APP_ID = "p7mmanager"
ORGANISATION = "MarcoLombardoDev"
__version__ = "1.1.0"

APP_AUTHOR = "Marco Lombardo"
APP_COPYRIGHT_YEAR = "2026"

#: Where commercial licensing enquiries go. Single source of truth: the
#: interface, the README and COMMERCIAL-LICENSE.md must never disagree.
CONTACT_EMAIL = "marco.lombardo@gmail.com"

#: Shown along the bottom of the window, and deliberately not something the
#: interface can be built without.
#:
#: AGPL-3.0 section 5 requires the work to carry Appropriate Legal Notices,
#: and section 7(b) lets an author require that attribution be preserved.
#: Orion, Iris, Proteus and Argus all show this line; this one has it from
#: its first release rather than added later.
LICENSE_NOTICE = (
    f"© {APP_COPYRIGHT_YEAR} {APP_AUTHOR} — {APP_NAME}"
    "  |  Licensed under AGPL-3.0"
    "  |  Commercial licensing:"
)

#: Subject line pre-filled when the address in the notice is clicked.
LICENSING_SUBJECT = f"{APP_NAME} — commercial licence enquiry"

__all__ = [
    "APP_NAME",
    "APP_SUBTITLE",
    "APP_ID",
    "APP_AUTHOR",
    "APP_COPYRIGHT_YEAR",
    "ORGANISATION",
    "CONTACT_EMAIL",
    "LICENSE_NOTICE",
    "LICENSING_SUBJECT",
    "__version__",
]
