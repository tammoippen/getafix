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
    """Header trade agreement (process and contract details). (BT-10-00)"""

    tag: ClassVar[str] = "ApplicableHeaderTradeAgreement"

    buyer_reference: str | None = field(
        default=None, metadata={"tag": "BuyerReference"}
    )
    """Buyer reference (BT-10).

    An identifier assigned by the Buyer and used for internal routing
    purposes.

    Note: The reference is set by the Buyer (e.g. contact data,
    department, office identifier, project code) but is stated in the
    Invoice by the Seller.
    """
    seller: SellerTradeParty
    """Seller details (supplier of the goods or services) (BG-4)."""
    buyer: BuyerTradeParty
    """Buyer details (recipient of the goods or services) (BG-7)."""
    seller_tax_representative_party: SellerTaxRepresentativeTradeParty | None = None
    """Seller tax representative party (BG-11)."""
    end_user: ProductEndUserTradeParty | None = None
    seller_order: SellerOrderReferencedDocument | None = None
    buyer_order: BuyerOrderReferencedDocument | None = None
    contract: ContractReferencedDocument | None = None
    additional_references: list[AdditionalReferencedDocument] | None = None
    procuring_project: ProcuringProject | None = None
    customer_order: UltimateCustomerOrderReferencedDocument | None = None
