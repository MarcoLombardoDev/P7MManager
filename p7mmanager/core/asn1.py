# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Minimal BER/DER reader used to inspect CMS (PKCS#7) and X.509 structures.

The parser is intentionally self contained: P7M Manager must run on a plain
Python installation (no pip install, no OpenSSL), which is the common case on
locked down corporate desktops.

It accepts BER as well as DER because real world CAdES files produced by some
signing devices use indefinite lengths and segmented OCTET STRINGs.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterator
from dataclasses import dataclass, field

__all__ = [
    "Asn1Error",
    "Node",
    "parse",
    "parse_all",
    "decode_oid",
    "decode_integer",
    "decode_string",
    "decode_time",
    "decode_bitstring",
]

# Tag classes
UNIVERSAL = 0
APPLICATION = 1
CONTEXT = 2
PRIVATE = 3

# Universal tag numbers we care about
BOOLEAN = 0x01
INTEGER = 0x02
BIT_STRING = 0x03
OCTET_STRING = 0x04
NULL = 0x05
OID = 0x06
UTF8_STRING = 0x0C
SEQUENCE = 0x10
SET = 0x11
NUMERIC_STRING = 0x12
PRINTABLE_STRING = 0x13
T61_STRING = 0x14
IA5_STRING = 0x16
UTC_TIME = 0x17
GENERALIZED_TIME = 0x18
UNIVERSAL_STRING = 0x1C
BMP_STRING = 0x1E

_MAX_DEPTH = 60

_STRING_TAGS = {
    UTF8_STRING: "utf-8",
    PRINTABLE_STRING: "ascii",
    NUMERIC_STRING: "ascii",
    IA5_STRING: "ascii",
    T61_STRING: "latin-1",
    UNIVERSAL_STRING: "utf-32-be",
    BMP_STRING: "utf-16-be",
    OCTET_STRING: "utf-8",
}


class Asn1Error(ValueError):
    """Raised when a byte stream is not valid BER/DER."""


@dataclass
class Node:
    """A single TLV element.

    ``start``/``end`` delimit the whole encoding inside ``buf`` while
    ``content_start``/``content_end`` delimit the value only.
    """

    buf: bytes
    cls: int
    constructed: bool
    tag: int
    start: int
    content_start: int
    content_end: int
    end: int
    indefinite: bool = False
    children: list[Node] = field(default_factory=list)

    # -- raw access ---------------------------------------------------
    @property
    def content(self) -> bytes:
        return self.buf[self.content_start : self.content_end]

    @property
    def raw(self) -> bytes:
        return self.buf[self.start : self.end]

    @property
    def length(self) -> int:
        return self.content_end - self.content_start

    # -- helpers ------------------------------------------------------
    def is_universal(self, tag: int) -> bool:
        return self.cls == UNIVERSAL and self.tag == tag

    def is_context(self, tag: int) -> bool:
        return self.cls == CONTEXT and self.tag == tag

    def child(self, index: int) -> Node:
        try:
            return self.children[index]
        except IndexError as exc:  # pragma: no cover - defensive
            raise Asn1Error(f"missing child #{index}") from exc

    def find_context(self, tag: int) -> Node | None:
        for node in self.children:
            if node.is_context(tag):
                return node
        return None

    def walk(self) -> Iterator[Node]:
        yield self
        for child in self.children:
            yield from child.walk()

    def octets(self) -> bytes:
        """Value of an OCTET STRING, joining BER segments when needed."""
        if not self.constructed:
            return self.content
        out = bytearray()
        for child in self.children:
            out += child.octets()
        return bytes(out)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        kind = {UNIVERSAL: "U", APPLICATION: "A", CONTEXT: "C", PRIVATE: "P"}[self.cls]
        return f"<Node {kind}{self.tag:#x} len={self.length} kids={len(self.children)}>"


def _read_identifier(buf: bytes, i: int) -> tuple:
    if i >= len(buf):
        raise Asn1Error("truncated identifier octet")
    first = buf[i]
    cls = first >> 6
    constructed = bool(first & 0x20)
    tag = first & 0x1F
    i += 1
    if tag == 0x1F:  # high tag number form
        tag = 0
        for _ in range(4):
            if i >= len(buf):
                raise Asn1Error("truncated high tag number")
            byte = buf[i]
            i += 1
            tag = (tag << 7) | (byte & 0x7F)
            if not byte & 0x80:
                break
        else:
            raise Asn1Error("tag number too long")
    return cls, constructed, tag, i


def _read_length(buf: bytes, i: int) -> tuple:
    if i >= len(buf):
        raise Asn1Error("truncated length octet")
    first = buf[i]
    i += 1
    if first < 0x80:
        return first, i, False
    if first == 0x80:
        return -1, i, True  # indefinite, terminated by end-of-contents
    count = first & 0x7F
    if count > 6:
        raise Asn1Error("unsupported length field size")
    if i + count > len(buf):
        raise Asn1Error("truncated length value")
    value = int.from_bytes(buf[i : i + count], "big")
    return value, i + count, False


def parse(buf: bytes, offset: int = 0, depth: int = 0) -> Node:
    """Parse one TLV starting at ``offset``."""
    if depth > _MAX_DEPTH:
        raise Asn1Error("structure nested too deeply")
    start = offset
    cls, constructed, tag, i = _read_identifier(buf, offset)
    length, i, indefinite = _read_length(buf, i)
    content_start = i

    if indefinite:
        if not constructed:
            raise Asn1Error("indefinite length on a primitive element")
        children: list[Node] = []
        while True:
            if i + 1 >= len(buf):
                raise Asn1Error("missing end-of-contents marker")
            if buf[i] == 0x00 and buf[i + 1] == 0x00:
                content_end = i
                end = i + 2
                break
            child = parse(buf, i, depth + 1)
            children.append(child)
            i = child.end
        return Node(buf, cls, constructed, tag, start, content_start, content_end,
                    end, True, children)

    content_end = content_start + length
    if content_end > len(buf):
        raise Asn1Error("element longer than the available data")

    node = Node(buf, cls, constructed, tag, start, content_start, content_end, content_end)
    if constructed:
        node.children = parse_all(buf, content_start, content_end, depth + 1)
    return node


def parse_all(buf: bytes, start: int, end: int, depth: int = 0) -> list[Node]:
    """Parse every TLV in ``buf[start:end]``."""
    nodes: list[Node] = []
    i = start
    while i < end:
        node = parse(buf, i, depth)
        if node.end <= i:  # pragma: no cover - defensive
            raise Asn1Error("zero length element")
        nodes.append(node)
        i = node.end
    return nodes


# ---------------------------------------------------------------------
# value decoders
# ---------------------------------------------------------------------

def decode_oid(node: Node) -> str:
    data = node.content
    if not data:
        raise Asn1Error("empty OBJECT IDENTIFIER")
    first = data[0]
    parts = [str(first // 40), str(first % 40)]
    value = 0
    for byte in data[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(value))
            value = 0
    return ".".join(parts)


def decode_integer(node: Node) -> int:
    if not node.content:
        return 0
    return int.from_bytes(node.content, "big", signed=True)


def decode_string(node: Node) -> str:
    encoding = _STRING_TAGS.get(node.tag, "utf-8") if node.cls == UNIVERSAL else "utf-8"
    data = node.octets() if node.constructed else node.content
    try:
        return data.decode(encoding).strip()
    except (UnicodeDecodeError, LookupError):
        return data.decode("latin-1", "replace").strip()


def decode_bitstring(node: Node) -> bytes:
    """Return the payload of a BIT STRING, dropping the unused-bits octet."""
    data = node.octets() if node.constructed else node.content
    if not data:
        return b""
    return data[1:]


def decode_time(node: Node) -> _dt.datetime | None:
    """Decode UTCTime/GeneralizedTime into an aware datetime (UTC)."""
    text = node.content.decode("ascii", "replace").strip()
    if not text:
        return None
    tz = _dt.timezone.utc
    offset = _dt.timedelta(0)
    if text.endswith("Z"):
        text = text[:-1]
    elif len(text) > 5 and text[-5] in "+-":
        sign = 1 if text[-5] == "+" else -1
        try:
            offset = sign * _dt.timedelta(hours=int(text[-4:-2]), minutes=int(text[-2:]))
        except ValueError:
            return None
        text = text[:-5]
    fractional = ""
    if "." in text:
        text, fractional = text.split(".", 1)
        fractional = "".join(ch for ch in fractional if ch.isdigit())[:6]

    if node.tag == UTC_TIME or (len(text) in (10, 12) and node.tag != GENERALIZED_TIME):
        if len(text) == 10:
            text += "00"
        if len(text) != 12:
            return None
        year = int(text[:2])
        year += 2000 if year < 50 else 1900
        rest = text[2:]
    else:
        if len(text) == 10:
            text += "00"
        if len(text) == 12:
            text += "00"
        if len(text) != 14:
            return None
        year = int(text[:4])
        rest = text[4:]
    try:
        value = _dt.datetime(
            year,
            int(rest[0:2]),
            int(rest[2:4]),
            int(rest[4:6]),
            int(rest[6:8]),
            int(rest[8:10]) if len(rest) >= 10 else 0,
            int(fractional.ljust(6, "0")) if fractional else 0,
            tzinfo=tz,
        )
    except ValueError:
        return None
    return value - offset
