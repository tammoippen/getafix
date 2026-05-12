from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar

from carthorse.schema.element import Element
from carthorse.schema.party import (
    ShipFromTradeParty,
    ShipToTradeParty,
    UltimateShipToTradeParty,
)
from carthorse.schema.references import (
    DeliveryNoteReferencedDocument,
    DespatchAdviceReferencedDocument,
    ReceivingAdviceReferencedDocument,
)
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class LogisticsTransportMovement(Element):
    """Transport mode details."""

    tag: ClassVar[str] = "SpecifiedLogisticsTransportMovement"
    profile: ClassVar[Profile] = Profile.EXTENDED

    mode: str | None = field(default=None, metadata={"tag": "ModeCode"})
    """Transport mode (code)."""


@dataclass(kw_only=True, slots=True)
class SupplyChainConsignment(Element):
    """Consignment or shipment details."""

    tag: ClassVar[str] = "RelatedSupplyChainConsignment"
    profile: ClassVar[Profile] = Profile.EXTENDED

    movement: list[LogisticsTransportMovement] | None = None


@dataclass(kw_only=True, slots=True)
class SupplyChainEvent(Element):
    """Actual delivery event details."""

    tag: ClassVar[str] = "ActualDeliverySupplyChainEvent"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    occurrence: date | None = field(
        default=None,
        metadata={"tag": "OccurrenceDateTime", "profile": Profile.BASIC_WL},
    )
    """Actual delivery date / delivery or performance date for VAT purposes.

    Provided either here for the whole Invoice or alternatively per
    line.

    In Germany, the delivery and performance date must in principle
    always be stated on Invoices. An exception is prepayment Invoices
    (ExchangedDocument\\TypeCode = 386), where the delivery or
    performance date is not yet known at the time of invoicing.

    EN 16931-ID: BT-72
    """


@dataclass(kw_only=True, slots=True)
class TradeDelivery(Element):
    """Header trade delivery group.

    Field order follows the Factur-X ``HeaderTradeDeliveryType`` XSD
    ``<xs:sequence>``: ``RelatedSupplyChainConsignment`` (EXTENDED),
    ``ShipToTradeParty``, ``UltimateShipToTradeParty`` (EXTENDED),
    ``ShipFromTradeParty`` (EXTENDED), ``ActualDeliverySupplyChainEvent``,
    ``DespatchAdviceReferencedDocument``,
    ``ReceivingAdviceReferencedDocument``,
    ``DeliveryNoteReferencedDocument`` (EXTENDED).
    """

    tag: ClassVar[str] = "ApplicableHeaderTradeDelivery"

    consignment: SupplyChainConsignment | None = None
    ship_to: ShipToTradeParty | None = None
    ultimate_ship_to: UltimateShipToTradeParty | None = None
    ship_from: ShipFromTradeParty | None = None
    event: SupplyChainEvent | None = None
    despatch_advice: DespatchAdviceReferencedDocument | None = None
    receiving_advice: ReceivingAdviceReferencedDocument | None = None
    delivery_note: DeliveryNoteReferencedDocument | None = None
