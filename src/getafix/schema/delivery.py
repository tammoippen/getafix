"""Header trade delivery (BG-13-00) — ship-to, dispatch and receipt.

``ApplicableHeaderTradeDelivery`` is the second sibling of the
``SupplyChainTradeTransaction``. It carries the where-and-when of the
goods or services covered by the invoice:

* the consignment / transport mode (BG-X-24, EXTENDED only);
* ship-to (BG-13, BASIC_WL+), ultimate-ship-to (BG-X-27, EXTENDED) and
  ship-from (BG-X-30, EXTENDED) parties — defined in :mod:`party`;
* the actual delivery date (BT-72) wrapped in a ``SupplyChainEvent``;
* the despatch advice (BT-16-00, BASIC_WL+) and receiving advice
  (BT-15-00, COMFORT+) references, plus the EXTENDED-only delivery
  note reference — defined in :mod:`references`.

No business rules are enforced in this module. ``BT-72`` participates
in ``BR-IC-11`` (intra-community supply must carry a delivery date or
an invoicing period) which lives in :mod:`trade`. The XSD
``<xs:sequence>`` of ``HeaderTradeDeliveryType`` dictates the field
order.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar

from getafix.schema.element import Element
from getafix.schema.party import (
    ShipFromTradeParty,
    ShipToTradeParty,
    UltimateShipToTradeParty,
)
from getafix.schema.references import (
    DeliveryNoteReferencedDocument,
    DespatchAdviceReferencedDocument,
    ReceivingAdviceReferencedDocument,
)
from getafix.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class LogisticsTransportMovement(Element):
    """Specified Logistics Transport Movement (BT-X-152-00).

    Transport-movement sub-block of the related supply-chain
    consignment; EXTENDED-only.
    """

    tag: ClassVar[str] = "SpecifiedLogisticsTransportMovement"
    profile: ClassVar[Profile] = Profile.EXTENDED

    mode: str | None = field(default=None, metadata={"tag": "ModeCode"})
    """Delivery method, code (BT-X-152).

    Code list: UN/CEFACT Recommendation 19 / UNTDID 8067 transport
    mode codes.
    """


@dataclass(kw_only=True, slots=True)
class SupplyChainConsignment(Element):
    """Related SupplyChain Consignment (BG-X-24).

    A consignment, at header level, related to this trade delivery.
    EXTENDED-only.
    """

    tag: ClassVar[str] = "RelatedSupplyChainConsignment"
    profile: ClassVar[Profile] = Profile.EXTENDED

    movement: list[LogisticsTransportMovement] | None = None
    """Logistics transport movements attached to the consignment (BT-X-152-00)."""


@dataclass(kw_only=True, slots=True)
class SupplyChainEvent(Element):
    """Actual delivery (BT-72-000).

    Detailed information about the actual delivery event.
    """

    tag: ClassVar[str] = "ActualDeliverySupplyChainEvent"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    occurrence: date | None = field(
        default=None,
        metadata={"tag": "OccurrenceDateTime", "profile": Profile.BASIC_WL},
    )
    """Actual delivery date (BT-72).

    The date on which the supply of goods or services was made or
    completed.

    Note: In Germany, the date of delivery and performance is a
    mandatory information on invoices. It may additionally be
    indicated at line level, but must in any case be present here. An
    exception is prepayment invoices (``ExchangedDocument/TypeCode =
    386``), where the delivery or performance date is not yet known
    at the time of invoicing.
    """


@dataclass(kw_only=True, slots=True)
class TradeDelivery(Element):
    """Header trade delivery (BG-13-00).

    A group of business terms providing information about where and
    when the goods and services invoiced are delivered.
    """

    tag: ClassVar[str] = "ApplicableHeaderTradeDelivery"

    consignment: SupplyChainConsignment | None = None
    """Related supply-chain consignment (BG-X-24); EXTENDED-only."""
    ship_to: ShipToTradeParty | None = None
    """Deliver-to party / ship-to details (BG-13); BASIC_WL+."""
    ultimate_ship_to: UltimateShipToTradeParty | None = None
    """Ultimate ship-to party (BG-X-27); EXTENDED-only."""
    ship_from: ShipFromTradeParty | None = None
    """Ship-from party (BG-X-30); EXTENDED-only."""
    event: SupplyChainEvent | None = None
    """Actual delivery event (BT-72-000) carrying BT-72; BASIC_WL+."""
    despatch_advice: DespatchAdviceReferencedDocument | None = None
    """Despatch advice reference (BT-16-00); BASIC_WL+."""
    receiving_advice: ReceivingAdviceReferencedDocument | None = None
    """Receiving advice reference (BT-15-00); COMFORT+."""
    delivery_note: DeliveryNoteReferencedDocument | None = None
    """Delivery note reference (BT-X-202-00); EXTENDED-only."""
