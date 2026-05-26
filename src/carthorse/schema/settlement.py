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
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.rules import Validator
from carthorse.rules.settlement import (
    br_5_currency_shape,
    br_29,
    br_50,
    br_51,
    br_53,
    br_61,
    br_co_14,
    br_co_15,
    br_co_16,
    br_co_18,
    br_co_19,
    br_co_25,
    bt_81_code_shape,
)
from carthorse.schema.accounting import (
    ApplicableTradeTax,
    HeaderTradeAllowanceCharge,
    MonetarySummation,
)
from carthorse.schema.element import Element, ETElement
from carthorse.schema.party import PayeeTradeParty
from carthorse.schema.references import InvoiceReferencedDocument
from carthorse.schema.types import (
    Currency,
    Namespace,
    Profile,
    UNTDID4461PaymentMeansCode,
)


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

    _validators: ClassVar[
        tuple[Validator["PayeePartyCreditorFinancialAccount"], ...]
    ] = (br_50,)

    iban_id: str | None = field(default=None, metadata={"tag": "IBANID"})
    """Payment account identifier (BT-84).

    A unique identifier of the financial account held at a payment
    service provider to which the payment should be made — IBAN in
    the SEPA case, a national account number otherwise.

    Note: per ``BR-50`` either ``iban_id`` or ``proprietary_id``
    must be present; ``BR-61`` further requires an IBAN for SEPA /
    local / non-SEPA credit transfers (not yet enforced).
    """
    account_name: str | None = field(
        default=None, metadata={"tag": "AccountName", "profile": Profile.COMFORT}
    )
    """Payment account name (BT-85); COMFORT+.

    The name of the payment account, used to identify the account
    when the account holder is different from the Payee.
    """
    proprietary_id: str | None = field(default=None, metadata={"tag": "ProprietaryID"})
    """National (non-SEPA) account number (BT-84-0).

    Note: prefer ``iban_id`` when appropriate; ``proprietary_id`` is
    reserved for the non-SEPA case.
    """


@dataclass(kw_only=True, slots=True)
class FinancialCard(Element):
    """Payment card (BG-18); COMFORT+.

    Carries the last 4..6 digits of the Payment card primary account
    number (BT-87) and an optional cardholder name (BT-88). ``BR-51``
    constrains BT-87 to exactly 4..6 numeric digits.
    """

    tag: ClassVar[str] = "ApplicableTradeSettlementFinancialCard"
    profile: ClassVar[Profile] = Profile.COMFORT

    _validators: ClassVar[tuple[Validator["FinancialCard"], ...]] = (br_51,)

    id: str = field(metadata={"tag": "ID"})
    """Payment card primary account number, last 4..6 digits (BT-87)."""
    cardholder_name: str | None = field(
        default=None, metadata={"tag": "CardholderName"}
    )
    """Payment card holder name (BT-88)."""


@dataclass(kw_only=True, slots=True)
class CreditorFinancialInstitution(Element):
    """Creditor's bank (BG-17 cont., BT-86); COMFORT+.

    A single ``BICID`` identifying the receiving bank for credit
    transfers. The XSD requires the ``BICID`` child element to be
    present (``minOccurs=1``) but real-world ZUGFeRD samples ship it
    self-closing when the BIC is unknown. The dataclass therefore
    treats the value as optional and the renderer always emits the
    wrapper element (empty when ``bic_id is None``) to keep
    re-rendered XML XSD-valid.
    """

    tag: ClassVar[str] = "PayeeSpecifiedCreditorFinancialInstitution"
    profile: ClassVar[Profile] = Profile.COMFORT

    bic_id: str | None = None
    """Payment service provider identifier (BT-86)."""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        inner = XML(f"{Namespace.ram.name}:BICID")
        if self.bic_id is not None:
            inner = inner[self.bic_id]
        return XML(self.get_tag())[inner]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        bic_qtag = Namespace.ram.get_qualified_tag("BICID")
        for child in elem:
            if child.tag == bic_qtag:
                if child.text is None:
                    return cls(bic_id=None)
                return cls(bic_id=child.text.strip())
        return cls(bic_id=None)


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

    _validators: ClassVar[tuple[Validator["PaymentMeans"], ...]] = (
        bt_81_code_shape,
        br_61,
    )

    type_code: UNTDID4461PaymentMeansCode = field(metadata={"tag": "TypeCode"})
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
    information: str | None = field(
        default=None, metadata={"tag": "Information", "profile": Profile.COMFORT}
    )
    """Free-text payment-means description (BT-82); COMFORT+."""
    financial_card: FinancialCard | None = None
    """Payment card (BG-18); COMFORT+."""
    payer: PayerPartyDebtorFinancialAccount | None = None
    """Debited account (BT-91-00) — direct-debit payments only."""
    payee: PayeePartyCreditorFinancialAccount | None = None
    """Credit-transfer account (BG-17) — credit-transfer payments only."""
    creditor_institution: CreditorFinancialInstitution | None = None
    """Creditor's bank (BG-17 cont. / BT-86); COMFORT+."""


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

    _validators: ClassVar[tuple[Validator["BillingSpecifiedPeriod"], ...]] = (
        br_co_19,
        br_29,
    )

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

    _validators: ClassVar[tuple[Validator["TradeSettlement"], ...]] = (
        br_5_currency_shape,
        br_co_18,
        br_53,
        br_co_25,
        br_co_14,
        br_co_15,
        br_co_16,
    )

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
    tax_currency_code: Currency | None = field(
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
    currency_code: Currency = field(metadata={"tag": "InvoiceCurrencyCode"})
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
    allowance_charge: list[HeaderTradeAllowanceCharge] | None = None
    """Header allowances (BG-20) and charges (BG-21), 0..*."""
    terms: PaymentTerms | None = None
    """Payment terms (BT-20-00); BASIC_WL+."""
    monetary_summation: MonetarySummation
    """Document totals (BG-22); required at every profile."""
    invoice_referenced_document: list[InvoiceReferencedDocument] | None = None
    """Preceding-invoice references (BG-3, 0..*); BASIC_WL+."""
    accounting_account: list[ReceivableAccountingAccount] | None = None
    """Buyer accounting references (BT-19-00, 0..*); BASIC_WL+."""
