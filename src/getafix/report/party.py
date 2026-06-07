"""Rendering for the trade parties (:mod:`getafix.schema.party`).

Builds the per-party panel (Seller / Buyer today; the same builder works
for any ``*TradeParty``) plus the two shared formatters every party
needs: :func:`format_address` for the postal block and
:func:`iter_tax_ids` for the VAT / tax-number lines.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from getafix.report._types import described_panel
from getafix.schema.party import PostalTradeAddressExtended

if TYPE_CHECKING:
    from getafix.schema.party import (
        BuyerTradeParty,
        PostalTradeAddress,
        SellerTradeParty,
    )

# One-line "what is this party" descriptions keyed by display role.
_PARTY_DESCRIPTIONS = {
    "Seller": "The supplier of the goods or services (BG-4).",
    "Buyer": "The customer receiving the goods or services (BG-7).",
}


def party_panel(role: str, party: SellerTradeParty | BuyerTradeParty | None) -> Panel:
    """Render one trade party as a green-bordered, titled panel."""
    description = _PARTY_DESCRIPTIONS.get(role, "Trade party.")
    if party is None:
        return described_panel(
            "(not set)", title=role, description=description, border_style="green"
        )
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    grid.add_row("Name:", party.name or "")
    if party.legal_organization is not None and party.legal_organization.trade_name:
        grid.add_row("Trading as:", party.legal_organization.trade_name)
    addr_text = format_address(party.address)
    if addr_text:
        grid.add_row("Address:", addr_text)
    if party.contact is not None:
        if party.contact.person_name:
            grid.add_row("Contact:", party.contact.person_name)
        if party.contact.email and party.contact.email.address:
            grid.add_row("E-mail:", party.contact.email.address)
        if party.contact.telephone and party.contact.telephone.number:
            grid.add_row("Phone:", party.contact.telephone.number)
    if party.electronic_address is not None and party.electronic_address.uri_id.id:
        uri = party.electronic_address.uri_id
        grid.add_row(
            "Electronic addr.:",
            f"{uri.id}"
            + (f" [dim](scheme {uri.scheme_id})[/dim]" if uri.scheme_id else ""),
        )
    for label, value in iter_tax_ids(party):
        grid.add_row(f"{label}:", value)
    return described_panel(
        grid,
        title=f"[bold]{role}[/bold]",
        description=description,
        border_style="green",
    )


def iter_tax_ids(
    party: SellerTradeParty | BuyerTradeParty,
) -> Iterable[tuple[str, str]]:
    """Yield ``(label, value)`` for each tax registration (VAT / tax number)."""
    for reg in party.tax_registrations or []:
        scheme = reg.id.scheme_id or "Tax ID"
        label = {"VA": "VAT ID", "FC": "Tax number"}.get(scheme, scheme)
        yield label, reg.id.id


def format_address(addr: PostalTradeAddress | PostalTradeAddressExtended | None) -> str:
    """Render a postal address as newline-separated lines (BG-5 / BG-8 / …)."""
    if addr is None:
        return ""
    lines: list[str] = [
        line for line in (addr.line_one, addr.line_two, addr.line_three) if line
    ]
    city_bits = [bit for bit in (addr.postcode, addr.city_name) if bit]
    if city_bits:
        lines.append(" ".join(city_bits))
    if isinstance(addr, PostalTradeAddressExtended) and addr.country_subdivision:
        lines.append(addr.country_subdivision)
    if addr.country_id:
        lines.append(addr.country_id)
    return "\n".join(lines)
