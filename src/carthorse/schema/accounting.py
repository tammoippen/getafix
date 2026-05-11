"""Monetary totals and VAT breakdown.

Owns the four BG groups that make up the financial spine of an invoice:

* ``BG-22 SpecifiedTradeSettlementHeaderMonetarySummation`` — the
  rectangular "totals" block at the bottom of the invoice. Eight
  amounts: line total, charge total, allowance total, tax basis total,
  tax total (one or two — invoice currency, optionally accounting
  currency), grand total, prepaid total, due-payable amount.
* ``BG-23 ApplicableTradeTax`` — one row per VAT category / rate
  combination. Required at BASIC_WL+ (``BR-CO-18``).
* ``BG-20 SpecifiedTradeAllowanceCharge[indicator=false]`` (Abschlag /
  allowance) and ``BG-21 SpecifiedTradeAllowanceCharge[indicator=true]``
  (Zuschlag / charge). Same shape, same dataclass; the
  ``ChargeIndicator`` is what tells them apart.
* ``CategoryTradeTax`` — the embedded VAT category block on each
  allowance / charge.

Validation rules covered (or missing) in this module:

* ✓ ``BR-CO-18`` (at least one BG-23 ≥ BASIC_WL) — in
  ``settlement.py``.
* ✓ ``BR-CO-21`` / ``BR-CO-22`` — allowance/charge requires reason or
  reason code, in :class:`TradeAllowanceCharge.validate_internal`.
* △ ``BR-5`` — ``TaxTotal.currency_id`` shape only.
* — ``BR-12`` (BT-106 required ≥ BASIC_WL): :class:`MonetarySummation`
  treats ``line_total`` as optional and gates it on ``>= BASIC_WL`` for
  rendering, but does not yet *require* it at BASIC_WL+.
* ✓ ``BR-CO-3`` (BT-7 vs BT-8 mutually exclusive) —
  :meth:`ApplicableTradeTax.validate_internal`.
* — ``BR-CO-10..17`` (sum identities): need line items.
* — ``BR-53`` (BT-6 ⇒ BT-111): needs multi-``TaxTotal`` model
  (``§1 #6``).
* — ``BR-48`` (rate required unless not-subject-to-VAT): not enforced.

For the per-VAT-category ``BR-AE/BR-E/BR-G/BR-IC/BR-IG/BR-IP/BR-O/
BR-S/BR-Z`` rule families and the EXTENDED ``BR-FXEXT-*`` rounding-
tolerance variants, see ``docs/VALIDATION.md``.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.types import CategoryCode, Profile


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

    line_total: Decimal | None = field(
        default=None, metadata={"tag": "LineTotalAmount", "profile": Profile.BASIC_WL}
    )
    """Summe der Nettobeträge aller Rechnungspositionen.

    Optional in carthorse: the MINIMUM profile XSD does not include
    ``LineTotalAmount`` at all. From BASIC_WL onwards the field is
    expected per ``BR-12``; that rule isn't yet enforced here.

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
    tax_total: list[TaxTotal] | None = None
    """``ram:TaxTotalAmount`` — the row of currency-tagged VAT totals.

    Up to two entries per the XSD: BT-110 carries the VAT total in
    invoice currency (``currencyID == BT-5``), BT-111 carries the same
    amount expressed in the seller's VAT accounting currency
    (``currencyID == BT-6``) and is required when ``BT-6`` is set
    (``BR-53``). MINIMUM permits at most one entry; from BASIC_WL
    onwards both may appear in that order.

    ``BR-53`` is not yet enforced.

    EN 16931-ID: BT-110, BT-111
    """
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
    charge_total: Decimal | None = field(
        default=None, metadata={"tag": "ChargeTotalAmount", "profile": Profile.BASIC_WL}
    )
    """Summe der Zuschläge auf Dokumentenebene

    Summe aller in der Rechnung enthaltenen Zuschläge der Dokumentenebene.

    Zuschläge der Positionsebene sind in den Gesamtpositionsbeträgen enthalten,
    die addiert werden, um den Gesamtnettobetrag der Positionen zu erhalten.

    EN 16931-ID: BT-108
    """
    allowance_total: Decimal | None = field(
        default=None,
        metadata={"tag": "AllowanceTotalAmount", "profile": Profile.BASIC_WL},
    )
    """Summe der Abschläge auf Dokumentenebene

    Summe aller in der Rechnung enthaltenen Abschläge der Dokumentenebene.

    Abschläge auf der Positionsebene sind in den Gesamtpositionsbeträgen enthalten,
    die addiert werden, um den Gesamtnettobetrag der Positionen zu erhalten.

    EN 16931-ID: BT-107
    """
    prepaid_total: Decimal | None = field(
        default=None,
        metadata={"tag": "TotalPrepaidAmount", "profile": Profile.BASIC_WL},
    )
    """Vorauszahlungsbetrag / Anzahlungsbetrag

    Die Summe der im Voraus gezahlten Beträge

    Dieser Betrag wird vom Rechnungsgesamtbetrag einschließlich Umsatzsteuer
    subtrahiert, um den fälligen Zahlungsbetrag zu berechnen.

    EN 16931-ID: BT-113
    """


@dataclass(kw_only=True, slots=True)
class ApplicableTradeTax(Element):
    """Umsatzsteueraufschlüsselung / Detailinformationen zu Steuerangaben

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    die Umsatzsteueraufschlüsselung in verschiedene Kategorien, Sätze und
    Befreiungsgründe enthält

    EN 16931-ID: BG-23
    """

    tag: ClassVar[str] = "ApplicableTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    calculated_amount: Decimal | None = field(
        default=None, metadata={"tag": "CalculatedAmount"}
    )
    """Kategoriespezifischer Steuerbetrag

    Der für die betreffende Umsatzsteuerkategorie zu entrichtende Gesamtbetrag.

    Wird durch Multiplikation des nach der Umsatzsteuerkategorie zu versteuernden
    Betrages mit dem für die betreffende Umsatzsteuerkategorie geltenden
    Umsatzsteuersatz berechnet.

    EN 16931-ID: BT-117
    """
    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """Code der Umsatzsteuerkategorie

    In der EN 16931 wird nur die Steuerart „Umsatzsteuer“ mit dem Code „VAT“ unterstützt.

    Sollen andere Steuerarten angegeben wie beispielsweise eine Versicherungssteuer
    oder eine Mineralölsteuer werden, muss das EXTENDED Profil genutzt werden. Der
    Code für die Steuerart muss dann der Codeliste UNTDID 5153 entnommen werden.

    Codeliste: UNTDID 5153

    EN 16931-ID: BT-118-0
    """
    basis_amount: Decimal | None = field(default=None, metadata={"tag": "BasisAmount"})
    """Steuerbasisbetrag

    EN 16931-ID: BT-116
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """Codierte Bezeichnung einer Umsatzsteuerkategorie

    Folgende Einträge aus UNTDID 5305 werden verwendet (nähere Angaben in Klammern):
    — (S) Normalsatz (Umsatzsteuer fällt nach Normalverfahren an);
    — (Z) nach dem Nullsatz zu versteuernde Waren (Umsatzsteuer fällt mit einem Prozentsatz von null an);
    — (E) steuerbefreit (USt./IGIC/IPSI);
    — (AE) Umkehrung der Steuerschuldnerschaft (es gelten die Regeln zur Umkehrung der Steuerschuldnerschaft bei USt./IGIC/IPSI);
    — (K) umsatzsteuerumsatzsteuerbefreit für innergemeinschaftliche Warenlieferungen (USt./IGIC/IPSI nicht erhoben aufgrund von Regeln zu innergemeinschaftlichen Lieferungen);
    — (G) freier Ausfuhrartikel, Steuer nicht erhoben (USt./IGIC/IPSI nicht erhoben aufgrund von Export außerhalb der EU);
    — (O) Dienstleistungen außerhalb des Steueranwendungsbereichs (Verkauf unterliegt nicht der USt./IGIC/IPSI);
    — (L) allgemeine indirekte Steuer der Kanarischen Inseln (IGIC-Steuer fällt an);
    — (M) IPSI (Steuer für Ceuta/Melilla) fällt an.

    Codeliste UNTID 5305

    EN 16931-ID: BT-118
    """
    exemption_reason: str | None = field(
        default=None, metadata={"tag": "ExemptionReason"}
    )
    """Grund der Steuerbefreiung (Freitext)

    EN 16931-ID: BT-120
    """
    exemption_reason_code: str | None = field(
        default=None, metadata={"tag": "ExemptionReasonCode"}
    )
    """Code für den Umsatzsteuerbefreiungsgrund

    In Codeform angegebener Grund für die Befreiung des Betrages von der Umsatzsteuerpflicht

    Codeliste VATEX

    EN 16931-ID: BT-121
    """
    tax_point_date: date | None = field(
        default=None, metadata={"tag": "TaxPointDate", "profile": Profile.COMFORT}
    )
    """Tax point date (BT-7).

    The date on which VAT becomes accountable for the Seller and the
    Buyer, when this differs from the invoice issue date. Mutually
    exclusive with :attr:`due_date_code` (BT-8) per ``BR-CO-3``.

    First permitted from EN 16931 / COMFORT onwards.

    EN 16931-ID: BT-7
    """
    due_date_code: str | None = field(default=None, metadata={"tag": "DueDateTypeCode"})
    """Code für das Datum der Steuerfälligkeit

    Der Code für das Datum, zu dem die Umsatzsteuer für den Verkäufer und für den Käufer abrechnungsrelevant wird

    Der Code muss zwischen den folgenden Einträgen aus UNTDID 2005 unterscheiden:
        - Ausstellungsdatum des Rechnungsdokuments;
        - tatsächliches Lieferdatum;
        - Datum der Zahlung.
    Der Code für das Steuererhebungsdatum für umsatzsteuerliche Zwecke wird
    verwendet, wenn das Steuererhebungsdatum für umsatzsteuerliche Zwecke bei
    Ausstellung der Rechnung nicht bekannt ist. Die Verwendung von BT-8 und BT-7
    schließt sich gegenseitig aus.

    Die in der Norm zitierten semantischen Werte, die durch die Werte 3, 35, 432
    in UNTDID2005 repräsentiert werden, werden auf die folgenden Werte von
    UNTDID2475 abgebildet, das ist die von CII 16B unterstützte relevante Codeliste:

    - 5: Ausstellungsdatum des Rechnungsbelegs
    - 29: Liefertermin, Ist-Zustand
    - 72: Bis heute bezahlt

    In Deutschland ist das Liefer- und Leistungsdatum maßgebend (BT-72)
    SupplyChainTradeTransaction/ApplicableHeaderTradeDelivery/
    ActualDeliverySupplyChainEvent/OccurrenceDateTime/DateTimeString).

    Codeliste: UNTDID 2475 (Untermenge)

        https://service.unece.org/trade/untdid/d96a/uncl/uncl2475.htm

    EN 16931-ID: BT-8
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """Kategoriespezifischer Umsatzsteuersatz / Steuerprozentsatz

    Der Umsatzsteuersatz, angegeben als für die betreffende Umsatzsteuerkategorie geltender Prozentsatz.
    Der Code der Umsatzsteuerkategorie und der kategoriespezifische Umsatzsteuersatz müssen einander entsprechen.

    Der anzugebende Wert ist der Prozentsatz. Zum Beispiel wird für 20% der
    Wert 20 amgegeben (und nicht 0.2)

    EN 16931-ID: BT-119
    """

    @override
    def validate_internal(self, profile: Profile) -> None:
        if self.type_code != "VAT" and self.profile != Profile.EXTENDED:
            raise ValidationError(
                "TypeCode",
                "TypeCodes other than VAT for BT-118-0 are only allowed in the EXTENDED profile.",
            )
        # BR-CO-3: BT-7 (TaxPointDate) and BT-8 (DueDateTypeCode) are
        # mutually exclusive on a single ApplicableTradeTax.
        if self.tax_point_date is not None and self.due_date_code is not None:
            raise ValidationError(
                "BR-CO-3",
                "Das Datum der Steuerfälligkeit (BT-7) und der Code für "
                "das Datum der Steuerfälligkeit (BT-8) schließen sich "
                "gegenseitig aus.",
            )
        # If BT-8 is supplied, it must follow UNTDID 2475 (digits or ZZZ,
        # max 3 chars). When absent — BR-CO-3 leaves the slot to BT-7,
        # or both may be omitted entirely.
        if self.due_date_code is not None and not (
            len(self.due_date_code) <= 3
            and (self.due_date_code.isdigit() or self.due_date_code == "ZZZ")
        ):
            raise ValueError(f"DueDateCode cannot be UNTDID 2475: {self.due_date_code}")

        # BR-CO-17: BT-117 = round(BT-116 * BT-119 / 100, 2). Dropped at
        # EXTENDED (the per-VAT-category BR-FXEXT-*-09 family supersedes
        # it). Skip when the rate is absent (e.g. category 'O').
        if (
            profile < Profile.EXTENDED
            and self.rate_applicable_percent is not None
            and self.basis_amount is not None
            and self.calculated_amount is not None
        ):
            expected = (
                self.basis_amount * self.rate_applicable_percent / Decimal("100")
            ).quantize(Decimal("0.01"))
            if self.calculated_amount.quantize(Decimal("0.01")) != expected:
                raise ValidationError(
                    "BR-CO-17",
                    f"BT-117 (CalculatedAmount) = {self.calculated_amount} "
                    f"weicht von round(BT-116 * BT-119 / 100, 2) "
                    f"= round({self.basis_amount} * "
                    f"{self.rate_applicable_percent} / 100, 2) "
                    f"= {expected} ab.",
                )


@dataclass(kw_only=True, slots=True)
class CategoryTradeTax(Element):
    """Detailinformationen zu Steuerangaben"""

    tag: ClassVar[str] = "CategoryTradeTax"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    type_code: str = field(default="VAT", metadata={"tag": "TypeCode"})
    """Code für die Umsatzsteuerkategorie des Zu- oder Abschlages auf Dokumentenebene

    In der EN 16931 wird nur die Steuerart „Umsatzsteuer“ mit dem Code „VAT“ unterstützt.

    Sollen andere Steuerarten angegeben wie beispielsweise eine Versicherungssteuer
    oder eine Mineralölsteuer werden, muss das EXTENDED Profil genutzt werden. Der
    Code für die Steuerart muss dann der Codeliste UNTDID 5153 entnommen werden.

    Codeliste: UNTDID 5153

    EN 16931-ID: BT-95-0 (Abschlag), BT-102-0 (Zuschlag)
    """
    category_code: CategoryCode = field(metadata={"tag": "CategoryCode"})
    """Code für die Umsatzsteuerkategorie des Zu- oder Abschlages auf Dokumentenebene

    Folgende Einträge aus UNTDID 5305 werden verwendet (nähere Angaben in Klammern):

    — (S) Normalsatz (Umsatzsteuer fällt nach Normalverfahren an);
    — (Z) nach dem Nullsatz zu versteuernde Waren (Umsatzsteuer fällt mit einem Prozentsatz von null an);
    — (E) steuerbefreit (USt./IGIC/IPSI);
    — (AE) Umkehrung der Steuerschuldnerschaft (es gelten die Regeln zur Umkehrung der Steuerschuldnerschaft bei USt./IGIC/IPSI);
    — (K) umsatzsteuerumsatzsteuerbefreit für innergemeinschaftliche Warenlieferungen (USt./IGIC/IPSI nicht erhoben aufgrund von Regeln zu innergemeinschaftlichen Lieferungen);
    — (G) freier Ausfuhrartikel, Steuer nicht erhoben (USt./IGIC/IPSI nicht erhoben aufgrund von Export außerhalb der EU);
    — (O) Dienstleistungen außerhalb des Steueranwendungsbereichs (Verkauf unterliegt nicht der USt./IGIC/IPSI);
    — (L) allgemeine indirekte Steuer der Kanarischen Inseln (IGIC-Steuer fällt an);
    — (M) IPSI (Steuer für Ceuta/Melilla) fällt an.

    Codeliste UNTID 5305

    EN 16931-ID: BT-95 (Abschlag), BT-102 (Zuschlag)
    """
    rate_applicable_percent: Decimal | None = field(
        default=None, metadata={"tag": "RateApplicablePercent"}
    )
    """Umsatzsteuersatz für den Zu- oder Abschlag auf Dokumentenebene

    Der für den Zu- oder Abschlag auf Dokumentenebene geltende und in Prozent
    angegebene Umsatzsteuersatz.

    Der anzugebende Wert ist der Prozentsatz. Zum Beispiel wird für 20% der
    Wert 20 angegeben (und nicht 0.2).

    EN 16931-ID: BT-96 (Abschlag), BT-103 (Zuschlag)
    """

    @override
    def validate_internal(self, profile: Profile) -> None:
        if self.type_code != "VAT" and self.profile != Profile.EXTENDED:
            raise ValidationError(
                "TypeCode",
                "TypeCodes other than VAT for BT-95-0 / BT-102-0 are only allowed in the EXTENDED profile.",
            )


@dataclass(kw_only=True, slots=True)
class TradeAllowanceCharge(Element):
    """Zu- und Abschläge auf Dokumentenebene

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    Zu- und Abschläge enthält, die für die Rechnung als Ganzes gelten. Abzüge,
    wie z. B. für einbehaltene Steuern, dürfen ebenfalls in dieser Gruppe
    angegeben werden.

    EN 16931-ID: BG-20 (Abschlag), BG-21 (Zuschlag)
    """

    tag: ClassVar[str] = "SpecifiedTradeAllowanceCharge"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    indicator: bool = field(metadata={"tag": "ChargeIndicator"})
    """Schalter für Zu-/Abschlag

    Schalter, der angibt, ob die nachfolgenden Daten sich auf einen Zu- oder
    Abschlag beziehen.

    - Im Fall eine Abschlags (BG-27) ist der Wert des ChargeIndicators auf "false" zu setzen.
    - Im Fall eine Zuschlags (BG-28) ist der Wert des ChargeIndicators auf "true" zu setzen.

    EN 16931-ID: BG-20-0, BG-21-0, BG-20-00, BG-21-00
    """
    actual_amount: Decimal = field(metadata={"tag": "ActualAmount"})
    """Betrag des Zu- oder Abschlags auf Dokumentenebene

    Der Betrag eines Zu- oder Abschlags ohne Umsatzsteuer.

    EN 16931-ID: BT-92 (Abschlag), BT-99 (Zuschlag)
     """
    category_trade_tax: CategoryTradeTax | None = None
    """VAT category for the allowance / charge (BT-95-00 / BT-102-00).

    Required at BASIC_WL per the appendix narrative; from BASIC the
    XSD makes it optional. carthorse keeps it ``Optional`` so the
    same dataclass works at every profile.
    """
    calculation_percent: Decimal | None = field(
        default=None,
        metadata={"tag": "CalculationPercent", "profile": Profile.BASIC_WL},
    )
    """Prozentualer Zu- oder Abschlag auf Dokumentenebene

    Der Prozentsatz, der in Verbindung mit dem Grundbetrag des Zu- oder Abschlages
    auf Dokumentenebene zur Berechnung des Betrags des Abschlages auf Dokumentenebene
    verwendet werden darf.

    Bis zum Level COMFORT wird nur das Endergebnis der Rabattierung
    (Actual.Amount) übertragen.

    EN 16931-ID: BT-94 (Abschlag), BT-101 (Zuschlag)
    """
    basis_amount: Decimal | None = field(
        default=None, metadata={"tag": "BasisAmount", "profile": Profile.BASIC_WL}
    )
    """Grundbetrag des Zu- oder Abschlags auf Dokumentenebene

    Der Grundbetrag, der in Verbindung mit dem Prozentsatz des Zu- oder
    Abschlages auf Dokumentenebene zur Berechnung des Betrags des Abschlages
    auf Dokumentenebene verwendet werden darf.

    EN 16931-ID: BT-93 (Abschlag), BT-100 (Zuschlag)
    """
    reason: str | None = field(default=None, metadata={"tag": "Reason"})
    """Grund für den Zu- oder Abschlag auf Dokumentenebene

    Der in Textform angegebene Grund für den Zu- oder Abschlag auf Dokumentenebene.

    EN 16931-ID: BT-97 (Abschlag), BT-104 (Zuschlag)
    """
    reason_code: str | None = field(default=None, metadata={"tag": "ReasonCode"})
    """Code für den Grund für den Zu- oder Abschlag auf Dokumentenebene

    Einträge aus der UNTDID 5189 Codeliste verwenden. Der Code des Grundes für
    den Zu- oder Abschlag auf Dokumentenebene und der Grund für den Zu- oder
    Abschlag auf Dokumentenebene müssen einander entsprechen.

    Codelisten: UNTDID 5189

        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5189.htm

    EN 16931-ID: BT-98 (Abschlag), BT-105 (Zuschlag)
    """

    # Note: BR-CO-21/22 (header reason coupling) and BR-CO-23/24 (line
    # reason coupling) are enforced by ``Trade._validate_document_arithmetic``
    # because they need to know whether this allowance/charge is at
    # header or line level. Keeping the check there means the same
    # ``TradeAllowanceCharge`` dataclass works in both contexts.

    # Der Code des Grundes für den Abschlag auf Dokumentenebene (BT-98) und
    # der Grund für den Abschlag auf Dokumentenebene (BT-97) müssen dieselbe
    # Zuschlagsart anzeigen.
