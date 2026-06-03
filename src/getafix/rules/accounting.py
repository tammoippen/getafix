"""Validators for :mod:`getafix.schema.accounting`.

One function per ``BR-*`` rule (or per BT shape-check) that today
lives inside an ``Element.validate_internal`` body in
``accounting.py``. The signatures match :data:`getafix.rules.Validator`.

Each function:

* self-gates on profile (the rule's applies-to matrix from the
  ``Business Rules`` sheet) and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

See ``AGENTS.md`` "Validator architecture" for the design.
"""

# Pyright walks the static schema↔rules cycle and reports it; the
# runtime graph has no cycle (annotations are inert under ``from
# __future__ import annotations`` and the schema imports sit under
# TYPE_CHECKING). Silence the report module-wide.
# pyright: reportImportCycles=false

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from getafix.schema._numeric import round_half_away_from_zero
from getafix.schema.element import ValidationError
from getafix.schema.types import Profile

if TYPE_CHECKING:
    from getafix.schema import accounting as _acc


def br_5_currency_shape(m: _acc.TaxTotal, _profile: Profile) -> list[ValidationError]:
    """BR-5: An Invoice shall have an Invoice currency code (BT-5).

    Applies: MINIMUM+. Getafix stretches the rule to also check
    that the value has the ISO 4217 alpha-3 uppercase shape; the
    presence check itself is implicit through the required dataclass
    field.
    """
    cid = m.currency_id
    if len(cid) == 3 and cid.isalpha() and cid.upper() == cid:
        return []
    return [
        ValidationError(
            "BR-5",
            "Invoice currency code (BT-5) must be an ISO 4217 "
            f"alpha-3 uppercase code; got {cid!r}.",
        )
    ]


def br_12(m: _acc.MonetarySummation, profile: Profile) -> list[ValidationError]:
    """BR-12: An Invoice shall have the Sum of Invoice line net amount (BT-106).

    Applies: BASIC_WL+ (the MINIMUM XSD drops ``LineTotalAmount``
    from ``MonetarySummationType``, so the rule is not checkable
    there).
    """
    if profile < Profile.BASIC_WL:
        return []
    if m.line_total is not None:
        return []
    return [
        ValidationError(
            "BR-12",
            "An Invoice shall have the Sum of Invoice line net amount (BT-106).",
        )
    ]


def br_co_3(m: _acc.ApplicableTradeTax, _profile: Profile) -> list[ValidationError]:
    """BR-CO-3: Value added tax point date (BT-7) and Value added tax point
    date code (BT-8) are mutually exclusive.

    Applies: COMFORT+ (BT-7 is gated on COMFORT in getafix — the
    rule is only triggerable from there upwards).
    """
    if m.tax_point_date is None or m.due_date_code is None:
        return []
    return [
        ValidationError(
            "BR-CO-3",
            "Value added tax point date (BT-7) and Value added "
            "tax point date code (BT-8) are mutually exclusive.",
        )
    ]


def br_co_17(m: _acc.ApplicableTradeTax, profile: Profile) -> list[ValidationError]:
    """BR-CO-17: VAT category tax amount (BT-117) = VAT category taxable
    amount (BT-116) * (VAT category rate (BT-119) / 100), rounded to two
    decimals.

    Applies: BASIC_WL+ except EXTENDED. At EXTENDED the per-VAT-
    category ``BR-FXEXT-*-09`` family supersedes this rule with
    rounding-tolerance variants.

    Note: Factur-X §7.1.8 rounding is half-away-from-zero. The
    check is skipped when the rate is absent (e.g. category 'O').
    """
    if profile >= Profile.EXTENDED:
        return []
    if (
        m.rate_applicable_percent is None
        or m.basis_amount is None
        or m.calculated_amount is None
    ):
        return []
    expected = round_half_away_from_zero(
        m.basis_amount * m.rate_applicable_percent / Decimal("100")
    )
    if round_half_away_from_zero(m.calculated_amount) == expected:
        return []
    return [
        ValidationError(
            "BR-CO-17",
            "VAT category tax amount (BT-117) = "
            f"{m.calculated_amount} differs from "
            "round(BT-116 * BT-119 / 100, 2) = "
            f"round({m.basis_amount} * "
            f"{m.rate_applicable_percent} / 100, 2) = "
            f"{expected}.",
        )
    ]


def bt_8_code_shape(
    m: _acc.ApplicableTradeTax, _profile: Profile
) -> list[ValidationError]:
    """BT-8 (Value added tax point date code) must be a UNTDID 2475 code.

    Applies: BASIC_WL+. Not a numbered EN 16931 rule — a code-shape
    guard kept for back-compat with the error code ``"BT-8"``.
    ``due_date_code: UNTDID2475TaxPointDateCode | None`` already
    forces enum membership at construction time, so this validator
    only fires if a caller manually side-steps the enum.
    """
    code = m.due_date_code
    if code is None or (len(code) <= 3 and code.isdigit()):
        return []
    return [
        ValidationError(
            "BT-8",
            "Value added tax point date code (BT-8) must be a "
            f"UNTDID 2475 code; got {code!r}.",
        )
    ]


def br_48(m: _acc.ApplicableTradeTax, _profile: Profile) -> list[ValidationError]:
    """BR-48: Each VAT breakdown (BG-23) shall have a VAT category rate
    (BT-119), except if the Invoice is not subject to VAT.

    Applies: BASIC_WL+ (BG-23 first appears there). Category ``O``
    (Services outside scope of tax) is exempt because the rate is
    forbidden for that category per ``BR-O-5``.
    """
    if m.rate_applicable_percent is not None:
        return []
    if m.category_code == "O":
        return []
    return [
        ValidationError(
            "BR-48",
            "Each VAT breakdown (BG-23) shall have a VAT category rate "
            "(BT-119), except if the Invoice is not subject to VAT.",
        )
    ]


def bt_118_0_vat_only(
    m: _acc.ApplicableTradeTax, profile: Profile
) -> list[ValidationError]:
    """BT-118-0 (TypeCode on ApplicableTradeTax) must be ``"VAT"`` except
    at EXTENDED.

    Applies: BASIC_WL+ except EXTENDED (which permits the broader
    UNTDID 5153 code list for non-VAT tax types). Raises with error
    code ``"BT-118-0"`` for back-compat with existing tests.
    """
    if m.type_code == "VAT":
        return []
    # ApplicableTradeTax.profile is the dataclass-level minimum gate
    # (always BASIC_WL); only at EXTENDED is a non-"VAT" code legal.
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BT-118-0",
            "Tax type codes other than 'VAT' on BT-118-0 are only "
            "allowed in the EXTENDED profile.",
        )
    ]


_TAC_AMOUNT_CODE: dict[tuple[str, bool], str] = {
    ("header", False): "BR-DEC-01",
    ("header", True): "BR-DEC-05",
    ("line", False): "BR-DEC-24",
    ("line", True): "BR-DEC-27",
}
_TAC_BASIS_CODE: dict[tuple[str, bool], str] = {
    ("header", False): "BR-DEC-02",
    ("header", True): "BR-DEC-06",
    ("line", False): "BR-DEC-25",
    ("line", True): "BR-DEC-28",
}


def _too_many_decimals(value: Decimal | None, max_places: int = 2) -> bool:
    if value is None:
        return False
    exp = value.as_tuple().exponent
    return isinstance(exp, int) and -exp > max_places


def br_dec_tac_amounts(
    m: _acc.TradeAllowanceCharge, _profile: Profile
) -> list[ValidationError]:
    """``BR-DEC-{01,02,05,06,24,25,27,28}`` on TradeAllowanceCharge.

    One Decimal-precision check per (context, indicator) combination
    for both ``actual_amount`` (BT-92/99/136/141) and ``basis_amount``
    (BT-93/100/137/142). The correct BR-DEC-* code is looked up from
    the ``context`` ClassVar (header / line) and the ``indicator``
    field (False=allowance / True=charge).
    """
    errors: list[ValidationError] = []
    key = (m.context, m.indicator)
    if _too_many_decimals(m.actual_amount):
        errors.append(
            ValidationError(
                _TAC_AMOUNT_CODE[key],
                f"TradeAllowanceCharge actual_amount {m.actual_amount} "
                "carries more than 2 decimal places.",
            )
        )
    if _too_many_decimals(m.basis_amount):
        errors.append(
            ValidationError(
                _TAC_BASIS_CODE[key],
                f"TradeAllowanceCharge basis_amount {m.basis_amount} "
                "carries more than 2 decimal places.",
            )
        )
    return errors


def bt_95_0_102_0_vat_only(
    m: _acc.CategoryTradeTax, profile: Profile
) -> list[ValidationError]:
    """BT-95-0 / BT-102-0 (TypeCode on CategoryTradeTax) must be ``"VAT"``
    except at EXTENDED.

    Applies: BASIC_WL+ except EXTENDED. Raises with the combined
    error code ``"BT-95-0/BT-102-0"`` (the same ``CategoryTradeTax``
    element appears both on document-level allowances under BG-20-0
    and on document-level charges under BG-21-0; the rule is
    identical so a single code is emitted).
    """
    if m.type_code == "VAT":
        return []
    if profile >= Profile.EXTENDED:
        return []
    return [
        ValidationError(
            "BT-95-0/BT-102-0",
            "Tax type codes other than 'VAT' on BT-95-0 / BT-102-0 "
            "are only allowed in the EXTENDED profile.",
        )
    ]
