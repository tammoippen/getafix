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
    """Bankinstitut des Käufers"""

    tag: ClassVar[str] = "PayerPartyDebtorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str = field(metadata={"tag": "IBANID"})
    """Lastschriftverfahren: Kennung des zu belastenden Kontos

    Das durch die Lastschrift zu belastende Konto. Bei Lastschriftzahlung anzugeben

    EN 16931-ID: BG-19/BT-91
    """


@dataclass(kw_only=True, slots=True)
class PayeePartyCreditorFinancialAccount(Element):
    """Überweisung / Bankverbindung des Verkäufers

    Wenn mehrere Bankkonten für die Überweisung angegeben werden sollen, muss das
    Element SpecifiedTradeSettlementPaymentMeans entsprechend wiederholt werden.

    EN 16931-ID: BG-17
    """

    tag: ClassVar[str] = "PayeePartyCreditorFinancialAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    iban_id: str | None = field(default=None, metadata={"tag": "IBANID"})
    """Kennung des Zahlungskontos

    Eine eindeutige Kennung für das bei einem Zahlungsdienstleister geführte Finanzkonto, auf das die Zahlung erfolgen sollte, wie z. B. eine IBAN (im Falle einer SEPA-Zahlung), für eine nationale Kontonummer ProprietaryID nutzen

    In Bezug auf BR-50 und BR-61 muss entweder eine IBAN-ID oder eine ProprietaryID angegeben werden.
    
    EN 16931-ID: BT-84
    """
    proprietary_id: str | None = field(default=None, metadata={"tag": "ProprietaryID"})
    """Nationale Kontonummer (nicht für SEPA)

    Für SEPA-Zahlungen IBANID nutzen

    EN 16931-ID: BT-84-0
    """

    @override
    def validate_internal(self, profile: Profile) -> None:
        if self.iban_id is None and self.proprietary_id is None:
            raise ValidationError(
                "BR-50",
                "Falls in der Rechnung Überweisungsinformationen (BG-17) angegeben sind, muss eine Kennung des Zahlungskontos (BT-84) vorhanden sein.",
            )
        # NOTE: what about both are given?


@dataclass(kw_only=True, slots=True)
class PaymentMeans(Element):
    """Zahlungsanweisungen

    Nur wenn mehrere Bankkonten für Überweisungen übertragen werden sollen,
    kann das Element SpecifiedTradeSettlementPaymentMeans für jedes Bankkonto
    wiederholt werden. Der Code für die Zahlungsart im Element Typecode (BT-81)
    darf sich demzufolge in den Wiederholungen nicht unterscheiden.
    Die Elemente ApplicableTradeSettlementFinancialCard und PayerPartyDebtorFinancialAccount
    dürfen bei Banküberweisungen nicht angegeben werden.

    EN 16931-ID: BG-16
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementPaymentMeans"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    type_code: str = field(metadata={"tag": "TypeCode"})
    """Code für die Zahlungsart / Zahlungstyp

    Das als Code ausgedrückte erwartete oder genutzte Zahlungsmittel.

    Die Einträge aus der UNTDID 4461 Codeliste müssen verwendet werden.
    Es sollte zwischen SEPA- und Nicht-SEPA-Zahlungen unterschieden werden
    sowie zwischen Kreditzahlungen, Lastschriften, Kartenzahlungen und anderen
    Zahlungsmitteln.

    Codeliste: UNTDID 4461:
        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred4461.htm

    Insbesondere können folgende Codes verwendet werden:
        10 : Bargeld
        20 : Scheck
        30 : Überweisung
        42 : Payment to bank account
        48 : Kartenzahlung
        49 : Lastschrift
        57 : Dauerauftrag
        58 : SEPA Credit Transfer
        59 : SEPA Direct Debit
        97 : Report

    EN 16931-ID: BT-81
    """
    payer: PayerPartyDebtorFinancialAccount | None = None
    payee: PayeePartyCreditorFinancialAccount | None = None

    @override
    def validate_internal(self, profile: Profile) -> None:
        if not (
            len(self.type_code) <= 3
            and (self.type_code.isdigit() or self.type_code == "ZZZ")
        ):
            raise ValidationError(
                "UNTDID-4461",
                f"Given TypeCode='{self.type_code}' cannot be a UNTDID-4461: 1-97 and ZZZ",
            )


@dataclass(kw_only=True, slots=True)
class PaymentTerms(Element):
    """Detailinformationen zu Zahlungsbedingungen.

    XSD field order is ``Description`` (BT-20), ``DueDateDateTime``
    (BT-9), ``DirectDebitMandateID`` (BT-89).

    EN 16931-ID: BT-20-00
    """

    tag: ClassVar[str] = "SpecifiedTradePaymentTerms"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    description: str | None = field(default=None, metadata={"tag": "Description"})
    """Free-text payment terms (BT-20)."""
    due: date | None = field(default=None, metadata={"tag": "DueDateDateTime"})
    """Fälligkeitsdatum (BT-9)."""
    debit_mandate_id: str | None = field(
        default=None, metadata={"tag": "DirectDebitMandateID"}
    )
    """Kennung der Mandatsreferenz / Mandatsreferenz für SEPA.

    Wird verwendet, um den Käufer vorweg über eine SEPA-Lastschrift in
    Kenntnis zu setzen.

    EN 16931-ID: BT-89
    """


@dataclass(kw_only=True, slots=True)
class BillingSpecifiedPeriod(Element):
    """Invoicing period (BG-14 / BG-26) — start and/or end dates.

    The element name is ``BillingSpecifiedPeriod`` at both header
    (BG-14) and line (BG-26) level. The XSD allows either or both
    endpoints; ``BR-CO-19`` requires at least one of them when the
    group is used, and ``BR-29`` requires ``end >= start`` if both
    are given.

    EN 16931-ID: BG-14 (header), BG-26 (line)
    """

    tag: ClassVar[str] = "BillingSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    start: date | None = field(
        default=None, metadata={"tag": "StartDateTime", "profile": Profile.BASIC_WL}
    )
    """Start of the invoicing period.

    EN 16931-ID: BT-73 (header), BT-134 (line)
    """
    end: date | None = field(
        default=None, metadata={"tag": "EndDateTime", "profile": Profile.BASIC_WL}
    )
    """End of the invoicing period.

    EN 16931-ID: BT-74 (header), BT-135 (line)
    """

    @override
    def validate_internal(self, profile: Profile) -> None:
        if self.start is None and self.end is None:
            raise ValidationError(
                "BR-CO-19",
                "Wenn die Rechnungsperiode (BG-14) verwendet wird, muss mindestens "
                "eines der beiden Felder Start (BT-73) oder End (BT-74) ausgefüllt "
                "sein.",
            )
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValidationError(
                "BR-29",
                "Falls beide Daten angegeben sind, muss das Endedatum (BT-74) größer "
                "oder gleich dem Startdatum (BT-73) sein.",
            )


@dataclass(kw_only=True, slots=True)
class ReceivableAccountingAccount(Element):
    """Detailinformationen zur Buchungsreferenz"""

    tag: ClassVar[str] = "ReceivableSpecifiedTradeAccountingAccount"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: str = field(metadata={"tag": "ID"})
    """Buchungsreferenz des Käufers

    Ein Textwert, der angibt, an welcher Stelle die betreffenden Daten in den
    Finanzkonten des Käufers zu verbuchen sind.

    EN 16931-ID: BG-19
    """


@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    """Gruppierung von Angaben zur Zahlung und Rechnungsausgleich"""

    tag: ClassVar[str] = "ApplicableHeaderTradeSettlement"

    currency_code: str = field(metadata={"tag": "InvoiceCurrencyCode"})
    """Code für die Rechnungswährung

    Die Währung, in der alle Rechnungsbeträge angegeben werden, ausgenommen ist
    Steuergesamtbetrag in Buchungswährung.

    Die Rechnung ist in nur einer Währung auszustellen, ausgenommen hiervon ist
    nach Artikel 230 der Richtlinie 2006/112/EG über Umsatzsteuer der Steuergesamtbetrag
    in Buchungswährung (BT-111).
    Die Listen der zugelassenen Währungen werden von der ISO 4217 Maintenance Agency
    „Codes for the representation of currencies and funds” geführt.

    EN 16931-ID: BT-5
    """
    tax_currency_code: str | None = field(
        default=None, metadata={"tag": "TaxCurrencyCode", "profile": Profile.BASIC_WL}
    )
    """VAT accounting currency code.

    Optional from BASIC_WL onwards. When present, the seller's local
    currency for VAT accounting (which differs from the invoice
    currency BT-5). Triggers ``BR-53``: a ``TaxTotal`` entry with
    ``currency_id == tax_currency_code`` (BT-111) must also be
    provided in :attr:`monetary_summation`.

    EN 16931-ID: BT-6
    """
    monetary_summation: MonetarySummation
    creditor_reference: str | None = field(
        default=None,
        metadata={"tag": "CreditorReferenceID", "profile": Profile.BASIC_WL},
    )
    """Kennung des Gläubigers / Gläubiger-ID für SEPA

    Eindeutige Bankverbindungskennung des Zahlungsempfängers oder des Verkäufers,
    die von der Bank des Zahlungsempfängers oder des Verkäufers zugewiesen wird

    Wird verwendet, um den Käufer vorweg über eine SEPA-Lastschrift in Kenntnis zu setzen.

    EN 16931-ID: BG19/BT-90
    """
    payment_reference: str | None = field(
        default=None, metadata={"tag": "PaymentReference", "profile": Profile.BASIC_WL}
    )
    """Verwendungszweck / Kassenzeichen

    Ein Textwert, der zur Verknüpfung der Zahlung mit der vom Verkäufer
    ausgestellten Rechnung verwendet wird.

    Diese Referenz hilft dem Verkäufer, eine eingehende Zahlung dem betreffenden
    Zahlungsprozess zuzuordnen. Bei der Angabe des Textwertes, bei dem es sich
    üblicherweise um die Rechnungs-nummer der zu zahlenden Rechnung handelt,
    aber auch eine andere Verkäuferreferenz sein darf, sollte der Käufer diese
    Referenz in seinem Zahlungsauftrag oder bei Durchführung der Zahlung angeben.
    Bei einem Zahlungsvorgang wird diese Referenz dem Verkäufer als
    Überweisungsinformation zurückübermittelt.

    Um eine automatische Verarbeitung von grenzüberschreitenden SEPA-Zahlungen zu
    ermöglichen, sollten in diesem Feld ausschließlich lateinische Schriftzeichen
    und maximal 140 Zeichen verwendet werden. Siehe 1.4 der SEPA Credit Transfer
    und der SEPA Direct Debit Scheme Implementation Guides für weitere Angaben
    zu den zulässigen Schriftzeichen. Gegebenenfalls gelten für SEPA-Zahlungen
    innerhalb von Landesgrenzen andere Regeln.

    Ist die Überweisungsinformation nach ISO 11649:2009 über die strukturierte
    Referenz des Zahlungsempfängers strukturiert, so muss diese in SEPA-Zahlungsnachrichten
    dem Feld Structured Remittance Information Creditor Reference zugeordnet werden.

    Ist die Überweisungsinformation nach EACT-Norm für automatische Kontenabstimmung
    strukturiert, so muss diese in SEPA-Zahlungsnachrichten dem Feld Unstructured
    Remittance Information zugeordnet werden.

    Ist die Überweisungsinformation in SEPA-Zahlungsnachrichten dem Feld End To
    End Identification oder dem Feld Structured Remittance Information Creditor
    Reference zuzuordnen, darf der Inhalt, abgesehen von der Einschränkung auf
    lateinische Schriftzeichen, nicht mit einem ,/' beginnen oder enden und
    keine ,//' beinhalten.

    Im einfachsten Fall könnte dies zum Beispiel identisch mit der Rechnungsnummer sein.
    Hinweis: Soll die Zahlungsreferenz in SEPA-Überweisungen bzw. Lastschriften
    angegeben werden , darf nur der für SEPA erlaubte Zeichensatz verwendet werden.

    EN 16931-ID: BT-83
    """
    payee: PayeeTradeParty | None = None
    payment_means: list[PaymentMeans] | None = None
    trade_taxes: list[ApplicableTradeTax] | None = None
    billing_period: BillingSpecifiedPeriod | None = None
    """Header invoicing period (BG-14)."""
    allowance_charge: list[TradeAllowanceCharge] | None = None
    terms: PaymentTerms | None = None
    invoice_referenced_document: list[InvoiceReferencedDocument] | None = None
    """Preceding invoice references (BG-3); zero or more."""
    accounting_account: list[ReceivableAccountingAccount] | None = None

    @override
    def validate_internal(self, profile: Profile) -> None:
        if (
            len(self.currency_code) != 3
            or not self.currency_code.isalpha()
            or self.currency_code.upper() != self.currency_code
        ):
            raise ValueError(
                f"CurrencyID cannot be alpha-3 ISO 4217: {self.currency_code}"
            )

        if Profile.BASIC_WL <= profile and bool(self.trade_taxes) is False:
            raise ValidationError(
                "BR-CO-18",
                "Eine Rechnung muss mindestens eine Umsatzsteueraufschlüsselungsgruppe (BG-23) haben.",
            )

        if self.tax_currency_code is not None:
            tax_totals = self.monetary_summation.tax_total or []
            if not any(t.currency_id == self.tax_currency_code for t in tax_totals):
                raise ValidationError(
                    "BR-53",
                    "Falls der Code für die Währung der Umsatzsteuerbuchung "
                    "(BT-6) vorhanden ist, muss der Steuergesamtbetrag in "
                    "Buchungswährung (BT-111) angegeben werden.",
                )

        # BR-CO-25: positive DuePayableAmount (BT-115) requires either a
        # payment due date (BT-9) or payment terms description (BT-20).
        if self.monetary_summation.due_amount > 0 and (
            self.terms is None
            or (self.terms.due is None and self.terms.description is None)
        ):
            raise ValidationError(
                "BR-CO-25",
                "Wenn der fällige Zahlungsbetrag (BT-115) positiv ist, müssen "
                "entweder das Fälligkeitsdatum der Zahlung (BT-9) oder die "
                "Zahlungsbedingungen (BT-20) angegeben sein.",
            )

        super(TradeSettlement, self).validate_internal(profile)
