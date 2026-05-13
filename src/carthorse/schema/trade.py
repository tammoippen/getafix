"""Supply chain trade transaction (BG-25-00) and BG-25 line items.

:class:`Trade` is the second sibling of :class:`Document` and
stitches together the three header groups
(:class:`~carthorse.schema.agreement.TradeAgreement` (BT-10-00),
:class:`~carthorse.schema.delivery.TradeDelivery` (BG-13-00),
:class:`~carthorse.schema.settlement.TradeSettlement` (BG-19)) with a
list of :class:`TradeLineItem` (BG-25, BASIC+). The line sub-tree
content lives in :mod:`carthorse.schema.line`.

This module is also where every *cross-sibling* validator lives —
rules that need to read across line items, header allowances/charges
and the monetary summation in one pass.

Validation rules enforced here:

* ✓ ``BR-16`` — at BASIC+ an invoice must contain at least one line
  item.
* ✓ ``BR-CO-10`` — ``BT-106 = sum(BT-131)`` across line totals.
* ✓ ``BR-CO-11`` — ``BT-107 = sum(BT-92)`` across header allowances.
* ✓ ``BR-CO-12`` — ``BT-108 = sum(BT-99)`` across header charges.
* ✓ ``BR-CO-13`` — ``BT-109 = sum(BT-131) - sum(BT-92) + sum(BT-99)``.
* ✓ ``BR-CO-21`` / ``BR-CO-22`` — header allowance / charge needs
  reason text or reason code.
* ✓ ``BR-CO-23`` / ``BR-CO-24`` — same coupling at line level.
* ✓ ``BR-AE/E/G/IC/IG/IP/S/Z-{2,3,4}`` — per-VAT-category
  required-party matrix (see ``docs/VALIDATION.md §3.2``).
* ✓ ``BR-O-2 / BR-O-3 / BR-O-4`` — "Not subject to VAT" forbidden-id
  matrix (inverted predicate of the above).
* ✓ ``BR-IC-11`` / ``BR-IC-12`` — intra-community supply needs
  delivery date or period (BT-72 / BG-14) and a deliver-to country
  code (BT-80).
* ✓ ``BR-O-11..14`` — "Not subject to VAT" is single-rate.

See ``docs/VALIDATION.md`` for the full BR-* catalogue.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
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
    """Invoice line (BG-25).

    A group of business terms providing information on an individual
    invoice line. Required from BASIC upwards.
    """

    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC

    associated_document: DocumentLineDocument
    """Associated line document (BT-126-00) — line id and optional note."""
    product: TradeProduct
    """Item information (BG-31) — what is being invoiced."""
    agreement: LineTradeAgreement
    """Line trade agreement (BG-29) — gross and net price."""
    delivery: LineTradeDelivery
    """Line trade delivery (BT-129-00) — invoiced quantity."""
    settlement: LineTradeSettlement
    """Line trade settlement (BG-30-00) — line VAT, period,
    allowances/charges, line total."""


@dataclass(kw_only=True, slots=True)
class Trade(Element):
    """Supply chain trade transaction (BG-25-00).

    The header business-transaction wrapper. Holds the three sibling
    header groups (agreement, delivery, settlement) plus the list of
    line items, and is where every cross-sibling validator runs (see
    module docstring for the BR-* catalogue).
    """

    tag: ClassVar[str] = "SupplyChainTradeTransaction"
    namespace: ClassVar[Namespace] = Namespace.rsm

    items: list[TradeLineItem] = field(default_factory=list)
    """Invoice lines (BG-25, 0..*); required at BASIC+ (``BR-16``)."""
    agreement: TradeAgreement
    """Header trade agreement (BT-10-00) — parties and references."""
    delivery: TradeDelivery
    """Header trade delivery (BG-13-00) — ship-to and dispatch."""
    settlement: TradeSettlement
    """Header trade settlement (BG-19) — currency, payment, totals."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if Profile.BASIC_WL < profile and len(self.items) == 0:
            errors.append(
                ValidationError(
                    "BR-16", "An Invoice shall have at least one Invoice line (BG-25)."
                )
            )

        # Recurse into child validators first (so e.g. BR-CO-26 and
        # BR-CO-25 land in the list before our cross-field checks).
        errors.extend(super(Trade, self).validate_internal(profile))

        self._validate_vat_category_required_parties(errors)
        self._validate_document_arithmetic(errors)
        return errors

    def _validate_document_arithmetic(self, errors: list[ValidationError]) -> None:
        """BR-CO-10..13 and BR-CO-21..24 — sums and reason coupling
        across line items, header allowances/charges, and the header
        monetary summation. Appends to ``errors`` in document order."""
        summation = self.settlement.monetary_summation
        sum_line_totals = sum(
            (item.settlement.monetary_summation.line_total for item in self.items),
            Decimal("0"),
        )

        # BR-CO-10: BT-106 = sum of BT-131. Two guards: (1) BT-106 is
        # carthorse-optional (MINIMUM doesn't have it); (2) without
        # line items the spec rule is moot — let BR-16 surface that.
        if (
            self.items
            and summation.line_total is not None
            and summation.line_total != sum_line_totals
        ):
            errors.append(
                ValidationError(
                    "BR-CO-10",
                    "Sum of Invoice line net amount (BT-106) = "
                    f"{summation.line_total} differs from sum(BT-131) = "
                    f"{sum_line_totals}.",
                )
            )

        # Header allowance / charge sums (BR-CO-11, BR-CO-12, BR-CO-13).
        allowance_charges = self.settlement.allowance_charge or []
        # BR-CO-21 / BR-CO-22 — header allowance / charge needs reason
        # text or reason code (or both).
        for ac in allowance_charges:
            if ac.reason is None and ac.reason_code is None:
                if ac.indicator:
                    errors.append(
                        ValidationError(
                            "BR-CO-22",
                            "Each Document level charge (BG-21) shall "
                            "contain a Document level charge reason "
                            "(BT-104) or a Document level charge reason "
                            "code (BT-105), or both.",
                        )
                    )
                else:
                    errors.append(
                        ValidationError(
                            "BR-CO-21",
                            "Each Document level allowance (BG-20) shall "
                            "contain a Document level allowance reason "
                            "(BT-97) or a Document level allowance reason "
                            "code (BT-98), or both.",
                        )
                    )
        # BR-CO-23 / BR-CO-24 — same coupling but at line level
        # (BG-27 / BG-28). Different rule code per spec context.
        for item in self.items:
            for ac in item.settlement.allowance_charge or []:
                if ac.reason is None and ac.reason_code is None:
                    if ac.indicator:
                        errors.append(
                            ValidationError(
                                "BR-CO-24",
                                "Each Invoice line charge (BG-28) shall "
                                "contain an Invoice line charge reason "
                                "(BT-144) or an Invoice line charge "
                                "reason code (BT-145), or both.",
                            )
                        )
                    else:
                        errors.append(
                            ValidationError(
                                "BR-CO-23",
                                "Each Invoice line allowance (BG-27) shall "
                                "contain an Invoice line allowance reason "
                                "(BT-139) or an Invoice line allowance "
                                "reason code (BT-140), or both.",
                            )
                        )

        sum_allowances = sum(
            (ac.actual_amount for ac in allowance_charges if not ac.indicator),
            Decimal("0"),
        )
        sum_charges = sum(
            (ac.actual_amount for ac in allowance_charges if ac.indicator), Decimal("0")
        )

        # BR-CO-11: BT-107 = sum(BT-92).
        if (
            summation.allowance_total is not None
            and summation.allowance_total != sum_allowances
        ):
            errors.append(
                ValidationError(
                    "BR-CO-11",
                    "Sum of allowances on document level (BT-107) = "
                    f"{summation.allowance_total} differs from sum(BT-92) = "
                    f"{sum_allowances}.",
                )
            )

        # BR-CO-12: BT-108 = sum(BT-99).
        if summation.charge_total is not None and summation.charge_total != sum_charges:
            errors.append(
                ValidationError(
                    "BR-CO-12",
                    "Sum of charges on document level (BT-108) = "
                    f"{summation.charge_total} differs from sum(BT-99) = "
                    f"{sum_charges}.",
                )
            )

        # BR-CO-13: BT-109 = sum(BT-131) - sum(BT-92) + sum(BT-99). The
        # line-totals sum is only meaningful when there are line items.
        if self.items:
            expected_basis = sum_line_totals - sum_allowances + sum_charges
            if summation.tax_basis_total != expected_basis:
                errors.append(
                    ValidationError(
                        "BR-CO-13",
                        "Invoice total amount without VAT (BT-109) = "
                        f"{summation.tax_basis_total} differs from "
                        f"sum(BT-131) - sum(BT-92) + sum(BT-99) = "
                        f"{sum_line_totals} - {sum_allowances} + "
                        f"{sum_charges} = {expected_basis}.",
                    )
                )

    def _validate_vat_category_required_parties(
        self, errors: list[ValidationError]
    ) -> None:
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

        emitted: set[str] = set()

        def _emit(code: str, message: str) -> None:
            if code in emitted:
                return
            emitted.add(code)
            errors.append(ValidationError(code, f"{code}: {message}"))

        for category, ok, msg, (br_line, br_alw, br_chg) in families:
            if ok:
                continue

            for item in self.items:
                if item.settlement.applicable_trade_tax.category_code == category:
                    _emit(br_line, msg)
                    break

            for ac in self.settlement.allowance_charge or []:
                if (
                    ac.category_trade_tax is None
                    or ac.category_trade_tax.category_code != category
                ):
                    continue
                _emit(br_chg if ac.indicator else br_alw, msg)

        # BR-O — Not subject to VAT: inverted predicate. Each slot
        # carrying category 'O' forbids a different identifier set.
        s_has_vat_or_taxrep = _has_vat_id(seller) or _has_vat_id(tax_rep)

        for item in self.items:
            if item.settlement.applicable_trade_tax.category_code != CategoryCode.T_O:
                continue
            if s_has_vat_or_taxrep or buyer.id is not None:
                _emit(
                    "BR-O-2",
                    "An Invoice line with VAT category 'Not subject to VAT' "
                    "(O) shall not contain the Seller VAT identifier "
                    "(BT-31), the Seller tax representative VAT identifier "
                    "(BT-63) or the Buyer identifier (BT-46).",
                )
                break

        for ac in self.settlement.allowance_charge or []:
            if (
                ac.category_trade_tax is None
                or ac.category_trade_tax.category_code != CategoryCode.T_O
            ):
                continue
            if s_has_vat_or_taxrep or _has_vat_id(buyer):
                code = "BR-O-4" if ac.indicator else "BR-O-3"
                kind = "charge" if ac.indicator else "allowance"
                _emit(
                    code,
                    f"A document-level {kind} with VAT category 'Not subject "
                    "to VAT' (O) shall not contain the Seller VAT identifier "
                    "(BT-31), the Seller tax representative VAT identifier "
                    "(BT-63) or the Buyer VAT identifier (BT-48).",
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
                _emit(
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
                _emit(
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
                _emit(
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
                    _emit(
                        "BR-O-12",
                        "An Invoice with a VAT breakdown row of category "
                        "'Not subject to VAT' (O) shall not contain an "
                        "Invoice line whose category code is not 'Not "
                        "subject to VAT'.",
                    )
                    break
            for ac in self.settlement.allowance_charge or []:
                if (
                    ac.category_trade_tax is None
                    or ac.category_trade_tax.category_code == CategoryCode.T_O
                ):
                    continue
                code = "BR-O-14" if ac.indicator else "BR-O-13"
                kind = "charge" if ac.indicator else "allowance"
                _emit(
                    code,
                    "An Invoice with a VAT breakdown row of category 'Not "
                    "subject to VAT' (O) shall not contain a document-level "
                    f"{kind} whose VAT category code is not 'Not subject to "
                    "VAT'.",
                )
