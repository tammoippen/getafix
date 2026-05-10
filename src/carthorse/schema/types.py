import enum
from typing import override


@enum.unique
class Profile(enum.StrEnum):
    """Factur-X 1.08 / ZUGFeRD 2.4 conformance profile.

    The value of each member is the URN that goes into
    ``<ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>``
    (BT-24). The five profiles form a strict order from least to
    most permissive: every element accepted at MINIMUM is also
    accepted at BASIC_WL, BASIC adds line items on top of BASIC_WL,
    and so on. Higher profiles inherit every business rule from
    lower profiles, with EXTENDED additionally adding a CIUS overlay
    (``BR-FXEXT-*``) that replaces some ``BR-CO-*`` rules with
    rounding-tolerance variants — see ``docs/VALIDATION.md``.

    All four order comparators are overridden to compare by the
    declaration order of the members so e.g.
    ``Profile.BASIC_WL >= Profile.MINIMUM`` is ``True`` (whereas the
    inherited ``StrEnum`` lexicographic compare would say ``False``).
    """

    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    BASIC = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    COMFORT = "urn:cen.eu:en16931:2017"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

    def _ordinal(self) -> int:
        return list(Profile).index(self)

    @override
    def __lt__(self, value: str, /) -> bool:
        return self._ordinal() < Profile(value)._ordinal()

    @override
    def __le__(self, value: str, /) -> bool:
        return self._ordinal() <= Profile(value)._ordinal()

    @override
    def __gt__(self, value: str, /) -> bool:
        return self._ordinal() > Profile(value)._ordinal()

    @override
    def __ge__(self, value: str, /) -> bool:
        return self._ordinal() >= Profile(value)._ordinal()


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
    """UNTDID 5305 VAT category code (BT-95 / BT-102 / BT-118 / BT-151).

    Determines which ``BR-*-2/3/4`` family applies for required-party
    checks and which ``BR-*-5/6/7`` family constrains the rate. See
    ``docs/VALIDATION.md §3.2`` for the full matrix.
    """

    T_S = "S"  # Standard rate (BR-S-*); rate must be > 0
    T_Z = "Z"  # Zero rated (BR-Z-*); rate = 0; forbids exemption reason
    T_E = "E"  # Exempt from VAT (BR-E-*); rate = 0; requires exemption reason
    T_AE = "AE"  # Reverse charge (BR-AE-*); rate = 0; requires Buyer + Seller VAT IDs
    T_K = "K"  # Intra-community supply (BR-IC-*); also requires BT-72 or BG-14, plus BT-80
    T_G = "G"  # Export outside EU (BR-G-*); rate = 0; Seller VAT or tax-rep VAT (NOT BT-32)
    T_O = "O"  # Not subject to VAT (BR-O-*); rate forbidden, exclusive (BR-O-11..14)
    T_L = "L"  # IGIC — Canary Islands (BR-IG-*); rate ≥ 0
    T_M = "M"  # IPSI — Ceuta / Melilla (BR-IP-*); rate ≥ 0
