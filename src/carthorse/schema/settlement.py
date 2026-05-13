"""Header trade settlement (BG-19) — currency, payment, totals.

``ApplicableHeaderTradeSettlement`` (BG-19) is the third sibling of
the ``SupplyChainTradeTransaction``. It carries:

* the invoice currency (BT-5) and — at BASIC_WL+ — the optional VAT
  accounting currency (BT-6);
* SEPA-specific creditor reference and remittance information;
* payee details if different from seller (BG-10);
* zero-or-more payment means (BG-16) with associated debtor/creditor
  financial accounts (BG-17);
* one or more VAT breakdowns (BG-23) once at BASIC_WL+;
* optional invoicing period (BG-14);
* zero-or-more allowance (BG-20) and charge (BG-21) groups;
* optional payment terms (BT-20-00); EXTENDED upgrades this to a list;
* the monetary summation (BG-22);
* zero-or-more preceding-invoice references (BG-3);
* zero-or-more accounting references (BT-19-00).

Validation rules covered (or missing) in this module:

* ✓ ``BR-CO-18`` (at least one ``trade_taxes`` row at BASIC_WL+) — see
  :meth:`TradeSettlement.validate_internal`.
* ✓ ``BR-29`` (BG-14 start ≤ end) and ``BR-CO-19`` (BG-14 start or end
  required if used) — :class:`BillingSpecifiedPeriod`.
* ✓ ``BR-50`` (account info requires IBAN or proprietary id) — see
  :meth:`PayeePartyCreditorFinancialAccount.validate_internal`.
* ✓ ``BR-53`` (BT-6 set ⇒ a ``TaxTotal`` row with ``currency_id == BT-6``).
* △ ``BR-5`` — currency code shape only.
* △ ``BR-49`` — ``PaymentMeans.type_code`` shape; not the BG-16
  presence rule.
* ✓ ``BR-CO-25`` (positive ``DuePayableAmount`` ⇒ BT-9 or BT-20
  present) — :meth:`TradeSettlement.validate_internal`.
* — ``BR-61`` (SEPA / local / non-SEPA credit transfer requires BT-84):
  not enforced.

For the full BR-* catalogue see ``docs/VALIDATION.md``.
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
    """Buyer's bank account (debited account)."""

    tag: ClassVar[str] = "PayerPartyDebtorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str = field(metadata={"tag": "IBANID"})
    """Direct debit: debited account identifier (BT-91).

    The account to be debited by the direct debit. To be provided in
    case of direct debit payment.
    """


@dataclass(kw_only=True, slots=True)
class PayeePartyCreditorFinancialAccount(Element):
    """Credit transfer / Seller bank account details (BG-17).

    If several bank accounts are to be specified for credit transfer,
    the SpecifiedTradeSettlementPaymentMeans element must be repeated
    accordingly.
    """

    tag: ClassVar[str] = "PayeePartyCreditorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str | None = field(default=None, metadata={"tag": "IBANID"})
    """Payment account identifier (BT-84).

    A unique identifier of the financial account held at a payment
    service provider to which the payment should be made, such as an
    IBAN (in case of a SEPA payment). For a national account number,
    use ProprietaryID.

    With respect to BR-50 and BR-61, either an IBAN-ID or a
    ProprietaryID must be provided.
    """
    proprietary_id: str | None = field(default=None, metadata={"tag": "ProprietaryID"})
    """National account number (not for SEPA) (BT-84-0).

    For SEPA payments use IBANID.
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

    Only when several bank accounts are to be transmitted for credit
    transfers may the SpecifiedTradeSettlementPaymentMeans element be
    repeated for each bank account. The payment means type code in the
    TypeCode element (BT-81) must consequently not differ between the
    repetitions. The ApplicableTradeSettlementFinancialCard and
    PayerPartyDebtorFinancialAccount elements shall not be given for
    credit transfers.
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementPaymentMeans"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    type_code: str = field(metadata={"tag": "TypeCode"})
    """Payment means type code (BT-81).

    The expected or used means of payment, expressed as a code.

    Entries from the UNTDID 4461 code list must be used. A
    distinction should be made between SEPA and non-SEPA payments and
    between credit transfers, direct debits, card payments and other
    payment means.

    Code list: UNTDID 4461:
        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred4461.htm

    In particular, the following codes may be used:
        10 : In cash
        20 : Cheque
        30 : Credit transfer
        42 : Payment to bank account
        48 : Bank card
        49 : Direct debit
        57 : Standing order
        58 : SEPA Credit Transfer
        59 : SEPA Direct Debit
        97 : Report
    """
    payer: PayerPartyDebtorFinancialAccount | None = None
    payee: PayeePartyCreditorFinancialAccount | None = None

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
    """Payment terms details (BT-20-00).

    XSD field order is ``Description`` (BT-20), ``DueDateDateTime``
    (BT-9), ``DirectDebitMandateID`` (BT-89).
    """

    tag: ClassVar[str] = "SpecifiedTradePaymentTerms"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    description: str | None = field(default=None, metadata={"tag": "Description"})
    """Free-text payment terms (BT-20)."""
    due: date | None = field(default=None, metadata={"tag": "DueDateDateTime"})
    """Payment due date (BT-9)."""
    debit_mandate_id: str | None = field(
        default=None, metadata={"tag": "DirectDebitMandateID"}
    )
    """Mandate reference identifier / SEPA mandate reference (BT-89).

    Used to inform the Buyer in advance of a SEPA direct debit.
    """


@dataclass(kw_only=True, slots=True)
class BillingSpecifiedPeriod(Element):
    """Invoicing period (BG-14 / BG-26) — start and/or end dates.

    The element name is ``BillingSpecifiedPeriod`` at both header
    (BG-14) and line (BG-26) level. The XSD allows either or both
    endpoints; ``BR-CO-19`` requires at least one of them when the
    group is used, and ``BR-29`` requires ``end >= start`` if both
    are given.
    """

    tag: ClassVar[str] = "BillingSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    start: date | None = field(
        default=None, metadata={"tag": "StartDateTime", "profile": Profile.BASIC_WL}
    )
    """Start of the invoicing period (BT-73 (header), BT-134 (line))."""
    end: date | None = field(
        default=None, metadata={"tag": "EndDateTime", "profile": Profile.BASIC_WL}
    )
    """End of the invoicing period (BT-74 (header), BT-135 (line))."""

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
    """Buyer accounting reference details."""

    tag: ClassVar[str] = "ReceivableSpecifiedTradeAccountingAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: str = field(metadata={"tag": "ID"})
    """Buyer accounting reference (BT-19).

    A textual value that specifies where the relevant data is to be
    posted in the Buyer's financial accounts.
    """


@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    """Header trade settlement group (payment and settlement details)."""

    tag: ClassVar[str] = "ApplicableHeaderTradeSettlement"

    creditor_reference: str | None = field(
        default=None,
        metadata={"tag": "CreditorReferenceID", "profile": Profile.BASIC_WL},
    )
    """Bank assigned creditor identifier / SEPA creditor identifier (BT-90).

    A unique banking reference identifier of the Payee or Seller
    assigned by the Payee's or Seller's bank.

    Used to inform the Buyer in advance of a SEPA direct debit.
    """
    payment_reference: str | None = field(
        default=None, metadata={"tag": "PaymentReference", "profile": Profile.BASIC_WL}
    )
    """Remittance information / payment reference (BT-83).

    A textual value used to link the payment to the Invoice issued by
    the Seller.

    This reference helps the Seller to assign an incoming payment to
    the relevant payment process. When stating the textual value —
    usually the Invoice number of the Invoice to be paid, but it may
    also be another Seller reference — the Buyer should include this
    reference in the payment order or when making the payment. In a
    payment transaction this reference is returned to the Seller as
    remittance information.

    To enable automatic processing of cross-border SEPA payments, only
    Latin characters and a maximum of 140 characters should be used in
    this field. See section 1.4 of the SEPA Credit Transfer and SEPA
    Direct Debit Scheme Implementation Guides for further details on
    the permissible characters. Different rules may apply for SEPA
    payments within national borders.

    If the remittance information is structured according to ISO
    11649:2009 via the Payee structured reference, it shall be mapped
    in SEPA payment messages to the Structured Remittance Information
    Creditor Reference field.

    If the remittance information is structured according to the EACT
    standard for automatic account reconciliation, it shall be mapped
    in SEPA payment messages to the Unstructured Remittance
    Information field.

    If the remittance information is mapped in SEPA payment messages
    to the End To End Identification field or to the Structured
    Remittance Information Creditor Reference field, the content —
    aside from the restriction to Latin characters — must not start or
    end with a "/" and must not contain "//".

    In the simplest case this could, for example, be identical to the
    Invoice number. Note: If the payment reference is to be stated in
    SEPA credit transfers or direct debits, only the character set
    permitted for SEPA may be used.
    """
    tax_currency_code: str | None = field(
        default=None, metadata={"tag": "TaxCurrencyCode", "profile": Profile.BASIC_WL}
    )
    """VAT accounting currency code (BT-6).

    Optional from BASIC_WL onwards. When present, the seller's local
    currency for VAT accounting (which differs from the invoice
    currency BT-5). Triggers ``BR-53``: a ``TaxTotal`` entry with
    ``currency_id == tax_currency_code`` (BT-111) must also be
    provided in :attr:`monetary_summation`.
    """
    currency_code: str = field(metadata={"tag": "InvoiceCurrencyCode"})
    """Invoice currency code (BT-5).

    The currency in which all Invoice amounts are given, except for
    the invoice VAT total in VAT accounting currency.

    The Invoice shall be issued in a single currency, with the
    exception, under Article 230 of Council Directive 2006/112/EC on
    VAT, of the invoice VAT total in VAT accounting currency
    (BT-111). The lists of valid currencies are maintained by the ISO
    4217 Maintenance Agency "Codes for the representation of
    currencies and funds".
    """
    payee: PayeeTradeParty | None = None
    payment_means: list[PaymentMeans] | None = None
    trade_taxes: list[ApplicableTradeTax] | None = None
    billing_period: BillingSpecifiedPeriod | None = None
    """Header invoicing period (BG-14)."""
    allowance_charge: list[TradeAllowanceCharge] | None = None
    terms: PaymentTerms | None = None
    monetary_summation: MonetarySummation
    invoice_referenced_document: list[InvoiceReferencedDocument] | None = None
    """Preceding invoice references (BG-3); zero or more."""
    accounting_account: list[ReceivableAccountingAccount] | None = None

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
