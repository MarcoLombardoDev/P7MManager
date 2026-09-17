# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Writing the document out: where it lands, and what happens to the original."""

from __future__ import annotations

from p7mmanager.core.analyzer import analyse
from p7mmanager.core.extractor import (
    Conflict,
    Destination,
    ExtractionSettings,
    extract,
)
from p7mmanager.core.scanner import scan

from .conftest import PDF_BYTES, XML_BYTES, requires_openssl


@requires_openssl
def test_extracts_beside_the_original(tmp_path, signed_pdf):
    source = tmp_path / "contratto.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())

    result = extract(source)

    assert result.written is True
    assert result.output_path == tmp_path / "contratto.pdf"
    assert result.output_path.read_bytes() == PDF_BYTES
    assert source.read_bytes() == signed_pdf.read_bytes(), "the container is read-only"


@requires_openssl
def test_extracts_xml_under_its_own_name(tmp_path, signed_xml):
    source = tmp_path / "fattura.xml.p7m"
    source.write_bytes(signed_xml.read_bytes())
    result = extract(source)
    assert result.output_path.name == "fattura.xml"
    assert result.output_path.read_bytes() == XML_BYTES


@requires_openssl
def test_rename_keeps_both_copies(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())
    settings = ExtractionSettings(conflict=Conflict.RENAME)

    first = extract(source, settings)
    second = extract(source, settings)

    assert first.output_path.name == "doc.pdf"
    assert second.output_path.name == "doc (2).pdf"


@requires_openssl
def test_skip_leaves_the_existing_file_alone(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())
    (tmp_path / "doc.pdf").write_bytes(b"gia' presente")

    result = extract(source, ExtractionSettings(conflict=Conflict.SKIP))

    assert result.skipped is True
    assert result.written is False
    assert (tmp_path / "doc.pdf").read_bytes() == b"gia' presente"


@requires_openssl
def test_overwrite_replaces_it(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())
    (tmp_path / "doc.pdf").write_bytes(b"vecchio")

    result = extract(source, ExtractionSettings(conflict=Conflict.OVERWRITE))

    assert result.written is True
    assert (tmp_path / "doc.pdf").read_bytes() == PDF_BYTES


@requires_openssl
def test_mirror_recreates_the_folder_structure(tmp_path, container_tree):
    output = tmp_path / "estratti"
    settings = ExtractionSettings(
        destination=Destination.MIRROR_TREE, output_dir=output, root_dir=container_tree
    )
    for path in scan([container_tree]):
        extract(path, settings)

    assert (output / "contratto.pdf").exists()
    assert (output / "2026" / "gennaio" / "fattura.xml").exists()
    assert not (output / "2026" / "febbraio" / "staccata.pdf").exists()


@requires_openssl
def test_single_folder_puts_everything_together(tmp_path, container_tree):
    output = tmp_path / "tutti"
    settings = ExtractionSettings(
        destination=Destination.SINGLE_FOLDER, output_dir=output
    )
    for path in scan([container_tree]):
        extract(path, settings)

    names = sorted(item.name for item in output.iterdir())
    assert names == ["contratto.pdf", "fattura.xml"]


@requires_openssl
def test_detached_signature_writes_nothing(tmp_path, signed_detached):
    source = tmp_path / "staccata.pdf.p7m"
    source.write_bytes(signed_detached.read_bytes())

    result = extract(source)

    assert result.written is False
    assert result.outcome.value == "warning"
    assert list(tmp_path.iterdir()) == [source]


@requires_openssl
def test_analyse_only_writes_nothing(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())

    result = extract(source, ExtractionSettings(analyse_only=True))

    assert result.written is False
    assert result.outcome.value == "ok"
    assert result.analysis.signature_count == 1
    assert list(tmp_path.iterdir()) == [source]


def test_a_damaged_container_is_an_error_not_a_crash(tmp_path):
    source = tmp_path / "rotto.pdf.p7m"
    source.write_bytes(b"\x30\x82\xff\xff non e' un contenitore")

    result = extract(source)

    assert result.outcome.value == "error"
    assert result.written is False
    assert result.message


def test_a_pdf_is_recovered_from_a_container_that_cannot_be_parsed(tmp_path):
    """What the scripts this replaces did for every file, kept as a fallback."""
    source = tmp_path / "strano.pdf.p7m"
    source.write_bytes(b"\x01\x02rumore" + PDF_BYTES + b"coda")

    result = extract(source)

    assert result.written is True
    # The scan cuts from %PDF to the last %%EOF, so the trailing newline of the
    # original is not part of what is recovered — the PDF itself is complete.
    assert result.output_path.read_bytes() == PDF_BYTES.rstrip(b"\n")
    assert result.analysis.recovered_by_scan is True
    assert result.outcome.value == "warning"


def test_a_missing_file_is_reported(tmp_path):
    result = extract(tmp_path / "non-esiste.p7m")
    assert result.outcome.value == "error"
    assert "not accessible" in result.message


@requires_openssl
def test_no_partial_file_is_left_when_writing_fails(tmp_path, signed_pdf, monkeypatch):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())

    def explode(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("p7mmanager.core.extractor.os.replace", explode)
    result = extract(source)

    assert result.written is False
    assert "write failed" in result.message
    assert [item.name for item in tmp_path.iterdir()] == ["doc.pdf.p7m"]


@requires_openssl
def test_the_analysis_can_be_reused(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    source.write_bytes(signed_pdf.read_bytes())
    analysis = analyse(source)

    result = extract(source, analysis=analysis)

    assert result.analysis is analysis
    assert result.written is True
