"""Rendering for the financial spine (:mod:`getafix.schema.accounting`).

Three sections, all driven off the header settlement:

* :func:`tax_table` — the VAT breakdown (BG-23), one row per category /
  rate;
* :func:`allowance_charge_panel` — document-level allowances (BG-20) and
  charges (BG-21);
* :func:`totals_panel` — the monetary summation (BG-22) down to the
  amount due.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from getafix.report._types import describe_table, described_panel
from getafix.report.types import dim_paren, format_amount, format_vat

if TYPE_CHECKING:
    from decimal import Decimal

    from getafix.schema.accounting import ApplicableTradeTax
    from getafix.schema.settlement import TradeSettlement


def tax_table(settlement: TradeSettlement) -> Table:
    """VAT breakdown (BG-23): taxable base and tax per category and rate."""
    currency = settlement.currency_code
    taxes = settlement.trade_taxes or []
    # The tax-point column (BT-7 date / BT-8 code) is rare — only add it
    # when at least one row carries it, so the common invoice stays narrow.
    has_tax_point = any(
        tax.tax_point_date is not None or tax.due_date_code is not None for tax in taxes
    )
    table = Table(
        title="VAT breakdown (BG-23)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Cat", no_wrap=True)
    table.add_column("Rate", justify="right")
    table.add_column(f"Basis [{currency}]", justify="right")
    table.add_column(f"Tax [{currency}]", justify="right")
    table.add_column("Exemption reason")
    if has_tax_point:
        table.add_column("Tax point (BT-7/8)", no_wrap=True)
    for tax in taxes:
        rate = tax.rate_applicable_percent
        reason = tax.exemption_reason or ""
        if tax.exemption_reason_code:
            reason = f"{dim_paren(tax.exemption_reason_code)} {reason}".strip()
        cells = [
            tax.category_code.value,
            f"{rate}%" if rate is not None else "-",
            f"{tax.basis_amount}" if tax.basis_amount is not None else "-",
            f"{tax.calculated_amount}" if tax.calculated_amount is not None else "-",
            reason,
        ]
        if has_tax_point:
            cells.append(_tax_point_cell(tax))
        table.add_row(*cells)
    return describe_table(
        table, "Taxable base and tax amount per VAT category and rate."
    )


def _tax_point_cell(tax: ApplicableTradeTax) -> str:
    """Tax point date (BT-7) or, failing that, the due-date code (BT-8)."""
    if tax.tax_point_date is not None:
        return tax.tax_point_date.isoformat()
    if tax.due_date_code is not None:
        return f"code {tax.due_date_code.value}"
    return "-"


def allowance_charge_panel(settlement: TradeSettlement) -> Table | None:
    """Document-level allowances (BG-20) and charges (BG-21).

    Each row shows the indicator label, reason, amount, optional VAT
    category + rate, and an optional ``% * basis`` derivation. Returns
    ``None`` if no header-level allowance/charge is present.
    """
    items = settlement.allowance_charge or []
    if not items:
        return None
    currency = settlement.currency_code
    table = Table(
        title="Document-level allowances & charges (BG-20 / BG-21)",
        title_style="bold",
        header_style="bold",
        border_style="blue",
        expand=True,
    )
    table.add_column("Kind", no_wrap=True)
    table.add_column("Reason")
    table.add_column(f"Amount [{currency}]", justify="right")
    table.add_column("Calc.", justify="right")
    table.add_column("VAT", justify="right", no_wrap=True)
    for ac in items:
        kind = "[red]Charge[/red]" if ac.indicator else "[green]Allowance[/green]"
        reason_bits = [ac.reason or ""]
        if ac.reason_code:
            reason_bits.append(dim_paren(ac.reason_code))
        if ac.calculation_percent is not None and ac.basis_amount is not None:
            calc = f"{ac.calculation_percent}% of {ac.basis_amount}"
        elif ac.calculation_percent is not None:
            calc = f"{ac.calculation_percent}%"
        elif ac.basis_amount is not None:
            calc = f"basis {ac.basis_amount}"
        else:
            calc = "-"
        ctt = ac.category_trade_tax
        vat = format_vat(ctt.category_code, ctt.rate_applicable_percent) if ctt else "-"
        table.add_row(
            kind,
            " ".join(b for b in reason_bits if b),
            f"{ac.actual_amount}",
            calc,
            vat,
        )
    return describe_table(
        table, "Discounts and surcharges applied to the whole invoice."
    )


def totals_panel(settlement: TradeSettlement) -> Panel:
    """Monetary summation (BG-22): line, tax and grand totals to amount due."""
    summ = settlement.monetary_summation
    currency = settlement.currency_code
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column(justify="right")
    rows: list[tuple[str, Decimal | None]] = [
        ("Line total (BT-106)", summ.line_total),
        ("Allowances (BT-107)", summ.allowance_total),
        ("Charges (BT-108)", summ.charge_total),
        ("Tax basis (BT-109)", summ.tax_basis_total),
    ]
    for label, value in rows:
        if value is None:
            continue
        grid.add_row(label, format_amount(value, currency))
    for tax in summ.tax_total or []:
        grid.add_row(
            f"Tax total ({tax.currency_id})", format_amount(tax.amount, tax.currency_id)
        )
    tail: list[tuple[str, Decimal | None]] = [
        ("Rounding (BT-114)", summ.rounding_amount),
        ("Grand total (BT-112)", summ.grand_total),
        ("Prepaid (BT-113)", summ.prepaid_total),
    ]
    for label, value in tail:
        if value is None:
            continue
        grid.add_row(label, format_amount(value, currency))
    grid.add_row(
        "[bold yellow]Amount due (BT-115)[/bold yellow]",
        f"[bold yellow]{format_amount(summ.due_amount, currency)}[/bold yellow]",
    )
    return described_panel(
        grid,
        title="[bold]Totals[/bold]",
        description="Net, tax and gross totals down to the amount due.",
        border_style="yellow",
    )
