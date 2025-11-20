from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, override

from tagic.xml import XML

from carthorse.schema.element import Element
from carthorse.schema.trade import Trade
from carthorse.schema.types import Namespace, Profile, TypeCode


@dataclass(kw_only=True, slots=True)
class BusinessDocument(Element):
    """Gruppierung der Geschäftsprozessinformationen"""

    tag: ClassVar[str] = "DocumentContextParameterType"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID", "ns": Namespace.ram})
    """Geschäftsprozesstyp / Geschäftsprozess

    Identifiziert den Kontext des Geschäftsprozesses, in dem die Transaktion erfolgt, um es dem Käufer zu ermöglichen, die Rechnung in angemessener Weise zu verarbeiten

    Anwendung: Diese Daten ermöglichen es, den Zweck der Abrechnung (Rechnung des Bevollmächtigten, Vertragspartners, Subunternehmers, Abrechnungsbeleg für einen Bauauftrag usw.) zu definieren.

    Beispiele: Produktionsmaterial, sonstiges Material, Frachtrechnung

    EN 16931-ID: BG-23
    """


@dataclass(kw_only=True, slots=True)
class GuidelineDocument(Element):
    """Gruppierung der Anwendungsempfehlungsinformationen"""

    tag: ClassVar[str] = "GuidelineSpecifiedDocumentContextParameter"

    id: Profile = field(metadata={"tag": "ID", "ns": Namespace.ram})
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

    test_indicator: bool | None = field(
        default=None,
        metadata={
            "tag": "TestIndicator",
            "profile": Profile.EXTENDED,
        },
    )
    """Testkennzeichen

    Das Testkennzeichen kann bei der Einführung eines neuen Systems verwendet
    werden, um die Rechnung als "Testrechnung" zu kennzeichnen.
    """

    guideline: GuidelineDocument
    business: BusinessDocument | None = None


@dataclass(kw_only=True, slots=True)
class IncludedNote(Element):
    """Freitext zur Rechnung

    Eine Gruppierung betriebswirtschaftlicher Begriffe zur Angabe rechnungsrelevanter
    Freitexte einschließlich einer Qualifizierung dieser

    EN 16931-ID: BG-1
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC

    content_code: str | None = field(
        default=None,
        metadata={
            "tag": "ContentCode",
            "profile": Profile.EXTENDED,
        },
    )
    content: str | None = field(
        default=None,
        metadata={"tag": "Content", "profile": Profile.BASIC},
    )
    subject_code: str | None = field(
        default=None,
        metadata={
            "tag": "SubjectCode",
            "profile": Profile.COMFORT,
        },
    )


@dataclass(kw_only=True, slots=True)
class EffectivePeriod(Element):
    """Vertragliches Fälligkeitsdatum der Rechnung

    Angabe nur erforderlich, falls das vertragliche Fälligkeitsdatum vom
    Fälligkeitsdatum der Zahlung (z.B. bei SEPA-Lastschriften) abweicht.
    """

    tag: ClassVar[str] = "EffectiveSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.EXTENDED

    complete: date = field(
        metadata={
            "tag": "CompleteDateTime",
            "profile": Profile.EXTENDED,
        }
    )


@dataclass(kw_only=True, slots=True)
class Header(Element):
    """Gruppierung der Eigenschaften, die das gesamte Dokument betreffen."""

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocument"

    id: str = field(metadata={"tag": "ID"})
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

    type_code: TypeCode = field(metadata={"tag": "TypeCode"})
    """Code für den Rechnungstyp / Dokumentenart (Code)
    
    Handelsrechnungen und Gutschriften sind nach den Einträgen in UNTDID 1001 
    definiert.
    Andere Einträge aus UNTDID 1001 mit spezifischen Rechnungen oder 
    Gutschriften dürfen, falls zutreffend, verwendet werden.

    Für die Profile BASIC WL und MINIMUM darf ausschließlich folgender Code verwendet werden:
    751 : Buchungshilfe - KEINE Rechnung

    EN 16931-ID: BT-3
    """

    issue_date: date = field(
        metadata={"tag": "IssueDateTime", "ns": Namespace.ram},
    )
    """Rechnungsdatum

    Das Datum, an dem die Rechnung ausgestellt wurde

    EN 16931-ID: BT-2
    """

    name: str | None = field(
        default=None,
        metadata={"tag": "Name", "profile": Profile.BASIC},
    )
    """Dokumentenart (Freitext)
    
    RECHNUNG, GUTSCHRIFT, BELASTUNGSANZEIGE, PROFORMARECHNUNG
    """

    copyright_indicator: bool | None = field(
        default=None,
        metadata={
            "tag": "CopyIndicator",
            "profile": Profile.EXTENDED,
        },
    )
    language_id: str | None = field(
        default=None,
        metadata={
            "tag": "LanguageID",
            "profile": Profile.EXTENDED,
        },
    )
    """Sprachkennzeichen

    Beispiel: de
    """
    notes: list[IncludedNote] | None = None
    effective_period: EffectivePeriod | None = None


@dataclass(kw_only=True, slots=True)
class Document(Element):
    """Rechnung

    Der Inhalt der ZUGFeRD-XML-Rechnung muss unabhängig vom Belegbild eine
    vollständige, eigenständige Rechnung abbilden. Sie soll den gleichen
    fachlichen Inhalt widerspiegeln, wie das Belegbild.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoice"

    context: Context
    header: Header
    trade: Trade

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        if profile != self.context.guideline.id:
            raise ValueError(
                f"{profile=} has to be the same as set profile: {self.context.guideline.id}"
            )
        return XML(
            self.get_tag(),
            attrs={f"xmlns:{ns.name}": ns.value for ns in Namespace},
            is_root=True,
            children=self._children_xml(profile),
        )

    def to_xml(self) -> XML:
        profile = self.context.guideline.id
        return self.to_xml_internal(profile)

    def validate(self) -> None:
        profile = self.context.guideline.id
        return self.validate_internal(profile)
