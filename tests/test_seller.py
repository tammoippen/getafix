"""BR-CO-26 — Seller must be identifiable by at least one of
BT-29 (id), BT-30 (legal organisation id) or BT-31 (VAT registration)."""

from __future__ import annotations

from getafix.schema.document import Profile
from getafix.schema.party import (
    ISO6523SchemeId,
    LegalOrganization,
    PostalTradeAddressExtended,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from getafix.schema.types import Country


def test_br_co_26_seller_must_be_identifiable():
    """BR-CO-26: at least one of BT-29 (Seller.id),
    BT-30 (Seller.legal_organization.id) or BT-31
    (Seller.tax_registrations[VAT]) must be present."""
    addr = PostalTradeAddressExtended(country_id=Country.DE)

    # No identifier — fails.
    seller = SellerTradeParty(name="Acme", address=addr)
    errors = seller.validate_internal(Profile.MINIMUM)
    assert any(v.code == "BR-CO-26" for v in errors)

    # BT-29 set — ok.
    seller.id = "S-1234"
    seller.validate_internal(Profile.MINIMUM)

    # BT-30 set (no BT-29) — ok.
    seller.id = None
    seller.legal_organization = LegalOrganization(
        id=ISO6523SchemeId(id="0123456789", scheme_id="0021")
    )
    seller.validate_internal(Profile.MINIMUM)

    # BT-31 set (no BT-29, no BT-30) — ok.
    seller.legal_organization = None
    seller.tax_registrations = [
        SpecifiedTaxRegistration(id=TaxSchemeId(id="DE123456789", scheme_id="VA"))
    ]
    seller.validate_internal(Profile.MINIMUM)

    # Only FC tax registration (no VA) doesn't satisfy BR-CO-26.
    seller.tax_registrations = [
        SpecifiedTaxRegistration(id=TaxSchemeId(id="201/113/40209", scheme_id="FC"))
    ]
    errors = seller.validate_internal(Profile.MINIMUM)
    assert any(v.code == "BR-CO-26" for v in errors)
