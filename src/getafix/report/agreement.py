"""Rendering for the header trade agreement (:mod:`getafix.schema.agreement`).

The agreement holds the upstream references that frame the invoice. The
short ones (buyer reference, purchase / sales order, contract, project)
are shown as rows inside the top-level Invoice panel via
:func:`reference_rows`; the richer BG-24 supporting documents get their
own table via :func:`supporting_documents_panel`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from rich.table import Table

from getafix.report._types import describe_table
from getafix.report.references import format_attachment

if TYPE_CHECKING:
    from getafix.schema.agreement import TradeAgreement


def reference_rows(agreement: TradeAgreement) -> Iterable[tuple[str, str]]:
    """Yield ``(label, value)`` for each populated agreement reference.

    Order matches the XSD sequence: buyer reference (BT-10), purchase
    order (BT-13), sales order (BT-14), contract (BT-12), project
    (BT-11).
    """
    if agreement.buyer_reference:
        yield "Buyer reference (BT-10):", agreement.buyer_reference
    if agreement.buyer_order is not None:
        yield "Purchase order (BT-13):", agreement.buyer_order.issuer_assigned_id
    if agreement.seller_order is not None:
        yield "Sales order (BT-14):", agreement.seller_order.issuer_assigned_id
    if agreement.contract is not None:
        yield "Contract (BT-12):", agreement.contract.issuer_assigned_id
    if agreement.procuring_project is not None:
        proj = agreement.procuring_project
        yield "Project (BT-11):", f"{proj.id} — {proj.name}"


def supporting_documents_panel(agreement: TradeAgreement) -> Table | None:
    """Additional supporting documents (BG-24); ``None`` when none present.

    One row per :class:`~getafix.schema.references.AdditionalReferencedDocument`
    — the reference id (BT-122 / BT-17 / BT-18), description (BT-123),
    document type code (BT-17-0 / BT-18-0 / BT-122-0) and the document
    itself: an embedded attachment (BT-125) summarised by filename / MIME,
    or an external URL (BT-124).
    """
    refs = agreement.additional_references or []
    if not refs:
        return None
    table = Table(
        title="Supporting documents (BG-24)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Reference", no_wrap=True)
    table.add_column("Description")
    table.add_column("Type", no_wrap=True)
    table.add_column("Attachment / URL")
    for ref in refs:
        if ref.attached_object is not None:
            document = format_attachment(ref.attached_object)
        elif ref.uriid:
            document = ref.uriid
        else:
            document = "-"
        table.add_row(
            ref.issuer_assigned_id,
            ref.name or "",
            ref.type_code.value if ref.type_code is not None else "-",
            document,
        )
    return describe_table(
        table, "Documents substantiating the invoice (BT-122 / BT-124 / BT-125)."
    )
