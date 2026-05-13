"""Validators for :mod:`carthorse.schema.accounting`.

One function per ``BR-*`` rule (or per BT shape-check) that today
lives inside an ``Element.validate_internal`` body in
``accounting.py``. The signatures match :data:`carthorse.rules.Validator`.

Each function:

* self-gates on profile (the rule's applies-to matrix from the
  ``Business Rules`` sheet) and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

See ``docs/VALIDATOR_REFACTOR.md`` for the rework plan.
"""

# Each ``rules/<topic>.py`` module annotates against the element
# types it validates, which are defined in the matching
# ``schema/<topic>.py`` module. That schema module in turn imports
# the validator functions from here to wire them onto
# ``Element._validators`` — an architecturally-required cycle.
# Annotations are kept inert via ``from __future__ import annotations``
# so the runtime graph has no cycle, but pyright still walks the
# static cycle and reports it. The reportImportCycles directive
# below silences that signal across this module; see
# ``docs/VALIDATOR_REFACTOR.md`` for the architecture.
# pyright: reportImportCycles=false

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from carthorse.schema._numeric import round_half_away_from_zero
from carthorse.schema.element import ValidationError
from carthorse.schema.types import Profile

if TYPE_CHECKING:
    from carthorse.schema import accounting as _acc


def br_5_currency_shape(m: _acc.TaxTotal, profile: Profile) -> list[ValidationError]:
    """BR-5: An Invoice shall have an Invoice currency code (BT-5).

    Applies: MINIMUM+. Carthorse stretches the rule to also check
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


def br_co_3(m: _acc.ApplicableTradeTax, profile: Profile) -> list[ValidationError]:
    """BR-CO-3: Value added tax point date (BT-7) and Value added tax point
    date code (BT-8) are mutually exclusive.

    Applies: COMFORT+ (BT-7 is gated on COMFORT in carthorse — the
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
    m: _acc.ApplicableTradeTax, profile: Profile
) -> list[ValidationError]:
    """BT-8 (Value added tax point date code) must be a UNTDID 2475 code
    (digits up to 3 chars, or ``ZZZ``).

    Applies: BASIC_WL+. Not a numbered EN 16931 rule — a code-shape
    guard against malformed inputs. Raises with error code ``"BT-8"``
    for back-compat with existing tests.
    """
    code = m.due_date_code
    if code is None:
        return []
    if len(code) <= 3 and (code.isdigit() or code == "ZZZ"):
        return []
    return [
        ValidationError(
            "BT-8",
            "Value added tax point date code (BT-8) must be a "
            f"UNTDID 2475 code (digits or 'ZZZ'); got {code!r}.",
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
