"""Invoice line items (BG-25) and the BG-29 / BG-30 sub-tree.

``IncludedSupplyChainTradeLineItem`` (BG-25) appears from the BASIC
profile onwards. The structure mirrors the header but with
line-scoped element / BT IDs:

* :class:`DocumentLineDocument` (BT-126-00) — line identifier
  (BT-126) and optional free-text note (BT-127-00).
* :class:`TradeProduct` (BG-31) — what is being invoiced: name
  (BT-153), standard / seller / buyer identifiers (BT-157 / BT-155 /
  BT-156), description (BT-154).
* :class:`LineTradeAgreement` (BG-29) — net price (BT-146-00,
  required) and an optional gross price (BT-148-00) with a possible
  price-level allowance (BT-147-00).
* :class:`LineTradeDelivery` (BT-129-00) — billed quantity (BT-129)
  with mandatory unit code (BT-130).
* :class:`LineTradeSettlement` (BG-30-00) — line VAT (BG-30),
  optional invoicing period (BG-26), optional allowances (BG-27) and
  charges (BG-28), and the line total (BT-131-00).

This module covers the BASIC profile shape. EN 16931 enrichments
(``ApplicableProductCharacteristic`` BG-32, ``DesignatedProductClassification``
BG-33, ``OriginTradeCountry`` BG-34, line-level
``BuyerOrderReferencedDocument``, ``AdditionalReferencedDocument``,
``ReceivableSpecifiedTradeAccountingAccount``) and the EXTENDED
sub-line / ``IncludedReferencedProduct`` / per-line deviating-party
groups are tracked in ``docs/IMPLEMENTATION_PLAN.md`` and not yet
modelled.

Validation rules covered:

* ✓ ``BR-27`` (BT-146 ≥ 0) — :meth:`NetTradePrice.validate_internal`.
* ✓ ``BR-28`` (BT-148 ≥ 0) — :meth:`GrossTradePrice.validate_internal`.
* ✓ ``BR-29`` / ``BR-CO-19`` (period start ≤ end / at least one
  endpoint) inherited from :class:`BillingSpecifiedPeriod`.
* ✓ ``BR-CO-21..24`` allowance/charge reason coupling — inherited
  from :class:`TradeAllowanceCharge`.

Validation rules not yet enforced (see ``docs/VALIDATION.md``):

* ``BR-21..26`` — required line-level fields. Implicit through the
  required dataclass fields.
* ``BR-CO-4`` — line VAT category required. Implicit through
  ``LineTradeSettlement.applicable_trade_tax`` being non-optional.
* ``BR-CO-10`` / ``BR-CO-13`` — sum identities ``BT-106 = sum(BT-131)``
  and ``BT-109 = sum(BT-131) - sum(BT-92) + sum(BT-99)``. Cross-line;
  live in :mod:`trade`.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.rules import Validator
from carthorse.rules.line import br_27, br_28
from carthorse.schema.accounting import ApplicableTradeTax, TradeAllowanceCharge
from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.party import GlobalID
from carthorse.schema.settlement import BillingSpecifiedPeriod
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class LineIncludedNote(Element):
    """Invoice line note (BT-127-00).

    Detailed information about the free text of the line item.

    Note: distinct from :class:`carthorse.schema.document.IncludedNote`
    (header-level BG-1) because at BASIC the line note carries only
    ``Content``; ``SubjectCode`` is reserved for header notes.
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC

    content: str = field(metadata={"tag": "Content"})
    """Invoice line note (BT-127).

    A textual note that gives unstructured information that is
    relevant to the invoice line.
    """


@dataclass(kw_only=True, slots=True)
class Quantity(Element):
    """``udt:QuantityType`` — decimal value plus mandatory ``unitCode``.

    Used for the invoiced quantity (BT-129 with unit code BT-130) and
    the item price base quantity (BT-149 / BT-149-1 with unit code
    BT-150 / BT-150-1). The XML element name is set by the *enclosing
    field* — ``BilledQuantity`` for BT-129, ``BasisQuantity`` for the
    base quantity — via the ``tag`` ClassVar on subclasses or by
    re-tagging when nested.
    """

    tag: ClassVar[str] = "BilledQuantity"
    profile: ClassVar[Profile] = Profile.BASIC

    value: Decimal
    """The numeric quantity."""
    unit_code: str
    """Unit-of-measure code (BT-130 / BT-150).

    Code list: UN/ECE Recommendation 20 (and 21 for passengers, types
    of cargo, packages and packaging materials) — e.g. ``C62`` for
    "one", ``H87`` for "piece", ``KGM`` for kilogram.
    """

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), attrs={"unitCode": self.unit_code})[str(self.value)]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "unitCode" not in elem.attrib:
            raise ValueError("Quantity element missing required unitCode")
        if elem.text is None:
            raise ValueError
        return cls(value=Decimal(elem.text.strip()), unit_code=elem.attrib["unitCode"])


@dataclass(kw_only=True, slots=True)
class BasisQuantity(Quantity):
    """Item price base quantity (BT-149 / BT-149-1).

    The number of item units to which the price applies. Carries the
    unit-of-measure code (BT-150 / BT-150-1) which must match the
    invoiced-quantity unit (BT-130).
    """

    tag: ClassVar[str] = "BasisQuantity"


@dataclass(kw_only=True, slots=True)
class AppliedTradeAllowanceCharge(Element):
    """Item price discount (BT-147-00).

    The price-level allowance applied to the gross price to arrive
    at the net price. Only applies when the discount is provided per
    unit and is not already baked into the gross price.

    Note: distinct from :class:`carthorse.schema.accounting.TradeAllowanceCharge`
    (document- and line-level BG-20/21/27/28) because at BASIC the
    price-level only has ``ChargeIndicator`` and ``ActualAmount`` —
    no reason, category or VAT code. EN 16931 widens it with
    calculation percent and basis amount; carthorse keeps both
    optional so the same class works at either profile.
    """

    tag: ClassVar[str] = "AppliedTradeAllowanceCharge"
    profile: ClassVar[Profile] = Profile.BASIC

    indicator: bool = field(metadata={"tag": "ChargeIndicator"})
    """Allowance / charge indicator.

    Note: the spec only permits an *allowance* (``false``) at price
    level — a price-level charge is not modelled by EN 16931.
    """
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount", "amount": True})
    """Item price discount (BT-147).

    The total discount subtracted from the item gross price to
    calculate the item net price.
    """
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent", "profile": Profile.COMFORT}
    )
    """Item price discount percentage; COMFORT+."""
    basis_amount: Decimal | None = field(
        default=None,
        metadata={"tag": "BasisAmount", "profile": Profile.COMFORT, "amount": True},
    )
    """Item price discount basis amount; COMFORT+."""
    currency: str | None = None
    """Document currency (BT-5) echoed on every amount attribute.

    Populated on parse from the ``currencyID`` attribute; set
    explicitly when building programmatically.
    """


@dataclass(kw_only=True, slots=True)
class GrossTradePrice(Element):
    """Item gross price (BT-148-00).

    Detailed information on the gross price of the item — the unit
    price before subtracting the item price discount.
    """

    tag: ClassVar[str] = "GrossPriceProductTradePrice"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["GrossTradePrice"], ...]] = (br_28,)

    charge_amount: Decimal = field(metadata={"tag": "ChargeAmount", "amount": True})
    """Item gross price (BT-148).

    The unit price, exclusive of VAT, before subtracting the item
    price discount.

    Note: must not be negative — enforced by ``BR-28``.
    """
    basis_quantity: BasisQuantity | None = None
    """Item price base quantity (BT-149-1) for the gross price."""
    applied_allowance_charge: AppliedTradeAllowanceCharge | None = None
    """Item price discount (BT-147-00) applied to the gross price."""
    currency: str | None = None
    """Document currency (BT-5) echoed on the gross-price amount.

    Populated on parse from the ``currencyID`` attribute; set
    explicitly when building programmatically.
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors = [e for v in self._validators for e in v(self, profile)]
        errors.extend(super(GrossTradePrice, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class NetTradePrice(Element):
    """Item net price (BT-146-00).

    Detailed information on the net price of the item — the unit
    price actually billed (gross price less any item price discount).
    """

    tag: ClassVar[str] = "NetPriceProductTradePrice"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["NetTradePrice"], ...]] = (br_27,)

    charge_amount: Decimal = field(metadata={"tag": "ChargeAmount", "amount": True})
    """Item net price (BT-146).

    The price of an item, exclusive of VAT, after subtracting the
    item price discount.

    Note: the net price must equal the gross price (BT-148) less the
    item price discount (BT-147), and must not be negative —
    enforced by ``BR-27``.
    """
    basis_quantity: BasisQuantity | None = None
    """Item price base quantity (BT-149)."""
    currency: str | None = None
    """Document currency (BT-5) echoed on the net-price amount.

    Populated on parse from the ``currencyID`` attribute; set
    explicitly when building programmatically.
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors = [e for v in self._validators for e in v(self, profile)]
        errors.extend(super(NetTradePrice, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class TradeProduct(Element):
    """Item information (BG-31).

    A group of business terms providing information about the goods
    and services invoiced.
    """

    tag: ClassVar[str] = "SpecifiedTradeProduct"
    profile: ClassVar[Profile] = Profile.BASIC

    global_id: GlobalID | None = None
    """Item standard identifier (BT-157).

    An item identifier based on a registered scheme — the
    ``schemeID`` attribute is required when the value is set
    (``BR-64``).
    """
    seller_assigned_id: str | None = field(
        default=None, metadata={"tag": "SellerAssignedID", "profile": Profile.COMFORT}
    )
    """Item Seller's identifier (BT-155); COMFORT+."""
    buyer_assigned_id: str | None = field(
        default=None, metadata={"tag": "BuyerAssignedID", "profile": Profile.COMFORT}
    )
    """Item Buyer's identifier (BT-156); COMFORT+."""
    name: str = field(metadata={"tag": "Name"})
    """Item name (BT-153)."""
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Item description (BT-154); COMFORT+.

    Allows describing the item and its features in more detail than
    the item name.
    """


@dataclass(kw_only=True, slots=True)
class DocumentLineDocument(Element):
    """Associated line document (BT-126-00).

    Per-line wrapper carrying the line identifier and an optional
    free-text note.
    """

    tag: ClassVar[str] = "AssociatedDocumentLineDocument"
    profile: ClassVar[Profile] = Profile.BASIC

    line_id: str = field(metadata={"tag": "LineID"})
    """Invoice line identifier (BT-126).

    A unique identifier for the individual line within the invoice.
    """
    note: LineIncludedNote | None = None
    """Optional free-text line note (BT-127-00)."""


@dataclass(kw_only=True, slots=True)
class LineTradeAgreement(Element):
    """Line trade agreement / price details (BG-29).

    A group of business terms providing information about the price
    applied for the goods and services invoiced on the invoice line.

    Note: element order in the rendered XML follows the XSD sequence
    — ``GrossPriceProductTradePrice`` (optional) precedes
    ``NetPriceProductTradePrice`` (required).
    """

    tag: ClassVar[str] = "SpecifiedLineTradeAgreement"
    profile: ClassVar[Profile] = Profile.BASIC

    gross_price: GrossTradePrice | None = None
    """Item gross price (BT-148-00)."""
    net_price: NetTradePrice
    """Item net price (BT-146-00); required."""


@dataclass(kw_only=True, slots=True)
class LineTradeDelivery(Element):
    """Line trade delivery (BT-129-00).

    Carries the invoiced quantity for the line.
    """

    tag: ClassVar[str] = "SpecifiedLineTradeDelivery"
    profile: ClassVar[Profile] = Profile.BASIC

    billed_quantity: Quantity = field(metadata={"tag": "BilledQuantity"})
    """Invoiced quantity (BT-129) with unit-of-measure code (BT-130);
    required."""


@dataclass(kw_only=True, slots=True)
class LineMonetarySummation(Element):
    """Invoice line totals (BT-131-00).

    Detailed information about the line totals. Only
    ``LineTotalAmount`` (BT-131) is modelled at BASIC; EN 16931 does
    not add fields here.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementLineMonetarySummation"
    profile: ClassVar[Profile] = Profile.BASIC

    line_total: Decimal = field(metadata={"tag": "LineTotalAmount", "amount": True})
    """Invoice line net amount (BT-131).

    The total amount of the invoice line — net of VAT but inclusive
    of line-level allowances, charges and other relevant taxes
    (computed as ``net_price * billed_quantity +/- line allowances /
    charges``).
    """
    currency: str | None = None
    """Document currency (BT-5) echoed on the line-total amount.

    Populated on parse from the ``currencyID`` attribute; set
    explicitly when building programmatically.
    """


@dataclass(kw_only=True, slots=True)
class LineTradeSettlement(Element):
    """Line trade settlement (BG-30-00).

    Grouping of billing information at line level: line VAT
    (BG-30), optional invoicing period (BG-26), optional allowances
    (BG-27) and charges (BG-28), and the line total (BT-131-00).
    """

    tag: ClassVar[str] = "SpecifiedLineTradeSettlement"
    profile: ClassVar[Profile] = Profile.BASIC

    applicable_trade_tax: ApplicableTradeTax
    """Line VAT information (BG-30).

    Note: only ``TypeCode``, ``CategoryCode`` and the optional rate
    are populated at line level — the calculated and basis amounts
    live on the header-level breakdown (BG-23).
    """
    billing_period: BillingSpecifiedPeriod | None = None
    """Invoice line period (BG-26) — also known as the line delivery
    period."""
    allowance_charge: list[TradeAllowanceCharge] | None = None
    """Invoice line allowances (BG-27) and charges (BG-28).

    Note: same dataclass for both, distinguished by ``ChargeIndicator``.
    All charges and taxes are assumed to be liable to the same VAT
    rate as the invoice line.
    """
    monetary_summation: LineMonetarySummation
    """Invoice line totals (BT-131-00); required."""
