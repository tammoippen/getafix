"""Rendering for the header trade agreement (:mod:`getafix.schema.agreement`).

The agreement holds the upstream references that frame the invoice
(buyer reference, purchase / sales order, contract, project). They are
shown as rows inside the top-level Invoice panel rather than a panel of
their own, so this module contributes :func:`reference_rows` — the rows
:func:`getafix.report.document.header_panel` folds in.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

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
