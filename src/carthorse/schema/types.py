import enum
from typing import override


@enum.unique
class Profile(enum.StrEnum):
    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    BASIC = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    COMFORT = "urn:cen.eu:en16931:2017"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

    @override
    def __lt__(self, value: str, /) -> bool:
        p = Profile(value)
        ps = list(Profile)
        return ps.index(self) < ps.index(p)


@enum.unique
class Namespace(enum.StrEnum):
    rsm = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    qdt = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
    ram = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xs = "http://www.w3.org/2001/XMLSchema"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"
    udt = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"

    def get_qualified_tag(self, tag: str) -> str:
        return f"{{{self.value}}}{tag}"


@enum.unique
class TypeCode(enum.StrEnum):
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


@enum.unique
class CategoryCode(enum.StrEnum):
    T_S = "S"  # Umsatzsteuer fällt mit Normalsatz an
    T_Z = "Z"  # nach dem Nullsatz zu versteuernde Waren
    T_E = "E"  # Steuerbefreit
    T_AE = "AE"  # Umkehrung der Steuerschuldnerschaft
    T_K = "K"  # Kein Ausweis der Umsatzsteuer bei innergemeinschaftlichen Lieferungen
    T_G = "G"  # Steuer nicht erhoben aufgrund von Export außerhalb der EU
    T_O = "O"  # Außerhalb des Steueranwendungsbereichs
    T_L = "L"  # IGIC (Kanarische Inseln)
    T_M = "M"  # IPSI (Ceuta/Melilla)
