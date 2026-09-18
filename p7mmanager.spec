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

import sys
from pathlib import Path

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
