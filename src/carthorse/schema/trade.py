from dataclasses import dataclass, field
from typing import ClassVar, override

from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class TradeLineItem(Element):
    """Rechnungsposition

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    einzelne Rechnungspositionen enthält

    EN 16931-ID: BG-25
    """

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC


@dataclass(kw_only=True, slots=True)
class TradeDelivery(Element):
    """Gruppierung von Lieferangaben"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ApplicableHeaderTradeDelivery"


@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    """Gruppierung von Angaben zur Zahlung und Rechnungsausgleich"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ApplicableHeaderTradeSettlement"


@dataclass(kw_only=True, slots=True)
class Trade(Element):
    """Gruppierung der Informationen zum Geschäftsvorfall"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "SupplyChainTradeTransaction"

    agreement: TradeAgreement
    delivery: TradeDelivery
    settlement: TradeSettlement
    items: list[TradeLineItem] = field(default_factory=list)

    @override
    def validate_internal(self, profile: Profile) -> None:
        if Profile.BASIC_WL < profile and len(self.items) == 0:
            raise ValidationError(
                "BR-16",
                "An invoice must contain at least one invoice line item (BG-25).",
            )
        return super(Trade, self).validate_internal(profile)
