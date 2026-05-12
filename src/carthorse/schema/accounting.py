"""Monetary totals and VAT breakdown.

Owns the four BG groups that make up the financial spine of an invoice:

* ``BG-22 SpecifiedTradeSettlementHeaderMonetarySummation`` — the
  rectangular "totals" block at the bottom of the invoice. Eight
  amounts: line total, charge total, allowance total, tax basis total,
  tax total (one or two — invoice currency, optionally accounting
  currency), grand total, prepaid total, due-payable amount.
* ``BG-23 ApplicableTradeTax`` — one row per VAT category / rate
  combination. Required at BASIC_WL+ (``BR-CO-18``).
* ``BG-20 SpecifiedTradeAllowanceCharge[indicator=false]`` (Abschlag /
  allowance) and ``BG-21 SpecifiedTradeAllowanceCharge[indicator=true]``
  (Zuschlag / charge). Same shape, same dataclass; the
  ``ChargeIndicator`` is what tells them apart.
* ``CategoryTradeTax`` — the embedded VAT category block on each
  allowance / charge.

Validation rules covered (or missing) in this module:

* ✓ ``BR-CO-18`` (at least one BG-23 ≥ BASIC_WL) — in
  ``settlement.py``.
* ✓ ``BR-CO-21`` / ``BR-CO-22`` — allowance/charge requires reason or
  reason code, in :class:`TradeAllowanceCharge.validate_internal`.
* △ ``BR-5`` — ``TaxTotal.currency_id`` shape only.
* — ``BR-12`` (BT-106 required ≥ BASIC_WL): :class:`MonetarySummation`
  treats ``line_total`` as optional and gates it on ``>= BASIC_WL`` for
  rendering, but does not yet *require* it at BASIC_WL+.
* ✓ ``BR-CO-3`` (BT-7 vs BT-8 mutually exclusive) —
  :meth:`ApplicableTradeTax.validate_internal`.
* — ``BR-CO-10..17`` (sum identities): need line items.
* — ``BR-53`` (BT-6 ⇒ BT-111): needs multi-``TaxTotal`` model
  (``§1 #6``).
* — ``BR-48`` (rate required unless not-subject-to-VAT): not enforced.

For the per-VAT-category ``BR-AE/BR-E/BR-G/BR-IC/BR-IG/BR-IP/BR-O/
BR-S/BR-Z`` rule families and the EXTENDED ``BR-FXEXT-*`` rounding-
tolerance variants, see ``docs/VALIDATION.md``.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema._numeric import round_half_away_from_zero
from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.types import CategoryCode, Profile


@dataclass(kw_only=True, slots=True)
class TaxTotal(Element):
    """Invoice total VAT amount / Invoice total VAT amount in accounting currency.

    The total VAT amount for the Invoice.

    The VAT total amount expressed in the accounting currency accepted or
    required in the Seller's country.

    The Invoice total VAT amount is the sum of all VAT category tax amounts.

    To be used when the VAT accounting currency code (BT-6) under
    Article 230 of Council Directive 2006/112/EC on VAT differs from the
    invoice currency code (BT-5).
    The VAT total amount in the VAT accounting currency is not taken into
    account when calculating the Invoice totals.

    EN 16931-ID: BT-110, BT-111
    """

    tag: ClassVar[str] = "TaxTotalAmount"

    amount: Decimal
    """The Invoice total VAT amount is the sum of all VAT category tax
    amounts.
    """
    currency_id: str
    """VAT currency.

    ``currencyID`` is required to distinguish between the tax amount in
    invoice currency and the tax amount in VAT accounting currency.

    Code list: ISO 4217 — only the alphabetic representation may be used.
    Example: EUR, USD

    EN 16931-ID: BT-110-0, BT-111-0
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if (
            len(self.currency_id) != 3
            or not self.currency_id.isalpha()
            or self.currency_id.upper() != self.currency_id
        ):
            errors.append(
                ValidationError(
                    "BR-5",
                    "Invoice currency code (BT-5) must be an ISO 4217 "
                    f"alpha-3 uppercase code; got {self.currency_id!r}.",
                )
            )
        errors.extend(super(TaxTotal, self).validate_internal(profile))
        return errors

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), attrs={"currencyID": self.currency_id})[
            str(self.amount)
        ]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "currencyID" not in elem.attrib:
            raise ValueError
        if elem.text is None:
            raise ValueError
        currency_id = elem.attrib["currencyID"]
        value = elem.text.strip()
        return cls(amount=Decimal(value), currency_id=currency_id)


@dataclass(kw_only=True, slots=True)
class MonetarySummation(Element):
    """Document totals / Document level totals.

    A group of business terms providing the monetary totals for the Invoice.

    EN 16931-ID: BG-22
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementHeaderMonetarySummation"

    line_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "LineTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of Invoice line net amounts.

    Optional in carthorse: the MINIMUM profile XSD does not include
    ``LineTotalAmount`` at all. From BASIC_WL onwards the field is
    expected per ``BR-12``; that rule isn't yet enforced here.

    EN 16931-ID: BT-106
    """
    tax_basis_total: Decimal = field(
        metadata={"tag": "TaxBasisTotalAmount", "amount": True}
    )
    """Invoice total amount without VAT.

    The total amount of the Invoice without VAT. The Invoice total amount
    without VAT is the sum of Invoice line net amounts minus the sum of
    document level allowances plus the sum of document level charges.

    EN 16931-ID: BT-109
    """
    tax_total: list[TaxTotal] | None = None
    """``ram:TaxTotalAmount`` — the row of currency-tagged VAT totals.

    Up to two entries per the XSD: BT-110 carries the VAT total in
    invoice currency (``currencyID == BT-5``), BT-111 carries the same
    amount expressed in the seller's VAT accounting currency
    (``currencyID == BT-6``) and is required when ``BT-6`` is set
    (``BR-53``). MINIMUM permits at most one entry; from BASIC_WL
    onwards both may appear in that order.

    ``BR-53`` is not yet enforced.

    EN 16931-ID: BT-110, BT-111
    """
    grand_total: Decimal = field(
        metadata={"tag": "GrandTotalAmount", "amount": True}
    )
    """Invoice total amount with VAT / Grand total amount.

    The Invoice total amount with VAT is the Invoice total amount without
    VAT plus the Invoice total VAT amount.

    EN 16931-ID: BT-112
    """
    due_amount: Decimal = field(
        metadata={"tag": "DuePayableAmount", "amount": True}
    )
    """Amount due for payment.

    The outstanding amount that is requested to be paid.

    This amount is the Invoice total amount with VAT minus the paid amount
    that has been paid in advance. If the Invoice has been fully paid, this
    amount is zero. The amount may be negative; in that case the Seller
    owes the Buyer the amount.

    When prepayments have been made, this amount may differ from the
    Invoice grand total.

    EN 16931-ID: BT-115
    """
    charge_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "ChargeTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of charges on document level.

    Sum of all charges on document level in the Invoice.

    Charges on line level are included in the Invoice line net amounts
    which are summed up into the Sum of Invoice line net amounts.

    EN 16931-ID: BT-108
    """
    allowance_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "AllowanceTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of allowances on document level.

    Sum of all allowances on document level in the Invoice.

    Allowances on line level are included in the Invoice line net amounts
    which are summed up into the Sum of Invoice line net amounts.

    EN 16931-ID: BT-107
    """
    prepaid_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "TotalPrepaidAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on every amount
    in this group. Populated automatically on parse from the
    ``currencyID`` attribute of the first amount element; set explicitly
    by callers building a Document programmatically when emitting
    ``currencyID`` on the totals is desired (the XSD allows omitting
    it)."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # BR-12: An Invoice shall have the Sum of Invoice line net amount
        # (BT-106). The MINIMUM profile drops BT-106 from the XSD, so the
        # rule is checkable only from BASIC_WL up.
        if profile >= Profile.BASIC_WL and self.line_total is None:
            errors.append(
                ValidationError(
                    "BR-12",
                    "An Invoice shall have the Sum of Invoice line net "
                    "amount (BT-106).",
                )
            )
        errors.extend(
            super(MonetarySummation, self).validate_internal(profile)
        )
        return errors


@dataclass(kw_only=True, slots=True)
class ApplicableTradeTax(Element):
    """VAT breakdown / VAT details.

    A group of business terms providing information about VAT breakdown
    into different categories, rates and exemption reasons.

    EN 16931-ID: BG-23
    """

    tag: ClassVar[str] = "ApplicableTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    calculated_amount: Decimal | None = field(
        default=None, metadata={"tag": "CalculatedAmount", "amount": True}
    )
    """VAT category tax amount.

    The total VAT amount for a given VAT category.

    Calculated by multiplying the VAT category taxable amount with the
    VAT category rate of the relevant VAT category.

    EN 16931-ID: BT-117
    """
    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """VAT category type code.

    EN 16931 only supports the tax type "VAT" with the code "VAT".

    If other tax types — for example insurance tax or mineral oil tax —
    are to be carried, the EXTENDED profile must be used. The tax type
    code must then be taken from code list UNTDID 5153.

    Code list: UNTDID 5153

    EN 16931-ID: BT-118-0
    """
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "amount": True}
    )
    """VAT category taxable amount.

    EN 16931-ID: BT-116
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """Coded identification of a VAT category.

    The following entries from UNTDID 5305 are used (with notes in
    parentheses):
    — (S) Standard rate (VAT applies at the standard rate);
    — (Z) Zero rated goods (VAT applies at a rate of zero per cent);
    — (E) Exempt from VAT (VAT/IGIC/IPSI);
    — (AE) Reverse charge (the rules on reverse charge of VAT/IGIC/IPSI apply);
    — (K) VAT exempt for EEA intra-community supply of goods and services
      (VAT/IGIC/IPSI not levied due to rules on intra-community supplies);
    — (G) Free export item, VAT not charged (VAT/IGIC/IPSI not levied due
      to export outside the EU);
    — (O) Services outside scope of tax (sale not subject to VAT/IGIC/IPSI);
    — (L) Canary Islands general indirect tax (IGIC tax applies);
    — (M) Tax for production, services and importation in Ceuta and
      Melilla (IPSI applies).

    Code list: UNTDID 5305

    EN 16931-ID: BT-118
    """
    exemption_reason: str | None = field(
        default=None, metadata={"tag": "ExemptionReason"}
    )
    """VAT exemption reason text (free text).

    EN 16931-ID: BT-120
    """
    exemption_reason_code: str | None = field(
        default=None, metadata={"tag": "ExemptionReasonCode"}
    )
    """VAT exemption reason code.

    A coded statement of the reason for why the amount is exempted from
    VAT.

    Code list: VATEX

    EN 16931-ID: BT-121
    """
    tax_point_date: date | None = field(
        default=None, metadata={"tag": "TaxPointDate", "profile": Profile.COMFORT}
    )
    """Tax point date (BT-7).

    The date on which VAT becomes accountable for the Seller and the
    Buyer, when this differs from the invoice issue date. Mutually
    exclusive with :attr:`due_date_code` (BT-8) per ``BR-CO-3``.

    First permitted from EN 16931 / COMFORT onwards.

    EN 16931-ID: BT-7
    """
    due_date_code: str | None = field(default=None, metadata={"tag": "DueDateTypeCode"})
    """Value added tax point date code.

    The code for the date on which VAT becomes accountable for the
    Seller and for the Buyer.

    The code shall distinguish between the following entries from
    UNTDID 2005:
        - Invoice document issue date;
        - Actual delivery date;
        - Payment date.
    The Value added tax point date code is used when the Value added
    tax point date is not known at the time of invoice issue. BT-7
    (Value added tax point date) and BT-8 are mutually exclusive.

    The semantic values cited in the standard, represented by the
    values 3, 35, 432 in UNTDID 2005, are mapped to the following
    values in UNTDID 2475 — the relevant code list supported by
    CII 16B:

    - 5: Invoice document issue date
    - 29: Delivery date, actual
    - 72: Paid to date

    In Germany, the delivery and performance date is decisive (BT-72)
    SupplyChainTradeTransaction/ApplicableHeaderTradeDelivery/
    ActualDeliverySupplyChainEvent/OccurrenceDateTime/DateTimeString).

    Code list: UNTDID 2475 (subset)

        https://service.unece.org/trade/untdid/d96a/uncl/uncl2475.htm

    EN 16931-ID: BT-8
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """VAT category rate.

    The VAT rate, represented as a percentage that applies to the
    relevant VAT category. The VAT category code and the VAT category
    rate shall be consistent.

    The value to be provided is the percentage. For example, for 20%
    the value 20 is given (not 0.2).

    EN 16931-ID: BT-119
    """
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``BasisAmount`` (BT-116) and ``CalculatedAmount`` (BT-117).
    Populated on parse; set explicitly when building programmatically."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if self.type_code != "VAT" and self.profile != Profile.EXTENDED:
            errors.append(
                ValidationError(
                    "BT-118-0",
                    "Tax type codes other than 'VAT' on BT-118-0 are only "
                    "allowed in the EXTENDED profile.",
                )
            )
        # BR-CO-3: BT-7 (TaxPointDate) and BT-8 (DueDateTypeCode) are
        # mutually exclusive on a single ApplicableTradeTax.
        if self.tax_point_date is not None and self.due_date_code is not None:
            errors.append(
                ValidationError(
                    "BR-CO-3",
                    "Value added tax point date (BT-7) and Value added "
                    "tax point date code (BT-8) are mutually exclusive.",
                )
            )
        # If BT-8 is supplied, it must follow UNTDID 2475 (digits or ZZZ,
        # max 3 chars). When absent — BR-CO-3 leaves the slot to BT-7,
        # or both may be omitted entirely.
        if self.due_date_code is not None and not (
            len(self.due_date_code) <= 3
            and (self.due_date_code.isdigit() or self.due_date_code == "ZZZ")
        ):
            errors.append(
                ValidationError(
                    "BT-8",
                    "Value added tax point date code (BT-8) must be a "
                    f"UNTDID 2475 code (digits or 'ZZZ'); got {self.due_date_code!r}.",
                )
            )

        # BR-CO-17: BT-117 = round(BT-116 * BT-119 / 100, 2). Dropped at
        # EXTENDED (the per-VAT-category BR-FXEXT-*-09 family supersedes
        # it). Skip when the rate is absent (e.g. category 'O').
        if (
            profile < Profile.EXTENDED
            and self.rate_applicable_percent is not None
            and self.basis_amount is not None
            and self.calculated_amount is not None
        ):
            # Factur-X §7.1.8 rounding: half away from zero.
            expected = round_half_away_from_zero(
                self.basis_amount * self.rate_applicable_percent / Decimal("100")
            )
            if round_half_away_from_zero(self.calculated_amount) != expected:
                errors.append(
                    ValidationError(
                        "BR-CO-17",
                        "VAT category tax amount (BT-117) = "
                        f"{self.calculated_amount} differs from "
                        "round(BT-116 * BT-119 / 100, 2) = "
                        f"round({self.basis_amount} * "
                        f"{self.rate_applicable_percent} / 100, 2) = "
                        f"{expected}.",
                    )
                )
        errors.extend(super(ApplicableTradeTax, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class CategoryTradeTax(Element):
    """VAT category details for a document level allowance or charge."""

    tag: ClassVar[str] = "CategoryTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """Document level allowance/charge VAT category type code.

    EN 16931 only supports the tax type "VAT" with the code "VAT".

    If other tax types — for example insurance tax or mineral oil tax —
    are to be carried, the EXTENDED profile must be used. The tax type
    code must then be taken from code list UNTDID 5153.

    Code list: UNTDID 5153

    EN 16931-ID: BT-95-0 (Allowance), BT-102-0 (Charge)
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """Document level allowance/charge VAT category code.

    The following entries from UNTDID 5305 are used (with notes in
    parentheses):

    — (S) Standard rate (VAT applies at the standard rate);
    — (Z) Zero rated goods (VAT applies at a rate of zero per cent);
    — (E) Exempt from VAT (VAT/IGIC/IPSI);
    — (AE) Reverse charge (the rules on reverse charge of VAT/IGIC/IPSI apply);
    — (K) VAT exempt for EEA intra-community supply of goods and services
      (VAT/IGIC/IPSI not levied due to rules on intra-community supplies);
    — (G) Free export item, VAT not charged (VAT/IGIC/IPSI not levied due
      to export outside the EU);
    — (O) Services outside scope of tax (sale not subject to VAT/IGIC/IPSI);
    — (L) Canary Islands general indirect tax (IGIC tax applies);
    — (M) Tax for production, services and importation in Ceuta and
      Melilla (IPSI applies).

    Code list: UNTDID 5305

    EN 16931-ID: BT-95 (Allowance), BT-102 (Charge)
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """Document level allowance/charge VAT rate.

    The VAT rate, expressed as a percentage, that applies to the
    document level allowance or charge.

    The value to be provided is the percentage. For example, for 20%
    the value 20 is given (not 0.2).

    EN 16931-ID: BT-96 (Allowance), BT-103 (Charge)
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if self.type_code != "VAT" and self.profile != Profile.EXTENDED:
            errors.append(
                ValidationError(
                    "BT-95-0/BT-102-0",
                    "Tax type codes other than 'VAT' on BT-95-0 / BT-102-0 "
                    "are only allowed in the EXTENDED profile.",
                )
            )
        errors.extend(super(CategoryTradeTax, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class TradeAllowanceCharge(Element):
    """Document level allowances and charges.

    A group of business terms providing information about allowances
    and charges that apply to the Invoice as a whole. Deductions, such
    as for withheld taxes, may also be given in this group.

    EN 16931-ID: BG-20 (Allowance), BG-21 (Charge)
    """

    tag: ClassVar[str] = "SpecifiedTradeAllowanceCharge"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    indicator: bool = field(metadata={"tag": "ChargeIndicator"})
    """Allowance/Charge indicator.

    A flag indicating whether the data that follows refers to an
    allowance or a charge.

    - For an allowance (BG-20) the ChargeIndicator value is "false".
    - For a charge (BG-21) the ChargeIndicator value is "true".

    EN 16931-ID: BG-20-0, BG-21-0, BG-20-00, BG-21-00
    """
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount", "amount": True})
    """Document level allowance/charge amount.

    The amount of an allowance or charge, without VAT.

    EN 16931-ID: BT-92 (Allowance), BT-99 (Charge)
     """
    category_trade_tax: CategoryTradeTax | None = None
    """VAT category for the allowance / charge (BT-95-00 / BT-102-00).

    Required at BASIC_WL per the appendix narrative; from BASIC the
    XSD makes it optional. carthorse keeps it ``Optional`` so the
    same dataclass works at every profile.
    """
    calculation_percent: Decimal | None = field(
        default=None,
        metadata={"tag": "CalculationPercent", "profile": Profile.BASIC_WL},
    )
    """Document level allowance/charge percentage.

    The percentage that, in combination with the document level
    allowance/charge base amount, may be used to calculate the
    document level allowance/charge amount.

    Up to COMFORT only the final result of the discounting
    (ActualAmount) is transmitted.

    EN 16931-ID: BT-94 (Allowance), BT-101 (Charge)
    """
    basis_amount: Decimal | None = field(
        default=None,
        metadata={"tag": "BasisAmount", "profile": Profile.BASIC_WL, "amount": True},
    )
    """Document level allowance/charge base amount.

    The base amount that, in combination with the document level
    allowance/charge percentage, may be used to calculate the
    document level allowance/charge amount.

    EN 16931-ID: BT-93 (Allowance), BT-100 (Charge)
    """
    reason: str | None = field(default=None, metadata={"tag": "Reason"})
    """Document level allowance/charge reason.

    The reason for the document level allowance or charge, expressed
    as text.

    EN 16931-ID: BT-97 (Allowance), BT-104 (Charge)
    """
    reason_code: str | None = field(default=None, metadata={"tag": "ReasonCode"})
    """Document level allowance/charge reason code.

    Use entries from the UNTDID 5189 code list. The reason code and
    the reason text for the document level allowance or charge shall
    correspond.

    Code list: UNTDID 5189

        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5189.htm

    EN 16931-ID: BT-98 (Allowance), BT-105 (Charge)
    """
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``ActualAmount`` (BT-92 / BT-99) and ``BasisAmount`` (BT-93 / BT-100).
    Populated on parse; set explicitly when building programmatically."""

    # Note: BR-CO-21/22 (header reason coupling) and BR-CO-23/24 (line
    # reason coupling) are enforced by ``Trade._validate_document_arithmetic``
    # because they need to know whether this allowance/charge is at
    # header or line level. Keeping the check there means the same
    # ``TradeAllowanceCharge`` dataclass works in both contexts.

    # The document level allowance reason code (BT-98) and the
    # document level allowance reason (BT-97) shall indicate the same
    # allowance type.
