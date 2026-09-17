# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The window, driven the way a user drives it.

Run against the offscreen platform plugin, so these are real widgets, a real
queue and real worker threads — only the display is missing.
"""

from __future__ import annotations

import time

import pytest

from .conftest import requires_openssl

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from p7mmanager.core.extractor import Destination  # noqa: E402
from p7mmanager.core.jobs import JobState  # noqa: E402
from p7mmanager.i18n import Language, set_language  # noqa: E402
from p7mmanager.ui.main_window import MainWindow  # noqa: E402
from p7mmanager.ui.queue_model import Column, human_size  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(qapp, tmp_path):
    window = MainWindow()
    yield window
    window.queue.cancel()
    window.close()


def _run_to_completion(qapp, window, timeout: float = 60.0) -> None:
    """Start the queue and pump the event loop until the run is over."""
    window._start()
    deadline = time.time() + timeout
    while window.queue.is_running and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    for _ in range(10):  # let the last events through the timer's queue
        window._drain_events()
        qapp.processEvents()
    assert not window.queue.is_running, "the run did not finish in time"


def test_an_empty_window_says_what_to_do(window):
    assert window.model.rowCount() == 0
    assert "begin" in window.status.currentMessage()
    assert window.action_start.isEnabled() is False


@requires_openssl
def test_adding_a_folder_fills_the_queue(window, container_tree):
    added = window.add_paths([container_tree])

    assert added == 3
    assert window.model.rowCount() == 3
    assert window.action_start.isEnabled() is True


@requires_openssl
def test_a_non_container_file_is_ignored_when_a_folder_is_added(window, container_tree):
    window.add_paths([container_tree])
    names = {
        window.model.index(row, Column.NAME).data()
        for row in range(window.model.rowCount())
    }
    assert "lettera.txt" not in names


@requires_openssl
def test_running_the_queue_extracts_and_reports(qapp, window, container_tree, tmp_path):
    output = tmp_path / "estratti"
    window.add_paths([container_tree])
    window.destination_combo.setCurrentIndex(
        window.destination_combo.findData(Destination.SINGLE_FOLDER.value)
    )
    window.output_edit.setText(str(output))

    _run_to_completion(qapp, window)

    states = {job.name: job.state for job in window.queue.jobs}
    assert states["contratto.pdf.p7m"] is JobState.DONE
    assert states["fattura.xml.p7m"] is JobState.DONE
    assert states["staccata.pdf.p7m"] is JobState.WARNING
    assert sorted(item.name for item in output.iterdir()) == [
        "contratto.pdf",
        "fattura.xml",
    ]
    assert "Finished" in window.status.currentMessage()
    assert window.progress.value() == 100


@requires_openssl
def test_the_table_shows_the_signer_and_the_result(qapp, window, container_tree):
    window.add_paths([container_tree])
    window.analyse_only_check.setChecked(True)
    _run_to_completion(qapp, window)

    row = next(
        row
        for row in range(window.model.rowCount())
        if window.model.index(row, Column.NAME).data() == "contratto.pdf.p7m"
    )
    assert window.model.index(row, Column.SIGNER).data() == "Marco Lombardo"
    assert window.model.index(row, Column.SIGNATURES).data() == "1"
    assert window.model.index(row, Column.CONTENT).data() == "PDF document"
    assert "Done" in window.model.index(row, Column.STATE).data()


@requires_openssl
def test_selecting_a_row_shows_the_details(qapp, window, container_tree):
    window.add_paths([container_tree])
    window.analyse_only_check.setChecked(True)
    _run_to_completion(qapp, window)

    window.table.selectRow(0)
    qapp.processEvents()
    html = window.details.toPlainText()

    assert window.details.job is not None
    assert "Marco Lombardo" in html
    assert "not a legal validation" in html


@requires_openssl
def test_the_details_panel_states_what_was_checked(qapp, window, container_tree):
    window.add_paths([container_tree])
    window.analyse_only_check.setChecked(True)
    _run_to_completion(qapp, window)

    row = next(
        row
        for row in range(window.model.rowCount())
        if window.model.index(row, Column.NAME).data() == "contratto.pdf.p7m"
    )
    window.table.selectRow(row)
    qapp.processEvents()
    text = window.details.toPlainText()

    assert "Content matches the signed digest" in text
    assert "Signature matches the certificate's key" in text
    assert "TINIT-AAABBB80A01H501U" in text


@requires_openssl
def test_removing_and_clearing(qapp, window, container_tree):
    window.add_paths([container_tree])
    window.table.selectRow(0)
    window._remove_selected()
    assert window.model.rowCount() == 2

    window._clear(False)
    assert window.model.rowCount() == 0
    assert window.action_start.isEnabled() is False


@requires_openssl
def test_the_report_can_be_exported(qapp, window, container_tree, tmp_path):
    from p7mmanager.core.report import write_csv

    window.add_paths([container_tree])
    window.analyse_only_check.setChecked(True)
    _run_to_completion(qapp, window)

    target = write_csv(window.queue.jobs, tmp_path / "report.csv")
    assert "contratto.pdf.p7m" in target.read_text(encoding="utf-8-sig")


@requires_openssl
def test_options_are_remembered(qapp, window, tmp_path):
    window.output_edit.setText(str(tmp_path))
    window.workers_spin.setValue(7)
    window.recursive_check.setChecked(False)
    window._save_options()

    reopened = MainWindow()
    try:
        assert reopened.output_edit.text() == str(tmp_path)
        assert reopened.workers_spin.value() == 7
        assert reopened.recursive_check.isChecked() is False
    finally:
        reopened.close()


def test_switching_language_retranslates_the_window(window):
    window._set_language(Language.ITALIAN)
    try:
        assert window.action_add_files.text() == "Aggiungi file"
        assert window.options_box.title() == "Opzioni"
        assert window.model.headerData(
            Column.STATE, Qt.Orientation.Horizontal
        ) == "Stato"
    finally:
        set_language(Language.ENGLISH)


def test_human_size_uses_decimal_units():
    assert human_size(900) == "900 B"
    assert human_size(1707) == "1,7 kB"
    assert human_size(5_400_000) == "5,4 MB"
