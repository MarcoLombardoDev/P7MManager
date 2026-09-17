# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The console tool, including the behaviour it inherits from the scripts."""

from __future__ import annotations

import shutil

import pytest

from p7mmanager.cli import main

from .conftest import requires_openssl


@requires_openssl
def test_a_folder_is_processed_and_reported(capsys, tmp_path, container_tree):
    output = tmp_path / "out"
    code = main([str(container_tree), "-r", "-o", str(output)])
    captured = capsys.readouterr().out

    assert code == 0
    assert "OK" in captured
    assert "3 file(s): 2 extracted, 1 with warnings, 0 failed" in captured
    assert (output / "contratto.pdf").exists()


@requires_openssl
def test_the_detailed_table_has_a_header(capsys, container_tree):
    main([str(container_tree), "-r", "-d", "-n"])
    captured = capsys.readouterr().out

    assert "FileName" in captured
    assert "OutputFile" in captured
    assert "contratto.pdf.p7m" in captured
    assert "Marco Lombardo" in captured


@requires_openssl
def test_without_recurse_only_the_top_folder_is_read(capsys, container_tree):
    main([str(container_tree), "-n"])
    captured = capsys.readouterr().out

    assert "contratto.pdf.p7m" in captured
    assert "fattura.xml.p7m" not in captured


@requires_openssl
def test_analyse_only_writes_nothing(capsys, tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    shutil.copy(signed_pdf, source)

    main([str(tmp_path), "-n"])

    assert [item.name for item in tmp_path.iterdir()] == ["doc.pdf.p7m"]
    assert "analysed" in capsys.readouterr().out


@requires_openssl
def test_quiet_only_prints_what_needs_attention(capsys, container_tree):
    main([str(container_tree), "-r", "-n", "-q"])
    captured = capsys.readouterr().out

    assert "contratto.pdf.p7m" not in captured
    assert "staccata.pdf.p7m" in captured


@requires_openssl
def test_reports_are_written_when_asked(tmp_path, container_tree):
    csv_path = tmp_path / "r.csv"
    json_path = tmp_path / "r.json"

    code = main([str(container_tree), "-r", "-n", "--csv", str(csv_path),
                 "--json", str(json_path)])

    assert code == 0
    assert csv_path.exists() and json_path.exists()
    assert "contratto.pdf.p7m" in csv_path.read_text(encoding="utf-8-sig")


def test_an_empty_folder_says_so(capsys, tmp_path):
    code = main([str(tmp_path)])
    assert code == 1
    assert "No .p7m file found" in capsys.readouterr().out


def test_a_damaged_file_sets_a_failing_exit_code(capsys, tmp_path):
    (tmp_path / "rotto.p7m").write_bytes(b"\x30\x82\xff\xff spazzatura")
    code = main([str(tmp_path), "-n"])
    assert code == 3
    assert "ERROR" in capsys.readouterr().out


@requires_openssl
def test_mirror_recreates_the_tree(tmp_path, container_tree):
    output = tmp_path / "specchio"
    main([str(container_tree), "-r", "-o", str(output), "--mirror"])
    assert (output / "2026" / "gennaio" / "fattura.xml").exists()


@requires_openssl
def test_skip_existing_leaves_the_file_alone(tmp_path, signed_pdf):
    source = tmp_path / "doc.pdf.p7m"
    shutil.copy(signed_pdf, source)
    (tmp_path / "doc.pdf").write_bytes(b"gia' presente")

    main([str(tmp_path), "--skip-existing"])

    assert (tmp_path / "doc.pdf").read_bytes() == b"gia' presente"


def test_help_mentions_the_limits_of_the_check(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "not a legal validation" in capsys.readouterr().out
