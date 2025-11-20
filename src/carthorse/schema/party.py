from dataclasses import dataclass, field
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.types import Profile

# Validation:
# BR-CO-26 Verkäufer
# Um dem Käufer eine automatische Identifizierung eines Lieferanten zu ermöglichen, müssen die Kennung des Verkäufers (BT-29), die Kennung der rechtlichen Registrierung des Verkäufers (BT-30) und/oder die Umsatzsteuer-Identifikationsnummer des Verkäufers (BT-31) angegeben werden.
# BR-CO-9 Umsatzsteuer-Identifikationsnummern
# Den Umsatzsteuer-Identifikationsnummern des Verkäufers (BT-31), des Steuerbevollmächtigten des Verkäufers (BT-63) und des Käufers (BT-48) muss zur Kennzeichnung des Landes, das sie erteilt hat, jeweils ein Präfix nach ISO 3166-1 Alpha-2 vorangestellt werden, durch das das Ausstellerland identifiziert werden kann. Griechenland wird jedoch ermächtigt, das Präfix „EL“ zu verwenden.
# BR-18 Steuerbevollmächtigter des Verkäufers
# Falls sich der Verkäufer (BG-4) durch einen Steuerbevollmächtigten (BG-11) vertreten lässt, muss dessen Name (BT-62) in der Rechnung angegeben werden.

# BR-19 Steuerbevollmächtigter des Verkäufers
# Falls sich der Verkäufer (BG-4) durch einen Steuerbevollmächtigten (BG-11) vertreten lässt, muss die Postanschrift des Steuerbevollmächtigten des Verkäufers (BG-12) in der Rechnung angegeben werden.

# BR-56 Steuerbevollmächtigter des Verkäufers
# Jeder Steuerbevollmächtigte des Verkäufers (BG-11) muss über eine Umsatzsteuer-Identifikationsnummer des Steuerbevollmächtigten des Verkäufers (BT-63) verfügen.


@dataclass(kw_only=True, slots=True)
class SchemaID(Element):
    tag: ClassVar[str] = "ID"

    id: str
    schema_id: str
    """Kennung des Schemas"""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), attrs={"schemaID": self.schema_id})[self.id]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "schemaID" not in elem.attrib:
            raise ValueError
        if elem.text is None:
            raise ValueError
        schema_id = elem.attrib["schemaID"]
        value = elem.text.strip()
        return cls(id=value, schema_id=schema_id)


@dataclass(kw_only=True, slots=True)
class ISO6523SchemaId(SchemaID):
    """ISO-6523 SchemaId

    Hinweis: Wird das Identifikationsschema verwendet, muss es aus den Einträgen
    der von der ISO/IEC 6523 Maintenance Agency veröffentlichten Liste ausgewählt werden.

    Anwendung: Insbesondere können folgende Codes genutzt werden:
        0021 : SWIFT
        0088 : EAN
        0060 : DUNS
        0177 : ODETTE

    Codeliste: ISO 6523
    https://test-docs.peppol.eu/poacc/billing/3.0/2024-q4-release/codelist/ICD/
    """


@dataclass(kw_only=True, slots=True)
class GlobalID(ISO6523SchemaId):
    """GlobalID

    SchemaID:
    EN 16931-ID: BT-29-1 (Seller), BT-46-1 (Buyer)
    """

    tag: ClassVar[str] = "GlobalID"
    profile: ClassVar[Profile] = Profile.COMFORT


@dataclass(kw_only=True, slots=True)
class URIID(SchemaID):
    """GlobalID

    SchemaID:
    EN 16931-ID: BT-34 (Seller), BT-49 (Buyer)
    """

    tag: ClassVar[str] = "URIID"
    profile: ClassVar[Profile] = Profile.BASIC_WL


@dataclass(kw_only=True, slots=True)
class PostalTradeAddress(Element):
    tag: ClassVar[str] = "PostalTradeAddress"

    country_id: str = field(metadata={"tag": "CountryID"})
    """Land (Code)

    Codeliste: ISO 3166-1, Nur die Alpha-2 Darstellung darf verwendet werden

    Beispiel: DE
    """
    postcode: str | None = field(
        default=None, metadata={"tag": "PostcodeCode", "profile": Profile.BASIC_WL}
    )
    """Postleitzahl"""
    line_one: str | None = field(
        default=None, metadata={"tag": "LineOne", "profile": Profile.BASIC_WL}
    )
    """Adresszeile 1

    Hinweis: Angabe der Strasse oder des Postfachs. Bei Großkundenanschriften
    muss dieses Feld mit "-" belegt werden.

    Beispiel: Lieferantenstraße 20
    """
    line_two: str | None = field(
        default=None, metadata={"tag": "LineTwo", "profile": Profile.BASIC_WL}
    )
    """Adresszeile 2

    Beispiel: Gebäude 3
    """
    line_three: str | None = field(
        default=None, metadata={"tag": "LineThree", "profile": Profile.BASIC_WL}
    )
    """Adresszeile 3

    Beispiel: Tür B
    """
    city_name: str | None = field(
        default=None, metadata={"tag": "CityName", "profile": Profile.BASIC_WL}
    )
    """Ort
    Beispiel: München
    """


@dataclass(kw_only=True, slots=True)
class PostalTradeAddressExtended(PostalTradeAddress):
    country_subdivision: str | None = field(
        default=None,
        metadata={"tag": "CountrySubDivisionName", "profile": Profile.BASIC},
    )
    """Bundesland

    Beispiel: NRW

    EN 16931-ID: BT-68 (SellerTaxRepresentativeTradeParty)
    """


@dataclass(kw_only=True, slots=True)
class PhoneNumber(Element):
    tag: ClassVar[str] = "TelephoneUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Eine Telefonnummer der Kontaktstelle

    Beispiel: +49 (123) 56789-0

    EN 16931-ID: BT-42 (Seller), BT-57 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class FaxNumber(Element):
    tag: ClassVar[str] = "FaxUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Eine Faxnummer der Kontaktstelle

    Beispiel: +49 (123) 456789-999
    """


@dataclass(kw_only=True, slots=True)
class EmailURI(Element):
    tag: ClassVar[str] = "EmailURIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.EXTENDED

    address: str | None = field(metadata={"tag": "URIID", "profile": Profile.EXTENDED})
    """Eine E-Mailadresse der Kontaktstelle

    Beispiel: karin.mustermann@seller.tld

    EN 16931-ID: BT-43 (Seller), BT-58 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class TradeContact(Element):
    tag: ClassVar[str] = "DefinedTradeContact"
    profile: ClassVar[Profile] = Profile.COMFORT

    person_name: str | None = field(
        default=None, metadata={"tag": "PersonName", "profile": Profile.COMFORT}
    )
    """Ansprechpartnername des Verkäufers / Käufers

    Eine Kontaktstelle für einen Rechtsträger oder eine juristische Person, wie
    z. B. Personenname, Bezeichnung der Kontaktperson

    EN 16931-ID: BT-41 (Seller), BT-56 (Buyer)
    """
    department_name: str | None = field(
        default=None, metadata={"tag": "DepartmentName", "profile": Profile.COMFORT}
    )
    """Abteilungsname des Verkäufers / Käufers

    Eine Kontaktstelle für einen Rechtsträger oder eine juristische Person, wie
    z. B. Bezeichnung der Abteilung oder des Büros

    EN 16931-ID: BT-41-0 (Seller), BT-56-0 (Buyer)
    """
    telephone: PhoneNumber | None = None
    """Telefonnummer des Verkäufers / Käufers"""
    fax: FaxNumber | None = None
    """Faxnummer des Verkäufers / Käufers"""
    email: EmailURI | None = None
    """E-Mailadresse des Verkäufers / Käufers"""


@dataclass(kw_only=True, slots=True)
class LegalOrganization(Element):
    """Details zur Organisation"""

    tag: ClassVar[str] = "SpecifiedLegalOrganization"

    id: ISO6523SchemaId | None = None
    """Kennung der rechtlichen Registrierung des Verkäufers / Käufers

    Eine von einer offiziellen Registrierungsstelle ausgegebene Kennung, die den
    Verkäufer / Käufer als Rechtsträger oder juristische Person identifiziert

    EN 16931-ID: BT-30 (Seller), BT-47 (Buyer)
    """
    trade_name: str | None = field(
        default=None,
        metadata={"tag": "TradingBusinessName", "profile": Profile.BASIC_WL},
    )
    """Handelsname des Verkäufers / Käufers

    Ein Name, unter dem der Verkäufer / Käufer bekannt ist, sofern abweichend
    vom Namen des Verkäufers / Käufer (auch als Firmenname bekannt)

    EN 16931-ID: BT-28 (Seller), BT-45 (Buyer)
    """
    trade_address: PostalTradeAddress | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Detailinformationen zur Geschäftsanschrift"""


@dataclass(kw_only=True, slots=True)
class URIUniversalCommunication(Element):
    """Details zur elektronischen Adresse"""

    tag: ClassVar[str] = "URIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    uri_id: URIID
    """Elektronischen Adresse des Verkäufers / Käufers

    Seller: Gibt die elektronische Adresse des Verkäufers an, an die die Antwort auf die Rechnung auf Anwendungsebene gesendet werden kann.

    Buyer: Gibt die elektronische Adresse des Käufers an, an die die Rechnung gesendet wird

    EN 16931-ID: BT-34 (Seller), BT-49 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class TaxSchemaId(ISO6523SchemaId):
    """Umsatzsteueridentnummer / Steuernummer

    Zulässige Codes für schema_id:
    - VA Umsatzsteuernummer (BT-31, BT-48)
    - FC Steuernummer (BT-32)

    SchemaID:
    EN 16931-ID: BT-31-0, BT-32-0 (Seller)
    EN 16931-ID: BT-48 (Buyer)
    """

    # TODO: check VA/FC in TradeParty

    tag: ClassVar[str] = "GlobalID"

    @override
    def validate_internal(self, profile: Profile) -> None:
        if self.schema_id not in ("VA", "FC"):
            raise ValidationError(
                code="Enum", message="Only values 'VA' or 'FC' allowed."
            )


@dataclass(kw_only=True, slots=True)
class SpecifiedTaxRegistration(Element):
    """Detailinformationen zu Steuerangaben des Käufers / Verkäufers"""

    tag: ClassVar[str] = "SpecifiedTaxRegistration"

    id: TaxSchemaId


@dataclass(kw_only=True, slots=True)
class SellerTradeParty(Element):
    """Verkäufer / Detailinformationen zum Verkäufer (=Leistungserbringer)

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über den Verkäufer enthält

    EN 16931-ID: BG-4
    """

    tag: ClassVar[str] = "SellerTradeParty"

    name: str = field(metadata={"tag": "Name"})
    """Name des Verkäufers

    Der volle formelle Name, unter dem der Verkäufer im nationalen Register für
    juristische Personen oder als steuerpflichtige Person ein-getragen ist oder
    anderweitig als Person(en) handelt

    EN 16931-ID: BT-27
    """
    address: PostalTradeAddressExtended
    """Postanschrift des Verkäufers

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über die
    Verkäuferanschrift enthält. Um den rechtlichen Anforderungen zu entsprechen, muss
    eine ausreichende Anzahl an Komponenten der Anschrift eingegeben werden

    EN 16931-ID: BG-5
    """
    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.COMFORT}
    )

    """Kennung des Verkäufers / Durch den Kunden zugewiesene Lieferantennummer

    Hinweis: Bei vielen Systemen ist die Verkäuferkennung eine Schlüsselinformation.
    Es dürfen mehrere Verkäuferkennungen zugewiesen oder festgelegt werden. Sie dürfen
    durch Verwendung verschiedener Identifikationsschemen differenziert werden. Wird
    kein Schema angegeben, sollte sie dem Käufer und Verkäufer bekannt sein, z. B. eine
    zuvor ausgetauschte, vom Käufer zugewiesene Kennung des Verkäufers.

    Anwendung: Wenn der Verkäufer eine Global ID hat, soll diese genutzt werden. Ansonsten
    wird das Feld ID genutzt.

    EN 16931-ID: BT-29
    """
    global_ids: list[GlobalID] | None = None
    """Globaler Identifier des Verkäufers: GLN, DUNS, BIC, ODETTE, ...

    Hinweis: Das Identifikationsschema der Kennung des Verkäufers ist eine von
    einer globalen Registrierungsorganisation eindeutig einem Verkäufer
    zugewiesene Kennzeichnung.

    EN 16931-ID: BT-29-0
    """
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Sonstige rechtliche Informationen des Verkäufers

    Weitere rechtliche Informationen, die für den Verkäufer maßgeblich sind, wie z. B. Aktienkapital

    EN 16931-ID: BT-33
    """
    legal_organization: LegalOrganization | None = None
    """Details zur Organisation"""
    contact: TradeContact | None = None
    """Kontaktdaten des Verkäufers

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die für den Verkäufer
    maßgebliche Kontaktinformationen enthält

    EN 16931-ID: BG-6
    """
    electronic_address: URIUniversalCommunication | None = None
    """Details zur elektronischen Adresse"""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Steuernummer / Umsatzsteueridentnummer des Verkäufers

    Die örtliche Identifikation (definiert über die Verkäuferanschrift) des
    Verkäufers für Steuerzwecke oder einer Referenz, die es dem Verkäufer
    ermöglicht, seinen Meldestatus für Steuerzwecke anzugeben
    Die Umsatzsteuer-Identifikationsnummer des Verkäufers

    EN 16931-ID: BT-31, BT-32
    """


@dataclass(kw_only=True, slots=True)
class BuyerTradeParty(Element):
    """Käufer / Detailinformationen zum Käufer (=Leistungsempfänger)

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über den Käufer enthält

    EN 16931-ID: BG-7
    """

    tag: ClassVar[str] = "BuyerTradeParty"

    name: str = field(metadata={"tag": "Name"})
    """Name des Käufers

    Der volle Name des Käufers

    EN 16931-ID: BT-44
    """
    address: PostalTradeAddressExtended
    """Postanschrift des Käufers

    EN 16931-ID: BG-8
    """
    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.COMFORT}
    )

    """Kennung des Käufers / Kundennummer

    Hinweis: Wird kein Schema angegeben, sollte sie dem Käufer und Verkäufer bekannt sein, z. B. eine zuvor ausgetauschte, vom Verkäufer zugewiesene Kennung des Käufers.

    EN 16931-ID: BT-46
    """
    global_ids: list[GlobalID] | None = None
    """Globaler Identifier des Käufers: GLN, DUNS, BIC, ODETTE, ...

    Hinweis: Das Identifikationsschema der Kennung des Käufers ist eine von
    einer globalen Registrierungsorganisation eindeutig einem Käufer
    zugewiesene Kennzeichnung.

    EN 16931-ID: BT-46-0
    """
    legal_organization: LegalOrganization | None = None
    """Details zur Organisation"""
    contact: TradeContact | None = None
    """Kontaktdaten des Käufers

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die für den Käufer
    maßgebliche Kontaktinformationen enthält.
    Kontaktdaten können vom Käufer bei der Bestellung angegeben oder vor der
    Bestellung als Stammdaten ausgetauscht werden. Kontaktdaten sollten nicht
    für die Zwecke der internen Lenkung der erhaltenen Rechnung durch den Empfänger
    verwendet werden; hierfür sollte die Referenz des Käufers verwendet werden.
    
    EN 16931-ID: BG-9
    """
    electronic_address: URIUniversalCommunication | None = None
    """Details zur elektronischen Adresse"""
    tax_registrations: SpecifiedTaxRegistration | None = field(
        default=None, metadata={"profile": Profile.BASIC_WL}
    )
    """Umsatzsteuer-Identifikationsnummer des Käufers

    Die Umsatzsteuer-Identifikationsnummer des Käufers. Umsatzsteuernummer mit
    vorangestelltem Ländercode auf der Grundlage von EN ISO 3166-1, 2-ALPHA
    
    EN 16931-ID: BT-48
    """


@dataclass(kw_only=True, slots=True)
class SellerTaxRepresentativeTradeParty(Element):
    """Steuerbevollmächtigter des Verkäufers

    EN 16931-ID: BG-11
    """

    tag: ClassVar[str] = "SellerTaxRepresentativeTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    name: str = field(metadata={"tag": "Name"})
    """Name des Steuerbevollmächtigten des Verkäufers

    EN 16931-ID: BT-62
    """
    address: PostalTradeAddressExtended
    """Postanschrift des Steuerbevollmächtigten des Verkäufers

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über
    die Postanschrift des Steuerbevollmächtigten enthält. Falls sich der
    Verkäufer durch einen Steuerbevollmächtigten vertreten lässt, der für
    Zahlung der fälligen Umsatzsteuer verantwortlich ist, muss der Name/die
    Postanschrift des Steuerbevollmächtigten des Verkäufers in der Rechnung
    angegeben werden. Um den rechtlichen Anforderungen zu entsprechen, muss
    eine ausreichende Anzahl an Komponenten der Anschrift eingegeben werden.

    EN 16931-ID: BG-12
    """
    tax_registrations: SpecifiedTaxRegistration
    """Detailinformationen zur Steuernummer des Steuerbevollmächtigten des Verkäufers

    Umsatzsteuernummer mit vorangestelltem Ländercode auf der Grundlage von EN ISO 3166-1, 2-ALPHA
    „Codes for the representation of names of countries and their subdivisions“.

    EN 16931-ID: BT-63
    """
    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.EXTENDED}
    )
    """Identifier des Steuerbevollmächtigten"""
    global_ids: list[GlobalID] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Globaler Identifier des Steuerbevollmächtigten"""
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Details zur Organisation"""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Detailinformationen zum Ansprechpartner"""
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Details zur elektronischen Adresse"""


@dataclass(kw_only=True, slots=True)
class ProductEndUserTradeParty(Element):
    """Detailinformationen zum abweichenden Endverbraucher"""

    tag: ClassVar[str] = "ProductEndUserTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    name: str = field(metadata={"tag": "Name"})
    """Name/Firmierung des Endverbrauchers"""
    id: str | None = field(default=None, metadata={"tag": "ID"})

    """Identifikation des abweichenden Endverbrauchers"""
    global_ids: list[GlobalID] | None = None
    """Globaler Identifier des abweichenden Endverbrauchers"""
    legal_organization: LegalOrganization | None = None
    """Details zur Organisation"""
    contact: TradeContact | None = None
    """Detailinformationen zum Ansprechpartner des Endverbrauchers"""
    address: PostalTradeAddressExtended | None = None
    """Detailinformationen zur Anschrift des Endverbrauchers"""
    electronic_address: URIUniversalCommunication | None = None
    """Details zur elektronischen Adresse"""
    tax_registrations: SpecifiedTaxRegistration | None = field(
        default=None, metadata={"profile": Profile.BASIC_WL}
    )
    """Detailinformationen zur Steuernummer des abweichenden Endverbrauchers

    Steuernummer, Umsatzsteueridentnummer
    """


@dataclass(kw_only=True, slots=True)
class ShipToTradeParty(Element):
    """Lieferinfomationen / ZUGFeRD10: Detailinformationen zum abweichenden Warenempfänger

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen darüber
    enthält, wo und wann die in Rechnung gestellten Waren und Dienstleistungen
    geliefert bzw. erbracht werden

    EN 16931-ID: BG-13
    """

    tag: ClassVar[str] = "ShipToTradeParty"
    profile: ClassVar[Profile] = Profile.COMFORT

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Kennung des Lieferorts / Identifikation des Warenempfängers

    Eine Kennung für den Ort, an den die Waren geliefert oder an dem die Dienstleistungen erbracht werden.

    Wird kein Schema angegeben, sollte sie dem Käufer und Verkäufer bekannt sein,
    z. B. eine zuvor ausgetauschte, vom Käufer oder Verkäufer zugewiesene Kennung.
    
    EN 16931-ID: BT-71
    """
    global_id: GlobalID | None = None
    """Globaler Identifier der Kennung für den Lieferort

    EN 16931-ID: BT-71-0
    """
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Name/Firmierung des Waren- oder Dienstleistungsempfängers

    Der Name der Partei, an die die Waren geliefert bzw. für die die
    Dienstleistungen erbracht werden.
    Muss verwendet werden, wenn der Waren- bzw. Dienstleistungsempfänger nicht
    mit dem Käufer identisch ist.

    EN 16931-ID: BT-70
    """
    address: PostalTradeAddressExtended | None = None
    """Lieferanschrift

    Eine Gruppe von betriebswirtschaftlichen Begriffen, die Informationen über die Anschrift enthält, an die die in Rechnung gestellten Waren geliefert oder an der die in Rechnung gestellten Dienst-leistungen erbracht werden.

    Im Falle einer Abholung entspricht die Lieferanschrift der Abholanschrift. Um den rechtlichen Anforderungen zu entsprechen, muss eine ausreichende Anzahl an Komponenten der Anschrift eingegeben werden.

    EN 16931-ID: BG-15
    """

    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Details zur Organisation"""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Detailinformationen zum Ansprechpartner des Warenempfängers"""
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Details zur elektronischen Adresse"""
    tax_registrations: list[SpecifiedTaxRegistration] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Detailinformationen zu Steuerangaben des Warenempfängers

    Steuernummer, Umsatzsteueridentnummer
    """


@dataclass(kw_only=True, slots=True)
class ShipFromTradeParty(Element):
    """Identifikation des abweichenden Versenders"""

    tag: ClassVar[str] = "ShipFromTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Identifikation des Versenders

    Der Identifier des Versenders ist eine eindeutige, bilateral vereinbarte
    Kennzeichnung des Versenders.
    """
    global_id: GlobalID | None = None
    """Globaler Identifier des Versenders"""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Name/Firmierung des Versenders"""
    legal_organization: LegalOrganization | None = None
    """Details zur Organisation"""
    contact: TradeContact | None = None
    """Detailinformationen zum Ansprechpartner des Versenders"""
    address: PostalTradeAddressExtended | None = None
    """Detailinformationen zur Anschrift des Versenders"""
    electronic_address: URIUniversalCommunication | None = None
    """Details zur elektronischen Adresse"""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Detailinformationen zu Steuerangaben des Versenders

    Steuernummer, Umsatzsteueridentnummer
    """


@dataclass(kw_only=True, slots=True)
class UltimateShipToTradeParty(Element):
    """Detailinformationen zum abweichenden Endempfänger"""

    tag: ClassVar[str] = "UltimateShipToTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Identifikation des Endempfängers

    Der Identifier des Endempfängers ist eine eindeutige, bilateral
    vereinbarte Kennzeichnung des Endempfängers.
    """
    global_ids: list[GlobalID] | None = None
    """Globaler Identifier des Endempfängers"""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Name/Firmierung des Endempfängers"""
    legal_organization: LegalOrganization | None = None
    """Details zur Organisation"""
    contact: TradeContact | None = None
    """Detailinformationen zum Ansprechpartner des Endempfängers"""
    address: PostalTradeAddressExtended | None = None
    """Detailinformationen zur Anschrift des Endempfängers"""
    electronic_address: URIUniversalCommunication | None = None
    """Details zur elektronischen Adresse"""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Detailinformationen zu Steuerangaben des Endempfängers

    Steuernummer, Umsatzsteueridentnummer
    """
