# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.

"""Integrity and RSA verification — the two claims the tool actually makes."""

from __future__ import annotations

from p7mmanager.core import cms, verify
from p7mmanager.core.analyzer import analyse

from .conftest import requires_openssl


@requires_openssl
def test_a_good_signature_verifies(signed_pdf):
    signed = cms.parse_signed_data(signed_pdf.read_bytes())
    verify.verify_signed_data(signed)
    signer = signed.signers[0]
    assert signer.digest_matches is True
    assert signer.signature_valid is True
    assert signer.verification_note == ""


@requires_openssl
def test_sha512_signature_verifies(signed_sha512):
    signed = cms.parse_signed_data(signed_sha512.read_bytes())
    verify.verify_signed_data(signed)
    assert signed.signers[0].signature_valid is True


@requires_openssl
def test_both_signers_verify(signed_twice):
    signed = cms.parse_signed_data(signed_twice.read_bytes())
    verify.verify_signed_data(signed)
    assert all(signer.signature_valid for signer in signed.signers)
    assert all(signer.digest_matches for signer in signed.signers)


@requires_openssl
def test_tampering_with_the_document_is_caught(tmp_path, signed_pdf):
    """Flip one byte of the enclosed PDF: the digest must stop matching."""
    data = bytearray(signed_pdf.read_bytes())
    marker = data.find(b"%PDF-1.4")
    assert marker > 0
    data[marker + 7] = ord("7")  # %PDF-1.4 -> %PDF-1.7
    target = tmp_path / "manomesso.pdf.p7m"
    target.write_bytes(bytes(data))

    analysis = analyse(target)
    assert analysis.integrity is False
    assert analysis.outcome.value == "error"
    assert "does not match" in analysis.signers[0].verification_note


@requires_openssl
def test_tampering_with_the_signature_is_caught(tmp_path, signed_pdf):
    """Corrupt the signature bytes themselves: the RSA check must fail."""
    signed = cms.parse_signed_data(signed_pdf.read_bytes())
    original = signed.signers[0].signature
    data = bytearray(signed_pdf.read_bytes())
    position = bytes(data).find(original)
    assert position > 0
    data[position + 10] ^= 0xFF
    target = tmp_path / "firma-rotta.pdf.p7m"
    target.write_bytes(bytes(data))

    analysis = analyse(target)
    assert analysis.signatures_valid is False
    assert analysis.integrity is True  # the document itself is untouched


@requires_openssl
def test_detached_signature_reports_what_it_could_not_check(signed_detached):
    analysis = analyse(signed_detached)
    assert analysis.integrity is None
    assert analysis.detached is True
    assert "detached" in analysis.signers[0].verification_note


@requires_openssl
def test_verification_can_be_skipped(signed_pdf):
    analysis = analyse(signed_pdf, verify=False)
    assert analysis.signature_count == 1
    assert analysis.integrity is None
    assert analysis.signatures_valid is None


def test_digest_helper_knows_its_algorithms():
    assert verify.digest_for("sha256", b"") is not None
    assert verify.digest_for("sha256WithRSA", b"abc") == verify.digest_for("sha256", b"abc")
    assert verify.digest_for("whirlpool", b"abc") is None
