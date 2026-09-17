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

block_cipher = None

a = Analysis(
    ["p7mmanager/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[("resources/styles/p7mmanager.qss", "resources/styles")],
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
