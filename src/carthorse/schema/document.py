import enum
from dataclasses import dataclass
from typing import ClassVar, override

from tagic.xml import XML

from .element import Element, Namespace, Profile
from .fields import Date, Field, Indicator, String, StringId

TestIndicator = Indicator[Namespace.ram, "TestIndicator", Profile.EXTENDED]


@dataclass(kw_only=True, slots=True)
class BusinessDocumentContextParameter(Element):
    """Gruppierung der Geschäftsprozessinformationen"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "DocumentContextParameterType"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: StringId | None = None
    """Geschäftsprozesstyp / Geschäftsprozess

    Identifiziert den Kontext des Geschäftsprozesses, in dem die Transaktion erfolgt, um es dem Käufer zu ermöglichen, die Rechnung in angemessener Weise zu verarbeiten

    Anwendung: Diese Daten ermöglichen es, den Zweck der Abrechnung (Rechnung des Bevollmächtigten, Vertragspartners, Subunternehmers, Abrechnungsbeleg für einen Bauauftrag usw.) zu definieren.

    Beispiele: Produktionsmaterial, sonstiges Material, Frachtrechnung

    EN 16931-ID: BG-23
    """


@dataclass(kw_only=True, slots=True)
class GuidelineDocumentContextParameter(Element):
    """Gruppierung der Anwendungsempfehlungsinformationen"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "DocumentContextParameterType"

    id: StringId
    """Spezifikationskennung / Anwendungsempfehlung

    Eine Kennung der Spezifikation, die das gesamte Regelwerk zum semantischen Inhalt, zu den Kardinalitäten und den Geschäftsregeln enthält und zu denen die im Instanzdokument enthaltenen Daten conformant sind

    Hinweis: In diesem wird die Compliance oder Conformance der Instanz mit diesem Dokument angegeben. Rechnungen, die compliant sind, geben folgendes an: urn:cen.eu:en16931:2017. Rechnungen, die compliant mit einer Benutzerspezifikation sind, dürfen diese Benutzerspezifikation an dieser Stelle angeben.
    Es ist kein Identifikationsschema zu verwenden.

    EN 16931-ID: BG-24
    """


@dataclass(kw_only=True, slots=True)
class Context(Element):
    """Prozesssteuerung

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    den Geschäftsprozess und für das Rechnungsdokument geltende Regeln enthält

    EN 16931-ID: BG-2
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocumentContext"

    test_indicator: TestIndicator | None = None
    """Testkennzeichen

    Das Testkennzeichen kann bei der Einführung eines neuen Systems verwendet
    werden, um die Rechnung als "Testrechnung" zu kennzeichnen.
    """

    business_parameter: BusinessDocumentContextParameter | None = None
    guideline_parameter: GuidelineDocumentContextParameter | None = None

    @override
    def to_xml(self, profile: Profile) -> XML:
        modified = False
        # BR-1: Eine Rechnung muss eine Spezifikationskennung (BT-24) haben.
        if self.guideline_parameter is None:
            modified = True
            self.guideline_parameter = GuidelineDocumentContextParameter(
                id=StringId(value=profile.value)
            )
        else:
            # raises valueerror on false values
            _ = Profile(self.guideline_parameter.id.value)
        res = super(Context, self).to_xml(profile)
        if modified:
            self.guideline_parameter = None
        return res


NameStr = String[Namespace.ram, "Name", Profile.BASIC]


@enum.unique
class TypeCodeEnum(enum.StrEnum):
    T_80 = "80"
    T_81 = "81"
    T_82 = "82"
    T_83 = "83"
    T_84 = "84"
    T_Rechnungsdatenblatt = "130"
    T_Verkuerzte_Baurechnung = "202"
    T_Vorlaeufige_Baurechnung = "203"
    T_Baurechnung = "204"
    T_Zwischen_abschlags_rechnung = "211"
    T_261 = "261"
    T_262 = "262"
    T_295 = "295"
    T_296 = "296"
    T_308 = "308"
    T_Proformarechnung = "325"
    T_Teilrechnung = "326"
    T_Handelsrechnung = "380"
    T_Gutschriftanzeige = "381"
    T_Belastungsanzeige_383 = "383"
    T_Rechnungskorrektur = "384"
    T_Konsolidierte_Rechnung = "385"
    T_Vorauszahlungsrechnung = "386"
    T_Mietrechnung = "387"
    T_Steuerrechnung = "388"
    T_Gutschrift_Selbst_ausgestellte_Rechnung = "389"
    T_Delkredere_Rechnung = "390"
    T_Inkasso_Rechnung = "393"
    T_Leasing_Rechnung = "394"
    T_Konsignationsrechnung = "395"
    T_Inkasso_Gutschrift = "396"
    T_420 = "420"
    T_Belastungsanzeige_456 = "456"
    T_Storno_einer_Belastung = "457"
    T_Storno_einer_Gutschrift = "458"
    T_527 = "527"
    T_Rechnung_des_Versicherers = "575"
    T_Speditionsrechnung = "623"
    T_Hafenkostenrechnung = "633"
    T_751 = "751"
    T_Frachtrechnung = "780"
    T_Zollrechnung = "935"


@dataclass(kw_only=True, slots=True)
class TypeCode(Field):
    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "TypeCode"

    value: TypeCodeEnum


Content = String[Namespace.ram, "Content", Profile.BASIC]
ContentCode = String[Namespace.ram, "ContentCode", Profile.EXTENDED]
SubjectCode = String[Namespace.ram, "SubjectCode", Profile.COMFORT]


@dataclass(kw_only=True, slots=True)
class Note(Element):
    """Freitext zur Rechnung

    Eine Gruppierung betriebswirtschaftlicher Begriffe zur Angabe rechnungsrelevanter
    Freitexte einschließlich einer Qualifizierung dieser

    EN 16931-ID: BG-1
    """

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "IncludedNote"

    content_code: ContentCode | None = None
    content: Content | None = None
    subject_code: SubjectCode | None = None


CompleteDateTime = Date[Namespace.ram, "CompleteDateTime", Profile.EXTENDED]


@dataclass(kw_only=True, slots=True)
class EffectivePeriod(Element):
    """Vertragliches Fälligkeitsdatum der Rechnung

    Angabe nur erforderlich, falls das vertragliche Fälligkeitsdatum vom
    Fälligkeitsdatum der Zahlung (z.B. bei SEPA-Lastschriften) abweicht.
    """

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "EffectiveSpecifiedPeriod"

    complete: CompleteDateTime


IssueDateTime = Date[Namespace.ram, "IssueDateTime"]
CopyIndicator = Indicator[Namespace.ram, "CopyIndicator", Profile.EXTENDED]
LanguageId = String[Namespace.ram, "LanguageID", Profile.EXTENDED]


@dataclass(kw_only=True, slots=True)
class Header(Element):
    """Gruppierung der Eigenschaften, die das gesamte Dokument betreffen."""

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoiceType"

    id: StringId
    """Rechnungsnummer
    
    Eine eindeutige Kennung der Rechnung

    Hinweis: Die nach Artikel 226 (2) der Richtlinie 2006/112/EG geforderte 
    fortlaufende Nummer, die zur Identifizierung der Rechnung innerhalb des 
    Geschäftskontextes, des Zeitrahmens, der Betriebssysteme und der Aufzeichnungen 
    des Verkäufers einmalig vergeben wird. Sie kann auf einer oder mehreren 
    Reihen von Nummern basieren, die alphanumerische Zeichen enthalten dürfen. 
    Es ist kein Identifikationsschema zu verwenden.
    
    EN 16931-ID: BT-1
    """

    type_code: TypeCode
    """Code für den Rechnungstyp / Dokumentenart (Code)
    
    Handelsrechnungen und Gutschriften sind nach den Einträgen in UNTDID 1001 
    definiert.
    Andere Einträge aus UNTDID 1001 mit spezifischen Rechnungen oder 
    Gutschriften dürfen, falls zutreffend, verwendet werden.

    Für die Profile BASIC WL und MINIMUM darf ausschließlich folgender Code verwendet werden:
    751 : Buchungshilfe - KEINE Rechnung

    EN 16931-ID: BT-3
    """

    issue_date_time: IssueDateTime
    """Rechnungsdatum

    Das Datum, an dem die Rechnung ausgestellt wurde

    EN 16931-ID: BT-2
    """

    name: NameStr | None = None
    """Dokumentenart (Freitext)
    
    RECHNUNG, GUTSCHRIFT, BELASTUNGSANZEIGE, PROFORMARECHNUNG
    """

    copyright_indicator: CopyIndicator | None = None
    language_id: LanguageId | None = None
    """Sprachkennzeichen

    Beispiel: de
    """
    notes: list[Note] | None = None
    effective_period: EffectivePeriod | None = None


@dataclass(kw_only=True, slots=True)
class Document(Element):
    """Rechnung

    Der Inhalt der ZUGFeRD-XML-Rechnung muss unabhängig vom Belegbild eine
    vollständige, eigenständige Rechnung abbilden. Sie soll den gleichen
    fachlichen Inhalt widerspiegeln, wie das Belegbild.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoiceType"

    context: Context
    header: Header
    # trade: TradeTransaction

    @override
    def to_xml(self, profile: Profile) -> XML:
        return XML(
            self.get_tag(),
            attrs={f"xmlns:{ns.name}": ns.value for ns in Namespace},
            is_root=True,
            children=self._children_xml(profile),
        )
