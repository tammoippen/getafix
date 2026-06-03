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

This module covers the BASIC profile shape plus the COMFORT
product enrichments :class:`ProductCharacteristic` (BG-32),
:class:`ProductClassification` (BG-33), :class:`OriginCountry`
(BG-34) and the line-level reference fields
:class:`LineBuyerOrderReferencedDocument` (BT-132),
:class:`LineAdditionalReferencedDocument` (BT-128) and the line
reuse of :class:`~carthorse.schema.settlement.ReceivableAccountingAccount`
(BT-133). The EXTENDED sub-line / ``IncludedReferencedProduct`` /
per-line deviating-party groups are modelled here too; remaining
EXTENDED line-level references are listed in ``docs/STRUCTURES.md §5.1``.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, Literal, Self, override

from tagic.xml import XML

from carthorse.rules import Validator
from carthorse.rules._types import fields_only_at, max_decimals
from carthorse.rules.line import br_27, br_28
from carthorse.schema.accounting import ApplicableTradeTax, LineTradeAllowanceCharge
from carthorse.schema.element import Element, ETElement
from carthorse.schema.party import (
    GlobalID,
    ItemSellerTradeParty,
    ShipToTradeParty,
    UltimateShipToTradeParty,
)
from carthorse.schema.settlement import (
    BillingSpecifiedPeriod,
    ReceivableAccountingAccount,
)
from carthorse.schema.types import LineStatusReasonCode, Namespace, Profile


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
    """Numeric quantity — role-dependent BT id: BT-129 on
    ``BilledQuantity`` (invoiced quantity), BT-149 / BT-149-1 on
    ``BasisQuantity`` (item price base quantity)."""
    unit_code: str
    """Unit-of-measure code — role-dependent BT id: BT-130 on
    ``BilledQuantity``, BT-150 / BT-150-1 on ``BasisQuantity``.
    Rendered as the ``unitCode`` attribute.

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
        unit_code = elem.attrib.get("unitCode")
        if unit_code is None:
            raise ValueError("Quantity element missing required unitCode")
        if elem.text is None:
            raise ValueError
        return cls(value=Decimal(elem.text.strip()), unit_code=unit_code)


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
    """Allowance / charge indicator (BT-147-01 for the allowance side;
    BT-X-302-01 for the EXTENDED charge side).

    Note: EN 16931 only permits an *allowance* (``false``) at price
    level — a price-level charge (``true``) is an EXTENDED-only
    Factur-X extension under BT-X-302-00.
    """
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount", "amount": True})
    """Item price discount (BT-147).

    The total discount subtracted from the item gross price to
    calculate the item net price.
    """
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent", "profile": Profile.COMFORT}
    )
    """Item price discount percentage (BT-X-300); COMFORT+.

    Note: the XSD shares this node between allowance and charge — BT-X-300
    is the charge-side id, the allowance side has no published BT.
    """
    basis_amount: Decimal | None = field(
        default=None,
        metadata={"tag": "BasisAmount", "profile": Profile.COMFORT, "amount": True},
    )
    """Item price discount basis amount (BT-X-301); COMFORT+.

    Note: charge-side id; the allowance side has no published BT.
    """
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


@dataclass(kw_only=True, slots=True)
class ProductCharacteristic(Element):
    """Item attribute (BG-32); COMFORT+.

    A name/value pair describing a feature of the item — its colour,
    weight, dimensions, voltage, etc. ``BR-54`` requires both
    ``Description`` (BT-160) and ``Value`` (BT-161) when the group is
    present; the dataclass enforces this by declaring both as
    non-Optional.
    """

    tag: ClassVar[str] = "ApplicableProductCharacteristic"
    profile: ClassVar[Profile] = Profile.COMFORT

    description: str = field(metadata={"tag": "Description"})
    """Item attribute name (BT-160)."""
    value: str = field(metadata={"tag": "Value"})
    """Item attribute value (BT-161)."""


@dataclass(kw_only=True, slots=True)
class ProductClassification(Element):
    """Item classification (BT-158-00); COMFORT+.

    A coded classification of the item according to a registered
    scheme. ``list_id`` (BT-158-1) names the scheme — required when
    ``class_code`` (BT-158) is set per ``BR-65``. Optional
    ``list_version_id`` (BT-158-2) versions the scheme.

    Note: EN 16931 modelled this group as BG-33; Factur-X 1.08 folds
    it into the BT-158-00 wrapper id.

    Code list for ``list_id``: UNTDID 7143 (extended Code List).
    """

    tag: ClassVar[str] = "DesignatedProductClassification"
    profile: ClassVar[Profile] = Profile.COMFORT

    class_code: str
    """Item classification identifier (BT-158)."""
    list_id: str
    """Scheme identifier (BT-158-1); required per ``BR-65``."""
    list_version_id: str | None = None
    """Scheme version identifier (BT-158-2)."""
    class_name: str | None = None
    """Optional human-readable label for the classification scheme
    (BT-X-13 ``ClassName``); EXTENDED only.

    Real-world samples emit it next to the ``ClassCode`` listID to
    spell out the scheme verbatim — ``"Zolltarifnummer"`` for HS,
    ``"UNSPSC"``, ``"eCl@ss"``, ``"STQ"``, etc. — even though the
    listID attribute already encodes the same information. Echo it
    back on round-trip rather than dropping it.
    """

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        attrs: dict[str, str | bool] = {"listID": self.list_id}
        if self.list_version_id is not None:
            attrs["listVersionID"] = self.list_version_id
        children: list[XML] = [
            XML(f"{Namespace.ram.name}:ClassCode", attrs=attrs)[self.class_code]
        ]
        if self.class_name is not None:
            children.append(XML(f"{Namespace.ram.name}:ClassName")[self.class_name])
        return XML(self.get_tag())[*children]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        code_qtag = Namespace.ram.get_qualified_tag("ClassCode")
        name_qtag = Namespace.ram.get_qualified_tag("ClassName")
        class_code: str | None = None
        list_id: str | None = None
        list_version_id: str | None = None
        class_name: str | None = None
        for child in elem:
            if child.tag == code_qtag:
                if child.text is None:
                    raise ValueError(f"{cls.__name__}: ClassCode element has no text")
                class_code = child.text.strip()
                list_id = child.attrib.get("listID")
                list_version_id = child.attrib.get("listVersionID")
            elif child.tag == name_qtag:
                class_name = child.text.strip() if child.text else None
        if class_code is None or list_id is None:
            raise ValueError(f"{cls.__name__}: ClassCode + listID are required")
        return cls(
            class_code=class_code,
            list_id=list_id,
            list_version_id=list_version_id,
            class_name=class_name,
        )


@dataclass(kw_only=True, slots=True)
class OriginCountry(Element):
    """Item country of origin (BT-159-00); COMFORT+.

    The country from which the item originates, as an ISO 3166-1
    alpha-2 code on the single inner ``<ram:ID>`` element (BT-159).

    Note: EN 16931 modelled this group as BG-34; Factur-X 1.08 folds
    it into the BT-159-00 wrapper id.
    """

    tag: ClassVar[str] = "OriginTradeCountry"
    profile: ClassVar[Profile] = Profile.COMFORT

    id: str = field(metadata={"tag": "ID"})
    """Country code (BT-159), ISO 3166-1 alpha-2."""


@dataclass(kw_only=True, slots=True)
class UnitQuantity(Quantity):
    """Sub-product quantity within a bundle (BT-X-20); EXTENDED-only.

    The included quantity of a bundled sub-product. Same
    numeric+unitCode shape as :class:`Quantity` /
    :class:`BasisQuantity` — only the XML element name differs.
    Used by :class:`IncludedReferencedProduct`.
    """

    tag: ClassVar[str] = "UnitQuantity"
    profile: ClassVar[Profile] = Profile.EXTENDED


@dataclass(kw_only=True, slots=True)
class ChargeFreeQuantity(Quantity):
    """Free-goods quantity on an invoice line (BT-X-46); EXTENDED-only.

    The number of units delivered free of charge (e.g. "buy 10, get
    1 free"). Same numeric+unitCode shape as :class:`Quantity`."""

    tag: ClassVar[str] = "ChargeFreeQuantity"
    profile: ClassVar[Profile] = Profile.EXTENDED


@dataclass(kw_only=True, slots=True)
class PackageQuantity(Quantity):
    """Number of packages for an invoice line (BT-X-47); EXTENDED-only."""

    tag: ClassVar[str] = "PackageQuantity"
    profile: ClassVar[Profile] = Profile.EXTENDED


@dataclass(kw_only=True, slots=True)
class PerPackageUnitQuantity(Quantity):
    """Units per package for an invoice line (BT-X-561); EXTENDED-only."""

    tag: ClassVar[str] = "PerPackageUnitQuantity"
    profile: ClassVar[Profile] = Profile.EXTENDED


@dataclass(kw_only=True, slots=True)
class IndividualTradeProductInstance(Element):
    """Per-instance product details (BG-X-84, 0..*); EXTENDED only.

    Carries a per-unit batch lot ID (BT-X-306) and / or
    supplier-assigned serial number (BT-X-307).
    """

    tag: ClassVar[str] = "IndividualTradeProductInstance"
    profile: ClassVar[Profile] = Profile.EXTENDED

    batch_id: str | None = field(default=None, metadata={"tag": "BatchID"})
    """Batch / lot identifier (BT-X-306)."""
    supplier_assigned_serial_id: str | None = field(
        default=None, metadata={"tag": "SupplierAssignedSerialID"}
    )
    """Serial number assigned by the Supplier (BT-X-307)."""


@dataclass(kw_only=True, slots=True)
class IncludedReferencedProduct(Element):
    """Sub-product reference within a bundled item (BG-X-1, 0..*); EXTENDED only.

    Used when a single line item ships as a composite (bundle, set,
    case-pack) and the invoice needs to enumerate the constituents
    — e.g. a "Joghurt-Variety-12er" line with three sub-products
    Erdbeer / Banane / Schoko.

    Field order matches the XSD ``ReferencedProductType``: ``ID`` →
    ``GlobalID`` → ``SellerAssignedID`` → ``BuyerAssignedID`` →
    ``IndustryAssignedID`` → ``Name`` → ``Description`` →
    ``UnitQuantity``.
    """

    tag: ClassVar[str] = "IncludedReferencedProduct"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Local sub-product identifier (BT-X-308)."""
    global_id: GlobalID | None = None
    """Sub-product standard identifier (BT-X-15; GS1 / EAN / GTIN, etc.)."""
    seller_assigned_id: str | None = field(
        default=None, metadata={"tag": "SellerAssignedID"}
    )
    """Seller's sub-product identifier (BT-X-16)."""
    buyer_assigned_id: str | None = field(
        default=None, metadata={"tag": "BuyerAssignedID"}
    )
    """Buyer's sub-product identifier (BT-X-17)."""
    industry_assigned_id: str | None = field(
        default=None, metadata={"tag": "IndustryAssignedID"}
    )
    """Industry sub-product identifier (BT-X-309)."""
    name: str = field(metadata={"tag": "Name"})
    """Sub-product name (BT-X-18, required)."""
    description: str | None = field(default=None, metadata={"tag": "Description"})
    """Sub-product description (BT-X-19)."""
    unit_quantity: UnitQuantity | None = None
    """Sub-product quantity per bundle (BT-X-20; Quantity-shaped,
    tagged ``UnitQuantity``)."""


@dataclass(kw_only=True, slots=True)
class TradeProduct(Element):
    """Item information (BG-31).

    A group of business terms providing information about the goods
    and services invoiced. EN 16931 enriches the BASIC shape with
    the three product groups :class:`ProductCharacteristic` (BG-32),
    :class:`ProductClassification` (BG-33), and :class:`OriginCountry`
    (BG-34). EXTENDED layers on six per-item identifier / naming
    fields (``IndustryAssignedID`` / ``ModelID`` / ``BatchID`` /
    ``BrandName`` / ``ModelName``), plus the
    :class:`IndividualTradeProductInstance` (BG-X-84) and
    :class:`IncludedReferencedProduct` (BG-X-1) groups for per-unit
    serial / batch and for bundle / set composition.
    """

    tag: ClassVar[str] = "SpecifiedTradeProduct"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["TradeProduct"], ...]] = (
        fields_only_at(
            Profile.EXTENDED,
            "industry_assigned_id",
            "model_id",
            "batch_id",
            "brand_name",
            "model_name",
            "individual_product_instances",
            "included_referenced_products",
        ),
    )

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
    industry_assigned_id: str | None = field(
        default=None,
        metadata={"tag": "IndustryAssignedID", "profile": Profile.EXTENDED},
    )
    """Industry-assigned item identifier (BT-X-532); EXTENDED only.

    Codelist UNTDED 6313 + Factur-X extension (``BR-FXEXT-04``).
    """
    model_id: str | None = field(
        default=None, metadata={"tag": "ModelID", "profile": Profile.EXTENDED}
    )
    """Model / variant identifier (BT-X-533); EXTENDED only."""
    name: str = field(metadata={"tag": "Name"})
    """Item name (BT-153)."""
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Item description (BT-154); COMFORT+."""
    batch_id: list[str] | None = field(
        default=None, metadata={"tag": "BatchID", "profile": Profile.EXTENDED}
    )
    """Batch / lot identifiers (BT-X-534, 0..*); EXTENDED only.

    Per-batch traceability codes attached at the parent item level.
    For per-instance serial / batch carry the value on
    :attr:`individual_product_instances` instead.
    """
    brand_name: str | None = field(
        default=None, metadata={"tag": "BrandName", "profile": Profile.EXTENDED}
    )
    """Brand name (BT-X-535); EXTENDED only."""
    model_name: str | None = field(
        default=None, metadata={"tag": "ModelName", "profile": Profile.EXTENDED}
    )
    """Model name (BT-X-536); EXTENDED only."""
    characteristics: list[ProductCharacteristic] | None = None
    """Item attributes (BG-32, 0..*); COMFORT+."""
    classifications: list[ProductClassification] | None = None
    """Item classifications (BT-158-00, 0..*); COMFORT+."""
    individual_product_instances: list[IndividualTradeProductInstance] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Per-instance batch / serial details (BG-X-84, 0..*); EXTENDED only.

    Each entry carries a ``BatchID`` and / or
    ``SupplierAssignedSerialID`` (BT-X-307). The Maschinen sample
    exercises the single-serial case.
    """
    origin_country: OriginCountry | None = None
    """Item country of origin (BT-159-00, 0..1); COMFORT+."""
    included_referenced_products: list[IncludedReferencedProduct] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Sub-products bundled into this line item (BG-X-1, 0..*); EXTENDED only.

    Used for variety packs, case-packs, and bundles. Each entry
    carries its own GlobalID / Name / UnitQuantity. The
    Warenrechnung sample exercises the typical case.
    """


@dataclass(kw_only=True, slots=True)
class DocumentLineDocument(Element):
    """Associated line document (BT-126-00).

    Per-line wrapper carrying the line identifier, optional EXTENDED
    sub-invoice-line bookkeeping (parent link, status, subtype),
    and an optional free-text note.
    """

    tag: ClassVar[str] = "AssociatedDocumentLineDocument"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["DocumentLineDocument"], ...]] = (
        fields_only_at(
            Profile.EXTENDED, "parent_line_id", "status_code", "status_reason_code"
        ),
    )

    line_id: str = field(metadata={"tag": "LineID"})
    """Invoice line identifier (BT-126).

    A unique identifier for the individual line within the invoice.
    """
    parent_line_id: str | None = field(
        default=None, metadata={"tag": "ParentLineID", "profile": Profile.EXTENDED}
    )
    """Identifier of parent line (BT-X-304); EXTENDED only.

    References another line's ``line_id`` (BT-126). Used to build
    a hierarchical sub-invoice-line tree where ``GROUP`` subtotal
    lines sit above their constituent ``DETAIL`` children. The
    cross-line walker (``rules/extended.py``) checks every
    ``parent_line_id`` resolves to an existing ``line_id``
    (``BR-FXEXT-11``) and that the parent's ``status_reason_code``
    is set (``BR-FXEXT-06``).
    """
    status_code: str | None = field(
        default=None, metadata={"tag": "LineStatusCode", "profile": Profile.EXTENDED}
    )
    """Line status code (BT-X-7); EXTENDED only.

    Per the XSD this is ``qdt:LineStatusCodeType`` (UNTDID 1229,
    "action request" — ADD / DELETE / CHANGE / NO_ACTION / …).
    Modelled as a plain ``str`` — the UNTDID 1229 codelist is not
    enumerated by carthorse.
    """
    status_reason_code: LineStatusReasonCode | None = field(
        default=None,
        metadata={"tag": "LineStatusReasonCode", "profile": Profile.EXTENDED},
    )
    """Subtype of invoice line item (BT-X-8); EXTENDED only.

    Discriminator that the per-category sum rules (``BR-FXEXT-{cat}-08``
    in §5.3) and the line-level qualifications (``BR-FXEXT-22..27``
    in §5.4) consult to skip ``GROUP`` subtotal headers and
    ``INFORMATION`` lines. When omitted, the line behaves like
    ``DETAIL``.
    """
    note: LineIncludedNote | None = None
    """Optional free-text line note (BT-127-00)."""


@dataclass(kw_only=True, slots=True)
class LineBuyerOrderReferencedDocument(Element):
    """Line-level purchase-order line reference (BT-132-00); COMFORT+.

    Distinct from the header
    :class:`~carthorse.schema.references.BuyerOrderReferencedDocument`:
    at COMFORT this variant carries only ``LineID`` (BT-132 — the
    referenced purchase-order line position). EXTENDED widens it to
    additionally carry ``IssuerAssignedID`` (per-line purchase order
    document ID — when an invoice line references a *different*
    order from the header's) and ``FormattedIssueDateTime`` (the
    referenced order's issue date).
    """

    tag: ClassVar[str] = "BuyerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    _validators: ClassVar[tuple[Validator["LineBuyerOrderReferencedDocument"], ...]] = (
        fields_only_at(
            Profile.EXTENDED, "issuer_assigned_id", "formatted_issue_date_time"
        ),
    )

    issuer_assigned_id: str | None = field(
        default=None, metadata={"tag": "IssuerAssignedID", "profile": Profile.EXTENDED}
    )
    """Per-line purchase order document ID (BT-X-21); EXTENDED only.

    Used when an invoice line references a different purchase order
    than the header (BT-X-21 in the EXTENDED ``Sammelrechnung``
    aggregated-invoice pattern). At COMFORT the header's
    :class:`~carthorse.schema.references.BuyerOrderReferencedDocument`
    carries the single shared order; at EXTENDED each line may
    override.
    """
    line_id: str | None = field(default=None, metadata={"tag": "LineID"})
    """Referenced purchase-order line position (BT-132).

    Required in practice at COMFORT (the EN16931 use case for this
    element is per-line PO positions), but the XSD makes every
    field of ``ReferencedDocumentType`` optional and EXTENDED
    samples use this class as a wrapper for a per-line
    ``IssuerAssignedID`` reference without a ``LineID`` — so the
    field is modelled as ``Optional`` and the "required at COMFORT"
    contract is left to the consumer / future BR-X-* validator.
    """
    formatted_issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.EXTENDED},
    )
    """Issue date of the referenced order (BT-X-22, wrapped in
    BT-X-22-00); EXTENDED only."""


@dataclass(kw_only=True, slots=True)
class LineQuotationReferencedDocument(Element):
    """Line-level quotation reference (BG-X-47); EXTENDED only.

    Per-line pointer to a previously issued quotation that this
    invoice line corresponds to. Same ``ReferencedDocumentType``
    XSD shape as :class:`LineBuyerOrderReferencedDocument` — carries
    ``IssuerAssignedID`` (the quotation document identifier),
    ``LineID`` (the quotation's line position), and an optional
    ``FormattedIssueDateTime`` for the quotation's issue date.
    """

    tag: ClassVar[str] = "QuotationReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str | None = field(
        default=None, metadata={"tag": "IssuerAssignedID"}
    )
    """Quotation document identifier (BT-X-310)."""
    line_id: str | None = field(default=None, metadata={"tag": "LineID"})
    """Quotation line position (BT-X-311)."""
    formatted_issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Quotation issue date (BT-X-312, wrapped in BT-X-312-00)."""


@dataclass(kw_only=True, slots=True)
class LineAdditionalReferencedDocument(Element):
    """Line-level invoice-line object identifier (BT-128-00); COMFORT+.

    Distinct from the header :class:`~carthorse.schema.references.AdditionalReferencedDocument`:
    the line variant only carries ``IssuerAssignedID`` (BT-128), a
    fixed ``TypeCode`` of ``"130"`` (Invoicing data sheet, BT-128-0)
    and an optional ``ReferenceTypeCode`` (BT-128-1, UNTDID 1153
    scheme id). It never carries BT-122 supporting-document fields.
    """

    tag: ClassVar[str] = "AdditionalReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Invoice line object identifier (BT-128)."""
    type_code: Literal["130"] = field(default="130", metadata={"tag": "TypeCode"})
    """Document type code (BT-128-0); fixed to ``"130"``."""
    reference_type_code: str | None = field(
        default=None, metadata={"tag": "ReferenceTypeCode"}
    )
    """Scheme identifier (BT-128-1).

    Code list: UNTDID 1153 (reference qualifier).
    """


@dataclass(kw_only=True, slots=True)
class LineTradeAgreement(Element):
    """Line trade agreement / price details (BG-29).

    A group of business terms providing information about the price
    applied for the goods and services invoiced on the invoice line.

    Note: element order in the rendered XML follows the XSD sequence
    — ``BuyerOrderReferencedDocument`` (BT-132-00; COMFORT+) precedes
    ``QuotationReferencedDocument`` (EXTENDED) precedes
    ``GrossPriceProductTradePrice`` (optional) which precedes
    ``NetPriceProductTradePrice`` (required).

    :class:`~carthorse.schema.party.ItemSellerTradeParty` (BG-X-90)
    is modelled here (field :attr:`item_seller`).

    Deferred EXTENDED slots (per-line twins of structures already
    modelled at header level; no observed real-world use — add when
    a fixture needs them):

    * ``ApplicableTradeDeliveryTerms`` — line-level Incoterms.
    * ``SellerOrderReferencedDocument`` — per-line seller's order ref.
    * ``ContractReferencedDocument`` — per-line contract reference.
    * ``AdditionalReferencedDocument`` (0..*) — extra per-line refs.
    * ``UltimateCustomerOrderReferencedDocument`` (0..*) — per-line
      ultimate-customer order ref.
    """

    tag: ClassVar[str] = "SpecifiedLineTradeAgreement"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["LineTradeAgreement"], ...]] = (
        fields_only_at(Profile.EXTENDED, "quotation_ref", "item_seller"),
    )

    buyer_order_ref: LineBuyerOrderReferencedDocument | None = None
    """Referenced purchase-order line (BT-132-00); COMFORT+."""
    quotation_ref: LineQuotationReferencedDocument | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Referenced quotation line (BG-X-47, 0..1); EXTENDED only."""
    gross_price: GrossTradePrice | None = None
    """Item gross price (BT-148-00)."""
    net_price: NetTradePrice | None = None
    """Item net price (BT-146-00).

    Required at every profile up to EN 16931 (the EN16931 base rule
    ``BR-26`` makes BT-146 mandatory). EXTENDED relaxes this on
    ``GROUP`` / ``INFORMATION`` lines — the relaxation is enforced
    at runtime by ``br_fxext_26`` (rules/extended.py), and the
    EN16931 ``BR-26`` short-circuits at EXTENDED via the same
    machinery used for the rest of the BR-FXEXT-2x family.
    """
    item_seller: ItemSellerTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Line-level deviating seller (BG-X-90); EXTENDED-only.

    The seller-of-record for this line when it differs from the
    header Seller (marketplace / drop-ship)."""


@dataclass(kw_only=True, slots=True)
class LineTradeDelivery(Element):
    """Line trade delivery (BT-129-00).

    Carries the invoiced quantity for the line.
    """

    tag: ClassVar[str] = "SpecifiedLineTradeDelivery"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["LineTradeDelivery"], ...]] = (
        fields_only_at(
            Profile.EXTENDED,
            "charge_free_quantity",
            "package_quantity",
            "per_package_unit_quantity",
            "ship_to",
            "ultimate_ship_to",
        ),
    )

    billed_quantity: Quantity | None = field(
        default=None, metadata={"tag": "BilledQuantity"}
    )
    """Invoiced quantity (BT-129) with unit-of-measure code (BT-130).

    Required at every profile up to EN 16931 (``BR-22`` / ``BR-23``).
    EXTENDED relaxes both on ``GROUP`` / ``INFORMATION`` lines —
    runtime enforcement lives in ``br_fxext_22`` / ``br_fxext_23``.
    """
    charge_free_quantity: ChargeFreeQuantity | None = None
    """Free-goods quantity (BT-X-46); EXTENDED-only."""
    package_quantity: PackageQuantity | None = None
    """Number of packages (BT-X-47); EXTENDED-only."""
    per_package_unit_quantity: PerPackageUnitQuantity | None = None
    """Units per package (BT-X-561); EXTENDED-only."""
    ship_to: ShipToTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Line-level ship-to party (BG-X-7); EXTENDED-only — overrides
    the header ship-to for this line."""
    ultimate_ship_to: UltimateShipToTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Line-level ultimate ship-to party (BG-X-10); EXTENDED-only."""


@dataclass(kw_only=True, slots=True)
class LineMonetarySummation(Element):
    """Invoice line totals (BT-131-00).

    Detailed information about the line totals. Only
    ``LineTotalAmount`` (BT-131) is modelled at BASIC; EN 16931 does
    not add fields here.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementLineMonetarySummation"
    profile: ClassVar[Profile] = Profile.BASIC

    _validators: ClassVar[tuple[Validator["LineMonetarySummation"], ...]] = (
        max_decimals("BR-DEC-23", field_name="line_total"),
    )

    line_total: Decimal | None = field(
        default=None, metadata={"tag": "LineTotalAmount", "amount": True}
    )
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

    applicable_trade_tax: ApplicableTradeTax | None = None
    """Line VAT information (BG-30).

    Required at EN16931 (the EN16931 base requirement BR-21 / BR-CO-4
    is implicit — a DETAIL line cannot omit the line VAT category).
    EXTENDED relaxes this: GROUP subtotal headers and INFORMATION
    lines may omit BG-30 entirely, because the per-VAT-category sums
    (``BR-FXEXT-{cat}-08`` in §5.3) fold them by their child lines'
    own categorisation rather than the GROUP's. Hence the field
    becomes ``Optional`` overall; the runtime constraint is
    enforced by ``BR-FXEXT-CO-04`` (``rules/extended.py``) at
    EXTENDED.

    Note: only ``TypeCode``, ``CategoryCode`` and the optional rate
    are populated at line level — the calculated and basis amounts
    live on the header-level breakdown (BG-23).
    """
    billing_period: BillingSpecifiedPeriod | None = None
    """Invoice line period (BG-26) — also known as the line delivery
    period."""
    allowance_charge: list[LineTradeAllowanceCharge] | None = None
    """Invoice line allowances (BG-27) and charges (BG-28).

    Note: same dataclass for both, distinguished by ``ChargeIndicator``.
    All charges and taxes are assumed to be liable to the same VAT
    rate as the invoice line.
    """
    monetary_summation: LineMonetarySummation
    """Invoice line totals (BT-131-00); required."""
    additional_references: list[LineAdditionalReferencedDocument] | None = None
    """Invoice line object identifier(s) (BT-128-00, 0..*); COMFORT+."""
    accounting_account: ReceivableAccountingAccount | None = field(
        default=None, metadata={"profile": Profile.COMFORT}
    )
    """Line-level Buyer accounting reference (BT-133-00); COMFORT+.

    Reuses the header :class:`~carthorse.schema.settlement.ReceivableAccountingAccount`
    class; the field-level profile override pins line-level rendering
    to COMFORT (BT-133) instead of the class's native BASIC_WL (BT-19).
    """
