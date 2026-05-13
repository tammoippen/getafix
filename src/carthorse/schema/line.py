"""BG-25 invoice line item and its sub-tree.

The line item ``IncludedSupplyChainTradeLineItem`` (BG-25) shows up
from the BASIC profile onwards. The structure mirrors the header
shape but with line-specific element / BT IDs:

* ``AssociatedDocumentLineDocument`` (BT-126-00) — line ID + free
  text note.
* ``SpecifiedTradeProduct`` (BG-31) — what is being invoiced.
* ``SpecifiedLineTradeAgreement`` (BG-29) — net + optional gross
  price, with optional price-level allowance.
* ``SpecifiedLineTradeDelivery`` (BT-129-00) — billed quantity with
  unit code.
* ``SpecifiedLineTradeSettlement`` (BG-30-00) — line-level VAT
  category, optional period, optional allowance / charge groups, and
  the line total amount (BT-131).

This module covers the BASIC profile shape. EN 16931 enrichments
(``ApplicableProductCharacteristic`` BG-32, ``DesignatedProductClassification``
BG-33, ``OriginTradeCountry`` BG-34, line-level
``BuyerOrderReferencedDocument``, ``AdditionalReferencedDocument``,
``ReceivableSpecifiedTradeAccountingAccount``) and the EXTENDED
sub-line / IncludedReferencedProduct / per-line deviating party
groups are tracked in ``docs/IMPLEMENTATION_PLAN.md`` and not yet
modelled.

Validation rules covered:

* ✓ ``BR-29`` / ``BR-CO-19`` (period start ≤ end / at least one
  endpoint) inherited from :class:`BillingSpecifiedPeriod`.
* ✓ ``BR-CO-21..24`` allowance/charge reason coupling — inherited
  from :class:`TradeAllowanceCharge`.

Validation rules not yet enforced (see ``docs/VALIDATION.md``):

* ``BR-21..28`` — required line-level fields. Most are implicit
  through dataclass required fields; ``BR-27`` (BT-146 ≥ 0) and
  ``BR-28`` (BT-148 ≥ 0) are not yet checked.
* ``BR-CO-4`` — line VAT category required. Implicit through
  ``LineTradeTax.category_code`` being non-optional.
* ``BR-CO-10`` / ``BR-CO-13`` — sum identities BT-106 = sum(BT-131),
  BT-109 = sum(BT-131) - BT-107 + BT-108. Cross-line, not yet
  implemented.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.accounting import ApplicableTradeTax, TradeAllowanceCharge
from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.party import GlobalID
from carthorse.schema.settlement import BillingSpecifiedPeriod
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class LineIncludedNote(Element):
    """Line-level invoice note (BT-127-00) — just free-text content.

    Distinct from :class:`carthorse.schema.document.IncludedNote`
    (header-level BG-1) because at BASIC the line note carries only
    ``Content``; ``SubjectCode`` is reserved for header notes.
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC

    content: str = field(metadata={"tag": "Content"})


@dataclass(kw_only=True, slots=True)
class Quantity(Element):
    """``udt:QuantityType`` — decimal value plus mandatory ``unitCode`` (BT-129 (BilledQuantity), BT-149 (BasisQuantity)).

    ``unitCode`` follows UN/CEFACT Recommendation 20 / 21 (e.g. ``C62``
    for "one", ``H87`` for "piece", ``KGM`` for kilogram). The element
    name is set by the *enclosing field* (``BilledQuantity`` for
    BT-129, ``BasisQuantity`` for BT-149) — assigned via the
    ``tag`` ClassVar on subclasses or by re-tagging when nested.
    """

    tag: ClassVar[str] = "BilledQuantity"
    profile: ClassVar[Profile] = Profile.BASIC

    value: Decimal
    """The numeric quantity."""
    unit_code: str
    """UN/CEFACT Recommendation 20 / 21 unit-of-measure code."""

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
    """``ram:BasisQuantity`` — the unit basis for a price (BT-149)."""

    tag: ClassVar[str] = "BasisQuantity"


@dataclass(kw_only=True, slots=True)
class AppliedTradeAllowanceCharge(Element):
    """Price-level allowance (BT-147-00) applied to a gross price.

    Distinct from the document- and line-level
    :class:`carthorse.schema.accounting.TradeAllowanceCharge` because at
    BASIC the price-level only has ``ChargeIndicator`` and
    ``ActualAmount`` (no reason / category / VAT code). EN 16931
    widens it with calculation percent and basis amount; carthorse
    keeps both optional so the same class works at both profiles.
    """

    tag: ClassVar[str] = "AppliedTradeAllowanceCharge"
    profile: ClassVar[Profile] = Profile.BASIC

    indicator: bool = field(metadata={"tag": "ChargeIndicator"})
    """``false`` for an allowance (the spec only allows allowance at
    price level)."""
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount", "amount": True})
    """The price-level allowance amount (BT-147)."""
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent", "profile": Profile.COMFORT}
    )
    basis_amount: Decimal | None = field(
        default=None,
        metadata={"tag": "BasisAmount", "profile": Profile.COMFORT, "amount": True},
    )
    currency: str | None = None
    """Document currency (BT-5) echoed on the price-level amount(s).
    Populated on parse; set explicitly when building programmatically."""


@dataclass(kw_only=True, slots=True)
class GrossTradePrice(Element):
    """Gross item price (BT-148-00) — list price before allowance."""

    tag: ClassVar[str] = "GrossPriceProductTradePrice"
    profile: ClassVar[Profile] = Profile.BASIC

    charge_amount: Decimal = field(metadata={"tag": "ChargeAmount", "amount": True})
    """Item gross price (BT-148). Must not be negative (BR-28)."""
    basis_quantity: BasisQuantity | None = None
    """Item price basis quantity (BT-149-1)."""
    applied_allowance_charge: AppliedTradeAllowanceCharge | None = None
    """Price-level allowance (BG-X-1 in carthorse parlance, BT-147-00 in EN16931)."""
    currency: str | None = None
    """Document currency (BT-5) echoed on the gross price amount.
    Populated on parse; set explicitly when building programmatically."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # BR-28: The Item gross price (BT-148) shall NOT be negative.
        if self.charge_amount < 0:
            errors.append(
                ValidationError(
                    "BR-28", "The Item gross price (BT-148) shall NOT be negative."
                )
            )
        errors.extend(super(GrossTradePrice, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class NetTradePrice(Element):
    """Net item price (BT-146-00) — actual unit price billed."""

    tag: ClassVar[str] = "NetPriceProductTradePrice"
    profile: ClassVar[Profile] = Profile.BASIC

    charge_amount: Decimal = field(metadata={"tag": "ChargeAmount", "amount": True})
    """Item net price (BT-146). Must not be negative (BR-27)."""
    basis_quantity: BasisQuantity | None = None
    """Item price basis quantity (BT-149)."""
    currency: str | None = None
    """Document currency (BT-5) echoed on the net price amount.
    Populated on parse; set explicitly when building programmatically."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # BR-27: The Item net price (BT-146) shall NOT be negative.
        if self.charge_amount < 0:
            errors.append(
                ValidationError(
                    "BR-27", "The Item net price (BT-146) shall NOT be negative."
                )
            )
        errors.extend(super(NetTradePrice, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class TradeProduct(Element):
    """Item information (BG-31).
    """

    tag: ClassVar[str] = "SpecifiedTradeProduct"
    profile: ClassVar[Profile] = Profile.BASIC

    global_id: GlobalID | None = None
    """Item standard identifier with required schemeID (BT-157, BR-64)."""
    seller_assigned_id: str | None = field(
        default=None, metadata={"tag": "SellerAssignedID", "profile": Profile.COMFORT}
    )
    """Item Seller's identifier (BT-155); EN 16931+."""
    buyer_assigned_id: str | None = field(
        default=None, metadata={"tag": "BuyerAssignedID", "profile": Profile.COMFORT}
    )
    """Item Buyer's identifier (BT-156); EN 16931+."""
    name: str = field(metadata={"tag": "Name"})
    """Item name (BT-153)."""
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Item description (BT-154); EN 16931+."""


@dataclass(kw_only=True, slots=True)
class DocumentLineDocument(Element):
    """Per-line ``AssociatedDocumentLineDocument`` (BT-126-00)."""

    tag: ClassVar[str] = "AssociatedDocumentLineDocument"
    profile: ClassVar[Profile] = Profile.BASIC

    line_id: str = field(metadata={"tag": "LineID"})
    """Invoice line identifier (BT-126)."""
    note: LineIncludedNote | None = None
    """Optional free-text line note (BT-127-00)."""


@dataclass(kw_only=True, slots=True)
class LineTradeAgreement(Element):
    """Line-level agreement (BG-29) — gross + net price.

    Element order in the rendered XML follows the XSD sequence:
    ``GrossPriceProductTradePrice`` (optional) precedes
    ``NetPriceProductTradePrice`` (required).
    """

    tag: ClassVar[str] = "SpecifiedLineTradeAgreement"
    profile: ClassVar[Profile] = Profile.BASIC

    gross_price: GrossTradePrice | None = None
    """Item gross price (BT-148-00). Optional."""
    net_price: NetTradePrice
    """Item net price (BT-146-00). Required."""


@dataclass(kw_only=True, slots=True)
class LineTradeDelivery(Element):
    """Line-level delivery info (BT-129-00) — just the billed quantity."""

    tag: ClassVar[str] = "SpecifiedLineTradeDelivery"
    profile: ClassVar[Profile] = Profile.BASIC

    billed_quantity: Quantity = field(metadata={"tag": "BilledQuantity"})
    """Invoiced quantity (BT-129) with unit code (BT-130). Required."""


@dataclass(kw_only=True, slots=True)
class LineMonetarySummation(Element):
    """Line totals (BT-131-00).

    Only ``LineTotalAmount`` (BT-131) at BASIC. EN 16931 does not add
    fields here.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementLineMonetarySummation"
    profile: ClassVar[Profile] = Profile.BASIC

    line_total: Decimal = field(metadata={"tag": "LineTotalAmount", "amount": True})
    """Sum of (net price * quantity +/- line allowances/charges) (BT-131)."""
    currency: str | None = None
    """Document currency (BT-5) echoed on the line total.
    Populated on parse; set explicitly when building programmatically."""


@dataclass(kw_only=True, slots=True)
class LineTradeSettlement(Element):
    """Line-level settlement (BG-30-00).

    Carries the line VAT category (BG-30), an optional billing period
    (BG-26), optional allowance (BG-27) and charge (BG-28) groups, and
    the line total (BT-131-00).
    """

    tag: ClassVar[str] = "SpecifiedLineTradeSettlement"
    profile: ClassVar[Profile] = Profile.BASIC

    applicable_trade_tax: ApplicableTradeTax
    """Line VAT category (BG-30) — only TypeCode, CategoryCode and
    optional rate are populated at line level; the calculated/basis
    amounts live at header level (BG-23)."""
    billing_period: BillingSpecifiedPeriod | None = None
    """Line invoicing period (BG-26)."""
    allowance_charge: list[TradeAllowanceCharge] | None = None
    """Line allowance (BG-27) and/or charge (BG-28). Same dataclass
    distinguished by ``ChargeIndicator``."""
    monetary_summation: LineMonetarySummation
    """Line totals (BT-131-00). Required."""
