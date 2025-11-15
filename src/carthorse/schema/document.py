from dataclasses import dataclass
from typing import ClassVar, override

from tagic.xml import XML

from .element import Element, Namespace, Profile
from .fields import Indicator, StringId

TestIndicator = Indicator[Namespace.ram, "TestIndicator", Profile.EXTENDED]


@dataclass
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


@dataclass
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


@dataclass
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
        if self.guideline_parameter is None:
            modified = True
            self.guideline_parameter = GuidelineDocumentContextParameter(
                id=StringId(profile.value)
            )
        res = super().to_xml(profile)
        if modified:
            self.guideline_parameter = None
        return res


@dataclass
class Document(Element):
    """Rechnung

    Der Inhalt der ZUGFeRD-XML-Rechnung muss unabhängig vom Belegbild eine
    vollständige, eigenständige Rechnung abbilden. Sie soll den gleichen
    fachlichen Inhalt widerspiegeln, wie das Belegbild.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoiceType"

    context: Context
    # header: Header
    # trade: TradeTransaction

    @override
    def to_xml(self, profile: Profile) -> XML:
        return XML(
            self.get_tag(),
            attrs={f"xmlns:{ns.name}": ns.value for ns in Namespace},
            is_root=True,
            children=self._children_xml(profile),
        )
