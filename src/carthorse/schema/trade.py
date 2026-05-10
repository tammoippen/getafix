"""Top-level ``SupplyChainTradeTransaction`` (BG-25-00).

This module is intentionally tiny: it stitches together the three
sibling header groups (`agreement`, `delivery`, `settlement`) and a
list of line items (`items`).

The line item element ``IncludedSupplyChainTradeLineItem`` (BG-25) is
currently a stub. The full BASIC shape — ``AssociatedDocumentLineDocument``,
``SpecifiedTradeProduct`` (BG-31), ``SpecifiedLineTradeAgreement`` (BG-29),
``SpecifiedLineTradeDelivery`` and ``SpecifiedLineTradeSettlement``
(BG-30) — is described in ``docs/IMPLEMENTATION_PLAN.md §2.BASIC``. EN
16931 enriches BG-25 with product characteristics (BG-32),
classification (BG-33), origin country (BG-34), and per-line
references; EXTENDED adds sub-line hierarchy via BT-X-304 / BT-X-8
plus included referenced products (BG-X-1).

Validation rule covered here:

* ✓ ``BR-16`` — at BASIC and above an invoice must contain at least
  one line item. Raised by :meth:`Trade.validate_internal`.

(The comparator bug noted in ``schema/types.py`` means the cutoff is
currently ``> BASIC_WL`` rather than ``>= BASIC``; same effective
result.)
"""

from dataclasses import dataclass, field
from typing import ClassVar, override

from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class TradeLineItem(Element):
    """Rechnungsposition / invoice line item.

    Stub. The complete BG-25 sub-tree (BG-29 line agreement, BG-30 line
    settlement, BG-31 product, line delivery / quantity, line totals)
    is documented in ``docs/IMPLEMENTATION_PLAN.md §2.BASIC`` but not
    yet modelled.

    EN 16931-ID: BG-25
    """

    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC


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
