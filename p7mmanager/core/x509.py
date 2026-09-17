# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""X.509 certificate reader built on top of the local ASN.1 parser."""

from __future__ import annotations

import datetime as _dt
import hashlib
from contextlib import suppress
from dataclasses import dataclass, field

from . import asn1, oids

__all__ = ["Certificate", "Name", "parse_certificate", "format_name"]


@dataclass
class Name:
    """A distinguished name kept both as pairs and as a flat string."""

    pairs: list[tuple[str, str]] = field(default_factory=list)

    def get(self, key: str) -> str | None:
        for attr, value in self.pairs:
            if attr.lower() == key.lower():
                return value
        return None

    @property
    def common_name(self) -> str | None:
        return self.get("CN")

    @property
    def organization(self) -> str | None:
        return self.get("O")

    def __str__(self) -> str:
        return ", ".join(f"{k}={v}" for k, v in self.pairs)


@dataclass
class PublicKeyInfo:
    algorithm: str          # 'rsa', 'ecdsa', 'dsa' or the raw OID
    algorithm_oid: str
    bits: int | None = None
    curve: str | None = None
    rsa_modulus: int | None = None
    rsa_exponent: int | None = None


@dataclass
class Certificate:
    der: bytes
    serial: int
    version: int
    issuer: Name
    subject: Name
    not_before: _dt.datetime | None
    not_after: _dt.datetime | None
    signature_algorithm: str
    public_key: PublicKeyInfo
    extensions: dict[str, object] = field(default_factory=dict)
    tbs: asn1.Node | None = None

    # -- convenience --------------------------------------------------
    @property
    def serial_hex(self) -> str:
        raw = f"{self.serial:x}"
        if len(raw) % 2:
            raw = "0" + raw
        return raw.upper()

    @property
    def fingerprint_sha1(self) -> str:
        return hashlib.sha1(self.der).hexdigest().upper()

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self.der).hexdigest().upper()

    @property
    def display_name(self) -> str:
        return self.subject.common_name or str(self.subject) or "(unknown)"

    @property
    def is_ca(self) -> bool:
        basic = self.extensions.get("basicConstraints")
        return bool(isinstance(basic, dict) and basic.get("ca"))

    def is_valid_at(self, moment: _dt.datetime | None = None) -> bool | None:
        """True/False if the validity window covers ``moment``; None if unknown."""
        if self.not_before is None or self.not_after is None:
            return None
        moment = moment or _dt.datetime.now(_dt.timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=_dt.timezone.utc)
        return self.not_before <= moment <= self.not_after


def format_name(node: asn1.Node) -> Name:
    """Decode an RDNSequence."""
    pairs: list[tuple[str, str]] = []
    for rdn in node.children:              # SET OF AttributeTypeAndValue
        for attr in rdn.children:          # SEQUENCE { type, value }
            if len(attr.children) < 2:
                continue
            try:
                oid = asn1.decode_oid(attr.child(0))
            except asn1.Asn1Error:
                continue
            key = oids.DN_ATTRIBUTES.get(oid, oid)
            value_node = attr.child(1)
            try:
                value = asn1.decode_string(value_node)
            except Exception:  # pragma: no cover - defensive
                value = value_node.content.hex()
            pairs.append((key, value))
    return Name(pairs)


def _parse_algorithm(node: asn1.Node) -> str:
    if not node.children:
        return ""
    try:
        return asn1.decode_oid(node.child(0))
    except asn1.Asn1Error:
        return ""


def _algorithm_label(oid: str) -> str:
    """``sha256WithRSA`` rather than the bare OID, when the OID is known."""
    entry = oids.SIGNATURE_ALGORITHMS.get(oid)
    if entry is None:
        return oid
    family, digest = entry
    return f"{digest}With{family.upper()}" if digest else family


def _parse_public_key(node: asn1.Node) -> PublicKeyInfo:
    alg_oid = _parse_algorithm(node.child(0)) if node.children else ""
    family = oids.SIGNATURE_ALGORITHMS.get(alg_oid, (alg_oid, None))[0]
    info = PublicKeyInfo(algorithm=family, algorithm_oid=alg_oid)
    try:
        key_bits = asn1.decode_bitstring(node.child(1))
    except (asn1.Asn1Error, IndexError):
        return info
    if family == "rsa":
        try:
            seq = asn1.parse(key_bits)
            info.rsa_modulus = asn1.decode_integer(seq.child(0))
            info.rsa_exponent = asn1.decode_integer(seq.child(1))
            info.bits = info.rsa_modulus.bit_length()
        except (asn1.Asn1Error, IndexError):
            pass
    elif family == "ecdsa":
        params = node.child(0)
        if len(params.children) > 1 and params.child(1).is_universal(asn1.OID):
            with suppress(asn1.Asn1Error):
                info.curve = asn1.decode_oid(params.child(1))
        info.bits = max((len(key_bits) - 1) // 2 * 8, 0) or None
    return info


def _general_names(node: asn1.Node) -> list[str]:
    out: list[str] = []
    for item in node.children:
        if item.cls != asn1.CONTEXT:
            continue
        if item.tag in (1, 2, 6):  # rfc822Name, dNSName, uniformResourceIdentifier
            out.append(item.content.decode("ascii", "replace"))
        elif item.tag == 7:        # iPAddress
            out.append(".".join(str(b) for b in item.content))
        elif item.tag == 4 and item.children:  # directoryName
            out.append(str(format_name(item.child(0))))
    return out


def _parse_extension(oid: str, value: bytes) -> object:
    try:
        node = asn1.parse(value)
    except asn1.Asn1Error:
        return value.hex()

    if oid == oids.EXT_BASIC_CONSTRAINTS:
        result: dict[str, object] = {"ca": False}
        for child in node.children:
            if child.is_universal(asn1.BOOLEAN):
                result["ca"] = bool(child.content and child.content[0])
            elif child.is_universal(asn1.INTEGER):
                result["pathLen"] = asn1.decode_integer(child)
        return result

    if oid == oids.EXT_KEY_USAGE:
        data = node.content
        if not data:
            return []
        unused = data[0]
        bits = int.from_bytes(data[1:], "big") if len(data) > 1 else 0
        total = (len(data) - 1) * 8 - unused
        usages = []
        for index in range(total):
            shift = (len(data) - 1) * 8 - 1 - index
            if bits >> shift & 1 and index < len(oids.KEY_USAGE_BITS):
                usages.append(oids.KEY_USAGE_BITS[index])
        return usages

    if oid == oids.EXT_EXT_KEY_USAGE:
        out = []
        for child in node.children:
            try:
                value_oid = asn1.decode_oid(child)
            except asn1.Asn1Error:
                continue
            out.append(oids.EXT_KEY_USAGE_NAMES.get(value_oid, value_oid))
        return out

    if oid == oids.EXT_SUBJECT_ALT_NAME:
        return _general_names(node)

    if oid == oids.EXT_CRL_DISTRIBUTION_POINTS:
        urls: list[str] = []
        for sub in node.walk():
            if sub.cls == asn1.CONTEXT and sub.tag == 6 and not sub.constructed:
                urls.append(sub.content.decode("ascii", "replace"))
        return urls

    if oid == oids.EXT_AUTHORITY_INFO_ACCESS:
        entries: list[str] = []
        for access in node.children:
            if len(access.children) < 2:
                continue
            try:
                method = asn1.decode_oid(access.child(0))
            except asn1.Asn1Error:
                continue
            label = {
                "1.3.6.1.5.5.7.48.1": "OCSP",
                "1.3.6.1.5.5.7.48.2": "caIssuers",
            }.get(method, method)
            location = access.child(1)
            entries.append(f"{label}: {location.content.decode('ascii', 'replace')}")
        return entries

    if oid == oids.EXT_CERTIFICATE_POLICIES:
        policies = []
        for policy in node.children:
            if not policy.children:
                continue
            try:
                policies.append(asn1.decode_oid(policy.child(0)))
            except asn1.Asn1Error:
                continue
        return policies

    if oid == oids.EXT_QC_STATEMENTS:
        statements = []
        for statement in node.children:
            if not statement.children:
                continue
            try:
                value_oid = asn1.decode_oid(statement.child(0))
            except asn1.Asn1Error:
                continue
            statements.append(oids.QC_STATEMENTS.get(value_oid, value_oid))
        return statements

    if oid == "2.5.29.14":
        return node.content.hex().upper()

    return value.hex().upper()


def parse_certificate(der: bytes) -> Certificate:
    """Parse a DER encoded X.509 certificate."""
    root = asn1.parse(der)
    if not root.children:
        raise asn1.Asn1Error("invalid certificate")
    tbs = root.child(0)

    index = 0
    version = 1
    if tbs.children and tbs.child(0).is_context(0):
        try:
            version = asn1.decode_integer(tbs.child(0).child(0)) + 1
        except (asn1.Asn1Error, IndexError):
            version = 1
        index = 1

    serial = asn1.decode_integer(tbs.child(index))
    signature_algorithm = _parse_algorithm(tbs.child(index + 1))
    issuer = format_name(tbs.child(index + 2))
    validity = tbs.child(index + 3)
    not_before = asn1.decode_time(validity.child(0)) if validity.children else None
    not_after = asn1.decode_time(validity.child(1)) if len(validity.children) > 1 else None
    subject = format_name(tbs.child(index + 4))
    public_key = _parse_public_key(tbs.child(index + 5))

    extensions: dict[str, object] = {}
    ext_container = None
    for child in tbs.children[index + 6 :]:
        if child.is_context(3):
            ext_container = child
            break
    if ext_container is not None and ext_container.children:
        for ext in ext_container.child(0).children:
            if not ext.children:
                continue
            try:
                ext_oid = asn1.decode_oid(ext.child(0))
            except asn1.Asn1Error:
                continue
            payload = None
            for part in ext.children[1:]:
                if part.is_universal(asn1.OCTET_STRING):
                    payload = part.octets()
            if payload is None:
                continue
            label = oids.EXTENSIONS.get(ext_oid, ext_oid)
            extensions[label] = _parse_extension(ext_oid, payload)

    return Certificate(
        der=der,
        serial=serial,
        version=version,
        issuer=issuer,
        subject=subject,
        not_before=not_before,
        not_after=not_after,
        signature_algorithm=_algorithm_label(signature_algorithm),
        public_key=public_key,
        extensions=extensions,
        tbs=tbs,
    )
