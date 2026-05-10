"""Top-level ``SupplyChainTradeTransaction`` (BG-25-00) and BG-25 line items.

This module stitches together the three sibling header groups
(``agreement``, ``delivery``, ``settlement``) and a list of line items
(``items``). The line item content lives in
:mod:`carthorse.schema.line`.

Validation rules covered here:

* ✓ ``BR-16`` — at BASIC and above an invoice must contain at least
  one line item. Raised by :meth:`Trade.validate_internal`.
* ✓ Per-VAT-category required-party rules (BR-AE/E/G/IC/IG/IP/S/Z
  ``-2/-3/-4``) — see ``docs/VALIDATION.md §3.2``.
"""

from dataclasses import dataclass, field
from typing import ClassVar, override

from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.line import (
    DocumentLineDocument,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    TradeProduct,
)
from carthorse.schema.party import BuyerTradeParty, SellerTradeParty
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.types import CategoryCode, Namespace, Profile


def _has_vat_id(party: SellerTradeParty | BuyerTradeParty | None) -> bool:
    if party is None or not party.tax_registrations:
        return False
    return any(tr.id.scheme_id == "VA" for tr in party.tax_registrations)


def _has_vat_or_local_tax_id(party: SellerTradeParty | None) -> bool:
    if party is None or not party.tax_registrations:
        return False
    return any(
        tr.id.scheme_id in ("VA", "FC") for tr in party.tax_registrations
    )


def _has_buyer_legal_id(buyer: BuyerTradeParty) -> bool:
    return (
        buyer.legal_organization is not None
        and buyer.legal_organization.id is not None
    )


@dataclass(kw_only=True, slots=True)
class TradeLineItem(Element):
    """Invoice line item (BG-25).

    Carries the four required line-level groups in XSD order:
    ``AssociatedDocumentLineDocument`` (BT-126-00),
    ``SpecifiedTradeProduct`` (BG-31),
    ``SpecifiedLineTradeAgreement`` (BG-29),
    ``SpecifiedLineTradeDelivery`` (BT-129-00) and
    ``SpecifiedLineTradeSettlement`` (BG-30-00).

    Required from the BASIC profile onwards.

    EN 16931-ID: BG-25
    """

    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC

    associated_document: DocumentLineDocument
    product: TradeProduct
    agreement: LineTradeAgreement
    delivery: LineTradeDelivery
    settlement: LineTradeSettlement


@dataclass(kw_only=True, slots=True)
class Trade(Element):
    """Gruppierung der Informationen zum Geschäftsvorfall"""

    tag: ClassVar[str] = "SupplyChainTradeTransaction"
    namespace: ClassVar[Namespace] = Namespace.rsm

    agreement: TradeAgreement
    delivery: TradeDelivery
    settlement: TradeSettlement
    items: list[TradeLineItem] = field(default_factory=list)

    @override
    def validate_internal(self, profile: Profile) -> None:
        if Profile.BASIC_WL < profile and len(self.items) == 0:
            raise ValidationError(
                "BR-16",
                "An invoice must contain at least one invoice line item (BG-25).",
            )

        # Recurse into child validators first (so e.g. BR-CO-26 and
        # BR-CO-25 surface before our cross-field VAT-category checks).
        super(Trade, self).validate_internal(profile)

        self._validate_vat_category_required_parties()

    def _validate_vat_category_required_parties(self) -> None:
        """BR-AE/E/G/IC/IG/IP/S/Z-{2,3,4} required-party checks.

        For each line item / document-level allowance / document-level
        charge, the VAT category code constrains which Seller / Buyer
        identifiers must be present. The constraint matrix lives in
        ``docs/VALIDATION.md §3.2``.
        """
        seller = self.agreement.seller
        buyer = self.agreement.buyer
        tax_rep = self.agreement.seller_tax_representative_party

        seller_has_vat_or_local = _has_vat_or_local_tax_id(seller) or _has_vat_id(
            tax_rep
        )
        buyer_has_vat_or_legal = _has_vat_id(buyer) or _has_buyer_legal_id(buyer)

        # AE — Reverse charge: Seller must carry a VAT or local-tax id
        # (or the tax-rep does), and Buyer must carry a VAT id or legal
        # registration id. Same predicate, different rule code per the
        # element it appears on.
        ae_msg = (
            "{0}: VAT category 'Reverse charge' (AE) requires the Seller "
            "VAT identifier (BT-31), the Seller tax registration identifier "
            "(BT-32) and/or the Seller tax representative VAT identifier "
            "(BT-63), and the Buyer VAT identifier (BT-48) and/or the Buyer "
            "legal registration identifier (BT-47)."
        )
        ae_predicate_ok = seller_has_vat_or_local and buyer_has_vat_or_legal

        for item in self.items:
            if item.settlement.applicable_trade_tax.category_code == CategoryCode.T_AE:
                if not ae_predicate_ok:
                    raise ValidationError("BR-AE-2", ae_msg.format("BR-AE-2"))

        for ac in self.settlement.allowance_charge or []:
            if ac.category_trade_tax is None:
                continue
            if ac.category_trade_tax.category_code != CategoryCode.T_AE:
                continue
            if not ae_predicate_ok:
                code = "BR-AE-4" if ac.indicator else "BR-AE-3"
                raise ValidationError(code, ae_msg.format(code))
