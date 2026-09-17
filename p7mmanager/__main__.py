# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""``python -m p7mmanager``.

The import is absolute rather than relative on purpose: PyInstaller runs this
file as a top-level script, with no parent package, and a relative import
fails there with "attempted relative import with no known parent package" —
in the frozen build only, which is exactly where nobody is watching.
"""

from __future__ import annotations

from p7mmanager.main import main

if __name__ == "__main__":
    raise SystemExit(main())
