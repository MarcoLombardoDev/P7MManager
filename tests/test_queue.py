# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

"""The execution queue: scanning, running, cancelling, reporting."""

from __future__ import annotations

import shutil

from p7mmanager.core.extractor import Destination, ExtractionSettings
from p7mmanager.core.jobs import JobQueue
from p7mmanager.core.report import COLUMNS, as_dicts, write_csv, write_json
from p7mmanager.core.scanner import scan

from .conftest import requires_openssl


@requires_openssl
def test_scan_finds_containers_and_ignores_other_files(container_tree):
    found = scan([container_tree])
    names = sorted(path.name for path in found)
    assert names == ["contratto.pdf.p7m", "fattura.xml.p7m", "staccata.pdf.p7m"]


@requires_openssl
def test_scan_can_stay_in_the_top_folder(container_tree):
    found = scan([container_tree], recursive=False)
    assert [path.name for path in found] == ["contratto.pdf.p7m"]


@requires_openssl
def test_an_explicit_file_is_taken_even_without_the_extension(container_tree):
    letter = container_tree / "2026" / "lettera.txt"
    assert scan([letter]) == []
    assert scan([letter], include_all_files=True) == [letter]


@requires_openssl
def test_the_same_file_is_not_queued_twice(container_tree):
    queue = JobQueue()
    first = queue.add(scan([container_tree]))
    second = queue.add(scan([container_tree]))
    assert len(first) == 3
    assert second == []
    assert len(queue.jobs) == 3


@requires_openssl
def test_a_run_processes_every_file(tmp_path, container_tree):
    output = tmp_path / "out"
    queue = JobQueue(workers=4)
    queue.add(scan([container_tree]))
    assert queue.start(
        ExtractionSettings(destination=Destination.SINGLE_FOLDER, output_dir=output)
    )
    assert queue.wait(60)

    counts = queue.counts()
    assert counts["done"] == 2          # the pdf and the xml
    assert counts["warning"] == 1       # the detached signature
    assert counts["failed"] == 0
    assert not queue.is_running


@requires_openssl
def test_events_describe_the_run(tmp_path, container_tree):
    events = []
    queue = JobQueue(listener=events.append, workers=2)
    queue.add(scan([container_tree]))
    queue.start(ExtractionSettings(analyse_only=True))
    queue.wait(60)

    kinds = [event.kind for event in events]
    assert kinds.count("added") == 1
    assert kinds.count("started") == 1
    assert kinds.count("finished") == 1
    assert kinds.count("progress") == 3
    finished = [event for event in events if event.kind == "finished"][0]
    assert finished.done == 3
    assert finished.cancelled is False


@requires_openssl
def test_a_broken_listener_does_not_stop_the_queue(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    shutil.copy(signed_pdf, source)

    def explode(event):
        raise RuntimeError("l'ascoltatore e' rotto")

    queue = JobQueue(listener=explode)
    queue.add([source])
    queue.start(ExtractionSettings(analyse_only=True))
    queue.wait(30)
    assert queue.counts()["done"] == 1


@requires_openssl
def test_a_finished_queue_can_be_run_again(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    shutil.copy(signed_pdf, source)
    queue = JobQueue()
    queue.add([source])
    queue.start(ExtractionSettings(analyse_only=True))
    queue.wait(30)

    assert queue.start(ExtractionSettings(analyse_only=True)) is False
    assert queue.start(ExtractionSettings(analyse_only=True), rerun=True) is True
    queue.wait(30)
    assert queue.counts()["done"] == 1


@requires_openssl
def test_cancelling_leaves_the_queue_stopped(tmp_path, signed_pdf):
    for index in range(40):
        shutil.copy(signed_pdf, tmp_path / f"file{index:02d}.pdf.p7m")
    queue = JobQueue(workers=1)
    queue.add(scan([tmp_path]))
    queue.start(ExtractionSettings(analyse_only=True))
    queue.cancel()
    assert queue.wait(60)

    counts = queue.counts()
    assert not queue.is_running
    assert counts["cancelled"] >= 1
    assert counts["pending"] == 0


@requires_openssl
def test_clearing_keeps_what_is_not_finished(tmp_path, container_tree):
    queue = JobQueue()
    queue.add(scan([container_tree]))
    queue.start(ExtractionSettings(analyse_only=True))
    queue.wait(60)

    queue.clear(completed_only=True)
    assert queue.jobs == []


@requires_openssl
def test_report_columns_carry_the_evidence(tmp_path, container_tree):
    queue = JobQueue()
    queue.add(scan([container_tree]))
    queue.start(ExtractionSettings(analyse_only=True))
    queue.wait(60)

    rows = as_dicts(queue.jobs)
    assert {name for row in rows for name in row} == set(COLUMNS)
    signed = [row for row in rows if row["file"] == "contratto.pdf.p7m"][0]
    assert signed["signatures"] == 1
    assert "Marco Lombardo" in signed["signers"]
    assert signed["integrity"] == "ok"
    assert signed["signature_check"] == "ok"
    assert signed["certificate_serial"]

    csv_path = write_csv(queue.jobs, tmp_path / "report.csv")
    text = csv_path.read_text(encoding="utf-8-sig")
    assert text.startswith("file;folder;size")
    assert "contratto.pdf.p7m" in text

    json_path = write_json(queue.jobs, tmp_path / "report.json")
    import json

    document = json.loads(json_path.read_text(encoding="utf-8"))
    assert document["tool"] == "P7M Manager"
    assert "not a legal validation" in document["note"]
    assert len(document["files"]) == 3
