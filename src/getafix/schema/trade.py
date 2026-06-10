"""Supply chain trade transaction (BG-25-00) and BG-25 line items.

:class:`Trade` is the second sibling of :class:`Document` and
stitches together the three header groups
(:class:`~getafix.schema.agreement.TradeAgreement` (BT-10-00),
:class:`~getafix.schema.delivery.TradeDelivery` (BG-13-00),
:class:`~getafix.schema.settlement.TradeSettlement` (BG-19)) with a
list of :class:`TradeLineItem` (BG-25, BASIC+). The line sub-tree
content lives in :mod:`getafix.schema.line`.

This module is also where every *cross-sibling* validator wires in —
rules that need to read across line items, header allowances/charges
and the monetary summation in one pass. The validator functions
themselves live in :mod:`getafix.rules.trade`.
"""

from dataclasses import dataclass, field
from typing import ClassVar

from getafix.rules import Validator
from getafix.rules.extended import (
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
from getafix.rules.trade import (
    br_16,
    br_22,
    br_23,
    br_24,
    br_26,
    br_ae_2,
    br_ae_3,
    br_ae_4,
    br_af_2,
    br_af_3,
    br_af_4,
    br_ag_2,
    br_ag_3,
    br_ag_4,
    br_co_4,
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
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.element import Element
from getafix.schema.line import (
    DocumentLineDocument,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    TradeProduct,
)
from getafix.schema.settlement import TradeSettlement
from getafix.schema.types import Namespace, Profile


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
        # EN 16931 per-line "field shall be present" rules — short-
        # circuit at EXTENDED; the matching BR-FXEXT-2x in
        # rules/extended.py applies the DETAIL / unset filter there.
        br_22,
        br_23,
        br_24,
        br_26,
        br_co_4,
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
        # Replace the EN 16931 BR-22..27 / BR-CO-4 with DETAIL-or-unset
        # filters so GROUP / INFORMATION lines may legitimately omit
        # BT-129 / BT-130 / BT-131 / BT-146 / BT-151. The corresponding
        # ``br_*`` in :mod:`getafix.rules.trade` short-circuit at
        # EXTENDED so only these fire.
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
