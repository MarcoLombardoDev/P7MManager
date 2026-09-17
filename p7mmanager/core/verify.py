# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""What can honestly be checked without a trust store.

Two questions are answered here, and they are worth keeping apart:

*integrity* — does the document still hash to the value the signature covers?
A mismatch means the file was altered after signing, and it is the check that
catches a truncated download or an edited payload.

*signature* — does the signer's public key actually produce this signature over
those attributes? RSA PKCS#1 v1.5 is verified with integer arithmetic alone,
which needs no third-party crypto library. ECDSA and RSA-PSS are reported as
not verified rather than guessed at.

Neither is a legal validity check. Whether the certificate chains to a trusted
qualified authority, whether it was revoked, and whether the timestamp is
genuine are questions this tool deliberately does not answer — see
``docs/ARCHITECTURE.md``. The interface says so wherever it shows a result.
"""

from __future__ import annotations

import hashlib

from . import asn1, oids
from .cms import SignedData, Signer
from .x509 import Certificate

__all__ = ["verify_signed_data", "verify_signer", "digest_for"]

_DIGEST_ALIASES = {
    "sha1": "sha1",
    "sha224": "sha224",
    "sha256": "sha256",
    "sha384": "sha384",
    "sha512": "sha512",
    "md5": "md5",
    "sha3_224": "sha3_224",
    "sha3_256": "sha3_256",
    "sha3_384": "sha3_384",
    "sha3_512": "sha3_512",
}


def digest_for(name: str, data: bytes) -> bytes | None:
    """Hash ``data`` with the named algorithm, or ``None`` if unsupported."""
    key = _DIGEST_ALIASES.get(_normalise(name))
    if key is None:
        return None
    try:
        return hashlib.new(key, data).digest()
    except ValueError:  # pragma: no cover - hashlib without that algorithm
        return None


def _normalise(name: str) -> str:
    """Reduce ``sha256WithRSA``, ``SHA-256`` and friends to ``sha256``."""
    name = (name or "").lower()
    if "with" in name:
        name = name.split("with", 1)[0]
    name = name.replace("-", "")
    if name.startswith("sha3") and not name.startswith("sha3_"):
        name = "sha3_" + name[4:]
    return name


def _rsa_public_numbers(certificate: Certificate) -> tuple[int, int] | None:
    key = certificate.public_key
    if key.algorithm != "rsa" or key.rsa_modulus is None or key.rsa_exponent is None:
        return None
    return key.rsa_modulus, key.rsa_exponent


def _rsa_pkcs1_recover(signature: bytes, modulus: int, exponent: int) -> bytes | None:
    """Undo the RSA operation and strip the PKCS#1 v1.5 padding."""
    size = (modulus.bit_length() + 7) // 8
    if not signature or len(signature) > size:
        return None
    value = int.from_bytes(signature, "big")
    if value >= modulus:
        return None
    block = pow(value, exponent, modulus).to_bytes(size, "big")
    if len(block) < 11 or block[0] != 0x00 or block[1] != 0x01:
        return None
    separator = block.find(b"\x00", 2)
    if separator < 0 or any(byte != 0xFF for byte in block[2:separator]):
        return None
    return block[separator + 1 :]


def _digest_from_digestinfo(encoded: bytes) -> tuple[str, bytes] | None:
    """Read ``DigestInfo ::= SEQUENCE { AlgorithmIdentifier, OCTET STRING }``."""
    try:
        node = asn1.parse(encoded)
        algorithm = asn1.decode_oid(node.child(0).child(0))
        digest = node.child(1).octets()
    except (asn1.Asn1Error, IndexError):
        return None
    return oids.DIGEST_ALGORITHMS.get(algorithm, algorithm), digest


def verify_signer(signed_data: SignedData, signer: Signer) -> None:
    """Fill in ``digest_matches``/``signature_valid`` on ``signer`` in place."""
    notes: list[str] = []

    # 1. integrity of the encapsulated document
    if signer.message_digest is not None:
        if signed_data.content is None:
            notes.append("detached signature: the document is not in the file")
        else:
            computed = digest_for(signer.digest_algorithm, signed_data.content)
            if computed is None:
                notes.append(f"digest {signer.digest_algorithm} not supported")
            else:
                signer.digest_matches = computed == signer.message_digest
                if not signer.digest_matches:
                    notes.append("the content does not match the signed digest")
    elif signed_data.content is not None and not signer.has_signed_attributes:
        signer.digest_matches = None

    # 2. the signature itself
    certificate = signer.certificate
    if certificate is None:
        notes.append("the signer's certificate is not in the file")
        signer.verification_note = "; ".join(notes)
        return

    signed_bytes = signer.signed_attrs_der
    if signed_bytes is None:
        signed_bytes = signed_data.content
    if signed_bytes is None:
        notes.append("nothing to verify: detached signature without signed attributes")
        signer.verification_note = "; ".join(notes)
        return

    numbers = _rsa_public_numbers(certificate)
    if numbers is None:
        family = certificate.public_key.algorithm or "unknown"
        notes.append(f"{family} keys: signature not verified by this tool")
        signer.verification_note = "; ".join(notes)
        return
    if "pss" in (signer.signature_algorithm or "").lower():
        notes.append("RSA-PSS: signature not verified by this tool")
        signer.verification_note = "; ".join(notes)
        return

    recovered = _rsa_pkcs1_recover(signer.signature, *numbers)
    if recovered is None:
        signer.signature_valid = False
        notes.append("invalid RSA padding")
        signer.verification_note = "; ".join(notes)
        return

    parsed = _digest_from_digestinfo(recovered)
    if parsed is None:
        signer.signature_valid = False
        notes.append("DigestInfo illeggibile")
        signer.verification_note = "; ".join(notes)
        return

    algorithm, expected = parsed
    computed = digest_for(algorithm, signed_bytes)
    if computed is None:
        notes.append(f"digest {algorithm} not supported")
    else:
        signer.signature_valid = computed == expected
        if not signer.signature_valid:
            notes.append("the signature does not match the signed data")

    signer.verification_note = "; ".join(notes)


def verify_signed_data(signed_data: SignedData) -> None:
    """Verify every signer, and every counter-signature, in place."""
    for signer in signed_data.signers:
        verify_signer(signed_data, signer)
        for counter in signer.counter_signatures:
            # A counter-signature covers the signature value, not the document.
            counter.digest_matches = None
            if counter.certificate is None:
                counter.verification_note = "the counter-signature certificate is not enclosed"
