# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The window: a queue on the left, what is inside the selected file on the right.

The queue runs on worker threads, and Qt widgets belong to the thread that
made them. Rather than emit signals from those threads, the queue's events go
into a plain :class:`queue.Queue` and a timer on the GUI thread drains it —
one place where thread affinity has to be right, and it is the only place.
That also means the engine stays unaware of Qt, which is the rule the layout
in CLAUDE.md sets.
"""

from __future__ import annotations

import logging
import queue as queue_module
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStyle,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..core import report
from ..core.extractor import Conflict, Destination, ExtractionSettings
from ..core.jobs import DEFAULT_WORKERS, JobQueue, QueueEvent
from ..core.scanner import scan
from ..i18n import Language, current_language, set_language, tr
from ..utils.settings import Settings
from .details import DetailsPanel
from .queue_model import Column, QueueModel

log = logging.getLogger(__name__)

__all__ = ["MainWindow"]

_CONTAINER_FILTER = "*.p7m *.P7M *.p7s *.p7 *.cms"


class MainWindow(QMainWindow):
    """Everything the user sees."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or Settings()
        self._events: queue_module.Queue[QueueEvent] = queue_module.Queue()
        self.queue = JobQueue(listener=self._events.put, workers=DEFAULT_WORKERS)
        self._last_folder = self.settings.get("last_folder", str(Path.home()))

        self.setObjectName("mainWindow")
        self.setAcceptDrops(True)
        self.resize(1320, 800)

        self._build_widgets()
        self._build_actions()
        self._restore_options()
        self._retranslate()
        self._update_actions()

        self._pump = QTimer(self)
        self._pump.setInterval(60)
        self._pump.timeout.connect(self._drain_events)
        self._pump.start()

    # -----------------------------------------------------------------
    # construction
    # -----------------------------------------------------------------
    def _build_widgets(self) -> None:
        central = QWidget(self)
        central.setObjectName("central")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(10, 10, 10, 6)
        outer.setSpacing(8)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, central)

        left = QWidget(self.splitter)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.options_box = QGroupBox(left)
        self._build_options(self.options_box)
        left_layout.addWidget(self.options_box)

        self.table = QTableView(left)
        self.model = QueueModel(self)
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(lambda _index: self._open_output())
        self.table.selectionModel().selectionChanged.connect(self._selection_changed)

        header = self.table.horizontalHeader()
        # The name is what a user scans the queue for, so it gets a generous
        # width of its own rather than whatever is left over after six other
        # columns have taken theirs; the last column absorbs the slack.
        header.setMinimumSectionSize(70)
        for column in (Column.SIZE, Column.SIGNATURES):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for column in (Column.NAME, Column.STATE, Column.SIGNER, Column.CONTENT):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(Column.OUTPUT, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(Column.NAME, 240)
        self.table.setColumnWidth(Column.STATE, 250)
        self.table.setColumnWidth(Column.SIGNER, 140)
        self.table.setColumnWidth(Column.CONTENT, 115)
        left_layout.addWidget(self.table, 1)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar(left)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        progress_row.addWidget(self.progress, 1)
        self.counts_label = QLabel(left)
        self.counts_label.setObjectName("hint")
        progress_row.addWidget(self.counts_label)
        left_layout.addLayout(progress_row)

        self.details = DetailsPanel(self.splitter)
        # Without a floor the queue's own minimum width squeezes the details
        # into a column too narrow to read a distinguished name in.
        self.details.setMinimumWidth(380)
        left.setMinimumWidth(520)
        self.splitter.addWidget(left)
        self.splitter.addWidget(self.details)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setCollapsible(1, False)
        self.splitter.setSizes([860, 460])

        outer.addWidget(self.splitter, 1)
        self.setCentralWidget(central)
        self.status = self.statusBar()

    def _build_options(self, box: QGroupBox) -> None:
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 6, 10, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.destination_label = QLabel(box)
        self.destination_combo = QComboBox(box)
        self.destination_combo.setMinimumWidth(210)
        for destination in (
            Destination.BESIDE_SOURCE,
            Destination.SINGLE_FOLDER,
            Destination.MIRROR_TREE,
        ):
            self.destination_combo.addItem("", destination.value)
        self.destination_combo.currentIndexChanged.connect(self._destination_changed)

        self.output_edit = QLineEdit(box)
        self.output_edit.setReadOnly(True)
        self.output_button = QPushButton(box)
        self.output_button.clicked.connect(self._choose_output_folder)

        self.conflict_label = QLabel(box)
        self.conflict_combo = QComboBox(box)
        self.conflict_combo.setMinimumWidth(210)
        for conflict in (Conflict.RENAME, Conflict.OVERWRITE, Conflict.SKIP):
            self.conflict_combo.addItem("", conflict.value)

        self.recursive_check = QCheckBox(box)
        self.recursive_check.setChecked(True)
        self.analyse_only_check = QCheckBox(box)
        self.verify_check = QCheckBox(box)
        self.verify_check.setChecked(True)

        self.workers_label = QLabel(box)
        self.workers_spin = QSpinBox(box)
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(DEFAULT_WORKERS)

        grid.addWidget(self.destination_label, 0, 0)
        grid.addWidget(self.destination_combo, 0, 1)
        grid.addWidget(self.output_edit, 0, 2)
        grid.addWidget(self.output_button, 0, 3)
        grid.addWidget(self.conflict_label, 1, 0)
        grid.addWidget(self.conflict_combo, 1, 1)

        checks = QHBoxLayout()
        checks.setSpacing(16)
        checks.addWidget(self.recursive_check)
        checks.addWidget(self.analyse_only_check)
        checks.addWidget(self.verify_check)
        checks.addStretch(1)
        checks.addWidget(self.workers_label)
        self.workers_spin.setMaximumWidth(70)
        checks.addWidget(self.workers_spin)
        # A row of their own: sharing one with the destination field left the
        # labels elided on a narrow window, which is where they matter most.
        grid.addLayout(checks, 2, 0, 1, 4)
        grid.setColumnStretch(2, 1)

    def _build_actions(self) -> None:
        style = self.style()

        def make(icon: QStyle.StandardPixmap, slot, shortcut=None) -> QAction:
            action = QAction(style.standardIcon(icon), "", self)
            action.triggered.connect(slot)
            if shortcut:
                action.setShortcut(shortcut)
            return action

        self.action_add_files = make(
            QStyle.StandardPixmap.SP_FileIcon, self._add_files, QKeySequence.StandardKey.Open
        )
        self.action_add_folder = make(
            QStyle.StandardPixmap.SP_DirOpenIcon, self._add_folder, "Ctrl+Shift+O"
        )
        self.action_start = make(
            QStyle.StandardPixmap.SP_MediaPlay, self._start, "Ctrl+R"
        )
        self.action_cancel = make(
            QStyle.StandardPixmap.SP_MediaStop, self._cancel, "Esc"
        )
        self.action_remove = make(
            QStyle.StandardPixmap.SP_DialogDiscardButton, self._remove_selected, "Del"
        )
        self.action_clear = make(
            QStyle.StandardPixmap.SP_DialogResetButton, lambda: self._clear(False)
        )
        self.action_clear_done = QAction(self)
        self.action_clear_done.triggered.connect(lambda: self._clear(True))
        self.action_export = make(
            QStyle.StandardPixmap.SP_DialogSaveButton, self._export_report, "Ctrl+E"
        )
        self.action_open_output = QAction(self)
        self.action_open_output.triggered.connect(self._open_output)
        self.action_open_folder = QAction(self)
        self.action_open_folder.triggered.connect(self._open_folder)
        self.action_quit = QAction(self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.triggered.connect(self.close)
        self.action_about = QAction(self)
        self.action_about.triggered.connect(self._about)

        toolbar = self.addToolBar("main")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.addAction(self.action_add_files)
        toolbar.addAction(self.action_add_folder)
        toolbar.addSeparator()
        toolbar.addAction(self.action_start)
        toolbar.addAction(self.action_cancel)
        toolbar.addSeparator()
        toolbar.addAction(self.action_remove)
        toolbar.addAction(self.action_clear)
        toolbar.addSeparator()
        toolbar.addAction(self.action_export)
        self.toolbar = toolbar
        widget = toolbar.widgetForAction(self.action_start)
        if widget is not None:
            widget.setObjectName("primaryAction")

        self.menu_file = self.menuBar().addMenu("")
        self.menu_file.addAction(self.action_add_files)
        self.menu_file.addAction(self.action_add_folder)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_export)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_quit)

        self.menu_queue = self.menuBar().addMenu("")
        self.menu_queue.addAction(self.action_start)
        self.menu_queue.addAction(self.action_cancel)
        self.menu_queue.addSeparator()
        self.menu_queue.addAction(self.action_remove)
        self.menu_queue.addAction(self.action_clear_done)
        self.menu_queue.addAction(self.action_clear)

        self.menu_view = self.menuBar().addMenu("")
        self.menu_language = self.menu_view.addMenu("")
        group = QActionGroup(self)
        group.setExclusive(True)
        self.language_actions: dict[Language, QAction] = {}
        for language in (Language.ENGLISH, Language.ITALIAN):
            action = QAction(language.label, self)
            action.setCheckable(True)
            action.setChecked(language is current_language())
            action.triggered.connect(lambda _checked, lang=language: self._set_language(lang))
            group.addAction(action)
            self.menu_language.addAction(action)
            self.language_actions[language] = action

        self.menu_help = self.menuBar().addMenu("")
        self.menu_help.addAction(self.action_about)

    # -----------------------------------------------------------------
    # translation
    # -----------------------------------------------------------------
    def _retranslate(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.options_box.setTitle(tr("Options"))
        self.destination_label.setText(tr("Destination"))
        for index, text in enumerate(
            ("Beside the original file", "One folder", "Mirror the source tree")
        ):
            self.destination_combo.setItemText(index, tr(text))
        self.output_button.setText(tr("Choose…"))
        self.conflict_label.setText(tr("If the file exists"))
        for index, text in enumerate(("Rename", "Overwrite", "Skip")):
            self.conflict_combo.setItemText(index, tr(text))
        self.recursive_check.setText(tr("Include subfolders"))
        self.analyse_only_check.setText(tr("Analyse only, do not extract"))
        self.verify_check.setText(tr("Verify signatures"))
        self.workers_label.setText(tr("Parallel workers"))

        self.action_add_files.setText(tr("Add files"))
        self.action_add_folder.setText(tr("Add folder"))
        self.action_start.setText(tr("Start"))
        self.action_cancel.setText(tr("Cancel"))
        self.action_remove.setText(tr("Remove"))
        self.action_clear.setText(tr("Clear"))
        self.action_clear_done.setText(tr("Clear &completed"))
        self.action_export.setText(tr("Export report"))
        self.action_open_output.setText(tr("Open document"))
        self.action_open_folder.setText(tr("Open folder"))
        self.action_quit.setText(tr("&Quit"))
        self.action_about.setText(tr("&About"))

        self.menu_file.setTitle(tr("&File"))
        self.menu_queue.setTitle(tr("&Queue"))
        self.menu_view.setTitle(tr("&View"))
        self.menu_language.setTitle(tr("&Language"))
        self.menu_help.setTitle(tr("&Help"))

        self.model.retranslate()
        self.details.refresh()
        self._update_counts()
        if not self.queue.jobs:
            self.status.showMessage(tr("Add .p7m files or a folder to begin"))

    def _set_language(self, language: Language) -> None:
        set_language(language)
        self.settings.set("language", language.value)
        self._retranslate()

    # -----------------------------------------------------------------
    # options
    # -----------------------------------------------------------------
    def _restore_options(self) -> None:
        destination = self.settings.get("destination", Destination.BESIDE_SOURCE.value)
        index = self.destination_combo.findData(destination)
        self.destination_combo.setCurrentIndex(max(index, 0))
        conflict = self.settings.get("conflict", Conflict.RENAME.value)
        index = self.conflict_combo.findData(conflict)
        self.conflict_combo.setCurrentIndex(max(index, 0))
        self.output_edit.setText(self.settings.get("output_dir", ""))
        self.recursive_check.setChecked(bool(self.settings.get("recursive", True)))
        self.analyse_only_check.setChecked(bool(self.settings.get("analyse_only", False)))
        self.verify_check.setChecked(bool(self.settings.get("verify", True)))
        self.workers_spin.setValue(int(self.settings.get("workers", DEFAULT_WORKERS)))
        self._destination_changed()

    def _save_options(self) -> None:
        self.settings.update(
            {
                "destination": self.destination_combo.currentData(),
                "conflict": self.conflict_combo.currentData(),
                "output_dir": self.output_edit.text(),
                "recursive": self.recursive_check.isChecked(),
                "analyse_only": self.analyse_only_check.isChecked(),
                "verify": self.verify_check.isChecked(),
                "workers": self.workers_spin.value(),
                "last_folder": self._last_folder,
            }
        )

    def _destination_changed(self) -> None:
        needs_folder = self.destination_combo.currentData() != Destination.BESIDE_SOURCE.value
        self.output_edit.setEnabled(needs_folder)
        self.output_button.setEnabled(needs_folder)

    def _choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, tr("Choose the destination folder"),
            self.output_edit.text() or self._last_folder
        )
        if folder:
            self.output_edit.setText(folder)

    def current_settings(self) -> ExtractionSettings:
        """The extraction settings the controls currently describe."""
        destination = Destination(self.destination_combo.currentData())
        output = self.output_edit.text().strip()
        if destination is not Destination.BESIDE_SOURCE and not output:
            destination = Destination.BESIDE_SOURCE
        root = None
        if destination is Destination.MIRROR_TREE:
            root = self._common_root()
        return ExtractionSettings(
            destination=destination,
            output_dir=Path(output) if output else None,
            root_dir=root,
            conflict=Conflict(self.conflict_combo.currentData()),
            verify=self.verify_check.isChecked(),
            analyse_only=self.analyse_only_check.isChecked(),
        )

    def _common_root(self) -> Path | None:
        """The deepest folder every queued file sits under, for mirroring."""
        folders = [job.path.parent.resolve() for job in self.queue.jobs]
        if not folders:
            return None
        common = folders[0]
        for folder in folders[1:]:
            while common != folder and common not in folder.parents:
                if common.parent == common:
                    return common
                common = common.parent
        return common

    # -----------------------------------------------------------------
    # queue operations
    # -----------------------------------------------------------------
    def _add_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Add files"),
            self._last_folder,
            f"{tr('Signed containers')} ({_CONTAINER_FILTER});;{tr('All files')} (*)",
        )
        if names:
            self._last_folder = str(Path(names[0]).parent)
            self.add_paths([Path(name) for name in names], explicit=True)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, tr("Choose a folder to scan"), self._last_folder
        )
        if not folder:
            return
        self._last_folder = folder
        self.status.showMessage(tr("Scanning folder…"))
        found = scan([folder], recursive=self.recursive_check.isChecked())
        if not found:
            self.status.showMessage(
                tr("No .p7m file found in {folder}").format(folder=folder), 8000
            )
            return
        self.add_paths(found)

    def add_paths(self, paths, explicit: bool = False) -> int:
        """Add files and folders to the queue; returns how many were added."""
        collected = scan(
            paths, recursive=self.recursive_check.isChecked(), include_all_files=explicit
        )
        added = self.queue.add(collected)
        self.model.set_jobs(self.queue.jobs)
        self._update_actions()
        self._update_counts()
        if added:
            self.status.showMessage(
                tr("{n} files added").format(n=len(added)), 5000
            )
            if not self.table.selectionModel().hasSelection():
                self.table.selectRow(0)
        return len(added)

    def _start(self) -> None:
        if self.queue.is_running:
            return
        self.queue.set_workers(self.workers_spin.value())
        self._save_options()
        settings = self.current_settings()
        if not self.queue.start(settings, rerun=True):
            self.status.showMessage(tr("Nothing to do"), 5000)
            return
        self.progress.setValue(0)
        self._update_actions()

    def _cancel(self) -> None:
        if self.queue.is_running:
            self.queue.cancel()
            self.status.showMessage(tr("Run cancelled"), 5000)

    def _selected_jobs(self) -> list:
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        return [job for job in (self.model.job_at(row) for row in sorted(rows)) if job]

    def _remove_selected(self) -> None:
        jobs = self._selected_jobs()
        if not jobs:
            return
        self.queue.remove(job.id for job in jobs)
        self.model.set_jobs(self.queue.jobs)
        self.details.show_job(None)
        self._update_actions()
        self._update_counts()

    def _clear(self, completed_only: bool) -> None:
        self.queue.clear(completed_only=completed_only)
        self.model.set_jobs(self.queue.jobs)
        self.details.show_job(None)
        self._update_actions()
        self._update_counts()

    # -----------------------------------------------------------------
    # events from the worker threads
    # -----------------------------------------------------------------
    def _drain_events(self) -> None:
        touched = False
        while True:
            try:
                event = self._events.get_nowait()
            except queue_module.Empty:
                break
            touched = True
            self._handle_event(event)
        if touched:
            self._update_counts()

    def _handle_event(self, event: QueueEvent) -> None:
        if event.kind == "job" and event.job is not None:
            self.model.job_changed(event.job)
            current = self.details.job
            if current is not None and current.id == event.job.id:
                self.details.refresh()
        elif event.kind == "progress":
            if event.total:
                self.progress.setValue(int(event.done / event.total * 100))
            self.status.showMessage(
                tr("Processing {done} of {total}").format(
                    done=event.done, total=event.total
                )
            )
        elif event.kind == "started":
            self.progress.setValue(0)
            self._update_actions()
        elif event.kind == "finished":
            self.progress.setValue(100 if not event.cancelled else self.progress.value())
            counts = self.queue.counts()
            if event.cancelled:
                self.status.showMessage(tr("Run cancelled"), 8000)
            else:
                phrase = (
                    "Finished: {ok} analysed, {warn} with warnings, {failed} failed"
                    if self.analyse_only_check.isChecked()
                    else "Finished: {ok} extracted, {warn} with warnings, {failed} failed"
                )
                self.status.showMessage(
                    tr(phrase)
                    .format(
                        ok=counts["done"],
                        warn=counts["warning"] + counts["skipped"],
                        failed=counts["failed"],
                    ),
                    0,
                )
            self._update_actions()
            self.details.refresh()

    # -----------------------------------------------------------------
    # small helpers
    # -----------------------------------------------------------------
    def _selection_changed(self) -> None:
        jobs = self._selected_jobs()
        self.details.show_job(jobs[0] if jobs else None)
        self._update_actions()

    def _update_actions(self) -> None:
        running = self.queue.is_running
        has_jobs = bool(self.queue.jobs)
        has_selection = bool(self.table.selectionModel().selectedRows())
        self.action_start.setEnabled(has_jobs and not running)
        self.action_cancel.setEnabled(running)
        self.action_add_files.setEnabled(not running)
        self.action_add_folder.setEnabled(not running)
        self.action_remove.setEnabled(has_selection and not running)
        self.action_clear.setEnabled(has_jobs and not running)
        self.action_clear_done.setEnabled(has_jobs and not running)
        self.action_export.setEnabled(has_jobs)
        self.options_box.setEnabled(not running)

    def _update_counts(self) -> None:
        total = len(self.queue.jobs)
        if not total:
            self.counts_label.setText(tr("No file in the queue"))
            self.progress.setValue(0)
            return
        counts = self.queue.counts()
        self.counts_label.setText(
            f"{tr('{n} files in the queue').format(n=total)} · "
            f"{tr('Done')}: {counts['done']} · "
            f"{tr('Warning')}: {counts['warning'] + counts['skipped']} · "
            f"{tr('Failed')}: {counts['failed']}"
        )

    def _show_context_menu(self, position) -> None:
        if not self._selected_jobs():
            return
        menu = QMenu(self)
        menu.addAction(self.action_open_output)
        menu.addAction(self.action_open_folder)
        menu.addSeparator()
        menu.addAction(self.action_remove)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _open_output(self) -> None:
        jobs = self._selected_jobs()
        if not jobs:
            return
        job = jobs[0]
        target = job.output_path or job.path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _open_folder(self) -> None:
        jobs = self._selected_jobs()
        if not jobs:
            return
        job = jobs[0]
        folder = (job.output_path or job.path).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _export_report(self) -> None:
        jobs = self.queue.jobs
        if not jobs:
            self.status.showMessage(tr("Nothing to export yet"), 5000)
            return
        name, selected = QFileDialog.getSaveFileName(
            self,
            tr("Export report"),
            str(Path(self._last_folder) / "p7m-report.csv"),
            f"{tr('CSV report')} (*.csv);;{tr('JSON report')} (*.json)",
        )
        if not name:
            return
        path = Path(name)
        try:
            if path.suffix.lower() == ".json" or "json" in selected.lower():
                path = path.with_suffix(".json")
                report.write_json(jobs, path)
            else:
                path = path.with_suffix(".csv")
                report.write_csv(jobs, path)
        except OSError as exc:
            QMessageBox.warning(
                self,
                APP_NAME,
                tr("Could not save the report: {error}").format(error=exc.strerror or exc),
            )
            return
        self.status.showMessage(tr("Report saved to {path}").format(path=path), 8000)

    def _about(self) -> None:
        # Built outside the f-string: nested quotes across lines are a syntax
        # error before Python 3.12, and this project targets 3.10.
        disclaimer = tr(
            "This tool checks integrity and, for RSA, the signature itself. It is "
            "not a legal validation: it has no trust list, does not check "
            "revocation and does not validate timestamps against an authority."
        )
        licence = tr(
            "Free software under AGPL-3.0-or-later; a commercial licence is "
            "available."
        )
        summary = tr("Inspect signed .p7m containers and extract what they carry")
        version = tr("Version {version}").format(version=__version__)
        QMessageBox.about(
            self,
            tr("About P7M Manager"),
            f"<h3>{APP_NAME}</h3><p>{summary}</p><p>{version}</p>"
            f"<p>{disclaimer}</p><p><small>{licence}</small></p>",
        )

    # -----------------------------------------------------------------
    # drag and drop, closing
    # -----------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.mimeData().hasUrls() and not self.queue.is_running:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt naming
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.add_paths(paths, explicit=True)
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self.queue.is_running:
            answer = QMessageBox.question(
                self,
                APP_NAME,
                tr("A run is in progress. Cancel it and quit?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.queue.cancel()
        self._save_options()
        self._pump.stop()
        event.accept()
