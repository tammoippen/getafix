from dataclasses import dataclass, field
from typing import ClassVar

from carthorse.schema.element import Element
from carthorse.schema.party import (
    BuyerTradeParty,
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
)
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class TradeAgreement(Element):
    """Gruppierung der Vertragsangaben"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ApplicableHeaderTradeAgreement"

    seller: SellerTradeParty
    """Detailinformationen zum Verkäufer (=Leistungserbringer)

    EN 16931-ID: BG-4
    """
    buyer: BuyerTradeParty
    """Detailinformationen zum Käufer (=Leistungsempfänger)

    EN 16931-ID: BG-7
    """
    buyer_reference: str | None = field(
        default=None,
        metadata={
            "tag": "BuyerReference",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        },
    )
    """Referenz des Käufers

    Eine vom Käufer zugewiesene und für internes Routing benutzte Kennung

    Hinweis: Die Referenz wird vom Käufer festgelegt (z. B. Kontaktdaten, Abteilung,
    Bürokennung, Projektcode), vom Verkäufer aber in der Rechnung angegeben.

    EN 16931-ID: BT-10
    """
    seller_tax_representative_party: SellerTaxRepresentativeTradeParty | None = None
    """Steuerbevollmächtigter des Verkäufers

    EN 16931-ID: BG-11
    """
