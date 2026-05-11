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
    """Header trade agreement (process and contract details)."""

    tag: ClassVar[str] = "ApplicableHeaderTradeAgreement"

    seller: SellerTradeParty
    """Seller details (supplier of the goods or services).

    EN 16931-ID: BG-4
    """
    buyer: BuyerTradeParty
    """Buyer details (recipient of the goods or services).

    EN 16931-ID: BG-7
    """
    buyer_reference: str | None = field(
        default=None, metadata={"tag": "BuyerReference"}
    )
    """Buyer reference.

    An identifier assigned by the Buyer and used for internal routing
    purposes.

    Note: The reference is set by the Buyer (e.g. contact data,
    department, office identifier, project code) but is stated in the
    Invoice by the Seller.

    EN 16931-ID: BT-10
    """
    seller_tax_representative_party: SellerTaxRepresentativeTradeParty | None = None
    """Seller tax representative party.

    EN 16931-ID: BG-11
    """
    end_user: ProductEndUserTradeParty | None = None
    seller_order: SellerOrderReferencedDocument | None = None
    buyer_order: BuyerOrderReferencedDocument | None = None
    contract: ContractReferencedDocument | None = None
    additional_references: list[AdditionalReferencedDocument] | None = None
    procuring_project: ProcuringProject | None = None
    customer_order: UltimateCustomerOrderReferencedDocument | None = None
