"""Validators for :mod:`getafix.schema.settlement`.

One function per ``BR-*`` rule (or per BT shape-check) that today
lives inside an ``Element.validate_internal`` body in
``settlement.py``. The signatures match :data:`getafix.rules.Validator`.

Each function:

* self-gates on profile (the rule's applies-to matrix from the
  ``Business Rules`` sheet) and on the precondition data;
* returns ``list[ValidationError]`` (empty on success);
* never raises.

See ``AGENTS.md`` "Validator architecture" for the design.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING

from getafix.schema.element import ValidationError
from getafix.schema.types import Profile

_PAN_RE = re.compile(r"^\d{4,6}$")

if TYPE_CHECKING:
    from getafix.schema import settlement as _set


def br_50(
    m: _set.PayeePartyCreditorFinancialAccount, _profile: Profile
) -> list[ValidationError]:
    """BR-50: A Payment account identifier (BT-84) shall be present if Credit
    transfer (BG-16) information is provided in the Invoice.

    Applies: BASIC_WL+ (BG-17 / BT-84 do not exist below BASIC_WL).
    """
    if m.iban_id is not None or m.proprietary_id is not None:
        return []
    return [
        ValidationError(
            "BR-50",
            "A Payment account identifier (BT-84) shall be present "
            "if Credit transfer (BG-16) information is provided in "
            "the Invoice.",
        )
    ]


def br_51(m: _set.FinancialCard, _profile: Profile) -> list[ValidationError]:
    """BR-51: The last 4 to 6 digits of the Payment card primary account
    number (BT-87) shall be present if Payment card information (BG-18)
    is provided in the Invoice.

    Applies: COMFORT+ (BG-18 first appears at COMFORT). Format guard —
    the field's presence is enforced by the dataclass declaring it
    required.
    """
    if _PAN_RE.fullmatch(m.id):
        return []
    return [
        ValidationError(
            "BR-51", f"Payment card PAN (BT-87) {m.id!r} must be 4..6 digits."
        )
    ]


_CREDIT_TRANSFER_CODES = {"30", "42", "58"}


def br_61(m: _set.PaymentMeans, _profile: Profile) -> list[ValidationError]:
    """BR-61: If the Payment means type code (BT-81) means SEPA credit
    transfer, Local credit transfer or Non-SEPA international credit
    transfer, the Payment account identifier (BT-84) shall be present.

    Applies: BASIC_WL+ (BG-16 / BT-81 first appear there). The
    credit-transfer family covers UNTDID 4461 codes ``30`` (Credit
    transfer), ``42`` (Payment to bank account) and ``58`` (SEPA
    credit transfer).
    """
    if m.type_code not in _CREDIT_TRANSFER_CODES:
        return []
    if m.payee is not None and m.payee.iban_id is not None:
        return []
    return [
        ValidationError(
            "BR-61",
            "Payment means type code "
            f"{m.type_code!r} indicates a credit transfer; "
            "the Payment account identifier (BT-84, IBAN) shall be present.",
        )
    ]


def bt_81_code_shape(m: _set.PaymentMeans, _profile: Profile) -> list[ValidationError]:
    """BT-81 (Payment means type code) must be a UNTDID 4461 code
    (digits up to 3 chars, or ``ZZZ``).

    Applies: BASIC_WL+. Not a numbered EN 16931 rule — a code-shape
    guard against malformed inputs. Raises with error code ``"BT-81"``
    for back-compat with existing tests.
    """
    code = m.type_code
    if len(code) <= 3 and (code.isdigit() or code == "ZZZ"):
        return []
    return [
        ValidationError(
            "BT-81",
            f"Payment means type code (BT-81) {code!r} "
            "is not a UNTDID 4461 code (digits up to 3 chars, or 'ZZZ').",
        )
    ]


def br_co_19(
    m: _set.BillingSpecifiedPeriod, _profile: Profile
) -> list[ValidationError]:
    """BR-CO-19: If Invoicing period (BG-14) is used, the Invoicing period
    start date (BT-73) or the Invoicing period end date (BT-74) shall be
    filled, or both.

    Applies: BASIC_WL+ (BG-14 / BG-26 do not exist below BASIC_WL).
    Also enforced on BG-26 (line invoicing period) — same dataclass.
    """
    if m.start is not None or m.end is not None:
        return []
    return [
        ValidationError(
            "BR-CO-19",
            "If Invoicing period (BG-14) is used, the Invoicing "
            "period start date (BT-73) or the Invoicing period end "
            "date (BT-74) shall be filled, or both.",
        )
    ]


def br_29(m: _set.BillingSpecifiedPeriod, _profile: Profile) -> list[ValidationError]:
    """BR-29: If both Invoicing period start date (BT-73) and Invoicing
    period end date (BT-74) are given then the Invoicing period end date
    (BT-74) shall be later or equal to the Invoicing period start date
    (BT-73).

    Applies: BASIC_WL+. Also enforced on BG-26 (line invoicing
    period) — same dataclass.
    """
    if m.start is None or m.end is None:
        return []
    if m.end >= m.start:
        return []
    return [
        ValidationError(
            "BR-29",
            "If both Invoicing period start date (BT-73) and "
            "Invoicing period end date (BT-74) are given then the "
            "Invoicing period end date (BT-74) shall be later or "
            "equal to the Invoicing period start date (BT-73).",
        )
    ]


def br_5_currency_shape(
    m: _set.TradeSettlement, _profile: Profile
) -> list[ValidationError]:
    """BR-5: An Invoice shall have an Invoice currency code (BT-5).

    Applies: MINIMUM+. Getafix stretches the rule to also check
    that the value has the ISO 4217 alpha-3 uppercase shape; the
    presence check itself is implicit through the required dataclass
    field on :class:`~getafix.schema.settlement.TradeSettlement`.
    """
    cc = m.currency_code
    if len(cc) == 3 and cc.isalpha() and cc.upper() == cc:
        return []
    return [
        ValidationError(
            "BR-5",
            "Invoice currency code (BT-5) must be an ISO 4217 "
            f"alpha-3 uppercase code; got {cc!r}.",
        )
    ]


def br_co_18(m: _set.TradeSettlement, profile: Profile) -> list[ValidationError]:
    """BR-CO-18: An Invoice shall at least have one VAT breakdown group
    (BG-23).

    Applies: BASIC_WL+ (BG-23 is required from that profile up; the
    MINIMUM XSD does not carry it).
    """
    if profile < Profile.BASIC_WL:
        return []
    if m.trade_taxes:
        return []
    return [
        ValidationError(
            "BR-CO-18",
            "An Invoice shall at least have one VAT breakdown group (BG-23).",
        )
    ]


def br_53(m: _set.TradeSettlement, _profile: Profile) -> list[ValidationError]:
    """BR-53: If the VAT accounting currency code (BT-6) is present, then
    the Invoice total VAT amount in accounting currency (BT-111) shall be
    provided.

    Applies: BASIC_WL+ (BT-6 only exists from BASIC_WL up).
    """
    if m.tax_currency_code is None:
        return []
    tax_totals = m.monetary_summation.tax_total or []
    if any(t.currency_id == m.tax_currency_code for t in tax_totals):
        return []
    return [
        ValidationError(
            "BR-53",
            "If the VAT accounting currency code (BT-6) is "
            "present, then the Invoice total VAT amount in "
            "accounting currency (BT-111) shall be provided.",
        )
    ]


def br_co_25(m: _set.TradeSettlement, profile: Profile) -> list[ValidationError]:
    """BR-CO-25: In case the Amount due for payment (BT-115) is positive,
    either the Payment due date (BT-9) or the Payment terms (BT-20) shall
    be present.

    Applies: BASIC_WL+. Both source fields (BT-9 / BT-20) live in
    ``SpecifiedTradePaymentTerms`` which the MINIMUM XSD does not
    include — the rule is therefore unenforceable at MINIMUM.
    """
    if profile < Profile.BASIC_WL:
        return []
    if m.monetary_summation.due_amount <= 0:
        return []
    if m.terms is not None and any(
        t.due is not None or t.description is not None for t in m.terms
    ):
        return []
    return [
        ValidationError(
            "BR-CO-25",
            "In case the Amount due for payment (BT-115) is "
            "positive, either the Payment due date (BT-9) or the "
            "Payment terms (BT-20) shall be present.",
        )
    ]


def br_co_14(m: _set.TradeSettlement, _profile: Profile) -> list[ValidationError]:
    """BR-CO-14: Invoice total VAT amount (BT-110) = sum of VAT category
    tax amounts (BT-117) across BG-23 rows.

    Applies: BASIC_WL+ (BT-110 / BG-23 do not exist below BASIC_WL).
    Computed only when both pieces are populated.
    """
    if m.monetary_summation.tax_total is None or not m.trade_taxes:
        return []
    bt_110_in_invoice = next(
        (
            t.amount
            for t in m.monetary_summation.tax_total
            if t.currency_id == m.currency_code
        ),
        None,
    )
    if bt_110_in_invoice is None:
        return []
    bt_117_sum = sum(
        (tt.calculated_amount or Decimal("0") for tt in m.trade_taxes), Decimal("0")
    )
    if bt_110_in_invoice == bt_117_sum:
        return []
    return [
        ValidationError(
            "BR-CO-14",
            "Invoice total VAT amount (BT-110) "
            f"= {bt_110_in_invoice} differs from "
            f"sum(BT-117) = {bt_117_sum}.",
        )
    ]


def br_co_15(m: _set.TradeSettlement, profile: Profile) -> list[ValidationError]:
    """BR-CO-15: Invoice total amount with VAT (BT-112) = Invoice total
    amount without VAT (BT-109) + Invoice total VAT amount (BT-110).

    Applies: MINIMUM+ except EXTENDED. At EXTENDED
    ``BR-FXEXT-CO-15`` replaces this with a tolerance-banded variant.
    BT-111 (TaxTotalAmount in VAT accounting currency) does NOT
    enter this identity — only BT-110 (in invoice currency) does.
    """
    if profile >= Profile.EXTENDED:
        return []
    bt_110 = next(
        (
            t.amount
            for t in (m.monetary_summation.tax_total or [])
            if t.currency_id == m.currency_code
        ),
        Decimal("0"),
    )
    expected_grand = m.monetary_summation.tax_basis_total + bt_110
    if m.monetary_summation.grand_total == expected_grand:
        return []
    return [
        ValidationError(
            "BR-CO-15",
            "Invoice total amount with VAT (BT-112) "
            f"= {m.monetary_summation.grand_total} differs from "
            f"BT-109 + BT-110 = "
            f"{m.monetary_summation.tax_basis_total} + {bt_110} "
            f"= {expected_grand}.",
        )
    ]


def br_co_16(m: _set.TradeSettlement, _profile: Profile) -> list[ValidationError]:
    """BR-CO-16: Amount due for payment (BT-115) = Invoice total amount
    with VAT (BT-112) - Paid amount (BT-113) + Rounding amount (BT-114).

    Applies: MINIMUM+. BT-114 (RoundingAmount) is optional and only
    available from COMFORT onwards — treated as 0 when absent.
    BT-113 (TotalPrepaidAmount) is treated as 0 when absent.
    """
    prepaid = m.monetary_summation.prepaid_total or Decimal("0")
    rounding = m.monetary_summation.rounding_amount or Decimal("0")
    expected_due = m.monetary_summation.grand_total - prepaid + rounding
    if m.monetary_summation.due_amount == expected_due:
        return []
    return [
        ValidationError(
            "BR-CO-16",
            "Amount due for payment (BT-115) "
            f"= {m.monetary_summation.due_amount} differs from "
            f"BT-112 - BT-113 + BT-114 = "
            f"{m.monetary_summation.grand_total} - {prepaid} "
            f"+ {rounding} = {expected_due}.",
        )
    ]
