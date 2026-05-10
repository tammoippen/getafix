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

from collections.abc import Iterator
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
from carthorse.schema.party import BuyerTradeParty, SpecifiedTaxRegistration
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.types import CategoryCode, Namespace, Profile


def _iter_tax_registrations(
    registrations: (SpecifiedTaxRegistration | list[SpecifiedTaxRegistration] | None),
) -> Iterator[SpecifiedTaxRegistration]:
    """Yield each SpecifiedTaxRegistration regardless of carthorse's
    inconsistent cardinality on the field (some parties carry a single
    registration, others a ``list[...] | None``)."""
    if registrations is None:
        return
    if isinstance(registrations, list):
        yield from registrations
    else:
        yield registrations


def _has_vat_id(party: object) -> bool:
    if party is None:
        return False
    return any(
        tr.id.scheme_id == "VA"
        for tr in _iter_tax_registrations(getattr(party, "tax_registrations", None))
    )


def _has_vat_or_local_tax_id(party: object) -> bool:
    if party is None:
        return False
    return any(
        tr.id.scheme_id in ("VA", "FC")
        for tr in _iter_tax_registrations(getattr(party, "tax_registrations", None))
    )


def _has_buyer_legal_id(buyer: BuyerTradeParty) -> bool:
    return (
        buyer.legal_organization is not None and buyer.legal_organization.id is not None
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
        ``docs/VALIDATION.md §3.2``; this method walks every category
        family in turn.
        """
        seller = self.agreement.seller
        buyer = self.agreement.buyer
        tax_rep = self.agreement.seller_tax_representative_party

        # Predicates encoding the per-category required-party rules.
        # Returns True iff the rule is satisfied for the given parties.
        s_vat_local_or_taxrep = _has_vat_or_local_tax_id(seller) or _has_vat_id(tax_rep)
        s_vat_or_taxrep = _has_vat_id(seller) or _has_vat_id(tax_rep)
        b_vat_or_legal = _has_vat_id(buyer) or _has_buyer_legal_id(buyer)
        b_vat = _has_vat_id(buyer)

        ae_ok = s_vat_local_or_taxrep and b_vat_or_legal
        e_ok = s_vat_local_or_taxrep
        g_ok = s_vat_or_taxrep  # Export outside EU — VAT only, not BT-32.
        ic_ok = s_vat_or_taxrep and b_vat  # Intra-community — both VAT.

        # category → (predicate-ok, message stem, (line/all/charge BR codes))
        families: list[tuple[CategoryCode, bool, str, tuple[str, str, str]]] = [
            (
                CategoryCode.T_AE,
                ae_ok,
                "VAT category 'Reverse charge' (AE) requires the Seller "
                "VAT identifier (BT-31), the Seller tax registration "
                "identifier (BT-32) and/or the Seller tax representative "
                "VAT identifier (BT-63), and the Buyer VAT identifier "
                "(BT-48) and/or the Buyer legal registration identifier "
                "(BT-47).",
                ("BR-AE-2", "BR-AE-3", "BR-AE-4"),
            ),
            (
                CategoryCode.T_E,
                e_ok,
                "VAT category 'Exempt from VAT' (E) requires the Seller "
                "VAT identifier (BT-31), the Seller tax registration "
                "identifier (BT-32) and/or the Seller tax representative "
                "VAT identifier (BT-63).",
                ("BR-E-2", "BR-E-3", "BR-E-4"),
            ),
            (
                CategoryCode.T_G,
                g_ok,
                "VAT category 'Export outside the EU' (G) requires the "
                "Seller VAT identifier (BT-31) or the Seller tax "
                "representative VAT identifier (BT-63). The local tax "
                "identifier (BT-32) is *not* sufficient.",
                ("BR-G-2", "BR-G-3", "BR-G-4"),
            ),
            (
                CategoryCode.T_K,
                ic_ok,
                "VAT category 'Intra-community supply' (K) requires the "
                "Seller VAT identifier (BT-31) or the Seller tax "
                "representative VAT identifier (BT-63), and the Buyer VAT "
                "identifier (BT-48).",
                ("BR-IC-2", "BR-IC-3", "BR-IC-4"),
            ),
            (
                CategoryCode.T_L,
                e_ok,  # IGIC: same predicate as Exempt — VAT/local/tax-rep.
                "VAT category 'IGIC' (L, Canary Islands) requires the "
                "Seller VAT identifier (BT-31), the Seller tax registration "
                "identifier (BT-32) and/or the Seller tax representative "
                "VAT identifier (BT-63).",
                ("BR-IG-2", "BR-IG-3", "BR-IG-4"),
            ),
            (
                CategoryCode.T_M,
                e_ok,  # IPSI: same predicate.
                "VAT category 'IPSI' (M, Ceuta/Melilla) requires the "
                "Seller VAT identifier (BT-31), the Seller tax registration "
                "identifier (BT-32) and/or the Seller tax representative "
                "VAT identifier (BT-63).",
                ("BR-IP-2", "BR-IP-3", "BR-IP-4"),
            ),
            (
                CategoryCode.T_S,
                e_ok,
                "VAT category 'Standard rated' (S) requires the Seller "
                "VAT identifier (BT-31), the Seller tax registration "
                "identifier (BT-32) and/or the Seller tax representative "
                "VAT identifier (BT-63).",
                ("BR-S-2", "BR-S-3", "BR-S-4"),
            ),
            (
                CategoryCode.T_Z,
                e_ok,
                "VAT category 'Zero rated' (Z) requires the Seller VAT "
                "identifier (BT-31), the Seller tax registration identifier "
                "(BT-32) and/or the Seller tax representative VAT "
                "identifier (BT-63).",
                ("BR-Z-2", "BR-Z-3", "BR-Z-4"),
            ),
        ]

        for category, ok, msg, (br_line, br_alw, br_chg) in families:
            if ok:
                continue

            for item in self.items:
                if item.settlement.applicable_trade_tax.category_code == category:
                    raise ValidationError(br_line, f"{br_line}: {msg}")

            for ac in self.settlement.allowance_charge or []:
                if (
                    ac.category_trade_tax is None
                    or ac.category_trade_tax.category_code != category
                ):
                    continue
                code = br_chg if ac.indicator else br_alw
                raise ValidationError(code, f"{code}: {msg}")

        # BR-O — Not subject to VAT: inverted predicate. Each slot
        # carrying category 'O' forbids a different identifier set.
        s_has_vat_or_taxrep = _has_vat_id(seller) or _has_vat_id(tax_rep)

        for item in self.items:
            if item.settlement.applicable_trade_tax.category_code != CategoryCode.T_O:
                continue
            if s_has_vat_or_taxrep or buyer.id is not None:
                raise ValidationError(
                    "BR-O-2",
                    "An Invoice line with VAT category 'Not subject to VAT' "
                    "(O) shall not contain the Seller VAT identifier "
                    "(BT-31), the Seller tax representative VAT identifier "
                    "(BT-63) or the Buyer identifier (BT-46).",
                )

        for ac in self.settlement.allowance_charge or []:
            if (
                ac.category_trade_tax is None
                or ac.category_trade_tax.category_code != CategoryCode.T_O
            ):
                continue
            if s_has_vat_or_taxrep or _has_vat_id(buyer):
                code = "BR-O-4" if ac.indicator else "BR-O-3"
                raise ValidationError(
                    code,
                    f"{code}: A document-level "
                    f"{'charge' if ac.indicator else 'allowance'} "
                    "with VAT category 'Not subject to VAT' (O) shall not "
                    "contain the Seller VAT identifier (BT-31), the Seller "
                    "tax representative VAT identifier (BT-63) or the "
                    "Buyer VAT identifier (BT-48).",
                )

        # BR-IC-11 / BR-IC-12 — intra-community supply needs evidence of
        # cross-border delivery: a delivery date (BT-72) or invoicing
        # period (BG-14), and the deliver-to country code (BT-80).
        ic_in_use = any(
            item.settlement.applicable_trade_tax.category_code == CategoryCode.T_K
            for item in self.items
        ) or any(
            ac.category_trade_tax is not None
            and ac.category_trade_tax.category_code == CategoryCode.T_K
            for ac in self.settlement.allowance_charge or []
        )
        if ic_in_use:
            event = self.delivery.event
            has_delivery_date = event is not None and event.occurrence is not None
            period = self.settlement.billing_period
            has_period = period is not None and (
                period.start is not None or period.end is not None
            )
            if not (has_delivery_date or has_period):
                raise ValidationError(
                    "BR-IC-11",
                    "An Invoice with a VAT breakdown row of category "
                    "'Intra-community supply' (K) shall contain the actual "
                    "delivery date (BT-72) or the invoicing period (BG-14).",
                )

            ship_to = self.delivery.ship_to
            has_ship_to_country = (
                ship_to is not None
                and ship_to.address is not None
                and bool(ship_to.address.country_id)
            )
            if not has_ship_to_country:
                raise ValidationError(
                    "BR-IC-12",
                    "An Invoice with a VAT breakdown row of category "
                    "'Intra-community supply' (K) shall contain the "
                    "deliver-to country code (BT-80).",
                )

        # BR-O-11..14 — single-rate restriction. If any header BG-23 row
        # carries category 'O', the rest of the invoice must be O too:
        # no other BG-23 row, no non-O line / allowance / charge.
        trade_taxes = self.settlement.trade_taxes or []
        has_o_row = any(t.category_code == CategoryCode.T_O for t in trade_taxes)
        if has_o_row:
            if any(t.category_code != CategoryCode.T_O for t in trade_taxes):
                raise ValidationError(
                    "BR-O-11",
                    "An Invoice with a VAT breakdown row of category "
                    "'Not subject to VAT' (O) shall not contain other VAT "
                    "breakdown rows (BG-23).",
                )
            for item in self.items:
                if (
                    item.settlement.applicable_trade_tax.category_code
                    != CategoryCode.T_O
                ):
                    raise ValidationError(
                        "BR-O-12",
                        "An Invoice with a VAT breakdown row of category "
                        "'Not subject to VAT' (O) shall not contain an "
                        "Invoice line whose category code is not 'Not "
                        "subject to VAT'.",
                    )
            for ac in self.settlement.allowance_charge or []:
                if (
                    ac.category_trade_tax is None
                    or ac.category_trade_tax.category_code == CategoryCode.T_O
                ):
                    continue
                code = "BR-O-14" if ac.indicator else "BR-O-13"
                raise ValidationError(
                    code,
                    f"{code}: An Invoice with a VAT breakdown row of "
                    "category 'Not subject to VAT' (O) shall not contain a "
                    f"document-level {'charge' if ac.indicator else 'allowance'} "
                    "whose VAT category code is not 'Not subject to VAT'.",
                )
