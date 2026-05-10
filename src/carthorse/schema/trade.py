"""Top-level ``SupplyChainTradeTransaction`` (BG-25-00) and BG-25 line items.

This module stitches together the three sibling header groups
(``agreement``, ``delivery``, ``settlement``) and a list of line items
(``items``). The line item content lives in
:mod:`carthorse.schema.line`.

Validation rule covered here:

* ✓ ``BR-16`` — at BASIC and above an invoice must contain at least
  one line item. Raised by :meth:`Trade.validate_internal`.
"""

from dataclasses import dataclass, field
from typing import ClassVar, override

from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.line import (
    DocumentLineDocument,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    TradeProduct,
)
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class TradeLineItem(Element):
    """Invoice line item (BG-25).

    Carries the four required line-level groups in XSD order:
    ``AssociatedDocumentLineDocument`` (BT-126-00),
    ``SpecifiedTradeProduct`` (BG-31),
    ``SpecifiedLineTradeAgreement`` (BG-29),
    ``SpecifiedLineTradeDelivery`` (BT-129-00) and
    ``SpecifiedLineTradeSettlement`` (BG-30-00).

    Required from the BASIC profile onwards.

    EN 16931-ID: BG-25
    """

    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC

    associated_document: DocumentLineDocument
    product: TradeProduct
    agreement: LineTradeAgreement
    delivery: LineTradeDelivery
    settlement: LineTradeSettlement


@dataclass(kw_only=True, slots=True)
class Trade(Element):
    """Gruppierung der Informationen zum Geschäftsvorfall"""

    tag: ClassVar[str] = "SupplyChainTradeTransaction"
    namespace: ClassVar[Namespace] = Namespace.rsm

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
