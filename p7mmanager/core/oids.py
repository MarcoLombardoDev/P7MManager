# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""Object identifiers met while inspecting CAdES/PAdES signatures."""

from __future__ import annotations

# --- content types ---------------------------------------------------
ID_DATA = "1.2.840.113549.1.7.1"
ID_SIGNED_DATA = "1.2.840.113549.1.7.2"
ID_ENVELOPED_DATA = "1.2.840.113549.1.7.3"
ID_DIGESTED_DATA = "1.2.840.113549.1.7.5"
ID_ENCRYPTED_DATA = "1.2.840.113549.1.7.6"
ID_TIMESTAMP_TOKEN = "1.2.840.113549.1.9.16.1.4"

CONTENT_TYPES = {
    ID_DATA: "data",
    ID_SIGNED_DATA: "signedData",
    ID_ENVELOPED_DATA: "envelopedData",
    ID_DIGESTED_DATA: "digestedData",
    ID_ENCRYPTED_DATA: "encryptedData",
    "1.2.840.113549.1.7.4": "signedAndEnvelopedData",
    ID_TIMESTAMP_TOKEN: "id-ct-TSTInfo",
}

# --- signed / unsigned attributes ------------------------------------
ATTR_CONTENT_TYPE = "1.2.840.113549.1.9.3"
ATTR_MESSAGE_DIGEST = "1.2.840.113549.1.9.4"
ATTR_SIGNING_TIME = "1.2.840.113549.1.9.5"
ATTR_COUNTER_SIGNATURE = "1.2.840.113549.1.9.6"
ATTR_SIGNING_CERTIFICATE = "1.2.840.113549.1.9.16.2.12"
ATTR_SIGNING_CERTIFICATE_V2 = "1.2.840.113549.1.9.16.2.47"
ATTR_SIGNATURE_TIMESTAMP = "1.2.840.113549.1.9.16.2.14"
ATTR_COMMITMENT_TYPE = "1.2.840.113549.1.9.16.2.16"
ATTR_SIGNER_LOCATION = "1.2.840.113549.1.9.16.2.17"
ATTR_CONTENT_HINTS = "1.2.840.113549.1.9.16.2.4"
ATTR_ARCHIVE_TIMESTAMP_V2 = "1.2.840.113549.1.9.16.2.48"
ATTR_ARCHIVE_TIMESTAMP_V3 = "0.4.0.1733.2.4"

ATTRIBUTES = {
    ATTR_CONTENT_TYPE: "contentType",
    ATTR_MESSAGE_DIGEST: "messageDigest",
    ATTR_SIGNING_TIME: "signingTime",
    ATTR_COUNTER_SIGNATURE: "counterSignature",
    ATTR_CONTENT_HINTS: "contentHints",
    ATTR_SIGNING_CERTIFICATE: "signingCertificate",
    ATTR_SIGNING_CERTIFICATE_V2: "signingCertificateV2",
    ATTR_SIGNATURE_TIMESTAMP: "signatureTimeStampToken",
    ATTR_COMMITMENT_TYPE: "commitmentTypeIndication",
    ATTR_SIGNER_LOCATION: "signerLocation",
    ATTR_ARCHIVE_TIMESTAMP_V2: "archiveTimeStampV2",
    ATTR_ARCHIVE_TIMESTAMP_V3: "archiveTimeStampV3",
    "1.2.840.113549.1.9.16.2.18": "signerAttributes",
    "1.2.840.113549.1.9.16.2.20": "contentTimeStamp",
    "1.2.840.113549.1.9.16.2.21": "certificateRefs",
    "1.2.840.113549.1.9.16.2.22": "revocationRefs",
    "1.2.840.113549.1.9.16.2.23": "certValues",
    "1.2.840.113549.1.9.16.2.24": "revocationValues",
    "1.2.840.113549.1.9.16.2.25": "escTimeStamp",
    "1.2.840.113549.1.9.15": "smimeCapabilities",
}

# --- digest algorithms ------------------------------------------------
DIGEST_ALGORITHMS = {
    "1.2.840.113549.2.5": "md5",
    "1.3.14.3.2.26": "sha1",
    "2.16.840.1.101.3.4.2.1": "sha256",
    "2.16.840.1.101.3.4.2.2": "sha384",
    "2.16.840.1.101.3.4.2.3": "sha512",
    "2.16.840.1.101.3.4.2.4": "sha224",
    "2.16.840.1.101.3.4.2.7": "sha3_224",
    "2.16.840.1.101.3.4.2.8": "sha3_256",
    "2.16.840.1.101.3.4.2.9": "sha3_384",
    "2.16.840.1.101.3.4.2.10": "sha3_512",
}

# --- signature algorithms --------------------------------------------
RSA_ENCRYPTION = "1.2.840.113549.1.1.1"
RSASSA_PSS = "1.2.840.113549.1.1.10"

SIGNATURE_ALGORITHMS = {
    RSA_ENCRYPTION: ("rsa", None),
    "1.2.840.113549.1.1.2": ("rsa", "md2"),
    "1.2.840.113549.1.1.4": ("rsa", "md5"),
    "1.2.840.113549.1.1.5": ("rsa", "sha1"),
    "1.2.840.113549.1.1.11": ("rsa", "sha256"),
    "1.2.840.113549.1.1.12": ("rsa", "sha384"),
    "1.2.840.113549.1.1.13": ("rsa", "sha512"),
    "1.2.840.113549.1.1.14": ("rsa", "sha224"),
    RSASSA_PSS: ("rsa-pss", None),
    "1.2.840.10040.4.1": ("dsa", None),
    "1.2.840.10040.4.3": ("dsa", "sha1"),
    "2.16.840.1.101.3.4.3.2": ("dsa", "sha256"),
    "1.2.840.10045.2.1": ("ecdsa", None),
    "1.2.840.10045.4.1": ("ecdsa", "sha1"),
    "1.2.840.10045.4.3.1": ("ecdsa", "sha224"),
    "1.2.840.10045.4.3.2": ("ecdsa", "sha256"),
    "1.2.840.10045.4.3.3": ("ecdsa", "sha384"),
    "1.2.840.10045.4.3.4": ("ecdsa", "sha512"),
}

# --- distinguished name attributes -----------------------------------
DN_ATTRIBUTES = {
    "2.5.4.3": "CN",
    "2.5.4.4": "SN",
    "2.5.4.5": "serialNumber",
    "2.5.4.6": "C",
    "2.5.4.7": "L",
    "2.5.4.8": "ST",
    "2.5.4.9": "street",
    "2.5.4.10": "O",
    "2.5.4.11": "OU",
    "2.5.4.12": "title",
    "2.5.4.13": "description",
    "2.5.4.15": "businessCategory",
    "2.5.4.17": "postalCode",
    "2.5.4.20": "telephoneNumber",
    "2.5.4.42": "GN",
    "2.5.4.43": "initials",
    "2.5.4.44": "generationQualifier",
    "2.5.4.45": "x500UniqueIdentifier",
    "2.5.4.46": "dnQualifier",
    "2.5.4.65": "pseudonym",
    "2.5.4.97": "organizationIdentifier",
    "1.2.840.113549.1.9.1": "emailAddress",
    "0.9.2342.19200300.100.1.1": "UID",
    "0.9.2342.19200300.100.1.25": "DC",
}

# --- certificate extensions ------------------------------------------
EXT_KEY_USAGE = "2.5.29.15"
EXT_SUBJECT_ALT_NAME = "2.5.29.17"
EXT_BASIC_CONSTRAINTS = "2.5.29.19"
EXT_CRL_DISTRIBUTION_POINTS = "2.5.29.31"
EXT_CERTIFICATE_POLICIES = "2.5.29.32"
EXT_EXT_KEY_USAGE = "2.5.29.37"
EXT_AUTHORITY_INFO_ACCESS = "1.3.6.1.5.5.7.1.1"
EXT_QC_STATEMENTS = "1.3.6.1.5.5.7.1.3"

EXTENSIONS = {
    "2.5.29.14": "subjectKeyIdentifier",
    EXT_KEY_USAGE: "keyUsage",
    "2.5.29.16": "privateKeyUsagePeriod",
    EXT_SUBJECT_ALT_NAME: "subjectAltName",
    EXT_BASIC_CONSTRAINTS: "basicConstraints",
    EXT_CRL_DISTRIBUTION_POINTS: "cRLDistributionPoints",
    EXT_CERTIFICATE_POLICIES: "certificatePolicies",
    "2.5.29.35": "authorityKeyIdentifier",
    EXT_EXT_KEY_USAGE: "extKeyUsage",
    EXT_AUTHORITY_INFO_ACCESS: "authorityInfoAccess",
    EXT_QC_STATEMENTS: "qcStatements",
}

KEY_USAGE_BITS = [
    "digitalSignature",
    "nonRepudiation",
    "keyEncipherment",
    "dataEncipherment",
    "keyAgreement",
    "keyCertSign",
    "cRLSign",
    "encipherOnly",
    "decipherOnly",
]

EXT_KEY_USAGE_NAMES = {
    "1.3.6.1.5.5.7.3.1": "serverAuth",
    "1.3.6.1.5.5.7.3.2": "clientAuth",
    "1.3.6.1.5.5.7.3.3": "codeSigning",
    "1.3.6.1.5.5.7.3.4": "emailProtection",
    "1.3.6.1.5.5.7.3.8": "timeStamping",
    "1.3.6.1.5.5.7.3.9": "OCSPSigning",
}

COMMITMENT_TYPES = {
    "1.2.840.113549.1.9.16.6.1": "proofOfOrigin",
    "1.2.840.113549.1.9.16.6.2": "proofOfReceipt",
    "1.2.840.113549.1.9.16.6.3": "proofOfDelivery",
    "1.2.840.113549.1.9.16.6.4": "proofOfSender",
    "1.2.840.113549.1.9.16.6.5": "proofOfApproval",
    "1.2.840.113549.1.9.16.6.6": "proofOfCreation",
}

QC_STATEMENTS = {
    "0.4.0.1862.1.1": "QcCompliance (eIDAS qualified signature)",
    "0.4.0.1862.1.2": "QcLimitValue",
    "0.4.0.1862.1.3": "QcRetentionPeriod",
    "0.4.0.1862.1.4": "QcSSCD (qualified signature device)",
    "0.4.0.1862.1.5": "QcPDS",
    "0.4.0.1862.1.6": "QcType",
    "0.4.0.1862.1.6.1": "QcType: electronic signature",
    "0.4.0.1862.1.6.2": "QcType: electronic seal",
    "0.4.0.1862.1.6.3": "QcType: website authentication",
    "1.3.76.16.6": "Qualified signature certificate (AgID)",
}


def name(table: dict, oid: str, prefix: str = "") -> str:
    """Return a readable label for ``oid`` falling back to the raw value."""
    label = table.get(oid)
    if label:
        return label
    return f"{prefix}{oid}" if prefix else oid
