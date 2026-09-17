# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The BER/DER reader, including the shapes real signing devices produce."""

from __future__ import annotations

import datetime as _dt

import pytest

from p7mmanager.core import asn1


def test_parses_a_sequence_of_integers():
    node = asn1.parse(bytes([0x30, 0x06, 0x02, 0x01, 0x05, 0x02, 0x01, 0x2A]))
    assert node.is_universal(asn1.SEQUENCE)
    assert [asn1.decode_integer(child) for child in node.children] == [5, 42]


def test_long_form_length():
    payload = b"\x00" * 300
    encoded = bytes([0x04, 0x82, 0x01, 0x2C]) + payload
    node = asn1.parse(encoded)
    assert node.length == 300
    assert node.octets() == payload


def test_indefinite_length_and_segmented_octet_string():
    """BER from a signing device: constructed OCTET STRING, no length up front."""
    encoded = bytes([0x24, 0x80]) + b"\x04\x03abc" + b"\x04\x03def" + b"\x00\x00"
    node = asn1.parse(encoded)
    assert node.indefinite
    assert node.octets() == b"abcdef"


def test_missing_end_of_contents_is_an_error():
    with pytest.raises(asn1.Asn1Error):
        asn1.parse(bytes([0x24, 0x80]) + b"\x04\x03abc")


def test_element_longer_than_the_buffer_is_an_error():
    with pytest.raises(asn1.Asn1Error):
        asn1.parse(bytes([0x04, 0x20, 0x01, 0x02]))


def test_decode_oid():
    # 1.2.840.113549.1.7.2 — signedData
    encoded = bytes([0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])
    assert asn1.decode_oid(asn1.parse(encoded)) == "1.2.840.113549.1.7.2"


def test_negative_integer():
    assert asn1.decode_integer(asn1.parse(bytes([0x02, 0x01, 0xFF]))) == -1


@pytest.mark.parametrize(
    "encoded, expected",
    [
        (b"\x17\x0d260917153522Z", _dt.datetime(2026, 9, 17, 15, 35, 22)),
        (b"\x18\x0f20260917153522Z", _dt.datetime(2026, 9, 17, 15, 35, 22)),
        (b"\x17\x0b2609171535Z", _dt.datetime(2026, 9, 17, 15, 35, 0)),
    ],
)
def test_decode_time(encoded, expected):
    value = asn1.decode_time(asn1.parse(encoded))
    assert value == expected.replace(tzinfo=_dt.timezone.utc)


def test_decode_time_with_offset():
    value = asn1.decode_time(asn1.parse(b"\x18\x1320260917153522+0200"))
    assert value == _dt.datetime(2026, 9, 17, 13, 35, 22, tzinfo=_dt.timezone.utc)


def test_two_digit_year_pivots_at_fifty():
    assert asn1.decode_time(asn1.parse(b"\x17\x0d490101000000Z")).year == 2049
    assert asn1.decode_time(asn1.parse(b"\x17\x0d500101000000Z")).year == 1950


def test_bmp_string_is_decoded_as_utf_16():
    """Qualified certificates name people, and the names carry accents."""
    body = "Città".encode("utf-16-be")
    encoded = bytes([0x1E, len(body)]) + body
    assert asn1.decode_string(asn1.parse(encoded)) == "Città"


def test_nesting_is_bounded():
    """A file that nests forever must raise, not recurse until the stack dies."""
    with pytest.raises(asn1.Asn1Error):
        asn1.parse(b"\x30\x80" * 100 + b"\x00\x00" * 100)
