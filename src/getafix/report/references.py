"""Rendering for the ``*ReferencedDocument`` family (:mod:`getafix.schema.references`).

Every referenced document on the invoice shares the same surface shape
for display purposes — an issuer-assigned identifier and an optional
issue date. :func:`format_reference` renders that shape once and is
reused by the Invoice panel (preceding invoices, BT-25), the Delivery
panel (despatch / receiving advice, BT-16 / BT-15) and anywhere else a
reference needs to show its date inline. :func:`format_attachment`
summarises an embedded supporting document (BT-125).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from getafix.report.types import dim_paren, format_bytes

if TYPE_CHECKING:
    from datetime import date

    from getafix.schema.references import AttachmentBinaryObject


class ReferencedDocument(Protocol):
    """Structural type for any reference carrying an id and optional date."""

    @property
    def issuer_assigned_id(self) -> str: ...

    @property
    def issue_date_time(self) -> date | None: ...


def format_reference(ref: ReferencedDocument) -> str:
    """Issuer-assigned id, with the issue date in dim parentheses when set."""
    value = ref.issuer_assigned_id
    if ref.issue_date_time is not None:
        value += f" {dim_paren(ref.issue_date_time.isoformat())}"
    return value


def format_attachment(attachment: AttachmentBinaryObject) -> str:
    """Embedded supporting document (BT-125) as ``<filename> (<mime>, <size>)``.

    Summarises the binary payload by its file name (BT-125-2), MIME
    type (BT-125-1) and decoded size rather than dumping the base64
    content.
    """
    size = format_bytes(len(attachment.binary_object))
    return f"{attachment.filename} {dim_paren(f'{attachment.mime_code.value}, {size}')}"
