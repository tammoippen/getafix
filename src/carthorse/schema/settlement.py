from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.party import PayeeTradeParty
from carthorse.schema.references import InvoiceReferencedDocument
from carthorse.schema.types import Profile

# TODO:
# BR-CO-10 Gesamtsummen auf Dokumentenebene
# Summe der Nettobeträge aller Rechnungspositionen (BT-106) = Summe Nettobeträge der Rechnungsposition (BT-131).
# BR-CO-13 Gesamtsummen auf Dokumentenebene
# Rechnungsgesamtbetrag ohne Umsatzsteuer (BT-109) = Summe Nettobeträge der Rechnungsposition (BT-131) - Summe der Abschläge auf Dokumentenebene (BT-107) + Summe der Zuschläge auf Dokumentenebene (BT-108).
# BR-CO-15 Gesamtsummen auf Dokumentenebene
# Rechnungsgesamtbetrag einschließlich Umsatzsteuer (BT-112) = Rechnungsgesamtbetrag ohne Umsatzsteuer (BT-109) + Gesamtbetrag der Rechnungsumsatzsteuer (BT-110).
# BR-CO-16 Gesamtsummen auf Dokumentenebene
# Fälliger Zahlungsbetrag (BT-115) = Gesamtbetrag der Rechnungsumsatzsteuer (BT-112) - Vorauszahlungsbetrag (BT-113) + Rundungsbetrag (BT-114).
# BR-53 Gesamtsummen auf Dokumentenebene
# Falls der Code für die Währung der Umsatzsteuerbuchung (BT-6) vorhanden ist, muss der Steuergesamtbetrag in Buchungswährung (BT-111) angegeben werden.
# BR-CO-14 Gesamtsummen auf Dokumentenebene
# Gesamtbetrag der Rechnungsumsatzsteuer (BT-110) = ?  kategoriespezifische Steuerbeträge (BT-117).
# BR-61 Zahlungsanweisungen
# Ist der Zahlungsmitteltyp (BT-81) eine SEPA-Überweisung, eine örtliche Überweisung oder eine internationale Überweisung ohne SEPA, muss die Kennung des Zahlungskontos (BT-84) angegeben werden.


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
class TaxTotal(Element):
    """Gesamtbetrag der Rechnungsumsatzsteuer / Steuergesamtbetrag in Buchungswährung / Steuergesamtbetrag

    Der Gesamtbetrag der Umsatzsteuer für die Rechnung.

    Der Steuergesamtbetrag in Buchungswährung, die im Land des Verkäufers gültig
    ist oder verlangt wird.

    Der Gesamtbetrag der Rechnungsumsatzsteuer ist die Summe aller Beträge für
    die einzelnen Umsatzsteuerkategorien.

    Zu verwenden, wenn der Code für die Währung der Umsatzsteuerbuchung (BT-6) nach
    Artikel 230 der Richtlinie 2006/112/EG über Umsatzsteuer vom Code für die
    Rechnungswährung (BT-5) abweicht.
    Der Steuergesamtbetrag in Buchungswährung wird bei der Berechnung der
    Rechnungssummen nicht berücksichtigt.

    EN 16931-ID: BT-110, BT-111
    """

    tag: ClassVar[str] = "TaxTotalAmount"

    amount: Decimal
    """Der Gesamtbetrag der Rechnungsumsatzsteuer ist die Summe aller Beträge
    für die einzelnen Umsatzsteuerkategorien.
    """
    currency_id: str
    """Währung der Umsatzsteuer

    Die Angabe von currencyID ist erforderlich, um zwischen dem Steuerbetrag
    in Belegwährung und dem Steuerbetrag in Buchwährung zu unterscheiden.

    Code Liste: ISO 4217 Nur die alphabetische Darstellung darf verwendet werden.
    Beispiel: EUR, USD

    EN 16931-ID: BT-110-0, BT-111-0
    """

    @override
    def validate_internal(self, profile: Profile) -> None:
        if (
            len(self.currency_id) != 3
            or not self.currency_id.isalpha()
            or self.currency_id.upper() != self.currency_id
        ):
            raise ValueError(
                f"CurrencyID cannot be alpha-3 ISO 4217: {self.currency_id}"
            )

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), attrs={"currencyID": self.currency_id})[
            str(self.amount)
        ]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "currencyID" not in elem.attrib:
            raise ValueError
        if elem.text is None:
            raise ValueError
        currency_id = elem.attrib["currencyID"]
        value = elem.text.strip()
        return cls(amount=Decimal(value), currency_id=currency_id)


@dataclass(kw_only=True, slots=True)
class MonetarySummation(Element):
    """Gesamtsummen auf Dokumentenebene / Detailinformationen zu Belegsummen

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die die monetären
    Gesamtsummen der Rechnung enthält

    EN 16931-ID: BG-22
    """

    tag: ClassVar[str] = "SpecifiedTradeSettlementHeaderMonetarySummation"

    line_total: Decimal = field(metadata={"tag": "LineTotalAmount"})
    """Summe der Nettobeträge aller Rechnungspositionen

    EN 16931-ID: BT-106
    """
    tax_basis_total: Decimal = field(metadata={"tag": "TaxBasisTotalAmount"})
    """Rechnungsgesamtbetrag ohne Umsatzsteuer

    Die Gesamtsumme der Rechnung ohne Umsatzsteuer. Der Rechnungsgesamtbetrag ohne
    Umsatzsteuer ist die Summe der Rechnungspositions-Nettobeträge abzüglich der
    Summe der Zuschläge auf Dokumentenebene zuzüglich der Summe der Abschläge der
    Dokumentenebene.

    EN 16931-ID: BT-109
    """
    tax_total: TaxTotal
    grand_total: Decimal = field(metadata={"tag": "GrandTotalAmount"})
    """Rechnungsgesamtbetrag einschließlich Umsatzsteuer / Bruttosumme

    Der Rechnungsgesamtbetrag einschließlich Umsatzsteuer ist der Rechnungsgesamtbetrag
    ohne Umsatzsteuer zuzüglich des Gesamtbetrages der Rechnungsumsatzsteuer.

    EN 16931-ID: BT-112
    """
    due_amount: Decimal = field(metadata={"tag": "DuePayableAmount"})
    """Fälliger Zahlungsbetrag / Zahlbetrag

    Der ausstehende Betrag, um dessen Zahlung gebeten wird.

    Dieser Betrag ist der Rechnungsgesamtbetrag einschließlich Umsatzsteuer
    abzüglich des im Voraus gezahlten Betrages. Im Falle einer vollständig
    beglichenen Rechnung ist dieser Betrag gleich null. Der Betrag kann negativ
    sein; in diesem Fall schuldet der Verkäufer dem Käufer den Betrag.

    Bei geleisteten Anzahlungen kann dieser vom Rechnungsendbetrag abweichen.

    EN 16931-ID: BT-115
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
    invoice_referenced_document: InvoiceReferencedDocument | None = None

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
