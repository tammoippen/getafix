"""EXTENDED-only business rules (``BR-FXEXT-*``).

Implements the rules from §5.2 and §5.3 of
``docs/PROFILES/EXTENDED.md``:

* §5.2 — six ``BR-FXEXT-CO-*`` tolerance-banded variants of
  EN 16931 ``BR-CO-04/10/11/12/13/15``. Each replaces the strict
  identity with ``|diff| ≤ 0.01 × N`` slack and (for the cases that
  fold logistics charges) extends the input set with
  ``Σ BT-X-272``. ``BR-FXEXT-CO-13`` is the lone outlier whose
  identity and ``N`` deliberately exclude ``BT-X-272`` — logistics
  fees flow into BT-108 separately and are checked by
  ``BR-FXEXT-CO-12``.

* §5.3 — ten ``BR-FXEXT-{cat}-08`` per-VAT-category sum identities
  replacing the per-row ``BR-CO-17`` for nine VAT categories, plus
  ``BR-FXEXT-S-09`` (the per-rate VAT-amount derivation check that
  only matters for category ``S``).

Every rule guards with ``if profile < Profile.EXTENDED: return []``
to stay silent below EXTENDED. The matching EN 16931 versions in
:mod:`carthorse.rules.trade` and :mod:`carthorse.rules.settlement`
guard with the inverse so the rule set is correct at every profile.

Sub-invoice-line exclusion of ``BT-X-8 == GROUP / INFORMATION``
lines (per the .sch rule text) is a no-op until §4.5 lands BT-X-8 —
every line currently parses as ``DETAIL`` so the accumulators are
already correct for present samples.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from carthorse.schema.element import ValidationError
from carthorse.schema.types import CategoryCode, LineStatusReasonCode, Profile

if TYPE_CHECKING:
    from carthorse.schema import trade as _trade


def _is_detail_line(item: object) -> bool:
    """``True`` if the line participates in monetary accumulators.

    Per the EXTENDED schematron, ``Σ BT-131`` and ``#BT-131`` are
    restricted to lines whose ``BT-X-8`` (``LineStatusReasonCode``)
    is ``DETAIL`` or absent — ``GROUP`` subtotal headers and
    ``INFORMATION`` lines are skipped.
    """
    code = item.associated_document.status_reason_code  # type: ignore[attr-defined]
    return code is None or code == LineStatusReasonCode.DETAIL


_TOLERANCE = Decimal("0.01")


def _err(code: str, msg: str) -> ValidationError:
    return ValidationError(code, msg)


def _within(diff: Decimal, n: int) -> bool:
    """``|diff| ≤ 0.01 × n``.

    When ``n == 0`` the rule devolves to strict equality
    (``|diff| ≤ 0``) — consistent with the schematron's behaviour
    when an empty input set produces a zero-count denominator.
    """
    return abs(diff) <= _TOLERANCE * n


# ---- per-aggregate amount accumulators -------------------------------------


def _line_amounts(m: "_trade.Trade") -> list[Decimal]:
    """``Σ BT-131`` across detail-or-unset line items.

    ``GROUP`` subtotal headers and ``INFORMATION`` lines are
    excluded per the EXTENDED schematron filter
    ``[not(LineStatusReasonCode) or LineStatusReasonCode='DETAIL']``.
    """
    return [
        item.settlement.monetary_summation.line_total
        for item in m.items
        if _is_detail_line(item)
    ]


def _allowance_amounts(m: "_trade.Trade") -> list[Decimal]:
    """``Σ BT-92`` across document-level allowances (charges excluded)."""
    return [
        ac.actual_amount
        for ac in (m.settlement.allowance_charge or [])
        if not ac.indicator
    ]


def _charge_amounts(m: "_trade.Trade") -> list[Decimal]:
    """``Σ BT-99`` across document-level charges (allowances excluded)."""
    return [
        ac.actual_amount
        for ac in (m.settlement.allowance_charge or [])
        if ac.indicator
    ]


def _logistics_amounts(m: "_trade.Trade") -> list[Decimal]:
    """``Σ BT-X-272`` across header logistics service charges."""
    return [
        lsc.applied_amount
        for lsc in (m.settlement.logistics_service_charges or [])
    ]


# ---- §5.2 BR-FXEXT-CO-* (tolerance variants) -------------------------------


def br_fxext_co_04(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-04: BT-151 required when BT-X-8 is ``DETAIL`` or unset.

    EN 16931 ``BR-CO-4`` is implicit through
    ``LineTradeSettlement.applicable_trade_tax`` being non-optional
    on the dataclass. EXTENDED relaxes the requirement on
    ``GROUP`` / ``INFORMATION`` lines, but BT-X-8 isn't modelled
    yet (§4.5) so every line is ``DETAIL`` and the dataclass
    constraint already covers it — this rule is a profile-gated
    placeholder so the EN 16931 → EXTENDED substitution catalogue
    stays complete.
    """
    if profile < Profile.EXTENDED:
        return []
    return []


def br_fxext_co_10(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-10: ``|BT-106 − Σ BT-131| ≤ 0.01 × #BT-131``."""
    if profile < Profile.EXTENDED:
        return []
    if not m.items:
        return []
    summation = m.settlement.monetary_summation
    if summation.line_total is None:
        return []
    line_amts = _line_amounts(m)
    diff = summation.line_total - sum(line_amts, Decimal("0"))
    if _within(diff, len(line_amts)):
        return []
    return [
        _err(
            "BR-FXEXT-CO-10",
            f"Sum of Invoice line net amount (BT-106) = "
            f"{summation.line_total} differs from Σ BT-131 = "
            f"{sum(line_amts, Decimal('0'))} by more than the EXTENDED "
            f"tolerance 0.01 × {len(line_amts)}.",
        )
    ]


def br_fxext_co_11(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-11: ``|BT-107 − Σ BT-92| ≤ 0.01 × #BT-92``."""
    if profile < Profile.EXTENDED:
        return []
    summation = m.settlement.monetary_summation
    if summation.allowance_total is None:
        return []
    alw_amts = _allowance_amounts(m)
    diff = summation.allowance_total - sum(alw_amts, Decimal("0"))
    if _within(diff, len(alw_amts)):
        return []
    return [
        _err(
            "BR-FXEXT-CO-11",
            f"Sum of allowances on document level (BT-107) = "
            f"{summation.allowance_total} differs from Σ BT-92 = "
            f"{sum(alw_amts, Decimal('0'))} by more than the EXTENDED "
            f"tolerance 0.01 × {len(alw_amts)}.",
        )
    ]


def br_fxext_co_12(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-12: ``|BT-108 − (Σ BT-99 + Σ BT-X-272)| ≤ 0.01 × (#BT-99 + #BT-X-272)``.

    Folds logistics service fees (BT-X-272) into the charge total
    — this is the rule the bare EN 16931 BR-CO-12 was previously
    false-positive on EXTENDED samples carrying logistics charges.
    """
    if profile < Profile.EXTENDED:
        return []
    summation = m.settlement.monetary_summation
    if summation.charge_total is None:
        return []
    chg_amts = _charge_amounts(m)
    log_amts = _logistics_amounts(m)
    expected = sum(chg_amts, Decimal("0")) + sum(log_amts, Decimal("0"))
    diff = summation.charge_total - expected
    n = len(chg_amts) + len(log_amts)
    if _within(diff, n):
        return []
    return [
        _err(
            "BR-FXEXT-CO-12",
            f"Sum of charges on document level (BT-108) = "
            f"{summation.charge_total} differs from Σ BT-99 + Σ BT-X-272 "
            f"= {expected} by more than the EXTENDED tolerance "
            f"0.01 × {n}.",
        )
    ]


def br_fxext_co_13(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-13: ``|BT-109 − Σ BT-131 + Σ BT-92 − (Σ BT-99 + Σ BT-X-272)| ≤ 0.01 × (#BT-131 + #BT-92 + #BT-99 + #BT-X-272)``.

    The human-readable assert text in ``FACTUR-X_EXTENDED.sch``
    (and the canonical XLSX) describes CO-13 as excluding
    ``Σ BT-X-272`` — but the actual XPath in the assert's ``test=``
    binds ``$BT99Sum`` to ``sum(charges) + sum(logistics_charges)``
    and ``$nbChargeItems`` to ``count(charges) + count(logistics_charges)``.
    The implementation follows the executable expression, not the
    text — logistics fees feed BT-108 which feeds BT-109, so they
    have to round-trip through the identity.
    """
    if profile < Profile.EXTENDED:
        return []
    if not m.items:
        return []
    summation = m.settlement.monetary_summation
    line_amts = _line_amounts(m)
    alw_amts = _allowance_amounts(m)
    chg_amts = _charge_amounts(m)
    log_amts = _logistics_amounts(m)
    expected = (
        sum(line_amts, Decimal("0"))
        - sum(alw_amts, Decimal("0"))
        + sum(chg_amts, Decimal("0"))
        + sum(log_amts, Decimal("0"))
    )
    diff = summation.tax_basis_total - expected
    n = len(line_amts) + len(alw_amts) + len(chg_amts) + len(log_amts)
    if _within(diff, n):
        return []
    return [
        _err(
            "BR-FXEXT-CO-13",
            f"Invoice total amount without VAT (BT-109) = "
            f"{summation.tax_basis_total} differs from "
            f"Σ BT-131 − Σ BT-92 + Σ BT-99 + Σ BT-X-272 = {expected} "
            f"by more than the EXTENDED tolerance 0.01 × {n}.",
        )
    ]


def br_fxext_co_15(m: "_trade.Trade", profile: Profile) -> list[ValidationError]:
    """BR-FXEXT-CO-15: ``|BT-112 − BT-109 − BT-110| ≤ 0.01 × (#BT-131 + #BT-92 + #BT-99 + #BT-X-272)``.

    Replaces EN 16931 ``BR-CO-15``. Tolerance now scales with every
    input row count (including logistics fees) even though the
    identity itself doesn't change.
    """
    if profile < Profile.EXTENDED:
        return []
    summation = m.settlement.monetary_summation
    currency = m.settlement.currency_code
    bt_110 = next(
        (t.amount for t in (summation.tax_total or []) if t.currency_id == currency),
        Decimal("0"),
    )
    diff = summation.grand_total - summation.tax_basis_total - bt_110
    n = (
        len(_line_amounts(m))
        + len(_allowance_amounts(m))
        + len(_charge_amounts(m))
        + len(_logistics_amounts(m))
    )
    if _within(diff, n):
        return []
    return [
        _err(
            "BR-FXEXT-CO-15",
            f"Invoice total amount with VAT (BT-112) = "
            f"{summation.grand_total} differs from BT-109 + BT-110 = "
            f"{summation.tax_basis_total + bt_110} by more than the "
            f"EXTENDED tolerance 0.01 × {n}.",
        )
    ]


# ---- §5.3 BR-FXEXT-{cat}-08 / -09 (per-VAT-category sums) ------------------


# T_K → "IC" because the .sch family is named after the EN 16931
# label ("Intra-community supply"), not the UNTDID 5305 letter "K".
# T_L → "AF" and T_M → "AG" land via the rename in §3.3.
_PER_CATEGORY_PREFIX: dict[CategoryCode, str] = {
    CategoryCode.T_S: "S",
    CategoryCode.T_Z: "Z",
    CategoryCode.T_E: "E",
    CategoryCode.T_AE: "AE",
    CategoryCode.T_G: "G",
    CategoryCode.T_K: "IC",
    CategoryCode.T_L: "AF",
    CategoryCode.T_M: "AG",
    CategoryCode.T_O: "O",
}


def _category_n(m: "_trade.Trade") -> int:
    """``#BT-131 + #BT-92 + #BT-99 + #BT-X-272`` — the tolerance count
    common to all §5.3 per-category checks."""
    return (
        len(_line_amounts(m))
        + len(_allowance_amounts(m))
        + len(_charge_amounts(m))
        + len(_logistics_amounts(m))
    )


def br_fxext_vat_category_sums(
    m: "_trade.Trade", profile: Profile
) -> list[ValidationError]:
    """BR-FXEXT-{S,Z,E,AE,G,IC,AF,AG,O}-08 and BR-FXEXT-S-09 — per-VAT-category
    sum identities at each BG-23 row.

    For every header VAT breakdown row (BG-23) carrying category
    ``X`` at rate ``r``:

    * **-08**: ``|BT-116 − Σ_rel(BT-131) + Σ_rel(BT-92) − Σ_rel(BT-99)
      − Σ_rel(BT-X-272)| ≤ 0.01 × N`` where ``Σ_rel`` restricts the
      input set to lines / allowances / charges / logistics-charges
      whose VAT category matches ``X`` and rate matches ``r``.
    * **-09** (S only): ``|BT-117 − BT-116 × BT-119 / 100| ≤ 0.01 × N``.

    Replaces the global ``BR-CO-17`` with one variant per category,
    each with tolerance ``N = #BT-131 + #BT-92 + #BT-99 + #BT-X-272``.
    """
    if profile < Profile.EXTENDED:
        return []
    errors: list[ValidationError] = []
    n = _category_n(m)
    for tt in m.settlement.trade_taxes or []:
        cat = tt.category_code
        if cat not in _PER_CATEGORY_PREFIX:
            continue
        rate = tt.rate_applicable_percent
        prefix = _PER_CATEGORY_PREFIX[cat]

        # -08: per-category basis identity.
        if tt.basis_amount is not None:
            line_amts = [
                item.settlement.monetary_summation.line_total
                for item in m.items
                if _is_detail_line(item)
                and item.settlement.applicable_trade_tax.category_code == cat
                and item.settlement.applicable_trade_tax.rate_applicable_percent
                == rate
            ]
            alw_amts = [
                ac.actual_amount
                for ac in (m.settlement.allowance_charge or [])
                if not ac.indicator
                and ac.category_trade_tax is not None
                and ac.category_trade_tax.category_code == cat
                and ac.category_trade_tax.rate_applicable_percent == rate
            ]
            chg_amts = [
                ac.actual_amount
                for ac in (m.settlement.allowance_charge or [])
                if ac.indicator
                and ac.category_trade_tax is not None
                and ac.category_trade_tax.category_code == cat
                and ac.category_trade_tax.rate_applicable_percent == rate
            ]
            # Each LogisticsServiceCharge carries 1..* AppliedTradeTax rows.
            # We attribute the full applied_amount to its first matching tax
            # classification — typical samples have exactly one row per
            # charge; the multi-row case is rare and the spec leaves the
            # apportionment unspecified.
            log_amts = [
                lsc.applied_amount
                for lsc in (m.settlement.logistics_service_charges or [])
                if lsc.applied_trade_tax
                and lsc.applied_trade_tax[0].category_code == cat
                and lsc.applied_trade_tax[0].rate_applicable_percent == rate
            ]
            expected = (
                sum(line_amts, Decimal("0"))
                - sum(alw_amts, Decimal("0"))
                + sum(chg_amts, Decimal("0"))
                + sum(log_amts, Decimal("0"))
            )
            diff = tt.basis_amount - expected
            if not _within(diff, n):
                errors.append(
                    _err(
                        f"BR-FXEXT-{prefix}-08",
                        f"VAT breakdown {cat.value!r} @ rate {rate}: "
                        f"basis (BT-116) = {tt.basis_amount} differs from "
                        f"Σ_rel BT-131 − Σ_rel BT-92 + Σ_rel BT-99 + "
                        f"Σ_rel BT-X-272 = {expected} by more than the "
                        f"EXTENDED tolerance 0.01 × {n}.",
                    )
                )

        # -09 (S only): rate × basis derivation.
        if (
            cat == CategoryCode.T_S
            and tt.calculated_amount is not None
            and tt.basis_amount is not None
            and rate is not None
        ):
            expected_tax = tt.basis_amount * rate / Decimal("100")
            diff_tax = tt.calculated_amount - expected_tax
            if not _within(diff_tax, n):
                errors.append(
                    _err(
                        "BR-FXEXT-S-09",
                        f"VAT breakdown 'S' @ rate {rate}: tax amount "
                        f"(BT-117) = {tt.calculated_amount} differs from "
                        f"BT-116 × BT-119 / 100 = {expected_tax} by more "
                        f"than the EXTENDED tolerance 0.01 × {n}.",
                    )
                )

    return errors
