"""Public re-exports for the carthorse Cross-Industry-Invoice schema.

The module tree mirrors the EN 16931 / Factur-X 1.08 / ZUGFeRD 2.4
business term groupings:

* :mod:`carthorse.schema.document` — ``CrossIndustryInvoice`` (BG-0),
  ``ExchangedDocumentContext`` (BG-2), ``ExchangedDocument`` (BT-1-00)
  and document-level metadata (BG-1 notes, EXTENDED test indicator,
  effective period).
* :mod:`carthorse.schema.party` — every ``*TradeParty`` (Seller,
  Buyer, Payee, Tax representative, Ship-to/from, Ultimate ship-to,
  Product end-user) plus their address, contact, identification and
  electronic-address sub-elements.
* :mod:`carthorse.schema.agreement` — ``ApplicableHeaderTradeAgreement``
  (BT-10-00) wiring the seller, buyer and the various referenced
  documents (orders, contracts, projects, additional supporting docs).
* :mod:`carthorse.schema.delivery` — ``ApplicableHeaderTradeDelivery``
  (BG-13-00) with ship-to party, actual delivery event, and
  despatch/receiving advice references.
* :mod:`carthorse.schema.settlement` — ``ApplicableHeaderTradeSettlement``
  (BG-19) covering currency, payee, payment means / terms, allowance /
  charge, payment references, accounting account.
* :mod:`carthorse.schema.accounting` — ``MonetarySummation`` (BG-22),
  ``ApplicableTradeTax`` (BG-23 / BG-30), ``CategoryTradeTax``,
  ``TaxTotal``, ``TradeAllowanceCharge`` (BG-20 / BG-21).
* :mod:`carthorse.schema.references` — every ``*ReferencedDocument`` and
  ``ProcuringProject``; ``AttachmentBinaryObject`` is the BT-125 binary
  payload.
* :mod:`carthorse.schema.trade` — ``SupplyChainTradeTransaction``
  (BG-25-00) wrapper plus ``TradeLineItem`` (BG-25). The line-item
  sub-tree (BG-29 agreement, BG-30 settlement, BG-31 product, …)
  lives in :mod:`carthorse.schema.line`.
* :mod:`carthorse.schema.element` — base :class:`Element`, generic XML
  render/parse, and the ``ProfileMismatch`` / ``ValidationError``
  exceptions.
* :mod:`carthorse.schema.types` — enums (``Profile``, ``Namespace``,
  ``TypeCode``, ``CategoryCode``, ``MIME``, UNTDID 1001).

For an overview of which structures are still missing per profile see
``docs/STRUCTURES.md`` and ``docs/IMPLEMENTATION_PLAN.md``. For the
cross-field business rules the model is meant to enforce see
``docs/VALIDATION.md``.
"""

from carthorse.schema.document import BusinessDocument as BusinessDocument
from carthorse.schema.document import Context as Context
from carthorse.schema.document import Document as Document
from carthorse.schema.document import EffectivePeriod as EffectivePeriod
from carthorse.schema.document import GuidelineDocument as GuidelineDocument
from carthorse.schema.document import Header as Header
from carthorse.schema.document import IncludedNote as IncludedNote
from carthorse.schema.trade import Trade as Trade
from carthorse.schema.types import Namespace as Namespace
from carthorse.schema.types import Profile as Profile
from carthorse.schema.types import TypeCode as TypeCode
