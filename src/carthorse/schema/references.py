import enum
from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement
from carthorse.schema.types import Namespace, Profile


@dataclass(kw_only=True, slots=True)
class BuyerOrderReferencedDocument(Element):
    """Detailangaben zur zugehörigen Bestellung"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "BuyerOrderReferencedDocument"

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "ns": Namespace.ram}
    )
    """Bestellreferenz / Bestellnummer

    Eine vom Käufer ausgegebene Kennung für eine referenzierte Bestellung

    EN 16931-ID: BT-13
    """


@dataclass(kw_only=True, slots=True)
class SellerOrderReferencedDocument(Element):
    """Detailangaben zur zugehörigen Auftragsbestätigung"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "SellerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={
            "tag": "IssuerAssignedID",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        }
    )
    """Verkaufsauftragsreferenz / Nummer der Auftragsbestätigung

    Eine vom Verkäufer ausgegebene Kennung für einen referenzierten Verkaufsauftrag

    EN 16931-ID: BT-14
    """


@dataclass(kw_only=True, slots=True)
class ContractReferencedDocument(Element):
    """Detailangaben zum zugehörigen Vertrag"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "ContractReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(
        metadata={
            "tag": "IssuerAssignedID",
            "ns": Namespace.ram,
            "profile": Profile.BASIC_WL,
        }
    )
    """Vertragsreferenz / Vertragsnummer

    Die Kennung eines Vertrags. Die Vertragsreferenz sollte im Kontext der
    spezifischen Handelsbeziehung und für einen definierten Zeitraum einmalig vergeben sein.

    EN 16931-ID: BT-12
    """


@dataclass(kw_only=True, slots=True)
class UltimateCustomerOrderReferencedDocument(Element):
    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "UltimateCustomerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "ns": Namespace.ram}
    )
    issue_date_time: date = field(
        metadata={"tag": "FormattedIssueDateTime", "ns": Namespace.ram}
    )


@enum.unique
class UNTDID1001TypeCode(enum.StrEnum):
    T_50 = "50"
    Rechnungsdatenblatt = "130"
    Referenzpapier = "916"


@enum.unique
class MIME(enum.StrEnum):
    pdf = "application/pdf"
    png = "image/png"
    jpeg = "image/jpeg"
    csv = "text/csv"
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    odf = "application/vnd.oasis.opendocument.spreadsheet"


@dataclass(kw_only=True, slots=True)
class AttachmentBinaryObject(Element):
    """Anhangsdokument / Binärdaten des zusätzlichen Dokuments

    Ein als Binärobjekt eingebettetes oder zusammen mit der Rechnung gesendetes
    Anhangsdokument. Ein Anhangsdokument wird dann verwendet, wenn für die
    zukünftige Bezugnahme oder für Auditierungszwecke eine Dokumentation in
    Verbindung mit der Rechnung aufbewahrt werden muss.

    EN 16931-ID: BT-125
    """

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "AttachmentBinaryObject"
    profile: ClassVar[Profile] = Profile.COMFORT

    mime_code: MIME
    """MIME-Code des Anhangsdokuments

    EN 16931-ID: BT-125-1
    """
    filename: str
    """Dateiname des Anhangsdokuments

    EN 16931-ID: BT-125-2
    """
    object: str
    """Encodetes Anhangsdokument"""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(
            self.get_tag(),
            attrs={"mimeCode": self.mime_code, "filename": self.filename},
        )[self.object]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "mimeCode" not in elem.attrib:
            raise ValueError
        if "filename" not in elem.attrib:
            raise ValueError
        if elem.text is None:
            raise ValueError
        mime_code = elem.attrib["mimeCode"]
        assert isinstance(mime_code, str)
        filename = elem.attrib["filename"]
        assert isinstance(filename, str)
        object = elem.text.strip()
        return cls(
            mime_code=MIME(mime_code.strip()), filename=filename.strip(), object=object
        )


@dataclass(kw_only=True, slots=True)
class AdditionalReferencedDocument(Element):
    """Rechnungsbegründende Unterlagen

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    rechnungsbegründende Unterlagen enthält, die Belege für die in der Rechnung
    gestellten Ansprüche enthalten.
    Die rechnungsbegründenden Unterlagen können sowohl für die Referenz einer
    Dokumentnummer, die dem Empfänger bekannt sein sollte, als auch eines
    externen (durch einen URL referenzierten) Dokuments oder eines eingebetteten
    Dokuments (wie z. B. eines Stundenzettels als PDF-Datei) verwendet werden.
    Die Option der Verknüpfung mit einem externen Dokument ist z. B. dann
    erforderlich, wenn es um große Anhänge und/oder um sensible Informationen,
    z. B. bei personenbezogenen Diensten, geht, die von der Rechnung getrennt werden müssen.

    EN 16931-ID: BG-24
    """

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "AdditionalReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={
            "tag": "IssuerAssignedID",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        }
    )
    """Dokumentenkennung / Dokumentennummer

    Die Kennung der Ausschreibung oder des Loses, auf die/das sich die Rechnung
    bezieht, oder eine vom Verkäufer angegebene Kennung für ein Objekt, auf
    dem die Rechnung basiert, oder eine Kennung der rechnungsbegründenden
    Unterlage.

    In manchen Ländern muss eine Referenz zu der Ausschreibung angegeben werden,
    die zu dem Vertrag geführt hat. Das kann je nach Anwendung eine Abonnementnummer,
    eine Telefonnummer, ein Zählerstand, ein Fahrzeug, eine Person usw. sein.
    
    EN 16931-ID: BT-17, BT-18, BT-122
    """
    uriid: str | None = field(
        default=None,
        metadata={"tag": "URIID", "ns": Namespace.ram, "profile": Profile.COMFORT},
    )
    """Bezugsort der rechnungsbgegründenden Unterlage

    Die URL (Uniform Resource Locator), unter der das externe Dokument verfügbar ist.

    Ein Mittel zur Auffindung der Ressource einschließlich des dafür vorgesehenen
    primären Zugangsverfahrens, z. B. http:// oder ftp://.
    Der Speicherort des externen Dokuments muss dann verwendet werden, wenn der
    Käufer weitere Informationen als Belege für die in Rechnung gestellten Beträge
    benötigt.
    Externe Dokumente sind nicht Bestandteil der Rechnung. Der Zugriff auf externe
    Dokumente kann gewisse Risiken bergen.

    EN 16931-ID: BT-124
    """
    type_code: UNTDID1001TypeCode | None = field(
        default=None,
        metadata={"tag": "TypeCode", "ns": Namespace.ram, "profile": Profile.COMFORT},
    )
    """Typ des referenzierten Dokuments

    * Der Code  916 "Referenzpapier" wird benutzt, um die Kennung der
      rechnungsbegründenden Unterlage zu referenzieren. (BT-122)
    * Der Code 50 "Price/sales catalogue response" wird benutzt, um die
      Ausschreibung oder das Los zu referenzieren. (BT-17)
    * Der Code 130 "Rechnungsdatenblatt" wird benutzt, um eine vom Verkäufer
      angegebene Kennung für ein Objekt zu referenzieren. (BT-18)

    EN 16931-ID: BT-17-0, BT-18-0, BT-122-0
    """
    name: str | None = field(
        default=None,
        metadata={"tag": "Name", "ns": Namespace.ram, "profile": Profile.COMFORT},
    )
    """Beschreibung der rechnungsbegründenden Unterlage

    Eine Beschreibung der Unterlage, wie z. B. Stundenabrechnung, Nutzungs- oder Verbrauchsbericht usw.

    EN 16931-ID: BT-123
    """
    attached_object: AttachmentBinaryObject | None = None


@dataclass(kw_only=True, slots=True)
class ProcuringProject(Element):
    """Detailangaben zu einer Projektreferenz"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "SpecifiedProcuringProject"
    profile: ClassVar[Profile] = Profile.COMFORT

    id: str = field(
        metadata={
            "tag": "ID",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        }
    )
    """Projektreferenz

    Die Kennung des Projektes, auf das sich die Rechnung bezieht.

    EN 16931-ID: BT-11
    """
    name: str = field(
        metadata={
            "tag": "Name",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        }
    )
    """Projektname

    Der Name des Projektes, auf das sich die Rechnung bezieht

    EN 16931-ID: BT-11-0
    """


@dataclass(kw_only=True, slots=True)
class DespatchAdviceReferencedDocument(Element):
    """Detailinformationen zum zugehörigen Lieferavis"""

    namespace: ClassVar[Namespace] = Namespace.ram
    tag: ClassVar[str] = "DespatchAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(
        metadata={
            "tag": "IssuerAssignedID",
            "ns": Namespace.ram,
            "profile": Profile.COMFORT,
        }
    )
    """Lieferavisreferenz

    Eine Kennung für ein referenziertes Lieferavis

    EN 16931-ID: BT-16
    """
