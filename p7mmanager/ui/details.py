# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""The panel that answers "what is in this file?".

Rendered as HTML into a ``QTextBrowser`` rather than built from widgets: the
content is a document — sections, labels, values, a few colours — and it can
be selected and copied into an email, which is what people do with it.

The verdict lines are worded to stay inside what was actually checked. Green
says the content matches the digest the signature covers, not that the
signature is legally valid, and the footer repeats the distinction.
"""

from __future__ import annotations

import datetime as _dt
import html

from PySide6.QtWidgets import QTextBrowser

from ..core.cms import Signer
from ..core.jobs import Job
from ..core.x509 import Certificate
from ..i18n import tr, tr_message

__all__ = ["DetailsPanel", "render_job"]

_GREEN = "#148f77"
_AMBER = "#b9770e"
_RED = "#c0392b"
_MUTED = "#6c757d"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=False)


def _moment(value: _dt.datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone().strftime("%d/%m/%Y %H:%M:%S")


def _row(label: str, value: str, colour: str | None = None) -> str:
    style = f' style="color:{colour}"' if colour else ""
    return (
        f'<tr><td class="label">{_escape(tr(label))}</td>'
        f'<td{style}>{value}</td></tr>'
    )


def _section(title: str) -> str:
    return f'<h2>{_escape(tr(title))}</h2>'


def _verdict(value: bool | None, yes: str, no: str) -> tuple[str, str]:
    if value is None:
        return tr("Not checked"), _MUTED
    return (tr(yes), _GREEN) if value else (tr(no), _RED)


def _certificate_block(certificate: Certificate, signing_time: _dt.datetime | None) -> str:
    parts = ['<table class="fields">']
    parts.append(_row("Subject", _escape(certificate.subject)))
    parts.append(_row("Issuer", _escape(certificate.issuer)))
    parts.append(_row("Serial number", f'<code>{_escape(certificate.serial_hex)}</code>'))
    parts.append(_row("Valid from", _escape(_moment(certificate.not_before))))
    parts.append(_row("Valid until", _escape(_moment(certificate.not_after))))

    if signing_time is not None:
        valid_then = certificate.is_valid_at(signing_time)
        text, colour = _verdict(
            valid_then, "Valid at the time of signing", "Not valid at the time of signing"
        )
        parts.append(_row("Signature", _escape(text), colour))
    else:
        valid_now = certificate.is_valid_at()
        if valid_now is not None:
            label = "Currently valid" if valid_now else "Expired"
            parts.append(
                _row("Certificate", _escape(tr(label)), _GREEN if valid_now else _AMBER)
            )

    key = certificate.public_key
    key_text = key.algorithm.upper()
    if key.bits:
        key_text += f" {key.bits} bit"
    if key.curve:
        key_text += f" ({key.curve})"
    parts.append(_row("Key", _escape(key_text)))

    qualified = certificate.extensions.get("qcStatements")
    if isinstance(qualified, list) and qualified:
        parts.append(_row("Qualified certificate", _escape(", ".join(qualified)), _GREEN))

    fingerprint = certificate.fingerprint_sha256
    grouped = " ".join(fingerprint[i : i + 4] for i in range(0, len(fingerprint), 4))
    parts.append(_row("Fingerprint (SHA-256)", f'<code class="fp">{_escape(grouped)}</code>'))
    parts.append("</table>")
    return "".join(parts)


def _signer_block(signer: Signer, index: int, total: int) -> str:
    heading = _escape(signer.display_name)
    if total > 1:
        heading = f"{index + 1}/{total} — {heading}"
    parts = [f'<h3>{heading}</h3>', '<table class="fields">']

    parts.append(_row("Signed on", _escape(_moment(signer.signing_time))))
    algorithms = " / ".join(
        part for part in (signer.digest_algorithm, signer.signature_algorithm) if part
    )
    parts.append(_row("Signature algorithm", _escape(algorithms or "—")))

    text, colour = _verdict(
        signer.digest_matches,
        "Content matches the signed digest",
        "Content does not match the signed digest",
    )
    parts.append(_row("Integrity", _escape(text), colour))

    text, colour = _verdict(
        signer.signature_valid,
        "Signature matches the certificate's key",
        "Signature does not match the certificate's key",
    )
    parts.append(_row("Signature check", _escape(text), colour))

    if signer.commitment:
        parts.append(_row("Commitment", _escape(signer.commitment)))
    if signer.location:
        parts.append(_row("Place", _escape(signer.location)))
    if signer.verification_note:
        parts.append(
            _row("Warnings", _escape(tr_message(signer.verification_note)), _AMBER)
        )
    parts.append("</table>")

    if signer.certificate is not None:
        parts.append(f'<h4>{_escape(tr("Certificate"))}</h4>')
        parts.append(_certificate_block(signer.certificate, signer.signing_time))

    if signer.timestamps:
        parts.append(f'<h4>{_escape(tr("Timestamps"))}</h4><table class="fields">')
        for stamp in signer.timestamps:
            value = _moment(stamp.generated)
            if stamp.authority:
                value += f" — {stamp.authority}"
            parts.append(_row("Timestamp", _escape(value)))
        parts.append("</table>")

    if signer.counter_signatures:
        parts.append(f'<h4>{_escape(tr("Counter-signatures"))}</h4><table class="fields">')
        for counter in signer.counter_signatures:
            parts.append(
                _row("Signer", _escape(f"{counter.display_name} — {_moment(counter.signing_time)}"))
            )
        parts.append("</table>")
    return "".join(parts)


_STYLE = """
<style>
  body { font-family: 'Segoe UI','SF Pro Text','Noto Sans','DejaVu Sans',sans-serif;
         font-size: 10.5pt; color: #212529; }
  h1 { font-size: 13pt; color: #2c3e50; margin: 0 0 2px 0; }
  h2 { font-size: 11pt; color: #2c3e50; margin: 16px 0 4px 0;
       border-bottom: 1px solid #dee2e6; padding-bottom: 3px; }
  h3 { font-size: 10.5pt; color: #2c3e50; margin: 12px 0 3px 0; }
  h4 { font-size: 10pt; color: #495057; margin: 10px 0 2px 0; }
  table.fields { border-collapse: collapse; margin: 0; }
  td { padding: 2px 8px 2px 0; vertical-align: top; }
  td.label { color: #6c757d; white-space: nowrap; padding-right: 14px; }
  code { font-family: 'Consolas','SF Mono','DejaVu Sans Mono',monospace; font-size: 9.5pt; }
  code.fp { color: #495057; }
  p.path { color: #6c757d; margin: 0 0 6px 0; }
  p.footer { color: #6c757d; font-size: 9pt; border-top: 1px solid #dee2e6;
             margin-top: 18px; padding-top: 6px; }
  ul.warnings { margin: 4px 0 0 0; padding-left: 18px; color: #b9770e; }
</style>
"""

_DISCLAIMER = (
    "This tool checks integrity and, for RSA, the signature itself. It is not a "
    "legal validation: it has no trust list, does not check revocation and does "
    "not validate timestamps against an authority."
)


def render_job(job: Job | None) -> str:
    """The details of one queued file, as an HTML document."""
    if job is None:
        return (
            f"{_STYLE}<body><p class='path'>"
            f"{_escape(tr('Select a file to see its details'))}</p></body>"
        )

    parts = [_STYLE, "<body>", f"<h1>{_escape(job.name)}</h1>",
             f"<p class='path'>{_escape(job.path.parent)}</p>"]

    result = job.result
    if result is None:
        parts.append(f"<p>{_escape(tr('Queued'))}</p></body>")
        return "".join(parts)

    analysis = result.analysis
    parts.append(_section("Container"))
    parts.append('<table class="fields">')
    parts.append(_row("Size", _escape(f"{analysis.size:n} byte")))
    parts.append(_row("Encoding", _escape(analysis.encoding.value)))
    if analysis.signed_data is not None:
        parts.append(_row("Signed content", _escape(analysis.signed_data.content_type_name)))
    if analysis.nesting > 1:
        parts.append(_row("Nesting", _escape(f"{analysis.nesting} buste")))
    parts.append(_row("Signatures found", _escape(str(analysis.signature_count))))
    if analysis.signed_data is not None and analysis.signed_data.certificates:
        parts.append(
            _row("Certificates", _escape(str(len(analysis.signed_data.certificates))))
        )
    parts.append("</table>")

    if analysis.error:
        parts.append(
            f"<p style='color:{_RED}'>{_escape(tr_message(analysis.error))}</p>"
        )

    total = len(analysis.signers)
    if total:
        parts.append(_section("Signatures"))
        for index, signer in enumerate(analysis.signers):
            parts.append(_signer_block(signer, index, total))

    parts.append(_section("Payload"))
    parts.append('<table class="fields">')
    if analysis.payload_kind is not None:
        parts.append(_row("Type", _escape(tr(analysis.payload_kind.label))))
        parts.append(_row("Size", _escape(f"{analysis.payload_size:n} byte")))
    if result.output_path is not None:
        colour = _GREEN if result.written else _AMBER
        parts.append(_row("Written to", _escape(str(result.output_path)), colour))
    elif not analysis.has_payload:
        parts.append(_row("Output", _escape(tr("Not extracted")), _AMBER))
    parts.append("</table>")

    if analysis.warnings:
        parts.append(_section("Warnings"))
        parts.append("<ul class='warnings'>")
        for warning in analysis.warnings:
            parts.append(f"<li>{_escape(tr_message(warning))}</li>")
        parts.append("</ul>")

    parts.append(f"<p class='footer'>{_escape(tr(_DISCLAIMER))}</p></body>")
    return "".join(parts)


class DetailsPanel(QTextBrowser):
    """A read-only view of :func:`render_job`."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(False)
        self.setReadOnly(True)
        self._job: Job | None = None
        self.show_job(None)

    def show_job(self, job: Job | None) -> None:
        self._job = job
        self.setHtml(render_job(job))

    def refresh(self) -> None:
        """Re-render, for a job the queue has just finished or a language change."""
        self.show_job(self._job)

    @property
    def job(self) -> Job | None:
        return self._job
