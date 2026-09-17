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

__all__ = ["APP_NAME", "APP_ID", "ORGANISATION", "__version__"]

APP_NAME = "P7M Manager"
APP_ID = "p7mmanager"
ORGANISATION = "MarcoLombardoDev"
__version__ = "1.0.0"
