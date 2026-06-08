"""Rendering for the invoice-line sub-tree (:mod:`getafix.schema.line`).

A single line spreads across several schema elements; this module turns
them into the cells the line-items table shows:

* :func:`item_cell` — the Item column: the BG-31 product plus the
  line-scoped detail (classification, note, period, line allowances /
  charges, references) as dim follow-up lines;
* :func:`net_price_cell` — the net price (BT-146) with the gross-price /
  discount / basis-quantity derivation (BT-148 / BT-147 / BT-149) shown
  dim underneath;
* :func:`line_vat_cell` — the per-line VAT category + rate (BG-30).

The table that arranges these cells lives in :mod:`getafix.report.trade`,
mirroring how ``TradeLineItem`` lives in ``schema/trade.py`` while the
line sub-elements live in ``schema/line.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from getafix.report.types import format_vat

if TYPE_CHECKING:
    from collections.abc import Iterable

    from getafix.schema.accounting import ApplicableTradeTax
    from getafix.schema.line import LineTradeAgreement, ProductClassification
    from getafix.schema.trade import TradeLineItem


def _dim(text: str) -> str:
    return f"[dim]{text}[/dim]"


def item_cell(item: TradeLineItem) -> str:
    """Compose the Item column for one invoice line.

    The item name (BT-153) on top, then — all as dim follow-up lines —
    the description (BT-154), identifiers (BT-157 standard / BT-155
    seller / BT-156 buyer), classification (BG-33), characteristics
    (BG-32), origin (BG-34), line note (BT-127), invoicing period
    (BG-26), line allowances / charges (BG-27 / BG-28) and line
    references (BT-132 / BT-128 / BT-133).
    """
    product = item.product
    lines: list[str] = [product.name or ""]
    if product.description:
        lines.append(_dim(product.description))
    id_bits: list[str] = []
    if product.global_id is not None and product.global_id.id:
        id_bits.append(f"Std#: {product.global_id.id}")
    if product.seller_assigned_id:
        id_bits.append(f"Seller#: {product.seller_assigned_id}")
    if product.buyer_assigned_id:
        id_bits.append(f"Buyer#: {product.buyer_assigned_id}")
    if id_bits:
        lines.append(_dim(" · ".join(id_bits)))
    classes = product.classifications or []
    if classes:
        rendered = " · ".join(_classification(c) for c in classes[:3])
        if len(classes) > 3:
            rendered += f" · (+{len(classes) - 3})"
        lines.append(_dim(f"Class: {rendered}"))
    chars = product.characteristics or []
    if chars:
        rendered = " · ".join(f"{c.description}: {c.value}" for c in chars[:3])
        if len(chars) > 3:
            rendered += f" · (+{len(chars) - 3})"
        lines.append(_dim(rendered))
    if product.origin_country is not None:
        lines.append(_dim(f"Origin: {product.origin_country.id}"))
    note = item.associated_document.note
    if note is not None and note.content:
        lines.append(_dim(f"Note: {note.content}"))
    period = item.settlement.billing_period
    if period is not None and (period.start or period.end):
        start = period.start.isoformat() if period.start else "…"
        end = period.end.isoformat() if period.end else "…"
        lines.append(_dim(f"Period: {start} → {end}"))
    for ac in item.settlement.allowance_charge or []:
        kind = "Charge" if ac.indicator else "Allowance"
        sign = "+" if ac.indicator else "-"
        reason = f" {ac.reason}" if ac.reason else ""
        lines.append(_dim(f"{sign} {kind}:{reason} {ac.actual_amount}"))
    lines.extend(_dim(bit) for bit in _line_reference_bits(item))
    return "\n".join(lines)


def net_price_cell(agreement: LineTradeAgreement) -> str:
    """Net price (BT-146) with its gross-price derivation underneath.

    Shows the net unit price on top; when a gross price (BT-148) is
    given, a dim ``gross … -discount`` line (BT-147) follows, and a dim
    ``per N unit`` line when the price applies to a base quantity
    (BT-149) other than one. Returns ``—`` on EXTENDED GROUP /
    INFORMATION lines, which carry no net price.
    """
    net = agreement.net_price
    if net is None:
        return "—"
    lines = [f"{net.charge_amount}"]
    gross = agreement.gross_price
    if gross is not None:
        bits = [f"gross {gross.charge_amount}"]
        discount = gross.applied_allowance_charge
        if discount is not None:
            sign = "+" if discount.indicator else "-"
            bits.append(f"{sign}{discount.actual_amount}")
        lines.append(_dim(" ".join(bits)))
    basis = net.basis_quantity
    if basis is not None and basis.value != 1:
        lines.append(_dim(f"per {basis.value} {basis.unit_code}"))
    return "\n".join(lines)


def line_vat_cell(tax: ApplicableTradeTax | None) -> str:
    """Per-line VAT cell (BG-30): ``<rate>% <category>``.

    EXTENDED GROUP / INFORMATION lines carry no line VAT — render an
    em-dash placeholder in that case.
    """
    if tax is None:
        return "—"
    return format_vat(tax.category_code, tax.rate_applicable_percent)


def _classification(classification: ProductClassification) -> str:
    """One item classification (BG-33) as ``<code> (<scheme>)``."""
    out = classification.class_code
    if classification.list_id:
        out += f" ({classification.list_id})"
    return out


def _line_reference_bits(item: TradeLineItem) -> Iterable[str]:
    """Yield the line-level references: order line, object id, account."""
    order = item.agreement.buyer_order_ref
    if order is not None and order.line_id:
        yield f"Order line: {order.line_id}"
    for ref in item.settlement.additional_references or []:
        yield f"Obj id: {ref.issuer_assigned_id}"
    account = item.settlement.accounting_account
    if account is not None:
        yield f"Acct: {account.id}"
