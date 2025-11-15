from dataclasses import dataclass
from typing import ClassVar, override

from tagic.xml import XML

from carthorse.schema.fields import Indicator

from .element import Element, Namespace, Profile

TestIndicator = Indicator[Namespace.ram, "TestIndicator", Profile.EXTENDED]


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

    # IndicatorField(
    #     NS_RAM, "TestIndicator", required=False, profile=EXTENDED, _d="Testkennzeichen"
    # )
    # business_parameter: BusinessDocumentContextParameter = Field(
    #     BusinessDocumentContextParameter,
    #     required=False,
    #     profile=EXTENDED,
    #     _d="Geschäftsprozess, Wert",
    # )
    # guideline_parameter: GuidelineDocumentContextParameter = Field(
    #     GuidelineDocumentContextParameter,
    #     required=True,
    #     profile=BASIC,
    #     _d="Anwendungsempfehlung",
    # )


@dataclass(kw_only=True)
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
    def to_xml(self) -> XML:
        return XML(
            self.get_tag(),
            attrs={f"xmlns:{ns.name}": ns.value for ns in Namespace},
            is_root=True,
            children=self._children_xml(),
        )
