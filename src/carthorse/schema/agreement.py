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
* EXTENDED: adds ``ProductEndUserTradeParty`` (BG-X-18) and
  ``UltimateCustomerOrderReferencedDocument`` (BG-X-23).

No business rules are enforced in this module. ``BR-6`` (Seller name
required) and ``BR-7`` (Buyer name required) are implicit through the
required ``seller`` / ``buyer`` fields. Field order follows the XSD
``HeaderTradeAgreementType`` ``<xs:sequence>``; see
``docs/STRUCTURES.md §3.4``.
"""

from dataclasses import dataclass, field
from typing import ClassVar

from carthorse.schema.element import Element
from carthorse.schema.party import (
    BuyerTradeParty,
    ProductEndUserTradeParty,
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
)
from carthorse.schema.references import (
    AdditionalReferencedDocument,
    BuyerOrderReferencedDocument,
    ContractReferencedDocument,
    ProcuringProject,
    SellerOrderReferencedDocument,
    UltimateCustomerOrderReferencedDocument,
)


@dataclass(kw_only=True, slots=True)
class TradeAgreement(Element):
    """Header trade agreement (BT-10-00).

    Container for the process and contract details of the invoice:
    trading parties plus every upstream document reference.
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
    seller_tax_representative_party: SellerTaxRepresentativeTradeParty | None = None
    """Seller tax representative party (BG-11); BASIC_WL+."""
    end_user: ProductEndUserTradeParty | None = None
    """Product end user party (BG-X-18); EXTENDED-only.

    The party acting as the end user for the products in this header
    trade agreement.
    """
    seller_order: SellerOrderReferencedDocument | None = None
    """Sales order reference (BT-14-00); COMFORT+."""
    buyer_order: BuyerOrderReferencedDocument | None = None
    """Purchase order reference (BT-13-00); MINIMUM+."""
    contract: ContractReferencedDocument | None = None
    """Contract reference (BT-12-00); BASIC_WL+."""
    additional_references: list[AdditionalReferencedDocument] | None = None
    """Additional supporting documents (BG-24, 0..*); COMFORT+."""
    procuring_project: ProcuringProject | None = None
    """Project reference (BT-11-00); COMFORT+."""
    customer_order: UltimateCustomerOrderReferencedDocument | None = None
    """Ultimate customer order reference (BG-X-23); EXTENDED-only."""
