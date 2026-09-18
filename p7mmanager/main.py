# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Application entry point.

Deliberately small: parse the arguments, hand ``--cli`` straight to the
console tool, otherwise configure logging, create the ``QApplication``,
install a last-resort exception handler so a bug becomes a log entry and a
message rather than a silent crash, and show the window.
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from . import APP_NAME, ORGANISATION, __version__
from .i18n import Language, detect_language, set_language
from .utils.logging import setup_logging

log = logging.getLogger(__name__)

__all__ = ["main"]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="p7mmanager",
        description=f"{APP_NAME} — inspect signed .p7m containers and extract what "
        "they carry",
    )
    parser.add_argument("paths", nargs="*", type=Path,
                        help=".p7m files or folders to load into the queue")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--cli", action="store_true",
                        help="run without a window; see --cli --help")
    parser.add_argument("--language", choices=[lang.value for lang in Language],
                        help="force the interface language instead of following the system")
    parser.add_argument("--self-check", action="store_true",
                        help="start Qt, report the platform plugin in use, and exit")
    parser.add_argument("--log-level", default=None,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(list(argv) if argv is not None else None)


def _apply_stylesheet(app) -> None:
    """The flatly palette Orion, Iris and Proteus share.

    A missing or unreadable stylesheet leaves the platform's own look, which
    is a perfectly good interface. It is not worth failing to start over.
    """
    from .utils.paths import resources_dir

    sheet = resources_dir() / "styles" / "p7mmanager.qss"
    try:
        app.setStyleSheet(sheet.read_text(encoding="utf-8"))
    except OSError:
        log.debug("No stylesheet at %s; using the platform look", sheet)


def _set_application_icon(app) -> None:
    """Use the bundled application icon, if it is where we expect it."""
    from PySide6.QtGui import QIcon

    from .utils.paths import resources_dir

    candidate = resources_dir() / "icons" / "p7mmanager.png"
    if candidate.exists():
        app.setWindowIcon(QIcon(str(candidate)))
        return
    log.debug("No application icon found; using the platform default")


def _install_exception_hook(window) -> None:
    from PySide6.QtWidgets import QMessageBox

    def hook(kind, value, tb) -> None:
        if issubclass(kind, KeyboardInterrupt):  # pragma: no cover
            sys.__excepthook__(kind, value, tb)
            return
        log.error("Unhandled exception", exc_info=(kind, value, tb))
        details = "".join(traceback.format_exception(kind, value, tb))
        try:
            box = QMessageBox(window)
            box.setWindowTitle(APP_NAME)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(f"{kind.__name__}: {value}")
            box.setDetailedText(details)
            box.exec()
        except Exception:  # pragma: no cover - the dialog itself failed
            print(details, file=sys.stderr)

    sys.excepthook = hook


def _choose_language(requested: str | None) -> Language:
    if requested:
        return Language(requested)
    from .utils.settings import Settings

    stored = Settings().get("language")
    if stored in (Language.ENGLISH.value, Language.ITALIAN.value):
        return Language(stored)
    import locale

    system, _ = locale.getdefaultlocale()
    return detect_language(system)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)

    # --cli hands everything after it to the console tool's own parser,
    # untouched. Parsing it here first would reject the flags that tool
    # documents -- `--cli documenti -r -d` is in the README -- because this
    # parser has never heard of them.
    if "--cli" in arguments:
        from .cli import main as cli_main

        return cli_main([item for item in arguments if item != "--cli"])

    args = _parse_args(arguments)

    setup_logging(args.log_level or logging.INFO)

    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName(ORGANISATION)
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv[:1])
    set_language(_choose_language(args.language))

    if args.self_check:
        # Two lines, the second in a fixed "key: value" shape, because the
        # release workflow parses it: a bundle whose Qt platform plugin is
        # missing still passes --version, and would then fail on a desktop.
        print(f"{APP_NAME} {__version__}")
        print(f"platform plugin: {app.platformName()}")
        return 0

    _apply_stylesheet(app)
    _set_application_icon(app)

    from .ui.main_window import MainWindow

    window = MainWindow()
    _install_exception_hook(window)
    # Maximised, like Orion: a queue of five hundred files wants the screen.
    # The saved size is not lost — Qt keeps it as the window's normal size.
    window.showMaximized()

    if args.paths:
        window.add_paths(args.paths, explicit=True)

    return app.exec()


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
