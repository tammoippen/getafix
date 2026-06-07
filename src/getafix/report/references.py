"""Rendering for the ``*ReferencedDocument`` family (:mod:`getafix.schema.references`).

Every referenced document on the invoice shares the same surface shape
for display purposes — an issuer-assigned identifier and an optional
issue date. :func:`format_reference` renders that shape once and is
reused by the Invoice panel (preceding invoices, BT-25), the Delivery
panel (despatch / receiving advice, BT-16 / BT-15) and anywhere else a
reference needs to show its date inline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import date


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
        value += f" [dim]({ref.issue_date_time.isoformat()})[/dim]"
    return value
