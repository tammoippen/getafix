"""Rendering for the trade parties (:mod:`getafix.schema.party`).

Builds the per-party panels plus the shared formatters every party
needs:

* :func:`party_panel` — the Seller / Buyer panel (name, identifiers,
  legal organisation, address, contact, tax ids);
* :func:`tax_representative_panel` — the Seller's tax representative
  (BG-11);
* :func:`format_address` / :func:`iter_tax_ids` — reused by the panels
  above and by the Delivery / Payment sections.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table

from getafix.report._types import described_panel
from getafix.report.types import scheme_suffix
from getafix.schema.party import PostalTradeAddressExtended, SellerTradeParty

if TYPE_CHECKING:
    from getafix.schema.party import (
        BuyerTradeParty,
        PostalTradeAddress,
        SellerTaxRepresentativeTradeParty,
        SpecifiedTaxRegistration,
    )

# One-line "what is this party" descriptions keyed by display role.
_PARTY_DESCRIPTIONS = {
    "Seller": "The supplier of the goods or services (BG-4).",
    "Buyer": "The customer receiving the goods or services (BG-7).",
}

# Per-role BT ids for the identification rows. Seller and Buyer share the
# same fields with parallel BT numbering; an unknown role gets no id
# suffix (the row still renders, just without the cross-reference).
_PARTY_BT: dict[str, dict[str, str]] = {
    "Seller": {
        "id": "BT-29",
        "global": "BT-29-0",
        "legal": "BT-30",
        "info": "BT-33",
        "dept": "BT-41-0",
    },
    "Buyer": {"id": "BT-46", "global": "BT-46-0", "legal": "BT-47", "dept": "BT-56-0"},
}


def _bt(role: str, field: str) -> str:
    """`` (BT-xx)`` suffix for ``field`` on ``role``, or empty when unmapped."""
    bt = _PARTY_BT.get(role, {}).get(field)
    return f" ({bt})" if bt else ""


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
    legal = party.legal_organization
    if legal is not None and legal.trade_name:
        grid.add_row("Trading as:", legal.trade_name)
    if party.id:
        grid.add_row(f"ID{_bt(role, 'id')}:", party.id)
    for gid in party.global_ids or []:
        grid.add_row(
            f"Global ID{_bt(role, 'global')}:",
            f"{gid.id}{scheme_suffix(gid.scheme_id)}",
        )
    if legal is not None and legal.id is not None:
        grid.add_row(
            f"Legal reg.{_bt(role, 'legal')}:",
            f"{legal.id.id}{scheme_suffix(legal.id.scheme_id)}",
        )
    # Additional legal information (BT-33) is Seller-only in the model.
    if isinstance(party, SellerTradeParty) and party.description:
        grid.add_row(f"Legal info{_bt(role, 'info')}:", party.description)
    addr_text = format_address(party.address)
    if addr_text:
        grid.add_row("Address:", addr_text)
    if party.contact is not None:
        if party.contact.person_name:
            grid.add_row("Contact:", party.contact.person_name)
        if party.contact.department_name:
            grid.add_row(
                f"Department{_bt(role, 'dept')}:", party.contact.department_name
            )
        if party.contact.email and party.contact.email.address:
            grid.add_row("E-mail:", party.contact.email.address)
        if party.contact.telephone and party.contact.telephone.number:
            grid.add_row("Phone:", party.contact.telephone.number)
    if party.electronic_address is not None and party.electronic_address.uri_id.id:
        uri = party.electronic_address.uri_id
        grid.add_row("Electronic addr.:", f"{uri.id}{scheme_suffix(uri.scheme_id)}")
    for label, value in iter_tax_ids(party):
        grid.add_row(f"{label}:", value)
    return described_panel(
        grid,
        title=f"[bold]{role}[/bold]",
        description=description,
        border_style="green",
    )


def tax_representative_panel(
    party: SellerTaxRepresentativeTradeParty | None,
) -> Panel | None:
    """Seller's tax representative (BG-11), or ``None`` when not set.

    The fiscal representative liable for the Seller's VAT — its own
    name (BT-62), address (BG-12) and VAT identifier (BT-63).
    """
    if party is None:
        return None
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()
    grid.add_row("Name:", party.name or "")
    addr_text = format_address(party.address)
    if addr_text:
        grid.add_row("Address:", addr_text)
    label, value = _tax_id_row(party.tax_registrations)
    grid.add_row(f"{label}:", value)
    return described_panel(
        grid,
        title="[bold]Tax representative[/bold]",
        description="The Seller's tax representative liable for the VAT (BG-11).",
        border_style="green",
    )


def iter_tax_ids(
    party: SellerTradeParty | BuyerTradeParty,
) -> Iterable[tuple[str, str]]:
    """Yield ``(label, value)`` for each tax registration (VAT / tax number)."""
    for reg in party.tax_registrations or []:
        yield _tax_id_row(reg)


def _tax_id_row(reg: SpecifiedTaxRegistration) -> tuple[str, str]:
    """Map one tax registration to its display ``(label, value)``."""
    scheme = reg.id.scheme_id or "Tax ID"
    label = {"VA": "VAT ID", "FC": "Tax number"}.get(scheme, scheme)
    return label, reg.id.id


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
