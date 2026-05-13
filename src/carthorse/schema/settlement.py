"""Header trade settlement (BG-19) — currency, payment, totals.

``ApplicableHeaderTradeSettlement`` is the third sibling of the
``SupplyChainTradeTransaction``. It carries:

* the invoice currency (BT-5) and the optional VAT accounting
  currency (BT-6, BASIC_WL+);
* SEPA-specific creditor reference (BT-90) and remittance
  information (BT-83);
* payee details if different from seller (BG-10);
* zero-or-more payment means (BG-16) with the associated debited
  account (BT-91-00) and creditor account (BG-17);
* one or more VAT breakdowns (BG-23) at BASIC_WL+;
* optional invoicing period (BG-14, also reused at line level as
  BG-26);
* zero-or-more allowance (BG-20) and charge (BG-21) groups —
  defined in :mod:`accounting`;
* optional payment terms (BT-20-00); EXTENDED upgrades this to a
  list of payment-term blocks;
* the monetary summation (BG-22) — defined in :mod:`accounting`;
* zero-or-more preceding-invoice references (BG-3) — defined in
  :mod:`references`;
* zero-or-more accounting references (BT-19-00).

Validation rules enforced here:

* △ ``BR-5`` — :meth:`TradeSettlement.validate_internal` checks the
  alpha-3 uppercase shape of ``currency_code`` (BT-5); the ISO 4217
  registry is not consulted.
* ✓ ``BR-50`` — :meth:`PayeePartyCreditorFinancialAccount.validate_internal`
  requires IBAN-ID or proprietary id.
* ✓ ``BR-53`` — BT-6 set ⇒ a ``TaxTotal`` row with ``currency_id ==
  BT-6`` must be present.
* △ ``BR-49`` — :meth:`PaymentMeans.validate_internal` checks
  the UNTDID 4461 code shape of ``type_code``; the BG-16 presence
  rule itself is not enforced.
* ✓ ``BR-CO-18`` — at least one ``trade_taxes`` row at BASIC_WL+.
* ✓ ``BR-CO-19`` / ``BR-29`` —
  :meth:`BillingSpecifiedPeriod.validate_internal`: BG-14 needs at
  least one endpoint, and ``end >= start`` when both are present.
  The same validator runs on BG-26 (line invoicing period).
* ✓ ``BR-CO-14`` — ``BT-110 = sum(BT-117)`` across BG-23 rows.
* ✓ ``BR-CO-15`` — ``BT-112 = BT-109 + BT-110``.
* ✓ ``BR-CO-16`` — ``BT-115 = BT-112 - BT-113 + BT-114``.
* ✓ ``BR-CO-25`` — positive ``DuePayableAmount`` (BT-115) requires
  BT-9 or BT-20 (gated on BASIC_WL+ since BT-9 / BT-20 live in
  ``SpecifiedTradePaymentTerms`` which MINIMUM omits).

Validation rules not yet enforced (see ``docs/VALIDATION.md``):

* ``BR-61`` — SEPA / local / non-SEPA credit transfer needs BT-84.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, override

from carthorse.schema.accounting import (
    ApplicableTradeTax,
    MonetarySummation,
    TradeAllowanceCharge,
)
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.party import PayeeTradeParty
from carthorse.schema.references import InvoiceReferencedDocument
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class PayerPartyDebtorFinancialAccount(Element):
    """Debited account (BT-91-00).

    Buyer's bank account for direct-debit payments. Provided when
    the payment means is a direct debit.
    """

    tag: ClassVar[str] = "PayerPartyDebtorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str = field(metadata={"tag": "IBANID"})
    """Debited account identifier (BT-91).

    The account to be debited by the direct debit.
    """


@dataclass(kw_only=True, slots=True)
class PayeePartyCreditorFinancialAccount(Element):
    """Credit transfer / Seller bank account (BG-17).

    A group of business terms specifying credit-transfer payment
    details.

    Note: if several bank accounts are to be transmitted, the
    enclosing :class:`PaymentMeans` (BG-16) must be repeated — one
    entry per account.
    """

    tag: ClassVar[str] = "PayeePartyCreditorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str | None = field(default=None, metadata={"tag": "IBANID"})
    """Payment account identifier (BT-84).

    A unique identifier of the financial account held at a payment
    service provider to which the payment should be made — IBAN in
    the SEPA case, a national account number otherwise.

    Note: per ``BR-50`` either ``iban_id`` or ``proprietary_id``
    must be present; ``BR-61`` further requires an IBAN for SEPA /
    local / non-SEPA credit transfers (not yet enforced).
    """
    proprietary_id: str | None = field(default=None, metadata={"tag": "ProprietaryID"})
    """National (non-SEPA) account number (BT-84-0).

    Note: prefer ``iban_id`` when appropriate; ``proprietary_id`` is
    reserved for the non-SEPA case.
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if self.iban_id is None and self.proprietary_id is None:
            errors.append(
                ValidationError(
                    "BR-50",
                    "A Payment account identifier (BT-84) shall be present "
                    "if Credit transfer (BG-16) information is provided in "
                    "the Invoice.",
                )
            )
        errors.extend(
            super(PayeePartyCreditorFinancialAccount, self).validate_internal(profile)
        )
        return errors


@dataclass(kw_only=True, slots=True)
class PaymentMeans(Element):
    """Payment instructions (BG-16).

    A group of business terms providing information about the
    payment. Repeated 0..* on :class:`TradeSettlement`.

    Note: only repeat when several bank accounts are to be
    transmitted for credit transfers — the payment means
    ``type_code`` (BT-81) must not differ between repetitions. The
    debtor financial account (BT-91-00) and the payment card group
    (BG-18) must NOT be given for credit transfers.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementPaymentMeans"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    type_code: str = field(metadata={"tag": "TypeCode"})
    """Payment means type code (BT-81).

    The expected or used means of payment, expressed as a code.
    Distinguishes SEPA from non-SEPA payments and between credit
    transfers, direct debits, card payments and other means.

    Code list: UNTDID 4461. Frequently-used codes:

    * ``10`` — cash
    * ``20`` — cheque
    * ``30`` — credit transfer
    * ``42`` — payment to bank account
    * ``48`` — bank card
    * ``49`` — direct debit
    * ``57`` — standing order
    * ``58`` — SEPA credit transfer
    * ``59`` — SEPA direct debit
    * ``97`` — report

    https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred4461.htm
    """
    payer: PayerPartyDebtorFinancialAccount | None = None
    """Debited account (BT-91-00) — direct-debit payments only."""
    payee: PayeePartyCreditorFinancialAccount | None = None
    """Credit-transfer account (BG-17) — credit-transfer payments only."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if not (
            len(self.type_code) <= 3
            and (self.type_code.isdigit() or self.type_code == "ZZZ")
        ):
            errors.append(
                ValidationError(
                    "BT-81",
                    f"Payment means type code (BT-81) {self.type_code!r} "
                    "is not a UNTDID 4461 code (digits up to 3 chars, or 'ZZZ').",
                )
            )
        errors.extend(super(PaymentMeans, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class PaymentTerms(Element):
    """Payment terms (BT-20-00).

    A group of business terms providing the textual description of
    the payment terms, the payment due date and (for SEPA direct
    debits) the mandate reference.

    Note: XSD field order is ``Description`` (BT-20),
    ``DueDateDateTime`` (BT-9), ``DirectDebitMandateID`` (BT-89).
    EXTENDED upgrades the parent settlement to a *list* of
    ``SpecifiedTradePaymentTerms`` — carthorse models the single
    case only.
    """

    tag: ClassVar[str] = "SpecifiedTradePaymentTerms"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    description: str | None = field(default=None, metadata={"tag": "Description"})
    """Payment terms, free text (BT-20).

    A textual description of the payment terms that apply to the
    amount due for payment — including the description of possible
    penalties. May contain multiple lines and multiple terms.
    """
    due: date | None = field(default=None, metadata={"tag": "DueDateDateTime"})
    """Payment due date (BT-9).

    The date when the payment is due — the due date of the net
    payment. For partial payments this is the first net due date;
    the description of more complex schedules belongs in
    :attr:`description` (BT-20).
    """
    debit_mandate_id: str | None = field(
        default=None, metadata={"tag": "DirectDebitMandateID"}
    )
    """SEPA mandate reference (BT-89).

    Unique identifier assigned by the Payee for referencing the
    direct-debit mandate. Used to pre-notify the Buyer of a SEPA
    direct debit.
    """


@dataclass(kw_only=True, slots=True)
class BillingSpecifiedPeriod(Element):
    """Invoicing period (BG-14 at header / BG-26 at line).

    A group of business terms providing information on the period
    the invoice covers — also called the delivery period.

    Note: the element name ``BillingSpecifiedPeriod`` is shared
    between header (BG-14) and line (BG-26) level — the BT IDs on
    the endpoints differ (BT-73/BT-74 vs BT-134/BT-135).
    ``BR-CO-19`` requires at least one endpoint when the group is
    used, and ``BR-29`` requires ``end >= start`` if both are given.
    """

    tag: ClassVar[str] = "BillingSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    start: date | None = field(
        default=None, metadata={"tag": "StartDateTime", "profile": Profile.BASIC_WL}
    )
    """Invoicing period start date (BT-73 header / BT-134 line).

    The initial date of delivery of goods or services.
    """
    end: date | None = field(
        default=None, metadata={"tag": "EndDateTime", "profile": Profile.BASIC_WL}
    )
    """Invoicing period end date (BT-74 header / BT-135 line).

    The date on which the delivery of goods or services was
    completed.
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if self.start is None and self.end is None:
            errors.append(
                ValidationError(
                    "BR-CO-19",
                    "If Invoicing period (BG-14) is used, the Invoicing "
                    "period start date (BT-73) or the Invoicing period end "
                    "date (BT-74) shall be filled, or both.",
                )
            )
        if self.start is not None and self.end is not None and self.end < self.start:
            errors.append(
                ValidationError(
                    "BR-29",
                    "If both Invoicing period start date (BT-73) and "
                    "Invoicing period end date (BT-74) are given then the "
                    "Invoicing period end date (BT-74) shall be later or "
                    "equal to the Invoicing period start date (BT-73).",
                )
            )
        errors.extend(super(BillingSpecifiedPeriod, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class ReceivableAccountingAccount(Element):
    """Buyer accounting reference (BT-19-00).

    Wrapper around BT-19 — the textual value specifying where the
    relevant data is to be posted in the Buyer's financial accounts.
    """

    tag: ClassVar[str] = "ReceivableSpecifiedTradeAccountingAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: str = field(metadata={"tag": "ID"})
    """Buyer accounting reference (BT-19).

    A textual value that specifies where to book the relevant data
    in the Buyer's financial accounts.
    """


@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    """Header trade settlement (BG-19).

    Container for currency, payee, payment means, VAT breakdown,
    invoicing period, header allowances/charges, payment terms, the
    monetary summation, preceding-invoice references, and accounting
    references.
    """

    tag: ClassVar[str] = "ApplicableHeaderTradeSettlement"

    creditor_reference: str | None = field(
        default=None,
        metadata={"tag": "CreditorReferenceID", "profile": Profile.BASIC_WL},
    )
    """Bank-assigned creditor identifier (BT-90).

    A unique banking reference identifier of the Payee or Seller
    assigned by the Payee's or Seller's bank — typically the SEPA
    creditor identifier. Used to pre-notify the Buyer of a SEPA
    direct debit.
    """
    payment_reference: str | None = field(
        default=None, metadata={"tag": "PaymentReference", "profile": Profile.BASIC_WL}
    )
    """Remittance information (BT-83).

    A textual value used to link the payment to the invoice — most
    commonly the invoice number. In a payment transaction this
    reference is returned to the Seller as remittance information.

    Note: for cross-border SEPA payments only Latin characters and
    at most 140 characters should be used; the value must not start
    or end with ``/`` and must not contain ``//``. Structured
    references following ISO 11649:2009 map to the SEPA Structured
    Remittance Information / Creditor Reference field; EACT
    structured references map to the Unstructured Remittance
    Information field. National-border SEPA payments may relax
    these rules.
    """
    tax_currency_code: str | None = field(
        default=None, metadata={"tag": "TaxCurrencyCode", "profile": Profile.BASIC_WL}
    )
    """VAT accounting currency code (BT-6); BASIC_WL+.

    The currency used for VAT accounting and reporting purposes as
    accepted or required in the Seller's country.

    Note: required only when it differs from the invoice currency
    (BT-5). When set, ``BR-53`` requires a second ``TaxTotal`` row
    in :attr:`monetary_summation` carrying BT-111 with
    ``currency_id == tax_currency_code``.

    Code list: ISO 4217.
    """
    currency_code: str = field(metadata={"tag": "InvoiceCurrencyCode"})
    """Invoice currency code (BT-5).

    The currency in which all invoice amounts are given, except for
    the invoice VAT total in VAT accounting currency (BT-111). Only
    one currency may be used in the invoice, except for that BT-111
    exception per Article 230 of Council Directive 2006/112/EC.

    Code list: ISO 4217.
    """
    payee: PayeeTradeParty | None = None
    """Payee (BG-10); BASIC_WL+ — provided when different from the
    Seller."""
    payment_means: list[PaymentMeans] | None = None
    """Payment means (BG-16, 0..*); BASIC_WL+."""
    trade_taxes: list[ApplicableTradeTax] | None = None
    """VAT breakdown rows (BG-23, 1..*); required from BASIC_WL+
    (``BR-CO-18``)."""
    billing_period: BillingSpecifiedPeriod | None = None
    """Header invoicing period (BG-14); BASIC_WL+."""
    allowance_charge: list[TradeAllowanceCharge] | None = None
    """Header allowances (BG-20) and charges (BG-21), 0..*."""
    terms: PaymentTerms | None = None
    """Payment terms (BT-20-00); BASIC_WL+."""
    monetary_summation: MonetarySummation
    """Document totals (BG-22); required at every profile."""
    invoice_referenced_document: list[InvoiceReferencedDocument] | None = None
    """Preceding-invoice references (BG-3, 0..*); BASIC_WL+."""
    accounting_account: list[ReceivableAccountingAccount] | None = None
    """Buyer accounting references (BT-19-00, 0..*); BASIC_WL+."""

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if (
            len(self.currency_code) != 3
            or not self.currency_code.isalpha()
            or self.currency_code.upper() != self.currency_code
        ):
            errors.append(
                ValidationError(
                    "BR-5",
                    "Invoice currency code (BT-5) must be an ISO 4217 "
                    f"alpha-3 uppercase code; got {self.currency_code!r}.",
                )
            )

        if Profile.BASIC_WL <= profile and not self.trade_taxes:
            errors.append(
                ValidationError(
                    "BR-CO-18",
                    "An Invoice shall at least have one VAT breakdown group (BG-23).",
                )
            )

        if self.tax_currency_code is not None:
            tax_totals = self.monetary_summation.tax_total or []
            if not any(t.currency_id == self.tax_currency_code for t in tax_totals):
                errors.append(
                    ValidationError(
                        "BR-53",
                        "If the VAT accounting currency code (BT-6) is "
                        "present, then the Invoice total VAT amount in "
                        "accounting currency (BT-111) shall be provided.",
                    )
                )

        # BR-CO-25: positive DuePayableAmount (BT-115) requires either a
        # payment due date (BT-9) or payment terms description (BT-20).
        # Both source fields live inside ``SpecifiedTradePaymentTerms``
        # which the MINIMUM XSD does not include — the rule is therefore
        # unenforceable at MINIMUM and only kicks in from BASIC_WL up.
        if (
            profile >= Profile.BASIC_WL
            and self.monetary_summation.due_amount > 0
            and (
                self.terms is None
                or (self.terms.due is None and self.terms.description is None)
            )
        ):
            errors.append(
                ValidationError(
                    "BR-CO-25",
                    "In case the Amount due for payment (BT-115) is "
                    "positive, either the Payment due date (BT-9) or the "
                    "Payment terms (BT-20) shall be present.",
                )
            )

        # BR-CO-14: BT-110 (TaxTotalAmount in invoice currency) = sum of
        # BT-117 (CalculatedAmount on each BG-23 row). Computed only
        # when both pieces are populated.
        if self.monetary_summation.tax_total is not None and self.trade_taxes:
            bt_110_in_invoice = next(
                (
                    t.amount
                    for t in self.monetary_summation.tax_total
                    if t.currency_id == self.currency_code
                ),
                None,
            )
            if bt_110_in_invoice is not None:
                bt_117_sum = sum(
                    (tt.calculated_amount or Decimal("0") for tt in self.trade_taxes),
                    Decimal("0"),
                )
                if bt_110_in_invoice != bt_117_sum:
                    errors.append(
                        ValidationError(
                            "BR-CO-14",
                            "Invoice total VAT amount (BT-110) "
                            f"= {bt_110_in_invoice} differs from "
                            f"sum(BT-117) = {bt_117_sum}.",
                        )
                    )

        # BR-CO-15: BT-112 (GrandTotalAmount) = BT-109 (TaxBasisTotalAmount)
        # + BT-110 (the TaxTotalAmount in invoice currency). BT-111
        # (TaxTotalAmount in VAT accounting currency) does NOT enter
        # this identity.
        bt_110 = next(
            (
                t.amount
                for t in (self.monetary_summation.tax_total or [])
                if t.currency_id == self.currency_code
            ),
            Decimal("0"),
        )
        expected_grand = self.monetary_summation.tax_basis_total + bt_110
        if self.monetary_summation.grand_total != expected_grand:
            errors.append(
                ValidationError(
                    "BR-CO-15",
                    "Invoice total amount with VAT (BT-112) "
                    f"= {self.monetary_summation.grand_total} differs from "
                    f"BT-109 + BT-110 = "
                    f"{self.monetary_summation.tax_basis_total} + {bt_110} "
                    f"= {expected_grand}.",
                )
            )

        # BR-CO-16: BT-115 (DuePayableAmount) = BT-112 - BT-113
        # (TotalPrepaidAmount) + BT-114 (RoundingAmount). BT-114 is
        # optional and only available from COMFORT onwards — treat as
        # 0 when absent.
        prepaid = self.monetary_summation.prepaid_total or Decimal("0")
        rounding = self.monetary_summation.rounding_amount or Decimal("0")
        expected_due = self.monetary_summation.grand_total - prepaid + rounding
        if self.monetary_summation.due_amount != expected_due:
            errors.append(
                ValidationError(
                    "BR-CO-16",
                    "Amount due for payment (BT-115) "
                    f"= {self.monetary_summation.due_amount} differs from "
                    f"BT-112 - BT-113 + BT-114 = "
                    f"{self.monetary_summation.grand_total} - {prepaid} "
                    f"+ {rounding} = {expected_due}.",
                )
            )

        errors.extend(super(TradeSettlement, self).validate_internal(profile))
        return errors
