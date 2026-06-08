"""Rendering for the header trade settlement (:mod:`getafix.schema.settlement`).

The settlement is the busiest schema module, so its report counterpart
contributes both rows that fold into other sections and panels of its
own:

* :func:`billing_period_row` / :func:`preceding_invoice_rows` — rows the
  Invoice panel folds in (BG-14 period, BG-3 preceding invoices);
* :func:`payment_panel` — how and to whom to pay (BG-10 / BG-16 / BT-20);
* :func:`logistics_charges_panel` — logistics service charges (BG-X-42,
  EXTENDED);
* :func:`advance_payments_panel` — prepayments (BG-X-45, EXTENDED).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.table import Table

from getafix.report._types import describe_table, described_panel
from getafix.report.references import format_reference
from getafix.report.types import format_vat, scheme_suffix

if TYPE_CHECKING:
    from getafix.schema.settlement import TradeSettlement


def billing_period_row(settlement: TradeSettlement) -> tuple[str, str] | None:
    """Invoicing period (BG-14) as a ``start → end`` row, or ``None``."""
    period = settlement.billing_period
    if period is None or not (period.start or period.end):
        return None
    start = period.start.isoformat() if period.start else "…"
    end = period.end.isoformat() if period.end else "…"
    return "Period (BG-14):", f"{start} → {end}"


def preceding_invoice_rows(settlement: TradeSettlement):
    """Yield a ``(label, value)`` row per preceding-invoice reference (BT-25)."""
    for ref in settlement.invoice_referenced_document or []:
        yield "Preceding invoice (BT-25):", format_reference(ref)


def accounting_currency_row(settlement: TradeSettlement) -> tuple[str, str] | None:
    """VAT accounting currency (BT-6) row, or ``None`` when not set.

    Present only when VAT is accounted in a currency other than the
    invoice currency (BT-5); the matching total is BT-111.
    """
    if settlement.tax_currency_code is None:
        return None
    return "VAT acct currency (BT-6):", settlement.tax_currency_code


def accounting_reference_rows(settlement: TradeSettlement):
    """Yield a ``(label, value)`` row per Buyer accounting reference (BT-19)."""
    for account in settlement.accounting_account or []:
        yield "Booking ref (BT-19):", account.id


def payment_panel(settlement: TradeSettlement) -> RenderableType | None:
    """Payment instructions: payee, terms, means, bank account, references.

    Returns ``None`` when the settlement carries no payment information
    at all.
    """
    if not (
        settlement.payment_means
        or settlement.terms
        or settlement.payment_reference
        or settlement.creditor_reference
        or settlement.payee
    ):
        return None
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    payee = settlement.payee
    if payee is not None:
        grid.add_row("Payee (BG-10):", payee.name)
        for pid in payee.id or []:
            grid.add_row("Payee id (BT-60):", pid)
        if payee.global_id is not None:
            grid.add_row(
                "Payee id (BT-60-0):",
                f"{payee.global_id.id}{scheme_suffix(payee.global_id.scheme_id)}",
            )
    for t in settlement.terms or []:
        if t.description:
            grid.add_row("Terms:", t.description)
        if t.due:
            grid.add_row("Due date:", t.due.isoformat())
        if t.debit_mandate_id:
            grid.add_row("SEPA mandate:", t.debit_mandate_id)
    for pm in settlement.payment_means or []:
        grid.add_row("Means (BT-81):", pm.type_code)
        if pm.information:
            grid.add_row("Means info (BT-82):", pm.information)
        if pm.payee is not None:
            if pm.payee.iban_id:
                grid.add_row("IBAN (BT-84):", pm.payee.iban_id)
            if pm.payee.proprietary_id:
                grid.add_row("Account (BT-84):", pm.payee.proprietary_id)
            if pm.payee.account_name:
                grid.add_row("Account name (BT-85):", pm.payee.account_name)
        if pm.creditor_institution is not None and pm.creditor_institution.bic_id:
            grid.add_row("BIC (BT-86):", pm.creditor_institution.bic_id)
        if pm.financial_card is not None:
            holder = pm.financial_card.cardholder_name
            value = f"··· {pm.financial_card.id}"
            if holder:
                value += f" ({holder})"
            grid.add_row("Card (BG-18):", value)
        if pm.payer is not None and pm.payer.iban_id:
            grid.add_row("Debited IBAN (BT-91):", pm.payer.iban_id)
    if settlement.payment_reference:
        grid.add_row("Reference (BT-83):", settlement.payment_reference)
    if settlement.creditor_reference:
        grid.add_row("Creditor id (BT-90):", settlement.creditor_reference)
    return described_panel(
        grid,
        title="[bold]Payment[/bold]",
        description="How and to whom the invoice should be paid.",
        border_style="magenta",
    )


def logistics_charges_panel(settlement: TradeSettlement) -> Table | None:
    """Logistics service charges (BG-X-42); EXTENDED only.

    One row per :class:`~getafix.schema.settlement.LogisticsServiceCharge`
    (description, applied amount, VAT category + rate). Returns ``None``
    for BASIC / COMFORT documents and for EXTENDED documents that don't
    carry any logistics charge.
    """
    items = settlement.logistics_service_charges or []
    if not items:
        return None
    currency = settlement.currency_code
    table = Table(
        title="Logistics service charges (BG-X-42)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Description")
    table.add_column(f"Amount [{currency}]", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)
    for lsc in items:
        # Each logistics charge has 1..* AppliedTradeTax rows; in the
        # common case there's exactly one — render its category + rate.
        # If there are multiple, join with " / ".
        vat_cells = [
            format_vat(atx.category_code, atx.rate_applicable_percent)
            for atx in lsc.applied_trade_tax
        ]
        table.add_row(
            lsc.description,
            f"{lsc.applied_amount}",
            " / ".join(vat_cells) if vat_cells else "-",
        )
    return describe_table(table, "Freight, handling and insurance charges (EXTENDED).")


def advance_payments_panel(settlement: TradeSettlement) -> Table | None:
    """Advance payments / prepayments (BG-X-45); EXTENDED only.

    One row per :class:`~getafix.schema.settlement.AdvancePayment`
    (received date, paid amount, included tax category + rate + amount,
    optional prepayment invoice reference). Returns ``None`` for BASIC /
    COMFORT documents and for EXTENDED documents with no prepayment.
    """
    items = settlement.advance_payments or []
    if not items:
        return None
    currency = settlement.currency_code
    table = Table(
        title="Advance payments (BG-X-45)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Received", no_wrap=True)
    table.add_column(f"Paid [{currency}]", justify="right")
    table.add_column("Included VAT", justify="right", no_wrap=True)
    table.add_column("Prepayment invoice")
    for adv in items:
        # IncludedTradeTax is 1..* per XSD; common case is one row.
        # Render each as "<calculated> @ <rate>% <category>" and
        # join with " / " when several.
        vat_cells: list[str] = []
        for tax in adv.included_trade_tax:
            rate = tax.rate_applicable_percent
            calc = tax.calculated_amount
            cell = f"{calc}" if calc is not None else "—"
            if rate is not None:
                cell = f"{cell} @ {rate}% {tax.category_code.value}"
            else:
                cell = f"{cell} {tax.category_code.value}"
            vat_cells.append(cell)
        ref = adv.invoice_referenced_document
        ref_cell = "—"
        if ref is not None:
            ref_cell = ref.issuer_assigned_id
            if ref.issue_date_time is not None:
                ref_cell = f"{ref_cell} ({ref.issue_date_time.isoformat()})"
        table.add_row(
            adv.received_date_time.isoformat() if adv.received_date_time else "—",
            f"{adv.paid_amount}",
            " / ".join(vat_cells) if vat_cells else "-",
            ref_cell,
        )
    return describe_table(table, "Amounts already paid before this invoice (EXTENDED).")
