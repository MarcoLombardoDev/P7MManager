# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# PyInstaller recipe for a standalone build:
#
#     pyinstaller p7mmanager.spec
#
# Qt's own modules are the only large thing in here. The engine is standard
# library, so nothing else needs collecting — and the exclusions below keep
# out modules PyInstaller would otherwise pull in through the standard
# library, one of which (readline) drags a GPL-3 library with no linking
# exception into the archive. That combination is the one a redistribution
# licence cannot survive; see COMMERCIAL-LICENSE.md.

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(SPECPATH, "tools"))  # noqa: F821 - PyInstaller
from collect_licences import collect as collect_licences  # noqa: E402

block_cipher = None

# Windows wants an .ico, macOS an .icns, and PyInstaller takes a PNG for
# everything else. All three are drawn by tools/make_icon.py and committed, so
# a build never depends on the fonts — or the Pillow — a runner happens to
# have. A missing icon is not worth failing a build over: the platform default
# is ugly, not broken.
_icons = Path("resources") / "icons"
_icon_file = {"win32": "p7mmanager.ico", "darwin": "p7mmanager.icns"}.get(
    sys.platform, "p7mmanager.png"
)
_icon_path = _icons / _icon_file
icon = str(_icon_path) if _icon_path.exists() else None

a = Analysis(
    ["p7mmanager/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("resources/styles/p7mmanager.qss", "resources/styles"),
        # The window and taskbar icon is read at runtime from here, so it
        # ships inside the bundle as well as being embedded in the executable.
        ("resources/icons/p7mmanager.png", "resources/icons"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "readline",
        "tkinter",
        "test",
        "unittest",
        "pydoc_data",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
    ],
    cipher=block_cipher,
    noarchive=False,
)

# Everything in this bundle is being redistributed, and most of it asks for
# its terms to travel with the binary. The texts are staged here rather than by
# the release workflow because only this file has ``a.binaries`` -- the list of
# what PyInstaller actually resolved on this machine -- and that list is the
# only way to reach the system libraries. Running the collector as a separate
# step outside the build, which is what happened until now, produced a tree
# covering the wheels and nothing else: an archive with roughly eighty system
# libraries in it and not one of their licence files, several of them LGPL-2.1
# whose §6 wants a copy of the licence with the object code, and §11 of
# COMMERCIAL-LICENSE.md promising the recipient exactly that.
#
# The tree is not added to ``a.datas``: the release workflow copies it to the
# root of the archive, where somebody looking for it can see it, instead of
# burying it under _internal/.
collect_licences(
    SPECPATH,  # noqa: F821 - injected by PyInstaller
    os.path.join(SPECPATH, "build", "licenses"),  # noqa: F821
    a.binaries,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="P7MManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="P7MManager",
)

# macOS expects an application bundle, not a folder of files: double-clicking a
# COLLECT directory does nothing there. Built from the same collection, so the
# three platforms ship identical contents in the shape each one expects.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="P7MManager.app",
        icon=icon,
        bundle_identifier="dev.marcolombardo.p7mmanager",
        info_plist={
            "CFBundleName": "P7M Manager",
            "CFBundleDisplayName": "P7M Manager",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
