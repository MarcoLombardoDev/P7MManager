# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Reading real containers: one signature, two, detached, nested, armoured."""

from __future__ import annotations

import datetime as _dt

import pytest

from p7mmanager.core import analyzer, cms
from p7mmanager.core.analyzer import ContainerEncoding, analyse

from .conftest import PDF_BYTES, requires_openssl


@requires_openssl
def test_one_signature_over_a_pdf(signed_pdf):
    signed = cms.parse_signed_data(signed_pdf.read_bytes())
    assert signed.content == PDF_BYTES
    assert signed.detached is False
    assert signed.signature_count == 1
    assert signed.certificates

    signer = signed.signers[0]
    assert signer.certificate is not None
    assert signer.certificate.subject.common_name == "Marco Lombardo"
    assert signer.certificate.subject.get("serialNumber") == "TINIT-AAABBB80A01H501U"
    assert signer.digest_algorithm == "sha256"
    assert isinstance(signer.signing_time, _dt.datetime)
    assert signer.message_digest is not None


@requires_openssl
def test_digest_algorithm_is_read_from_the_file(signed_sha512):
    signed = cms.parse_signed_data(signed_sha512.read_bytes())
    assert signed.digest_algorithms == ["sha512"]
    assert signed.signers[0].digest_algorithm == "sha512"


@requires_openssl
def test_detached_signature_has_no_content(signed_detached):
    signed = cms.parse_signed_data(signed_detached.read_bytes())
    assert signed.detached is True
    assert signed.content is None
    assert signed.signers[0].certificate is not None


@requires_openssl
def test_two_signatures_are_both_reported(signed_twice):
    signed = cms.parse_signed_data(signed_twice.read_bytes())
    assert signed.signature_count == 2
    names = sorted(signer.display_name for signer in signed.signers)
    assert names == ["Giulia Rossi", "Marco Lombardo"]


@requires_openssl
def test_base64_armoured_container_is_decoded(signed_base64):
    data = signed_base64.read_bytes()
    assert data.startswith(b"-----BEGIN")
    der, encoding = analyzer.decode_container(data)
    assert encoding is ContainerEncoding.PEM
    assert cms.parse_signed_data(der).content == PDF_BYTES


@requires_openssl
def test_base64_without_pem_banners_is_decoded(tmp_path, signed_pdf):
    import base64

    target = tmp_path / "nudo.pdf.p7m"
    target.write_bytes(base64.encodebytes(signed_pdf.read_bytes()))
    analysis = analyse(target)
    assert analysis.encoding is ContainerEncoding.BASE64
    assert analysis.payload == PDF_BYTES


@requires_openssl
def test_nested_envelope_is_unwrapped_to_the_document(signed_nested):
    analysis = analyse(signed_nested)
    assert analysis.nesting == 2
    assert analysis.payload == PDF_BYTES
    assert analysis.payload_kind.key == "pdf"
    assert analysis.signature_count == 2


def test_something_that_is_not_cms_is_rejected():
    with pytest.raises(cms.CmsError):
        cms.parse_signed_data(b"questo non e' un contenitore firmato")


def test_enveloped_data_is_named_in_the_error():
    """An encrypted container is not a failure to parse: say what it is."""
    # ContentInfo { contentType = envelopedData, [0] { SEQUENCE {} } }
    encoded = bytes.fromhex("300f06092a864886f70d010703a0023000")
    with pytest.raises(cms.CmsError) as error:
        cms.parse_signed_data(encoded)
    assert "envelopedData" in str(error.value)


@requires_openssl
def test_looks_like_cms_accepts_real_files_and_rejects_pdfs(signed_pdf):
    assert cms.looks_like_cms(signed_pdf.read_bytes())
    assert not cms.looks_like_cms(PDF_BYTES)
