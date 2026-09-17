# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The queue, as a table.

The model holds the very :class:`~p7mmanager.core.jobs.Job` objects the queue
is working on rather than copies of them, so a worker thread's progress shows
up by emitting ``dataChanged`` on one row — no duplicated state to keep in
step, and no row rebuilt while the user is looking at it.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from ..core.jobs import Job, JobState
from ..i18n import tr, tr_message

__all__ = ["QueueModel", "Column"]

# flatly, as in the stylesheet
_GREEN = QColor("#18bc9c")
_AMBER = QColor("#b9770e")
_RED = QColor("#e74c3c")
_MUTED = QColor("#95a5a6")
_TEXT = QColor("#212529")

_STATE_LABELS = {
    JobState.PENDING: "Queued",
    JobState.RUNNING: "Working",
    JobState.DONE: "Done",
    JobState.WARNING: "Warning",
    JobState.SKIPPED: "Skipped",
    JobState.FAILED: "Failed",
    JobState.CANCELLED: "Cancelled",
}

_STATE_COLOURS = {
    JobState.PENDING: _MUTED,
    JobState.RUNNING: _TEXT,
    JobState.DONE: _GREEN,
    JobState.WARNING: _AMBER,
    JobState.SKIPPED: _AMBER,
    JobState.FAILED: _RED,
    JobState.CANCELLED: _MUTED,
}


class Column:
    NAME = 0
    SIZE = 1
    STATE = 2
    SIGNATURES = 3
    SIGNER = 4
    CONTENT = 5
    OUTPUT = 6
    COUNT = 7


_HEADERS = {
    Column.NAME: "File",
    Column.SIZE: "Size",
    Column.STATE: "Status",
    Column.SIGNATURES: "Signatures",
    Column.SIGNER: "Signer",
    Column.CONTENT: "Content",
    Column.OUTPUT: "Output",
}


def human_size(size: int) -> str:
    """``1707`` -> ``1,7 kB``. Decimal units, as every file manager shows."""
    if size < 1000:
        return f"{size} B"
    for unit in ("kB", "MB", "GB"):
        size /= 1000.0
        if size < 1000 or unit == "GB":
            return f"{size:.1f} {unit}".replace(".", ",")
    return f"{size:.1f} GB"  # pragma: no cover - unreachable


class QueueModel(QAbstractTableModel):
    """A read-only table over the queue's jobs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._jobs: list[Job] = []

    # -- Qt interface --------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._jobs)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else Column.COUNT

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return tr(_HEADERS.get(section, ""))
        return section + 1

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        job = self._jobs[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._text(job, column)
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(job)
        if role == Qt.ItemDataRole.ForegroundRole:
            if column == Column.STATE:
                return _STATE_COLOURS.get(job.state, _TEXT)
            if job.state in (JobState.CANCELLED, JobState.PENDING):
                return _MUTED
            return None
        if role == Qt.ItemDataRole.FontRole and column == Column.STATE:
            font = QFont()
            font.setBold(job.state in (JobState.FAILED, JobState.WARNING))
            return font
        if role == Qt.ItemDataRole.TextAlignmentRole and column in (
            Column.SIZE,
            Column.SIGNATURES,
        ):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.UserRole:
            return job
        return None

    # -- contents ------------------------------------------------------
    def _text(self, job: Job, column: int) -> str:
        if column == Column.NAME:
            return job.name
        if column == Column.SIZE:
            return human_size(job.size)
        if column == Column.STATE:
            label = tr(_STATE_LABELS.get(job.state, ""))
            if job.state.is_final and job.message:
                return f"{label} — {tr_message(job.message)}"
            return label
        if column == Column.SIGNATURES:
            return str(job.signature_count) if job.result else ""
        if column == Column.SIGNER:
            return job.signers
        if column == Column.CONTENT:
            if job.result and job.result.analysis.payload_kind:
                return tr(job.result.analysis.payload_kind.label)
            return ""
        if column == Column.OUTPUT:
            output = job.output_path
            return output.name if output else ""
        return ""

    def _tooltip(self, job: Job) -> str:
        lines = [str(job.path)]
        if job.message:
            lines.append(tr_message(job.message))
        if job.result:
            for warning in job.result.analysis.warnings:
                lines.append("⚠ " + tr_message(warning))
            if job.output_path:
                lines.append("→ " + str(job.output_path))
        return "\n".join(lines)

    # -- updates -------------------------------------------------------
    def set_jobs(self, jobs: list[Job]) -> None:
        self.beginResetModel()
        self._jobs = list(jobs)
        self.endResetModel()

    def job_at(self, row: int) -> Job | None:
        if 0 <= row < len(self._jobs):
            return self._jobs[row]
        return None

    def row_of(self, job: Job) -> int:
        for row, candidate in enumerate(self._jobs):
            if candidate.id == job.id:
                return row
        return -1

    def job_changed(self, job: Job) -> None:
        """Repaint the row of a job a worker has just touched."""
        row = self.row_of(job)
        if row < 0:
            return
        self.dataChanged.emit(
            self.index(row, 0), self.index(row, Column.COUNT - 1)
        )

    def retranslate(self) -> None:
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, Column.COUNT - 1)
        if self._jobs:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._jobs) - 1, Column.COUNT - 1)
            )
