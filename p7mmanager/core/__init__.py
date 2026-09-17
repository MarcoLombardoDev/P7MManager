# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The engine: reading containers, checking them, extracting what they hold.

Nothing in this package imports Qt.
"""

from __future__ import annotations

from .analyzer import Analysis, ContainerEncoding, Outcome, analyse, analyse_bytes
from .cms import CmsError, SignedData, Signer, parse_signed_data
from .extractor import (
    Conflict,
    Destination,
    ExtractionResult,
    ExtractionSettings,
    extract,
)
from .jobs import DEFAULT_WORKERS, Job, JobQueue, JobState, QueueEvent
from .payload import PayloadKind, identify
from .scanner import scan
from .x509 import Certificate

__all__ = [
    "Analysis",
    "Certificate",
    "CmsError",
    "Conflict",
    "ContainerEncoding",
    "DEFAULT_WORKERS",
    "Destination",
    "ExtractionResult",
    "ExtractionSettings",
    "Job",
    "JobQueue",
    "JobState",
    "Outcome",
    "PayloadKind",
    "QueueEvent",
    "SignedData",
    "Signer",
    "analyse",
    "analyse_bytes",
    "extract",
    "identify",
    "parse_signed_data",
    "scan",
]
