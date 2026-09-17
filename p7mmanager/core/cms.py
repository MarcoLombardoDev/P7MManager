# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The CMS (PKCS#7) SignedData structure a .p7m file wraps around a document.

What a .p7m holds is a ``ContentInfo`` whose content is ``SignedData``: the
document itself (the *encapsulated content*), the certificates of whoever
signed it, and one ``SignerInfo`` per signature. This module turns that into
plain dataclasses; nothing here touches the filesystem or Qt, so the engine
and the test-suite can use it on bytes alone.

Detached signatures — where the encapsulated content is absent because the
document travels beside the signature — are parsed like any other, and report
``detached`` so the caller can say why there is nothing to extract.
"""

from __future__ import annotations

import datetime as _dt
from contextlib import suppress
from dataclasses import dataclass, field

from . import asn1, oids
from .x509 import Certificate, Name, format_name, parse_certificate

__all__ = [
    "CmsError",
    "Attribute",
    "TimeStamp",
    "Signer",
    "SignedData",
    "parse_signed_data",
    "looks_like_cms",
]


class CmsError(ValueError):
    """Raised when the bytes are not a CMS SignedData this tool can read."""


@dataclass
class Attribute:
    """A signed or unsigned attribute, kept with its values still encoded."""

    oid: str
    values: list[asn1.Node] = field(default_factory=list)

    @property
    def name(self) -> str:
        return oids.ATTRIBUTES.get(self.oid, self.oid)


@dataclass
class TimeStamp:
    """The interesting fields of an RFC 3161 token found on a signature."""

    generated: _dt.datetime | None = None
    serial: int | None = None
    policy: str | None = None
    authority: str | None = None
    digest_algorithm: str | None = None
    issuer: Name | None = None
    kind: str = "signatureTimeStamp"


@dataclass
class Signer:
    """One ``SignerInfo``: who signed, how, and with which attributes."""

    index: int
    version: int = 1
    issuer: Name | None = None
    serial: int | None = None
    subject_key_id: str | None = None
    digest_algorithm: str = ""
    signature_algorithm: str = ""
    signature: bytes = b""
    signed_attributes: list[Attribute] = field(default_factory=list)
    unsigned_attributes: list[Attribute] = field(default_factory=list)
    signed_attrs_der: bytes | None = None
    signing_time: _dt.datetime | None = None
    message_digest: bytes | None = None
    content_type: str | None = None
    commitment: str | None = None
    location: str | None = None
    certificate: Certificate | None = None
    counter_signatures: list[Signer] = field(default_factory=list)
    timestamps: list[TimeStamp] = field(default_factory=list)
    # Filled in by :mod:`p7mmanager.core.verify`.
    digest_matches: bool | None = None
    signature_valid: bool | None = None
    verification_note: str = ""

    @property
    def display_name(self) -> str:
        if self.certificate is not None:
            return self.certificate.display_name
        if self.issuer is not None:
            return f"{self.issuer.common_name or self.issuer} (serial {self.serial})"
        return "(unknown signer)"

    @property
    def has_signed_attributes(self) -> bool:
        return self.signed_attrs_der is not None

    def attribute(self, oid: str) -> Attribute | None:
        for attribute in self.signed_attributes + self.unsigned_attributes:
            if attribute.oid == oid:
                return attribute
        return None


@dataclass
class SignedData:
    """A parsed ``SignedData``, plus the raw bytes it was read from."""

    version: int
    content_type: str
    content: bytes | None
    detached: bool
    digest_algorithms: list[str] = field(default_factory=list)
    certificates: list[Certificate] = field(default_factory=list)
    signers: list[Signer] = field(default_factory=list)
    crl_count: int = 0

    @property
    def signature_count(self) -> int:
        return len(self.signers)

    @property
    def content_type_name(self) -> str:
        return oids.CONTENT_TYPES.get(self.content_type, self.content_type)


def looks_like_cms(data: bytes) -> bool:
    """Cheap guard: does this start like a DER SEQUENCE holding a ContentInfo?"""
    if len(data) < 16 or data[0] != 0x30:
        return False
    try:
        root = asn1.parse(data)
    except asn1.Asn1Error:
        return False
    if not root.children or not root.child(0).is_universal(asn1.OID):
        return False
    try:
        return asn1.decode_oid(root.child(0)) in oids.CONTENT_TYPES
    except asn1.Asn1Error:
        return False


def _algorithm_name(node: asn1.Node, table: dict) -> str:
    if not node.children:
        return ""
    try:
        oid = asn1.decode_oid(node.child(0))
    except asn1.Asn1Error:
        return ""
    value = table.get(oid)
    if isinstance(value, tuple):
        family, digest = value
        return f"{digest}With{family.upper()}" if digest else family
    return value or oid


def _parse_attributes(container: asn1.Node) -> list[Attribute]:
    attributes: list[Attribute] = []
    for item in container.children:
        if len(item.children) < 2:
            continue
        try:
            oid = asn1.decode_oid(item.child(0))
        except asn1.Asn1Error:
            continue
        attributes.append(Attribute(oid=oid, values=list(item.child(1).children)))
    return attributes


def _parse_tst_info(data: bytes, kind: str) -> TimeStamp | None:
    """Read the TSTInfo carried by an RFC 3161 token."""
    try:
        token = parse_signed_data(data)
    except (CmsError, asn1.Asn1Error):
        return None
    stamp = TimeStamp(kind=kind)
    if token.signers:
        stamp.issuer = token.signers[0].issuer
        if token.signers[0].certificate is not None:
            stamp.authority = token.signers[0].certificate.display_name
    if not token.content:
        return stamp
    try:
        info = asn1.parse(token.content)
    except asn1.Asn1Error:
        return stamp
    children = info.children
    if len(children) >= 2:
        with suppress(asn1.Asn1Error):
            stamp.policy = asn1.decode_oid(children[1])
    if len(children) >= 3 and children[2].children:
        stamp.digest_algorithm = _algorithm_name(children[2].child(0), oids.DIGEST_ALGORITHMS)
    if len(children) >= 4:
        with suppress(asn1.Asn1Error):
            stamp.serial = asn1.decode_integer(children[3])
    for child in children[4:]:
        if child.is_universal(asn1.GENERALIZED_TIME):
            stamp.generated = asn1.decode_time(child)
            break
    for child in children:
        if child.is_context(0) and child.children and stamp.authority is None:
            with_name = child.child(0)
            if with_name.constructed and with_name.children:
                stamp.authority = str(format_name(with_name.child(0)))
    return stamp


def _parse_signer(node: asn1.Node, index: int, certificates: list[Certificate]) -> Signer:
    signer = Signer(index=index)
    children = node.children
    if not children:
        raise CmsError("empty SignerInfo")

    signer.version = asn1.decode_integer(children[0])
    position = 1

    sid = children[position]
    if sid.is_context(0):  # subjectKeyIdentifier
        signer.subject_key_id = sid.octets().hex().upper()
    else:                   # issuerAndSerialNumber
        if sid.children:
            signer.issuer = format_name(sid.child(0))
        if len(sid.children) > 1:
            signer.serial = asn1.decode_integer(sid.child(1))
    position += 1

    signer.digest_algorithm = _algorithm_name(children[position], oids.DIGEST_ALGORITHMS)
    position += 1

    if position < len(children) and children[position].is_context(0):
        attrs_node = children[position]
        signer.signed_attributes = _parse_attributes(attrs_node)
        # The signature covers these attributes re-tagged as a SET OF.
        raw = bytearray(attrs_node.raw)
        raw[0] = 0x31
        signer.signed_attrs_der = bytes(raw)
        position += 1

    if position < len(children):
        signer.signature_algorithm = _algorithm_name(
            children[position], oids.SIGNATURE_ALGORITHMS
        )
        position += 1
    if position < len(children):
        signer.signature = children[position].octets()
        position += 1
    if position < len(children) and children[position].is_context(1):
        signer.unsigned_attributes = _parse_attributes(children[position])

    _read_known_attributes(signer, certificates)
    _match_certificate(signer, certificates)
    return signer


def _read_known_attributes(signer: Signer, certificates: list[Certificate]) -> None:
    for attribute in signer.signed_attributes:
        if not attribute.values:
            continue
        value = attribute.values[0]
        if attribute.oid == oids.ATTR_SIGNING_TIME:
            signer.signing_time = asn1.decode_time(value)
        elif attribute.oid == oids.ATTR_MESSAGE_DIGEST:
            signer.message_digest = value.octets()
        elif attribute.oid == oids.ATTR_CONTENT_TYPE:
            try:
                oid = asn1.decode_oid(value)
            except asn1.Asn1Error:
                continue
            signer.content_type = oids.CONTENT_TYPES.get(oid, oid)
        elif attribute.oid == oids.ATTR_COMMITMENT_TYPE:
            for sub in value.walk():
                if sub.is_universal(asn1.OID):
                    try:
                        oid = asn1.decode_oid(sub)
                    except asn1.Asn1Error:
                        continue
                    signer.commitment = oids.COMMITMENT_TYPES.get(oid, oid)
                    break
        elif attribute.oid == oids.ATTR_SIGNER_LOCATION:
            texts = [
                asn1.decode_string(sub)
                for sub in value.walk()
                if sub.cls == asn1.UNIVERSAL and sub.tag in (asn1.UTF8_STRING,
                                                             asn1.PRINTABLE_STRING)
            ]
            if texts:
                signer.location = ", ".join(texts)

    for attribute in signer.unsigned_attributes:
        if attribute.oid == oids.ATTR_COUNTER_SIGNATURE:
            for position, value in enumerate(attribute.values):
                try:
                    signer.counter_signatures.append(
                        _parse_signer(value, position, certificates)
                    )
                except (CmsError, asn1.Asn1Error, IndexError):
                    continue
        elif attribute.oid in (
            oids.ATTR_SIGNATURE_TIMESTAMP,
            oids.ATTR_ARCHIVE_TIMESTAMP_V2,
            oids.ATTR_ARCHIVE_TIMESTAMP_V3,
            "1.2.840.113549.1.9.16.2.20",
        ):
            label = oids.ATTRIBUTES.get(attribute.oid, attribute.oid)
            for value in attribute.values:
                stamp = _parse_tst_info(value.raw, label)
                if stamp is not None:
                    signer.timestamps.append(stamp)


def _match_certificate(signer: Signer, certificates: list[Certificate]) -> None:
    for certificate in certificates:
        # The serial identifies the certificate; the issuer disambiguates the
        # rare case of two authorities using the same serial number.
        if (
            signer.serial is not None
            and certificate.serial == signer.serial
            and (signer.issuer is None or str(certificate.issuer) == str(signer.issuer))
        ):
            signer.certificate = certificate
            return
    if signer.subject_key_id:
        for certificate in certificates:
            key_id = certificate.extensions.get("subjectKeyIdentifier")
            if isinstance(key_id, str) and key_id.upper() == signer.subject_key_id.upper():
                signer.certificate = certificate
                return


def parse_signed_data(data: bytes) -> SignedData:
    """Parse DER encoded CMS and return its SignedData.

    Raises :class:`CmsError` when the bytes hold something else — an
    ``envelopedData``, or no CMS at all.
    """
    try:
        root = asn1.parse(data)
    except asn1.Asn1Error as exc:
        raise CmsError(f"invalid ASN.1 structure: {exc}") from exc

    if not root.children:
        raise CmsError("empty ContentInfo")
    try:
        content_type = asn1.decode_oid(root.child(0))
    except asn1.Asn1Error as exc:
        raise CmsError("ContentInfo without a contentType") from exc

    if content_type != oids.ID_SIGNED_DATA:
        label = oids.CONTENT_TYPES.get(content_type, content_type)
        raise CmsError(f"CMS content is not signed data ({label})")

    wrapper = root.find_context(0)
    if wrapper is None or not wrapper.children:
        raise CmsError("SignedData missing")
    signed = wrapper.child(0)
    children = signed.children
    if len(children) < 4:
        raise CmsError("SignedData incomplete")

    version = asn1.decode_integer(children[0])
    digest_algorithms = [
        _algorithm_name(item, oids.DIGEST_ALGORITHMS) for item in children[1].children
    ]

    encap = children[2]
    encap_type = oids.ID_DATA
    if encap.children:
        with suppress(asn1.Asn1Error):
            encap_type = asn1.decode_oid(encap.child(0))
    content: bytes | None = None
    holder = encap.find_context(0)
    if holder is not None:
        if holder.children:
            content = holder.child(0).octets()
        else:
            content = holder.content

    certificates: list[Certificate] = []
    crl_count = 0
    signer_infos: list[asn1.Node] = []
    for child in children[3:]:
        if child.is_context(0):
            for item in child.children:
                if not item.is_universal(asn1.SEQUENCE):
                    continue  # attribute certificates and other choices
                try:
                    certificates.append(parse_certificate(item.raw))
                except (asn1.Asn1Error, IndexError, ValueError):
                    continue
        elif child.is_context(1):
            crl_count = len(child.children)
        elif child.is_universal(asn1.SET):
            signer_infos = list(child.children)

    signers: list[Signer] = []
    for index, info in enumerate(signer_infos):
        try:
            signers.append(_parse_signer(info, index, certificates))
        except (CmsError, asn1.Asn1Error, IndexError) as exc:
            signers.append(
                Signer(index=index, verification_note=f"unreadable SignerInfo: {exc}")
            )

    return SignedData(
        version=version,
        content_type=encap_type,
        content=content,
        detached=content is None,
        digest_algorithms=digest_algorithms,
        certificates=certificates,
        signers=signers,
        crl_count=crl_count,
    )
