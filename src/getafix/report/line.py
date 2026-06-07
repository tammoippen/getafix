"""Rendering for the invoice-line sub-tree (:mod:`getafix.schema.line`).

A single line spreads across several schema elements; this module turns
them into the cells the line-items table shows:

* :func:`item_cell` — the item block (BG-31 product) with its COMFORT
  enrichments (description, ids, characteristics, origin);
* :func:`line_vat_cell` — the per-line VAT category + rate (BG-30).

The table that arranges these cells lives in
:mod:`getafix.report.trade`, mirroring how ``TradeLineItem`` lives in
``schema/trade.py`` while the line sub-elements live in ``schema/line.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from getafix.report.types import format_vat

if TYPE_CHECKING:
    from getafix.schema.accounting import ApplicableTradeTax
    from getafix.schema.line import TradeProduct


def item_cell(product: TradeProduct) -> str:
    """Compose the ``Item`` cell: name plus optional COMFORT enrichments.

    Renders the item name (BT-153) followed by BT-154 description,
    BT-155 / BT-156 ids, BG-32 characteristics and BG-34 origin as dim
    follow-up lines.
    """
    lines: list[str] = [product.name or ""]
    if product.description:
        lines.append(f"[dim]{product.description}[/dim]")
    id_bits: list[str] = []
    if product.seller_assigned_id:
        id_bits.append(f"Seller#: {product.seller_assigned_id}")
    if product.buyer_assigned_id:
        id_bits.append(f"Buyer#: {product.buyer_assigned_id}")
    if id_bits:
        lines.append(f"[dim]{' · '.join(id_bits)}[/dim]")
    chars = product.characteristics or []
    if chars:
        rendered = " · ".join(f"{c.description}: {c.value}" for c in chars[:3])
        if len(chars) > 3:
            rendered += f" · (+{len(chars) - 3})"
        lines.append(f"[dim]{rendered}[/dim]")
    if product.origin_country is not None:
        lines.append(f"[dim]Origin: {product.origin_country.id}[/dim]")
    return "\n".join(lines)


def line_vat_cell(tax: ApplicableTradeTax | None) -> str:
    """Per-line VAT cell (BG-30): ``<rate>% <category>``.

    EXTENDED GROUP / INFORMATION lines carry no line VAT — render an
    em-dash placeholder in that case.
    """
    if tax is None:
        return "—"
    return format_vat(tax.category_code, tax.rate_applicable_percent)
