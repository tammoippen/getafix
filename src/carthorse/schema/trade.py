"""Supply chain trade transaction (BG-25-00) and BG-25 line items.

:class:`Trade` is the second sibling of :class:`Document` and
stitches together the three header groups
(:class:`~carthorse.schema.agreement.TradeAgreement` (BT-10-00),
:class:`~carthorse.schema.delivery.TradeDelivery` (BG-13-00),
:class:`~carthorse.schema.settlement.TradeSettlement` (BG-19)) with a
list of :class:`TradeLineItem` (BG-25, BASIC+). The line sub-tree
content lives in :mod:`carthorse.schema.line`.

This module is also where every *cross-sibling* validator wires in —
rules that need to read across line items, header allowances/charges
and the monetary summation in one pass. The validator functions
themselves live in :mod:`carthorse.rules.trade`.

Validation rules enforced here:

* ✓ ``BR-16`` — at BASIC+ an invoice must contain at least one line
  item.
* ✓ ``BR-CO-10`` — ``BT-106 = sum(BT-131)`` across line totals.
* ✓ ``BR-CO-11`` — ``BT-107 = sum(BT-92)`` across header allowances.
* ✓ ``BR-CO-12`` — ``BT-108 = sum(BT-99)`` across header charges.
* ✓ ``BR-CO-13`` — ``BT-109 = sum(BT-131) - sum(BT-92) + sum(BT-99)``.
* ✓ ``BR-CO-21`` / ``BR-CO-22`` — header allowance / charge needs
  reason text or reason code.
* ✓ ``BR-CO-23`` / ``BR-CO-24`` — same coupling at line level.
* ✓ ``BR-AE/E/G/IC/IG/IP/S/Z-{2,3,4}`` — per-VAT-category
  required-party matrix (see ``docs/VALIDATION.md §3.2``).
* ✓ ``BR-O-2 / BR-O-3 / BR-O-4`` — "Not subject to VAT" forbidden-id
  matrix (inverted predicate of the above).
* ✓ ``BR-IC-11`` / ``BR-IC-12`` — intra-community supply needs
  delivery date or period (BT-72 / BG-14) and a deliver-to country
  code (BT-80).
* ✓ ``BR-O-11..14`` — "Not subject to VAT" is single-rate.

See ``docs/VALIDATION.md`` for the full BR-* catalogue.
"""

from dataclasses import dataclass, field
from typing import ClassVar

from carthorse.rules import Validator
from carthorse.rules.trade import (
    br_16,
    br_ae_2,
    br_ae_3,
    br_ae_4,
    br_co_10,
    br_co_11,
    br_co_12,
    br_co_13,
    br_co_21,
    br_co_22,
    br_co_23,
    br_co_24,
    br_e_2,
    br_e_3,
    br_e_4,
    br_g_2,
    br_g_3,
    br_g_4,
    br_ic_2,
    br_ic_3,
    br_ic_4,
    br_ic_11,
    br_ic_12,
    br_af_2,
    br_af_3,
    br_af_4,
    br_ag_2,
    br_ag_3,
    br_ag_4,
    br_o_2,
    br_o_3,
    br_o_4,
    br_o_11,
    br_o_12,
    br_o_13,
    br_o_14,
    br_s_2,
    br_s_3,
    br_s_4,
    br_z_2,
    br_z_3,
    br_z_4,
    vat_category_exemption_reason,
    vat_category_rates,
)
from carthorse.rules.extended import (
    br_fxext_06,
    br_fxext_08,
    br_fxext_11,
    br_fxext_22,
    br_fxext_23,
    br_fxext_24,
    br_fxext_26,
    br_fxext_27,
    br_fxext_co_04,
    br_fxext_co_10,
    br_fxext_co_11,
    br_fxext_co_12,
    br_fxext_co_13,
    br_fxext_co_15,
    br_fxext_vat_category_sums,
)
from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import Element
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
    """Invoice line (BG-25).

    A group of business terms providing information on an individual
    invoice line. Required from BASIC upwards.
    """

    tag: ClassVar[str] = "IncludedSupplyChainTradeLineItem"
    profile: ClassVar[Profile] = Profile.BASIC

    associated_document: DocumentLineDocument
    """Associated line document (BT-126-00) — line id and optional note."""
    product: TradeProduct
    """Item information (BG-31) — what is being invoiced."""
    agreement: LineTradeAgreement
    """Line trade agreement (BG-29) — gross and net price."""
    delivery: LineTradeDelivery
    """Line trade delivery (BT-129-00) — invoiced quantity."""
    settlement: LineTradeSettlement
    """Line trade settlement (BG-30-00) — line VAT, period,
    allowances/charges, line total."""


@dataclass(kw_only=True, slots=True)
class Trade(Element):
    """Supply chain trade transaction (BG-25-00).

    The header business-transaction wrapper. Holds the three sibling
    header groups (agreement, delivery, settlement) plus the list of
    line items, and is where every cross-sibling validator runs (see
    module docstring for the BR-* catalogue).
    """

    tag: ClassVar[str] = "SupplyChainTradeTransaction"
    namespace: ClassVar[Namespace] = Namespace.rsm

    _validators: ClassVar[tuple[Validator["Trade"], ...]] = (
        br_16,
        # Per-VAT-category required-party matrix (BR-AE/E/G/IC/IG/IP/S/Z-2,3,4).
        br_ae_2,
        br_ae_3,
        br_ae_4,
        br_e_2,
        br_e_3,
        br_e_4,
        br_g_2,
        br_g_3,
        br_g_4,
        br_ic_2,
        br_ic_3,
        br_ic_4,
        br_af_2,
        br_af_3,
        br_af_4,
        br_ag_2,
        br_ag_3,
        br_ag_4,
        br_s_2,
        br_s_3,
        br_s_4,
        br_z_2,
        br_z_3,
        br_z_4,
        # 'Not subject to VAT' forbidden-id matrix (inverted predicate).
        br_o_2,
        br_o_3,
        br_o_4,
        # Intra-community supplementary rules.
        br_ic_11,
        br_ic_12,
        # 'Not subject to VAT' single-rate restriction.
        br_o_11,
        br_o_12,
        br_o_13,
        br_o_14,
        # Document-level arithmetic and reason coupling.
        br_co_10,
        br_co_21,
        br_co_22,
        br_co_23,
        br_co_24,
        br_co_11,
        br_co_12,
        br_co_13,
        # Per-VAT-category rate constraints (BR-{cat}-5/6/7) and
        # exemption-reason constraints (BR-{cat}-10).
        vat_category_rates,
        vat_category_exemption_reason,
        # EXTENDED CIUS — tolerance-banded BR-CO-* replacements and
        # per-VAT-category sum identities (§5.2 / §5.3 of EXTENDED.md).
        # Each guards with `if profile < Profile.EXTENDED: return []`
        # so it stays silent below; the matching EN 16931 br_co_*
        # functions guard with the inverse.
        br_fxext_co_04,
        br_fxext_co_10,
        br_fxext_co_11,
        br_fxext_co_12,
        br_fxext_co_13,
        br_fxext_co_15,
        br_fxext_vat_category_sums,
        # EXTENDED CIUS — sub-invoice-line cross-line walker
        # (§5.1 of EXTENDED.md). BR-FXEXT-12 is implicitly enforced
        # by LineMonetarySummation.line_total being non-optional.
        br_fxext_06,
        br_fxext_08,
        br_fxext_11,
        # EXTENDED CIUS — subtype-qualified line rules (§5.4).
        # All five are no-op placeholders: the BT-* fields they gate
        # are non-optional on carthorse dataclasses, so the EN 16931
        # base requirements always hold and these never have anything
        # to fire on. They become meaningful runtime checks if/when
        # those fields are ever relaxed to Optional for GROUP /
        # INFORMATION lines.
        br_fxext_22,
        br_fxext_23,
        br_fxext_24,
        br_fxext_26,
        br_fxext_27,
    )

    items: list[TradeLineItem] = field(default_factory=list)
    """Invoice lines (BG-25, 0..*); required at BASIC+ (``BR-16``)."""
    agreement: TradeAgreement
    """Header trade agreement (BT-10-00) — parties and references."""
    delivery: TradeDelivery
    """Header trade delivery (BG-13-00) — ship-to and dispatch."""
    settlement: TradeSettlement
    """Header trade settlement (BG-19) — currency, payment, totals."""
