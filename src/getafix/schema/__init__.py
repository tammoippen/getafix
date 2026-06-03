"""Public re-exports for the getafix Cross-Industry-Invoice schema.

The module tree mirrors the EN 16931 / Factur-X 1.08 / ZUGFeRD 2.4
business term groupings:

* :mod:`getafix.schema.document` — ``CrossIndustryInvoice`` (BG-0),
  ``ExchangedDocumentContext`` (BG-2), ``ExchangedDocument`` (BT-1-00)
  and document-level metadata (BG-1 notes, EXTENDED test indicator,
  effective period).
* :mod:`getafix.schema.party` — every ``*TradeParty`` (Seller,
  Buyer, Payee, Tax representative, Ship-to/from, Ultimate ship-to,
  Product end-user) plus their address, contact, identification and
  electronic-address sub-elements.
* :mod:`getafix.schema.agreement` — ``ApplicableHeaderTradeAgreement``
  (BT-10-00) wiring the seller, buyer and the various referenced
  documents (orders, contracts, projects, additional supporting docs).
* :mod:`getafix.schema.delivery` — ``ApplicableHeaderTradeDelivery``
  (BG-13-00) with ship-to party, actual delivery event, and
  despatch/receiving advice references.
* :mod:`getafix.schema.settlement` — ``ApplicableHeaderTradeSettlement``
  (BG-19) covering currency, payee, payment means / terms, allowance /
  charge, payment references, accounting account.
* :mod:`getafix.schema.accounting` — ``MonetarySummation`` (BG-22),
  ``ApplicableTradeTax`` (BG-23 / BG-30), ``CategoryTradeTax``,
  ``TaxTotal``, ``TradeAllowanceCharge`` (BG-20 / BG-21).
* :mod:`getafix.schema.references` — every ``*ReferencedDocument`` and
  ``ProcuringProject``; ``AttachmentBinaryObject`` is the BT-125 binary
  payload.
* :mod:`getafix.schema.trade` — ``SupplyChainTradeTransaction``
  (BG-25-00) wrapper plus ``TradeLineItem`` (BG-25). The line-item
  sub-tree (BG-29 agreement, BG-30 settlement, BG-31 product, …)
  lives in :mod:`getafix.schema.line`.
* :mod:`getafix.schema.element` — base :class:`Element`, generic XML
  render/parse, and the ``ProfileMismatch`` / ``ValidationError``
  exceptions.
* :mod:`getafix.schema.types` — enums (``Profile``, ``Namespace``,
  ``TypeCode``, ``CategoryCode``, ``MIME``, UNTDID 1001).

For the module → BG/BT field map and the EXTENDED coverage diff see
``docs/STRUCTURES.md``. For the cross-field business rules the model
is meant to enforce see ``docs/VALIDATION.md``.
"""

from getafix.schema.document import BusinessDocument as BusinessDocument
from getafix.schema.document import Context as Context
from getafix.schema.document import Document as Document
from getafix.schema.document import EffectivePeriod as EffectivePeriod
from getafix.schema.document import GuidelineDocument as GuidelineDocument
from getafix.schema.document import Header as Header
from getafix.schema.document import IncludedNote as IncludedNote
from getafix.schema.trade import Trade as Trade
from getafix.schema.types import Namespace as Namespace
from getafix.schema.types import Profile as Profile
from getafix.schema.types import TypeCode as TypeCode
