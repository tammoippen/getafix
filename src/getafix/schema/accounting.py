"""Monetary totals and VAT breakdown (BG-22, BG-23, BG-20, BG-21).

Owns the four BG groups that make up the financial spine of an
invoice:

* :class:`MonetarySummation` (BG-22) — the "totals" block at the
  bottom of the invoice. Line total (BT-106), charge total (BT-108),
  allowance total (BT-107), tax basis total (BT-109), one or two
  tax totals (BT-110 / BT-111 — invoice currency, optionally
  accounting currency), optional rounding amount (BT-114), grand
  total (BT-112), prepaid total (BT-113) and amount due (BT-115).
* :class:`ApplicableTradeTax` (BG-23 at header, BG-30 at line level)
  — one row per VAT category / rate combination. Required at
  BASIC_WL+ (``BR-CO-18``, enforced in :mod:`settlement`).
* :class:`TradeAllowanceCharge` — the unified dataclass for header
  allowances (BG-20), header charges (BG-21), line allowances
  (BG-27) and line charges (BG-28). ``ChargeIndicator`` (``false`` /
  ``true``) discriminates allowance from charge; placement on
  :class:`~getafix.schema.settlement.TradeSettlement` vs
  :class:`~getafix.schema.line.LineTradeSettlement` discriminates
  header from line.
* :class:`CategoryTradeTax` — the embedded VAT category block
  (BT-95-00 at allowance level, BT-102-00 at charge level).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, Literal, Self, override

from tagic.xml import XML

from getafix.rules import Validator
from getafix.rules._types import max_decimals
from getafix.rules.accounting import (
    br_5_currency_shape,
    br_12,
    br_48,
    br_co_3,
    br_co_17,
    br_dec_tac_amounts,
    bt_8_code_shape,
    bt_95_0_102_0_vat_only,
    bt_118_0_vat_only,
)
from getafix.schema.element import Element, ETElement
from getafix.schema.types import (
    CategoryCode,
    Currency,
    Profile,
    UNTDID2475TaxPointDateCode,
    VATEXCode,
)


@dataclass(kw_only=True, slots=True)
class TaxTotal(Element):
    """Invoice total VAT amount (BT-110 / BT-111).

    Single :class:`TaxTotal` instance per row of
    :attr:`MonetarySummation.tax_total`:

    * BT-110 (MINIMUM+) — total VAT in invoice currency. The
      ``currency_id`` matches ``InvoiceCurrencyCode`` (BT-5).
    * BT-111 (BASIC_WL+) — same total expressed in the Seller's VAT
      accounting currency. Used when BT-6 differs from BT-5
      (Article 230 of Council Directive 2006/112/EC); ignored when
      computing the invoice totals. Required when BT-6 is set
      (``BR-53``).
    """

    tag: ClassVar[str] = "TaxTotalAmount"

    _validators: ClassVar[tuple[Validator["TaxTotal"], ...]] = (
        br_5_currency_shape,
        # BR-DEC-13 (BT-110 invoice-currency tax total) and BR-DEC-15
        # (BT-111 accounting-currency tax total) cap `amount` at 2dp.
        # We can't easily discriminate the two BT IDs at validation
        # time so emit BR-DEC-13 for either — both names refer to the
        # same XSD ``amount`` field.
        max_decimals("BR-DEC-13", field_name="amount"),
    )

    amount: Decimal
    """Invoice total VAT amount (BT-110 / BT-111).

    All per-category VAT amounts added together.
    """
    currency_id: Currency
    """Currency identifier (BT-110-0 / BT-111-0).

    Distinguishes BT-110 (invoice currency) from BT-111 (accounting
    currency); rendered as the ``currencyID`` attribute.

    Code list: ISO 4217 — alphabetic representation only.

    Examples: ``EUR``, ``USD``.
    """

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
        currency_id = elem.attrib.get("currencyID")
        if currency_id is None:
            raise ValueError
        if elem.text is None:
            raise ValueError
        value = elem.text.strip()
        return cls(amount=Decimal(value), currency_id=Currency(currency_id))


@dataclass(kw_only=True, slots=True)
class MonetarySummation(Element):
    """Document totals (BG-22).

    The document-level money totals of the invoice.
    Several fields are optional at MINIMUM but expected at BASIC_WL+.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementHeaderMonetarySummation"

    _validators: ClassVar[tuple[Validator["MonetarySummation"], ...]] = (
        br_12,
        max_decimals("BR-DEC-09", field_name="line_total"),
        max_decimals("BR-DEC-10", field_name="allowance_total"),
        max_decimals("BR-DEC-11", field_name="charge_total"),
        max_decimals("BR-DEC-12", field_name="tax_basis_total"),
        max_decimals("BR-DEC-14", field_name="grand_total"),
        max_decimals("BR-DEC-16", field_name="prepaid_total"),
        max_decimals("BR-DEC-17", field_name="rounding_amount"),
        max_decimals("BR-DEC-18", field_name="due_amount"),
    )

    line_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "LineTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of invoice line net amounts (BT-106).

    Note: the MINIMUM profile XSD does not include
    ``LineTotalAmount`` at all — getafix keeps it optional. From
    BASIC_WL onwards ``BR-12`` requires it; the validator raises
    when the field is missing at that profile.
    """
    charge_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "ChargeTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of charges on document level (BT-108).

    Every document-level charge on the invoice, totalled.

    Note: charges on line level are *not* included here — they are
    folded into the line net amount which feeds ``line_total``
    (BT-106).
    """
    allowance_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "AllowanceTotalAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Sum of allowances on document level (BT-107).

    Every document-level allowance on the invoice, totalled.

    Note: allowances on line level are *not* included here — they
    are folded into the line net amount which feeds ``line_total``
    (BT-106).
    """
    tax_basis_total: Decimal = field(
        metadata={"tag": "TaxBasisTotalAmount", "amount": True}
    )
    """Invoice total amount without VAT (BT-109).

    Equals BT-106 - BT-107 + BT-108: line net amounts, less the
    document-level allowances, plus the document-level charges
    (``BR-CO-13``).
    """
    tax_total: list[TaxTotal] | None = None
    """Invoice total VAT amounts (BT-110 / BT-111); 0..2 entries.

    Note: BT-110 (in invoice currency) first; BT-111 (in VAT
    accounting currency) second, required when BT-6 is set
    (``BR-53``). MINIMUM permits at most one entry; from BASIC_WL
    onwards both may appear in that order.
    """
    rounding_amount: Decimal | None = field(
        default=None,
        metadata={"tag": "RoundingAmount", "profile": Profile.COMFORT, "amount": True},
    )
    """Rounding amount (BT-114).

    Amount added on top of the invoice total so the payable figure
    comes out rounded.

    Note: first permitted from COMFORT (EN 16931) onwards.
    Enters the ``BR-CO-16`` identity ``BT-115
    = BT-112 - BT-113 + BT-114``.
    """
    grand_total: Decimal = field(metadata={"tag": "GrandTotalAmount", "amount": True})
    """Invoice total amount with VAT (BT-112).

    VAT-inclusive invoice total: the net total (BT-109) plus the
    VAT total (BT-110).
    """
    prepaid_total: Decimal | None = field(
        default=None,
        metadata={
            "tag": "TotalPrepaidAmount",
            "profile": Profile.BASIC_WL,
            "amount": True,
        },
    )
    """Paid amount (BT-113).

    Everything already paid up front, totalled; subtracted from
    BT-112 when deriving the amount due for payment (BT-115).
    """
    due_amount: Decimal = field(metadata={"tag": "DuePayableAmount", "amount": True})
    """Amount due for payment (BT-115).

    The outstanding amount requested for payment — the VAT-inclusive
    invoice total (BT-112) less everything already paid up front
    (BT-113). Zero for a fully paid invoice; may be negative, in
    which case the Seller owes the Buyer.
    """
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on every
    amount in this group.

    Populated on parse from the ``currencyID`` attribute of the
    first amount element; set explicitly when building
    programmatically (the XSD allows omitting it on render).
    """


@dataclass(kw_only=True, slots=True)
class ApplicableTradeTax(Element):
    """VAT breakdown (BG-23 at header / BG-30 at line level).

    One row per VAT category / rate combination at header level,
    where it holds the calculated and basis amounts. At line level
    the same element only carries ``TypeCode``, ``CategoryCode`` and
    the optional rate — the amounts live on the header BG-23 rows.
    """

    tag: ClassVar[str] = "ApplicableTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    _validators: ClassVar[tuple[Validator["ApplicableTradeTax"], ...]] = (
        bt_118_0_vat_only,
        br_co_3,
        bt_8_code_shape,
        br_co_17,
        br_48,
        max_decimals("BR-DEC-19", field_name="basis_amount"),
        max_decimals("BR-DEC-20", field_name="calculated_amount"),
    )

    calculated_amount: Decimal | None = field(
        default=None, metadata={"tag": "CalculatedAmount", "amount": True}
    )
    """VAT category tax amount (BT-117).

    VAT owed under this category overall — the category taxable
    amount (BT-116) times the category rate (BT-119), rounded per
    Factur-X §7.1.8 (``BR-CO-17``).
    """
    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """VAT category type code (BT-118-0).

    EN 16931 only supports the value ``"VAT"``. Other tax types
    (insurance tax, mineral oil tax, …) are only allowed in the
    EXTENDED profile, where the value must come from UNTDID 5153.

    Code list: [UNTDID 5153](https://service.unece.org/trade/untdid/d16b/tred/tred5153.htm).
    """
    exemption_reason: str | None = field(
        default=None, metadata={"tag": "ExemptionReason"}
    )
    """VAT exemption reason, free text (BT-120).

    Plain-text explanation of why this amount carries no VAT or is
    exempt from it. See Articles 226 items 11 to 15 of Directive
    2006/112/EC.
    """
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "amount": True}
    )
    """VAT category taxable amount (BT-116).

    Adds up every taxable amount falling under this VAT category
    code and rate — the category's share of the line net amounts,
    less its document-level allowances, plus its document-level
    charges.
    """
    line_total_basis_amount: Decimal | None = field(
        default=None,
        metadata={
            "tag": "LineTotalBasisAmount",
            "amount": True,
            "profile": Profile.EXTENDED,
        },
    )
    """Sum of line net amounts at this category and rate (BT-X-262); EXTENDED only.

    Informational breakdown showing how much of BT-116 came from
    line items (BT-131 lines filtered to this category / rate)
    before document-level allowances and charges are netted in.
    Six of the current EXTENDED samples populate this — none of
    the EN16931 / lower-profile XSDs accept it, so the field gates
    at EXTENDED.
    """
    allowance_charge_basis_amount: Decimal | None = field(
        default=None,
        metadata={
            "tag": "AllowanceChargeBasisAmount",
            "amount": True,
            "profile": Profile.EXTENDED,
        },
    )
    """Net of document-level charges minus allowances at this
    category and rate (BT-X-263); EXTENDED only.

    Companion to :attr:`line_total_basis_amount` — the rest of the
    derivation that gets added to it to land at :attr:`basis_amount`
    (BT-116). Same EXTENDED gating.
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """VAT category code (BT-118).

    Code naming the VAT category. Category code and VAT rate
    (BT-119) must agree with each other.

    Code list: UNTDID 5305. The following entries are used:

    * ``S`` — Standard rate
    * ``Z`` — Zero rated
    * ``E`` — Exempt from VAT (VAT / IGIC / IPSI)
    * ``AE`` — VAT Reverse charge
    * ``K`` — VAT exempt for EEA intra-community supply
    * ``G`` — Free export item, VAT not charged
    * ``O`` — Services outside scope of tax
    * ``L`` — Canary Islands general indirect tax (IGIC)
    * ``M`` — Tax for production, services and importation in Ceuta
      and Melilla (IPSI)
    """
    exemption_reason_code: VATEXCode | None = field(
        default=None, metadata={"tag": "ExemptionReasonCode"}
    )
    """VAT exemption reason code (BT-121).

    Code stating why the amount escapes VAT.

    Code list: VATEX (maintained by the Connecting Europe Facility).
    """
    tax_point_date: date | None = field(
        default=None, metadata={"tag": "TaxPointDate", "profile": Profile.COMFORT}
    )
    """Value added tax point date (BT-7); COMFORT+.

    Date on which the VAT falls due for both Seller and Buyer —
    given only when it differs from the invoice issue date.

    Note: mutually exclusive with ``due_date_code`` (BT-8) per
    ``BR-CO-3``. The tax point typically falls on the day the goods
    were handed over or the services finished; see Article 226(7)
    of Council Directive 2006/112/EC. Rendered as
    ``<ram:TaxPointDate><udt:DateTimeString format="102">YYYYMMDD</udt:DateTimeString></ram:TaxPointDate>``
    per the EN16931 / Factur-X 1.08 appendix.
    """
    due_date_code: UNTDID2475TaxPointDateCode | None = field(
        default=None, metadata={"tag": "DueDateTypeCode"}
    )
    """Value added tax point date code (BT-8).

    Code standing in for the VAT due date when the tax point date
    itself isn't known at invoice issue.

    Note: mutually exclusive with ``tax_point_date`` (BT-7) per
    ``BR-CO-3``. In Germany, the delivery and performance date is
    decisive (BT-72 on the trade delivery).

    Code list: UNTDID 2475 (subset). The semantic values cited in
    the standard
    ([UNTDID 2005](https://service.unece.org/trade/untdid/d16b/tred/tred2005.htm)
    values ``3`` / ``35`` / ``432``) map to:

    * ``5`` — Invoice document issue date
    * ``29`` — Delivery date, actual
    * ``72`` — Paid to date

    https://service.unece.org/trade/untdid/d96a/uncl/uncl2475.htm
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """VAT category rate (BT-119).

    Percentage VAT rate of the category. Must agree with the
    category code (BT-118).

    Note: the value is the percentage itself — for 20%, pass ``20``,
    not ``0.2``.
    """
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``BasisAmount`` (BT-116) and ``CalculatedAmount`` (BT-117).

    Populated on parse; set explicitly when building
    programmatically.
    """


@dataclass(kw_only=True, slots=True)
class CategoryTradeTax(Element):
    """Allowance / charge VAT category (BT-95-00 / BT-102-00).

    Embedded VAT-category block on every document-level allowance
    (BG-20) and charge (BG-21). The same dataclass is reused at
    line-level allowances (BG-27) and charges (BG-28).
    """

    tag: ClassVar[str] = "CategoryTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    _validators: ClassVar[tuple[Validator["CategoryTradeTax"], ...]] = (
        bt_95_0_102_0_vat_only,
    )

    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """VAT type code (BT-95-0 allowance / BT-102-0 charge).

    EN 16931 only supports the value ``"VAT"``. Other tax types
    (insurance tax, mineral oil tax, …) are only allowed in
    EXTENDED, where the value must come from UNTDID 5153.

    Code list: [UNTDID 5153](https://service.unece.org/trade/untdid/d16b/tred/tred5153.htm).
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """VAT category code (BT-95 allowance / BT-102 charge).

    Coded identification of the VAT category that applies to this
    allowance or charge. See :attr:`ApplicableTradeTax.category_code`
    for the legal values.

    Code list: UNTDID 5305.
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """VAT rate (BT-96 allowance / BT-103 charge).

    Percentage VAT rate applying to the document-level allowance or
    charge.

    Note: the value is the percentage itself — for 20%, pass ``20``,
    not ``0.2``.
    """


@dataclass(kw_only=True, slots=True)
class TradeAllowanceCharge(Element):
    """Allowances and charges (BG-20 / BG-21 at header, BG-27 / BG-28 at line).

    Price reductions (allowances) and surcharges (charges) on the
    invoice. The same XSD element backs four BG groups:

    * ``ChargeIndicator = false`` ⇒ allowance (BG-20 header / BG-27
      line).
    * ``ChargeIndicator = true`` ⇒ charge (BG-21 header / BG-28
      line).

    Placement on :class:`~getafix.schema.settlement.TradeSettlement`
    vs :class:`~getafix.schema.line.LineTradeSettlement` selects
    header vs line. The header form may also represent deductions
    such as withheld taxes; the line form (BG-28) additionally
    covers non-VAT charges and taxes hitting an individual line.

    Abstract: instantiate :class:`HeaderTradeAllowanceCharge` or
    :class:`LineTradeAllowanceCharge` — those sentinel subclasses set
    the class-level ``context`` flag so :meth:`_field_profile` can
    pick the right BT-id when gating ``calculation_percent`` and
    ``basis_amount``. Those fields ship at BASIC_WL (BT-93 / BT-94 /
    BT-100 / BT-101) when on the document header but only at COMFORT
    (BT-137 / BT-138 / BT-141 / BT-142) on an invoice line.
    """

    tag: ClassVar[str] = "SpecifiedTradeAllowanceCharge"
    profile: ClassVar[Profile] = Profile.BASIC_WL
    context: ClassVar[Literal["header", "line"]]

    _validators: ClassVar[tuple[Validator["TradeAllowanceCharge"], ...]] = (
        br_dec_tac_amounts,
    )

    indicator: bool = field(metadata={"tag": "ChargeIndicator"})
    """Charge indicator (BG-20-0 / BG-21-0).

    Discriminates allowance (``false``) from charge (``true``).
    """
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent"}
    )
    """Allowance / charge percentage (BT-94 allowance / BT-101 charge
    at header; BT-138 / BT-142 at line).

    Percentage which, applied to the base amount, yields the
    allowance or charge amount. Gated BASIC_WL at header, COMFORT
    at line — see :meth:`_field_profile`.

    Note: up to COMFORT only the final result (``actual_amount``)
    is transmitted; the base amount and percentage are informational.
    """
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "amount": True}
    )
    """Allowance / charge base amount (BT-93 allowance / BT-100 charge
    at header; BT-137 / BT-141 at line).

    Base figure which, multiplied by the percentage, yields the
    allowance or charge amount. Gated BASIC_WL at header, COMFORT
    at line — see :meth:`_field_profile`.
    """
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount", "amount": True})
    """Allowance / charge amount (BT-92 allowance / BT-99 charge).

    Net (VAT-exclusive) value of the allowance or charge.
    """
    reason_code: str | None = field(default=None, metadata={"tag": "ReasonCode"})
    """Allowance / charge reason code (BT-98 allowance / BT-105 charge).

    Note: the reason code and the reason text shall indicate the
    same allowance / charge reason — enforced as ``BR-CO-21..24``
    in :mod:`trade`.

    Code list:
    [UNTDID 5189](https://service.unece.org/trade/untdid/d16b/tred/tred5189.htm)
    for allowances,
    [UNTDID 7161](https://service.unece.org/trade/untdid/d16b/tred/tred7161.htm)
    for charges.
    """
    reason: str | None = field(default=None, metadata={"tag": "Reason"})
    """Allowance / charge reason, free text (BT-97 allowance / BT-104 charge).

    Spells out in words why the allowance or charge applies.
    """
    category_trade_tax: CategoryTradeTax | None = None
    """VAT category for this allowance / charge (BT-95-00 / BT-102-00).

    Note: required at BASIC_WL per the appendix narrative; the XSD
    relaxes it to optional from BASIC onwards. Getafix keeps it
    ``Optional`` so the same dataclass works at every profile.
    """
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``ActualAmount`` (BT-92 / BT-99) and ``BasisAmount`` (BT-93 /
    BT-100).

    Populated on parse; set explicitly when building
    programmatically.
    """

    def __post_init__(self) -> None:
        if type(self) is TradeAllowanceCharge:
            raise TypeError(
                "TradeAllowanceCharge is abstract; instantiate "
                "HeaderTradeAllowanceCharge or LineTradeAllowanceCharge."
            )
        # Per-field type-shape checking lives in ``Element.__setattr__`` and
        # runs during construction, so there's no base ``__post_init__`` to
        # chain to here.

    @override
    def _field_profile(self, name: str) -> Profile | None:
        if name in ("calculation_percent", "basis_amount"):
            return Profile.COMFORT if self.context == "line" else Profile.BASIC_WL
        return None


@dataclass(kw_only=True, slots=True)
class HeaderTradeAllowanceCharge(TradeAllowanceCharge):
    """Document-level allowance / charge (BG-20 / BG-21).

    ``calculation_percent`` and ``basis_amount`` ship at BASIC_WL+
    (BT-93 / BT-94 / BT-100 / BT-101).
    """

    context: ClassVar[Literal["header", "line"]] = "header"


@dataclass(kw_only=True, slots=True)
class LineTradeAllowanceCharge(TradeAllowanceCharge):
    """Line-level allowance / charge (BG-27 / BG-28).

    ``calculation_percent`` and ``basis_amount`` ship at COMFORT+
    (BT-137 / BT-138 / BT-141 / BT-142).
    """

    context: ClassVar[Literal["header", "line"]] = "line"
