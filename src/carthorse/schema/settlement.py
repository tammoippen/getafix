"""Header trade settlement (BG-19) — currency, payment, totals.

``ApplicableHeaderTradeSettlement`` is the third sibling of the
``SupplyChainTradeTransaction``. It carries:

* the invoice currency (BT-5) and the optional VAT accounting
  currency (BT-6, BASIC_WL+);
* SEPA-specific creditor reference (BT-90) and remittance
  information (BT-83);
* payee details if different from seller (BG-10);
* EXTENDED-only settlement parties: the Seller's invoice file
  reference (BT-X-204), the Invoicer (BG-X-33), the Invoicee
  (BG-X-36), and the Payer (BG-X-73);
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
* zero-or-more accounting references (BT-19-00);
* zero-or-more EXTENDED advance payments (BG-X-45) with their
  included VAT (BG-X-46) and an optional prepayment-invoice
  reference (BG-X-85).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.rules import Validator
from carthorse.rules._types import fields_only_at, list_max_cardinality_below
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
from carthorse.schema.party import (
    InvoiceeTradeParty,
    InvoicerTradeParty,
    PayeeTradeParty,
    PayerTradeParty,
)
from carthorse.schema.references import InvoiceReferencedDocument
from carthorse.schema.types import (
    CategoryCode,
    Currency,
    Namespace,
    Profile,
    TypeCode,
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
    local / non-SEPA credit transfers.
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
class BasisPeriodMeasure(Element):
    """Period measure (``udt:MeasureType``) — numeric value + ``unitCode``.

    XSD shape: ``<Tag unitCode="DAY">10</Tag>``. Generic shape reused
    by the EXTENDED payment-penalty terms (BT-X-277, inside BG-X-43)
    and payment-discount terms (BT-X-283, inside BG-X-44) to express
    the time window the penalty / discount applies over.
    """

    tag: ClassVar[str] = "BasisPeriodMeasure"
    profile: ClassVar[Profile] = Profile.EXTENDED

    value: Decimal
    """Numeric period length. Role-dependent BT id — BT-X-277 on
    :class:`PaymentPenaltyTerms.basis_period_measure`, BT-X-283 on
    :class:`PaymentDiscountTerms.basis_period_measure`."""
    unit_code: str
    """UN/ECE Rec.20 time unit code (``DAY``, ``WEE``, ``MON``, …).
    Rendered as the ``@unitCode`` attribute — BT-X-278 on the
    penalty measure, BT-X-284 on the discount measure."""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), attrs={"unitCode": self.unit_code})[str(self.value)]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        unit_code = elem.attrib.get("unitCode")
        if unit_code is None:
            raise ValueError("BasisPeriodMeasure missing required unitCode")
        if elem.text is None:
            raise ValueError("BasisPeriodMeasure missing numeric content")
        return cls(value=Decimal(elem.text.strip()), unit_code=unit_code)


@dataclass(kw_only=True, slots=True)
class PaymentPenaltyTerms(Element):
    """Late-payment penalty terms (BG-X-43); EXTENDED only.

    Nested 0..1 on :class:`PaymentTerms`. Shape matches the XSD
    ``TradePaymentPenaltyTermsType``: every field is optional —
    callers populate the subset they need (e.g. just
    ``calculation_percent`` for a flat-rate late fee, or
    ``basis_period_measure + actual_amount`` for "after N days, owe
    X"). The mirror class :class:`PaymentDiscountTerms` covers the
    early-payment side with the same shape modulo the final amount
    field's XML tag.
    """

    tag: ClassVar[str] = "ApplicableTradePaymentPenaltyTerms"
    profile: ClassVar[Profile] = Profile.EXTENDED

    basis_date_time: date | None = field(
        default=None, metadata={"tag": "BasisDateTime"}
    )
    """Penalty basis date (BT-X-276, wrapped in BT-X-276-00; format
    attribute is BT-X-276-0)."""
    basis_period_measure: BasisPeriodMeasure | None = None
    """Penalty basis period (BT-X-277; ``@unitCode`` attribute is BT-X-278)."""
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "amount": True}
    )
    """Penalty basis amount (BT-X-279)."""
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent"}
    )
    """Penalty rate percentage (BT-X-280)."""
    actual_amount: Decimal | None = field(
        default=None, metadata={"tag": "ActualPenaltyAmount", "amount": True}
    )
    """Penalty amount (BT-X-281)."""


@dataclass(kw_only=True, slots=True)
class PaymentDiscountTerms(Element):
    """Early-payment discount terms (BG-X-44); EXTENDED only.

    Nested 0..1 on :class:`PaymentTerms`. Same shape as
    :class:`PaymentPenaltyTerms` except the final amount carries
    the ``ActualDiscountAmount`` XML tag rather than
    ``ActualPenaltyAmount``.
    """

    tag: ClassVar[str] = "ApplicableTradePaymentDiscountTerms"
    profile: ClassVar[Profile] = Profile.EXTENDED

    basis_date_time: date | None = field(
        default=None, metadata={"tag": "BasisDateTime"}
    )
    """Discount basis date (BT-X-282, wrapped in BT-X-282-00; format
    attribute is BT-X-282-0)."""
    basis_period_measure: BasisPeriodMeasure | None = None
    """Discount basis period (BT-X-283; ``@unitCode`` attribute is BT-X-284)."""
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "amount": True}
    )
    """Discount basis amount (BT-X-285)."""
    calculation_percent: Decimal | None = field(
        default=None, metadata={"tag": "CalculationPercent"}
    )
    """Discount rate percentage (BT-X-286)."""
    actual_amount: Decimal | None = field(
        default=None, metadata={"tag": "ActualDiscountAmount", "amount": True}
    )
    """Discount amount (BT-X-287)."""


@dataclass(kw_only=True, slots=True)
class PaymentTerms(Element):
    """Payment terms (BT-20-00).

    A group of business terms providing the textual description of
    the payment terms, the payment due date and (for SEPA direct
    debits) the mandate reference. EXTENDED adds optional partial-
    payment amount and nested penalty / discount terms; the
    settlement-level cardinality widens from 0..1 (BASIC_WL through
    COMFORT) to 0..* at EXTENDED (multiple payment-term schedules),
    so :attr:`TradeSettlement.terms` is modelled as a list and
    capped to one entry below EXTENDED by
    :func:`carthorse.rules._types.list_max_cardinality_below`.
    """

    tag: ClassVar[str] = "SpecifiedTradePaymentTerms"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    _validators: ClassVar[tuple[Validator["PaymentTerms"], ...]] = (
        fields_only_at(
            Profile.EXTENDED,
            "partial_payment_amount",
            "penalty_terms",
            "discount_terms",
            "payee",
        ),
    )

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
    partial_payment_amount: Decimal | None = field(
        default=None,
        metadata={
            "tag": "PartialPaymentAmount",
            "amount": True,
            "profile": Profile.EXTENDED,
        },
    )
    """Partial-payment amount for this term (BT-X-275); EXTENDED only."""
    penalty_terms: PaymentPenaltyTerms | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Late-payment penalty schedule (BG-X-43, EXTENDED only)."""
    discount_terms: PaymentDiscountTerms | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Early-payment discount schedule (BG-X-44, EXTENDED only)."""
    payee: PayeeTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Term-specific payee (BG-X-77, BT-X-504); EXTENDED only.

    A payee that applies to this particular payment-term schedule —
    e.g. when different instalments are collected by different
    parties. Reuses the BG-10 :class:`PayeeTradeParty` shape (same
    ``PayeeTradeParty`` element name)."""


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
class AppliedTradeTax(Element):
    """Logistics-service-charge VAT category (BT-X-273 / BT-X-274); EXTENDED only.

    Nested 1..* on :class:`LogisticsServiceCharge` (BG-X-42). The XSD
    type is the full ``ram:TradeTaxType`` (same shape as
    :class:`ApplicableTradeTax`), but per the EXTENDED technical
    appendix only the three coded fields are typically populated —
    the calculated and basis amounts live on the header BG-23 rows
    once the charge feeds the per-category sum.
    """

    tag: ClassVar[str] = "AppliedTradeTax"
    profile: ClassVar[Profile] = Profile.EXTENDED

    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """Tax type code (BT-X-273-0). ``"VAT"`` at EN16931; UNTDID 5153
    at EXTENDED for non-VAT tax types (insurance tax, mineral oil
    tax, …)."""
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """VAT category code (BT-X-273)."""
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """VAT rate (BT-X-274). Optional like on BG-23 — omitted on
    rate-less categories (``O``, ``AE``, ``K``)."""


@dataclass(kw_only=True, slots=True)
class LogisticsServiceCharge(Element):
    """Logistics service charge (BG-X-42); EXTENDED only.

    A charge applied to the invoice for logistics services (freight,
    handling, insurance, …). Its ``applied_amount`` (BT-X-272) sums
    into BT-108 alongside BG-21 document-level charges per
    ``BR-FXEXT-CO-12``, and into the per-category VAT breakdown via
    ``BR-FXEXT-{cat}-08``.

    Field order matches the XSD ``LogisticsServiceChargeType``
    ``<xs:sequence>``: ``Description`` → ``AppliedAmount`` →
    ``AppliedTradeTax``.
    """

    tag: ClassVar[str] = "SpecifiedLogisticsServiceCharge"
    profile: ClassVar[Profile] = Profile.EXTENDED

    description: str = field(metadata={"tag": "Description"})
    """Logistics service charge description (BT-X-271)."""
    applied_amount: Decimal = field(metadata={"tag": "AppliedAmount", "amount": True})
    """Logistics service charge amount (BT-X-272)."""
    applied_trade_tax: list[AppliedTradeTax]
    """Per-category VAT applied to the charge (BT-X-273-00 wrapper;
    1..* per XSD). Non-empty asserted in :meth:`__post_init__`."""
    currency: str | None = None

    def __post_init__(self) -> None:
        # XSD minOccurs=1 on AppliedTradeTax — the dataclass type is
        # ``list`` (not Optional), but a caller can still pass [];
        # mirror the XSD here so we don't silently render an
        # invalid LogisticsServiceCharge.
        if not self.applied_trade_tax:
            raise ValueError(
                "LogisticsServiceCharge.applied_trade_tax: at least one "
                "AppliedTradeTax entry is required (XSD minOccurs=1)."
            )


@dataclass(kw_only=True, slots=True)
class TaxCurrencyExchange(Element):
    """Tax-accounting-currency conversion (BG-X-41); EXTENDED only.

    Records the source → target currency exchange used to derive
    the tax-accounting-currency totals (BT-X-260..264) when the
    invoice is denominated in a currency different from the local
    tax accounting currency.

    Field order matches the XSD ``TradeCurrencyExchangeType``
    ``<xs:sequence>``: ``SourceCurrencyCode`` →
    ``TargetCurrencyCode`` → ``ConversionRate`` →
    ``ConversionRateDateTime``.
    """

    tag: ClassVar[str] = "TaxApplicableTradeCurrencyExchange"
    profile: ClassVar[Profile] = Profile.EXTENDED

    source_currency_code: Currency = field(metadata={"tag": "SourceCurrencyCode"})
    """Source currency code (BT-X-258)."""
    target_currency_code: Currency = field(metadata={"tag": "TargetCurrencyCode"})
    """Target (tax-accounting) currency code (BT-X-259)."""
    conversion_rate: Decimal = field(metadata={"tag": "ConversionRate"})
    """Conversion rate from source to target (BT-X-260)."""
    conversion_rate_date_time: date | None = field(
        default=None, metadata={"tag": "ConversionRateDateTime"}
    )
    """Conversion-rate date (BT-X-261, wrapped in BT-X-261-00). Plain
    date — XSD wraps it in ``udt:DateTimeType`` with the same
    ``format="102"`` (YYYYMMDD) pattern as BT-2 IssueDateTime."""


@dataclass(kw_only=True, slots=True)
class AdvancePaymentTradeTax(Element):
    """VAT included in an advance payment (BG-X-46); EXTENDED-only.

    The ``IncludedTradeTax`` of a :class:`AdvancePayment` — the VAT
    already accounted for in a prepayment. Same ``ram:TradeTaxType``
    as the BG-23 breakdown; only the fields the prepayment populates
    are modelled, in XSD-sequence order.
    """

    tag: ClassVar[str] = "IncludedTradeTax"
    profile: ClassVar[Profile] = Profile.EXTENDED

    calculated_amount: Decimal | None = field(
        default=None, metadata={"tag": "CalculatedAmount", "amount": True}
    )
    """VAT amount included in the prepayment (BT-X-293)."""
    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """Tax type code (BT-X-294); UNTDID 5153, normally ``"VAT"``."""
    exemption_reason: str | None = field(
        default=None, metadata={"tag": "ExemptionReason"}
    )
    """VAT exemption reason text (BT-X-295)."""
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """VAT category code (BT-X-296)."""
    exemption_reason_code: str | None = field(
        default=None, metadata={"tag": "ExemptionReasonCode"}
    )
    """VAT exemption reason code (BT-X-297)."""
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """VAT rate (BT-X-298)."""
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``CalculatedAmount`` (BT-X-293). Carthorse helper — not a BT
    field itself (the XSD encodes it as an attribute, not an
    element)."""


@dataclass(kw_only=True, slots=True)
class AdvancePaymentReferencedDocument(Element):
    """Prepayment-invoice reference on an advance payment (BG-X-85); EXTENDED-only.

    The ``InvoiceSpecifiedReferencedDocument`` of a
    :class:`AdvancePayment` — points at the prepayment / proforma
    invoice that recorded the advance.
    """

    tag: ClassVar[str] = "InvoiceSpecifiedReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Prepayment invoice identifier (BT-X-558)."""
    type_code: TypeCode | None = field(default=None, metadata={"tag": "TypeCode"})
    """Document type code (BT-X-559); UNTDID 1001 — typically
    :attr:`~carthorse.schema.types.TypeCode.T_ProformaInvoice`
    (``"325"``) or
    :attr:`~carthorse.schema.types.TypeCode.T_PrepaymentInvoice`
    (``"386"``)."""
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Prepayment invoice date (BT-X-560, wrapped in BT-X-560-00)."""


@dataclass(kw_only=True, slots=True)
class AdvancePayment(Element):
    """Advance payment / prepayment (BG-X-45); EXTENDED-only.

    Records an amount already paid before the invoice, together with
    the VAT it included and an optional reference to the prepayment
    invoice. ``PaidAmount`` (BT-X-291) reduces the amount still due.

    Field order matches the XSD ``AdvancePaymentType`` sequence:
    ``PaidAmount`` → ``FormattedReceivedDateTime`` →
    ``IncludedTradeTax`` (1..*) → ``InvoiceSpecifiedReferencedDocument``.
    """

    tag: ClassVar[str] = "SpecifiedAdvancePayment"
    profile: ClassVar[Profile] = Profile.EXTENDED

    paid_amount: Decimal = field(metadata={"tag": "PaidAmount", "amount": True})
    """Prepaid amount (BT-X-291)."""
    received_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedReceivedDateTime"}
    )
    """Date the prepayment was received (BT-X-292, wrapped in BT-X-292-00)."""
    included_trade_tax: list[AdvancePaymentTradeTax]
    """VAT included in the prepayment (BG-X-46, 1..* per XSD)."""
    invoice_referenced_document: AdvancePaymentReferencedDocument | None = None
    """Reference to the prepayment invoice (BG-X-85, 0..1)."""
    currency: str | None = None
    """Document currency (BT-5) echoed as ``currencyID`` on
    ``PaidAmount`` (BT-X-291). Carthorse helper — not a BT field
    itself (the XSD encodes it as an attribute, not an element)."""

    def __post_init__(self) -> None:
        # XSD minOccurs=1 on IncludedTradeTax.
        if not self.included_trade_tax:
            raise ValueError(
                "AdvancePayment.included_trade_tax: at least one IncludedTradeTax "
                "entry is required (XSD minOccurs=1)."
            )


@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    """Header trade settlement (BG-19).

    Container for currency, payee, payment means, VAT breakdown,
    invoicing period, header allowances/charges, logistics service
    charges (EXTENDED), payment terms, the monetary summation,
    preceding-invoice references, and accounting references.
    """

    tag: ClassVar[str] = "ApplicableHeaderTradeSettlement"

    _validators: ClassVar[tuple[Validator["TradeSettlement"], ...]] = (
        # EXTENDED-only fields: must be None at lower profiles, lest the
        # render machinery silently drop them.
        fields_only_at(
            Profile.EXTENDED,
            "invoice_issuer_reference",
            "invoicer",
            "invoicee",
            "payer",
            "currency_exchange",
            "logistics_service_charges",
            "advance_payments",
        ),
        # SpecifiedTradePaymentTerms widens from 0..1 (BASIC_WL..COMFORT)
        # to 0..* at EXTENDED — cap the carthorse list to 1 entry below
        # EXTENDED so an over-populated list fails loud rather than
        # tripping XSD validation.
        list_max_cardinality_below(Profile.EXTENDED, max_count=1, field_name="terms"),
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
    invoice_issuer_reference: str | None = field(
        default=None,
        metadata={"tag": "InvoiceIssuerReference", "profile": Profile.EXTENDED},
    )
    """Seller's reference / file number for the invoice (BT-X-204);
    EXTENDED-only."""
    invoicer: InvoicerTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Invoicer party (BG-X-33); EXTENDED-only — the party that
    issued the invoice when different from the Seller."""
    invoicee: InvoiceeTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Invoicee party (BG-X-36); EXTENDED-only — the party the
    invoice is addressed to when different from the Buyer."""
    payee: PayeeTradeParty | None = None
    """Payee (BG-10); BASIC_WL+ — provided when different from the
    Seller."""
    payer: PayerTradeParty | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Payer party (BG-X-73); EXTENDED-only — the party that settles
    the invoice when neither Buyer nor Payee."""
    currency_exchange: TaxCurrencyExchange | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax-accounting-currency conversion (BG-X-41, 0..1); EXTENDED only."""
    payment_means: list[PaymentMeans] | None = None
    """Payment means (BG-16, 0..*); BASIC_WL+."""
    trade_taxes: list[ApplicableTradeTax] | None = None
    """VAT breakdown rows (BG-23, 1..*); required from BASIC_WL+
    (``BR-CO-18``)."""
    billing_period: BillingSpecifiedPeriod | None = None
    """Header invoicing period (BG-14); BASIC_WL+."""
    allowance_charge: list[HeaderTradeAllowanceCharge] | None = None
    """Header allowances (BG-20) and charges (BG-21), 0..*."""
    logistics_service_charges: list[LogisticsServiceCharge] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Logistics service charges (BG-X-42, 0..*); EXTENDED only.

    Each entry sums into BT-108 via
    ``BR-FXEXT-CO-12`` and into its declared VAT category's BG-23 row
    via ``BR-FXEXT-{cat}-08``.
    """
    terms: list[PaymentTerms] | None = None
    """Payment terms (BT-20-00); BASIC_WL+ — singleton list at every
    profile up to and including COMFORT; multiple entries permitted
    only at EXTENDED (XSD widens from ``minOccurs=0`` to
    ``minOccurs=0 maxOccurs=unbounded``). Constructing a list of
    more than one entry at a non-EXTENDED profile renders fine but
    fails XSD validation when checked against the lower-profile
    schemas — exercised by ``test_xsd_validity``.
    """
    monetary_summation: MonetarySummation
    """Document totals (BG-22); required at every profile."""
    invoice_referenced_document: list[InvoiceReferencedDocument] | None = None
    """Preceding-invoice references (BG-3, 0..*); BASIC_WL+."""
    accounting_account: list[ReceivableAccountingAccount] | None = None
    """Buyer accounting references (BT-19-00, 0..*); BASIC_WL+."""
    advance_payments: list[AdvancePayment] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Advance payments / prepayments (BG-X-45, 0..*); EXTENDED-only.

    Each entry's ``PaidAmount`` reduces the amount still due."""
