"""Header trade agreement (BT-10-00) — parties and upstream references.

``ApplicableHeaderTradeAgreement`` is the first sibling of the
``SupplyChainTradeTransaction``. It carries the *who* and *why* of
the invoice: the trading parties (defined in :mod:`party`) and every
upstream reference document that frames the transaction (defined in
:mod:`references`).

Per-profile contents:

* MINIMUM: ``BuyerReference`` (BT-10), ``SellerTradeParty`` (BG-4),
  ``BuyerTradeParty`` (BG-7), ``BuyerOrderReferencedDocument``
  (BT-13-00).
* BASIC_WL: adds ``SellerTaxRepresentativeTradeParty`` (BG-11) and
  ``ContractReferencedDocument`` (BT-12-00).
* COMFORT: adds ``SellerOrderReferencedDocument`` (BT-14-00),
  ``AdditionalReferencedDocument`` 0..* (BG-24), and
  ``SpecifiedProcuringProject`` (BT-11-00).
* EXTENDED: adds ``SalesAgentTradeParty`` (BG-X-49),
  ``BuyerTaxRepresentativeTradeParty`` (BG-X-54),
  ``ProductEndUserTradeParty`` (BG-X-18),
  ``ApplicableTradeDeliveryTerms`` (BG-X-22),
  ``QuotationReferencedDocument`` (BG-X-61),
  ``BuyerAgentTradeParty`` (BG-X-62), and
  ``UltimateCustomerOrderReferencedDocument`` (BG-X-23).

No business rules are enforced in this module. ``BR-6`` (Seller name
required) and ``BR-7`` (Buyer name required) are implicit through the
required ``seller`` / ``buyer`` fields. Field order follows the XSD
``HeaderTradeAgreementType`` ``<xs:sequence>``; see
``docs/STRUCTURES.md §3.4``.
"""

from dataclasses import dataclass, field
from typing import ClassVar

from getafix.schema.element import Element
from getafix.schema.party import (
    BuyerAgentTradeParty,
    BuyerTaxRepresentativeTradeParty,
    BuyerTradeParty,
    ProductEndUserTradeParty,
    SalesAgentTradeParty,
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
)
from getafix.schema.references import (
    AdditionalReferencedDocument,
    BuyerOrderReferencedDocument,
    ContractReferencedDocument,
    ProcuringProject,
    QuotationReferencedDocument,
    SellerOrderReferencedDocument,
    UltimateCustomerOrderReferencedDocument,
)
from getafix.schema.types import Country, Incoterms, Profile


@dataclass(kw_only=True, slots=True)
class RelevantTradeLocation(Element):
    """Relevant trade location for delivery terms (BG-X-88); EXTENDED-only.

    The named place referenced by the Incoterm — e.g. the port /
    terminal for ``FCA`` / ``CIP``. Both children are optional.
    """

    tag: ClassVar[str] = "RelevantTradeLocation"
    profile: ClassVar[Profile] = Profile.EXTENDED

    country_id: Country | None = field(default=None, metadata={"tag": "CountryID"})
    """Location country code (BT-X-563)."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Location name (BT-X-564) — e.g. ``"Hamburg Hafen"``."""


@dataclass(kw_only=True, slots=True)
class TradeDeliveryTerms(Element):
    """Delivery / trade terms (BG-X-22); EXTENDED-only.

    Header-level Incoterms statement. The ``delivery_type_code``
    (BT-X-145) is required when the group is present.
    """

    tag: ClassVar[str] = "ApplicableTradeDeliveryTerms"
    profile: ClassVar[Profile] = Profile.EXTENDED

    delivery_type_code: Incoterms = field(metadata={"tag": "DeliveryTypeCode"})
    """Delivery condition code (BT-X-145).

    The XSD type ``qdt:DeliveryTermsCodeType`` is an unrestricted
    token; the EXTENDED schematron validates it against
    :class:`~getafix.schema.types.Incoterms` (the 11 Incoterms
    2020 codes).
    """
    relevant_location: RelevantTradeLocation | None = None
    """Named place the Incoterm applies to (BG-X-88, 0..1)."""


@dataclass(kw_only=True, slots=True)
class TradeAgreement(Element):
    """Header trade agreement (BT-10-00).

    Container for the process and contract details of the invoice:
    trading parties plus every upstream document reference. The
    EXTENDED additions are the agent parties
    (:class:`SalesAgentTradeParty` BG-X-49,
    :class:`BuyerTaxRepresentativeTradeParty` BG-X-54,
    :class:`BuyerAgentTradeParty` BG-X-62), the header
    :class:`~getafix.schema.references.QuotationReferencedDocument`
    (BG-X-61) and :class:`TradeDeliveryTerms` (BG-X-22).
    """

    tag: ClassVar[str] = "ApplicableHeaderTradeAgreement"

    buyer_reference: str | None = field(
        default=None, metadata={"tag": "BuyerReference"}
    )
    """Buyer reference (BT-10).

    An identifier assigned by the Buyer used for internal routing
    purposes.

    Note: the identifier is defined by the Buyer (e.g. contact id,
    department, office id, project code) but provided by the Seller
    in the invoice.
    """
    seller: SellerTradeParty
    """Seller (BG-4) — supplier of the goods or services."""
    buyer: BuyerTradeParty
    """Buyer (BG-7) — recipient of the goods or services."""
    sales_agent: SalesAgentTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Sales agent party (BG-X-49); EXTENDED-only."""
    buyer_tax_representative: BuyerTaxRepresentativeTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Buyer tax representative party (BG-X-54); EXTENDED-only."""
    seller_tax_representative_party: SellerTaxRepresentativeTradeParty | None = None
    """Seller tax representative party (BG-11); BASIC_WL+."""
    end_user: ProductEndUserTradeParty | None = None
    """Product end user party (BG-X-18); EXTENDED-only.

    The party acting as the end user for the products in this header
    trade agreement.
    """
    delivery_terms: TradeDeliveryTerms | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Delivery / trade terms (BG-X-22); EXTENDED-only."""
    seller_order: SellerOrderReferencedDocument | None = None
    """Sales order reference (BT-14-00); COMFORT+."""
    buyer_order: BuyerOrderReferencedDocument | None = None
    """Purchase order reference (BT-13-00); MINIMUM+."""
    quotation: QuotationReferencedDocument | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Header quotation reference (BG-X-61); EXTENDED-only."""
    contract: ContractReferencedDocument | None = None
    """Contract reference (BT-12-00); BASIC_WL+."""
    additional_references: list[AdditionalReferencedDocument] | None = None
    """Additional supporting documents (BG-24, 0..*); COMFORT+."""
    buyer_agent: BuyerAgentTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Buyer agent party (BG-X-62); EXTENDED-only."""
    procuring_project: ProcuringProject | None = None
    """Project reference (BT-11-00); COMFORT+."""
    customer_order: UltimateCustomerOrderReferencedDocument | None = None
    """Ultimate customer order reference (BG-X-23); EXTENDED-only."""
