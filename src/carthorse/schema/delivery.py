from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar

from carthorse.schema.element import Element
from carthorse.schema.party import ShipToTradeParty
from carthorse.schema.references import DespatchAdviceReferencedDocument
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class SupplyChainEvent(Element):
    """Detailinformationen zur tatsächlichen Lieferung"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ActualDeliverySupplyChainEvent"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    occurrence: date | None = field(
        default=None,
        metadata={
            "tag": "OccurrenceDateTime",
            "ns": Namespace.ram,
            "profile": Profile.BASIC_WL,
        },
    )
    """Tatsächlicher Lieferungszeitpunkt / Liefer- und Leistungsdatum im umsatzsteuerrechtlichen Sinn

    Angabe entweder hier für die gesamte Rechnung oder alternativ je Position

    In Deutschland muss grundsätzlich der Liefer- und Leistungstermin in
    Rechnungen angegeben werden. Eine Ausnahme bilden Vorauszahlungsrechnungen
    (ExchangedDocument\\TypeCode = 386), bei denen zum Zeitpunkt der
    Rechnungsstellung das Liefer- oder Leistungsdatum noch nicht fest steht.    

    EN 16931-ID: BT-72
    """


@dataclass(kw_only=True, slots=True)
class TradeDelivery(Element):
    """Gruppierung von Lieferangaben"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ApplicableHeaderTradeDelivery"

    ship_to: ShipToTradeParty | None = None
    event: SupplyChainEvent | None = None
    despatch_advice: DespatchAdviceReferencedDocument | None = None
