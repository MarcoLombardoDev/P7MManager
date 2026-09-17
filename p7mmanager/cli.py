# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The same engine, without a window.

The interface is the window; this exists so the tool can run in a scheduled
task or over SSH, and so the behaviour of the PowerShell and Python scripts it
replaces is still available one-for-one: point it at a folder, optionally with
``-r``, and get ``OK`` per file or a table with ``-d``.

It is a thin caller of :mod:`p7mmanager.core`, and shares the queue with the
window, so ``--workers`` speeds up a large folder the same way.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import APP_NAME, __version__
from .core.extractor import Conflict, Destination, ExtractionSettings
from .core.jobs import DEFAULT_WORKERS, JobQueue, JobState
from .core.report import write_csv, write_json
from .core.scanner import scan
from .i18n import tr_message

__all__ = ["main"]

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"

_STATE_TEXT = {
    JobState.DONE: ("OK", _GREEN),
    JobState.WARNING: ("WARN", _YELLOW),
    JobState.SKIPPED: ("SKIP", _YELLOW),
    JobState.FAILED: ("ERROR", _RED),
    JobState.CANCELLED: ("CANCELLED", _DIM),
    JobState.PENDING: ("PENDING", _DIM),
    JobState.RUNNING: ("RUNNING", _DIM),
}


def _colours_available(stream) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if sys.platform == "win32":
        # Windows 10 and later can do ANSI once the console mode says so.
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            return bool(kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7))
        except Exception:  # pragma: no cover - older consoles
            return False
    return True


class _Printer:
    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout
        self.colour = _colours_available(self.stream)

    def write(self, text: str = "", colour: str | None = None) -> None:
        if colour and self.colour:
            text = f"{colour}{text}{_RESET}"
        print(text, file=self.stream)

    def status(self, state: JobState, width: int = 0) -> str:
        """The state's label, padded to ``width`` columns as printed.

        Padding is computed on the label alone: the escape codes take no
        space on screen but would otherwise be counted by ``str.ljust``.
        """
        label, colour = _STATE_TEXT.get(state, ("?", ""))
        padding = " " * max(width - len(label), 0)
        if self.colour:
            return f"{colour}{label}{_RESET}{padding}"
        return label + padding


def _human_size(size: int) -> str:
    if size < 1000:
        return f"{size} B"
    for unit in ("kB", "MB", "GB"):
        size /= 1000.0
        if size < 1000 or unit == "GB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} GB"  # pragma: no cover


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="p7mmanager --cli",
        description=f"{APP_NAME} {__version__} — inspect .p7m containers and extract "
        "the documents they carry",
        epilog="Integrity and RSA signature checks only: no trust list, no revocation "
        "check, no timestamp validation. This is not a legal validation.",
    )
    parser.add_argument("paths", nargs="*", default=["."], type=Path,
                        help="files or folders to process (default: the current folder)")
    parser.add_argument("-r", "--recurse", action="store_true",
                        help="scan subfolders as well")
    parser.add_argument("-d", "--detailed", action="store_true",
                        help="print a table instead of one line per file")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="write the extracted documents here instead of beside "
                             "the originals")
    parser.add_argument("--mirror", action="store_true",
                        help="with --output, recreate the source folder structure")
    parser.add_argument("-n", "--analyse-only", action="store_true",
                        help="report what is inside without writing anything")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace an existing output file")
    parser.add_argument("--skip-existing", action="store_true",
                        help="leave an existing output file alone")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip the integrity and signature checks (faster)")
    parser.add_argument("-j", "--workers", type=int, default=DEFAULT_WORKERS, metavar="N",
                        help=f"files processed in parallel (default {DEFAULT_WORKERS})")
    parser.add_argument("--csv", type=Path, default=None, metavar="FILE",
                        help="also write a CSV report")
    parser.add_argument("--json", type=Path, default=None, metavar="FILE",
                        help="also write a JSON report")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="only print failures and the summary")
    return parser


def _settings_from(args: argparse.Namespace) -> ExtractionSettings:
    if args.output is None:
        destination = Destination.BESIDE_SOURCE
    elif args.mirror:
        destination = Destination.MIRROR_TREE
    else:
        destination = Destination.SINGLE_FOLDER
    conflict = Conflict.RENAME
    if args.overwrite:
        conflict = Conflict.OVERWRITE
    elif args.skip_existing:
        conflict = Conflict.SKIP
    root = None
    if destination is Destination.MIRROR_TREE:
        folders = [Path(path) for path in args.paths if Path(path).is_dir()]
        root = folders[0] if folders else None
    return ExtractionSettings(
        destination=destination,
        output_dir=args.output,
        root_dir=root,
        conflict=conflict,
        verify=not args.no_verify,
        analyse_only=args.analyse_only,
    )


def _print_detail_row(printer: _Printer, job) -> None:
    analysis = job.result.analysis if job.result else None
    signer = ""
    content = ""
    if analysis is not None:
        content = analysis.payload_kind.label if analysis.payload_kind else ""
        names = [item.display_name for item in analysis.signers]
        signer = names[0] if names else ""
    output = job.output_path.name if job.output_path else ""
    size = _human_size(analysis.payload_size) if analysis else ""
    printer.write(
        f"{job.name[:38]:<38} {printer.status(job.state, 9)} "
        f"{content[:22]:<22} {signer[:24]:<24} {output[:30]:<30} {size:>9}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    printer = _Printer()

    files = scan(args.paths, recursive=args.recurse)
    if not files:
        printer.write("No .p7m file found.", _YELLOW)
        return 1

    queue = JobQueue(workers=max(1, args.workers))
    queue.add(files)

    if args.detailed:
        printer.write(
            f"{'FileName':<38} {'Status':<9} {'Content':<22} {'Signer':<24} "
            f"{'OutputFile':<30} {'Size':>9}"
        )
        printer.write("-" * 136, _DIM)

    queue.start(_settings_from(args))
    queue.wait()

    for job in queue.jobs:
        if args.detailed:
            _print_detail_row(printer, job)
            continue
        if args.quiet and job.state in (JobState.DONE, JobState.SKIPPED):
            continue
        message = tr_message(job.message)
        printer.write(f"{printer.status(job.state, 6)} {job.name} — {message}")

    counts = queue.counts()
    printer.write()
    verb = "analysed" if args.analyse_only else "extracted"
    summary = (
        f"{len(files)} file(s): {counts['done']} {verb}, "
        f"{counts['warning'] + counts['skipped']} with warnings, "
        f"{counts['failed']} failed"
    )
    printer.write(summary, _GREEN if not counts["failed"] else _YELLOW)

    for destination, writer in ((args.csv, write_csv), (args.json, write_json)):
        if destination is None:
            continue
        try:
            writer(queue.jobs, destination)
            printer.write(f"Report written to {destination}", _DIM)
        except OSError as exc:
            printer.write(f"Could not write {destination}: {exc}", _RED)
            return 2

    return 0 if not counts["failed"] else 3


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
