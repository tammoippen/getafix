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
    """UNTDID 1001 invoice document type code (BT-3).

    Names follow the official EN 16931 / Factur-X 1.08 code list
    (``ZF24_EN/Documentation/2_EN16931 code lists values v16 ….xlsx``
    sheet ``1001``). Each member's EN16931 interpretation column —
    ``Invoice`` or ``Credit Note`` — determines which document role
    the code plays.

    At BASIC_WL and MINIMUM only :attr:`T_AccountingNote` (``751``)
    may be used — that profile carries only the accounting summary
    rather than an invoice proper.
    """

    T_RequestForPayment = "71"
    T_DebitNoteGoods = "80"
    T_CreditNoteGoods = "81"
    T_MeteredServicesInvoice = "82"
    T_CreditNoteFinancialAdjustment = "83"
    T_DebitNoteFinancialAdjustment = "84"
    T_TaxNotification = "102"
    T_InvoicingDataSheet = "130"
    T_DirectPaymentValuation = "202"
    T_ProvisionalPaymentValuation = "203"
    T_PaymentValuation = "204"
    T_InterimPaymentApplication = "211"
    T_FinalPaymentRequest = "218"
    T_PaymentRequestCompletedUnits = "219"
    T_SelfBilledCreditNote = "261"
    T_ConsolidatedCreditNote = "262"
    T_PriceVariationInvoice = "295"
    T_PriceVariationCreditNote = "296"
    T_DelcredereCreditNote = "308"
    T_ProformaInvoice = "325"
    T_PartialInvoice = "326"
    T_CommercialInvoiceWithPackingList = "331"
    T_CommercialInvoice = "380"
    T_CreditNote = "381"
    T_CommissionNote = "382"
    T_DebitNote = "383"
    T_CorrectedInvoice = "384"
    T_ConsolidatedInvoice = "385"
    T_PrepaymentInvoice = "386"
    T_HireInvoice = "387"
    T_TaxInvoice = "388"
    T_SelfBilledInvoice = "389"
    T_DelcredereInvoice = "390"
    T_FactoredInvoice = "393"
    T_LeaseInvoice = "394"
    T_ConsignmentInvoice = "395"
    T_FactoredCreditNote = "396"
    T_OCRPaymentCreditNote = "420"
    T_DebitAdvice = "456"
    T_ReversalOfDebit = "457"
    T_ReversalOfCredit = "458"
    T_SelfBilledDebitNote = "527"
    T_InsurersInvoice = "575"
    T_ForwardersInvoice = "623"
    T_PortChargesDocument = "633"
    T_AccountingNote = "751"
    T_FreightInvoice = "780"
    T_ConsularInvoice = "870"
    T_PartialConstructionInvoice = "875"
    T_PartialFinalConstructionInvoice = "876"
    T_FinalConstructionInvoice = "877"
    T_CustomsInvoice = "935"


@enum.unique
class UNTDID1001TypeCode(enum.StrEnum):
    """``TypeCode`` discriminator on :class:`AdditionalReferencedDocument`.

    Selects which EN 16931 business term the supporting-document
    reference carries:

    * ``50`` "Price/sales catalogue response" → tender or lot
      reference (BT-17).
    * ``130`` "Invoicing data sheet" → invoiced-object identifier
      (BT-18).
    * ``916`` "Reference paper" → supporting-document reference
      (BT-122).
    """

    T_PriceCatalogueResponse = "50"
    T_InvoicingDataSheet = "130"
    T_ReferencePaper = "916"


@enum.unique
class Incoterms(enum.StrEnum):
    """ICC Incoterms 2020 — delivery condition code (BT-X-145) on
    :class:`~carthorse.schema.agreement.TradeDeliveryTerms`.

    The XSD type ``qdt:DeliveryTermsCodeType`` is an unrestricted
    token; the EXTENDED schematron validates the value against the
    11-entry codelist shipped in ``FACTUR-X_EXTENDED_codedb.xml``
    (Incoterms 2020). ``DAT`` from Incoterms 2010 was renamed
    ``DPU`` in the 2020 revision and isn't accepted.
    """

    EXW = "EXW"
    """Ex Works — buyer collects at seller's premises."""
    FCA = "FCA"
    """Free Carrier — seller delivers to a named carrier."""
    CPT = "CPT"
    """Carriage Paid To — seller pays freight to a named destination."""
    CIP = "CIP"
    """Carriage and Insurance Paid To — CPT plus insurance."""
    DAP = "DAP"
    """Delivered At Place — seller delivers to a named place, unloaded."""
    DPU = "DPU"
    """Delivered at Place Unloaded — DAP with seller-side unloading."""
    DDP = "DDP"
    """Delivered Duty Paid — seller carries all costs incl. import duty."""
    FAS = "FAS"
    """Free Alongside Ship (sea / inland waterway only)."""
    FOB = "FOB"
    """Free On Board (sea / inland waterway only)."""
    CFR = "CFR"
    """Cost and Freight (sea / inland waterway only)."""
    CIF = "CIF"
    """Cost, Insurance and Freight (sea / inland waterway only)."""


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
    T_L = "L"  # IGIC — Canary Islands (BR-AF-*); rate ≥ 0
    T_M = "M"  # IPSI — Ceuta / Melilla (BR-AG-*); rate ≥ 0


# AUTOGEN START Currency
@enum.unique
class Currency(enum.StrEnum):
    """ISO 4217 currency code (BR-CL-03 / BR-CL-04 / BR-CL-05).

    Source: ``Currency`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    AED = "AED"  # UAE Dirham
    AFN = "AFN"  # Afghani
    ALL = "ALL"  # Lek
    AMD = "AMD"  # Armenian Dram
    ANG = "ANG"  # Netherlands Antillean Guilder
    AOA = "AOA"  # Kwanza
    ARS = "ARS"  # Argentine Peso
    AUD = "AUD"  # Australian Dollar
    AWG = "AWG"  # Aruban Florin
    AZN = "AZN"  # Azerbaijan Manat
    BAM = "BAM"  # Convertible Mark
    BBD = "BBD"  # Barbados Dollar
    BDT = "BDT"  # Taka
    BGN = "BGN"  # Bulgarian Lev
    BHD = "BHD"  # Bahraini Dinar
    BIF = "BIF"  # Burundi Franc
    BMD = "BMD"  # Bermudian Dollar
    BND = "BND"  # Brunei Dollar
    BOB = "BOB"  # Boliviano
    BOV = "BOV"  # Mvdol
    BRL = "BRL"  # Brazilian Real
    BSD = "BSD"  # Bahamian Dollar
    BTN = "BTN"  # Ngultrum
    BWP = "BWP"  # Pula
    BYN = "BYN"  # Belarusian Ruble
    BZD = "BZD"  # Belize Dollar
    CAD = "CAD"  # Canadian Dollar
    CDF = "CDF"  # Congolese Franc
    CHE = "CHE"  # WIR Euro
    CHF = "CHF"  # Swiss Franc
    CHW = "CHW"  # WIR Franc
    CLF = "CLF"  # Unidad de Fomento
    CLP = "CLP"  # Chilean Peso
    CNY = "CNY"  # Yuan Renminbi
    CNH = "CNH"  # Renminbi (offshore)
    COP = "COP"  # Colombian Peso
    COU = "COU"  # Unidad de Valor Real
    CRC = "CRC"  # Costa Rican Colon
    CUP = "CUP"  # Cuban Peso
    CVE = "CVE"  # Cabo Verde Escudo
    CZK = "CZK"  # Czech Koruna
    DJF = "DJF"  # Djibouti Franc
    DKK = "DKK"  # Danish Krone
    DOP = "DOP"  # Dominican Peso
    DZD = "DZD"  # Algerian Dinar
    EGP = "EGP"  # Egyptian Pound
    ERN = "ERN"  # Nakfa
    ETB = "ETB"  # Ethiopian Birr
    EUR = "EUR"  # Euro
    FJD = "FJD"  # Fiji Dollar
    FKP = "FKP"  # Falkland Islands Pound
    GBP = "GBP"  # Pound Sterling
    GEL = "GEL"  # Lari
    GHS = "GHS"  # Ghana Cedi
    GIP = "GIP"  # Gibraltar Pound
    GMD = "GMD"  # Dalasi
    GNF = "GNF"  # Guinean Franc
    GTQ = "GTQ"  # Quetzal
    GYD = "GYD"  # Guyana Dollar
    HKD = "HKD"  # Hong Kong Dollar
    HNL = "HNL"  # Lempira
    HTG = "HTG"  # Gourde
    HUF = "HUF"  # Forint
    IDR = "IDR"  # Rupiah
    ILS = "ILS"  # New Israeli Sheqel
    INR = "INR"  # Indian Rupee
    IQD = "IQD"  # Iraqi Dinar
    IRR = "IRR"  # Iranian Rial
    ISK = "ISK"  # Iceland Krona
    JMD = "JMD"  # Jamaican Dollar
    JOD = "JOD"  # Jordanian Dinar
    JPY = "JPY"  # Yen
    KES = "KES"  # Kenyan Shilling
    KGS = "KGS"  # Som
    KHR = "KHR"  # Riel
    KMF = "KMF"  # Comorian Franc
    KPW = "KPW"  # North Korean Won
    KRW = "KRW"  # Won
    KWD = "KWD"  # Kuwaiti Dinar
    KYD = "KYD"  # Cayman Islands Dollar
    KZT = "KZT"  # Tenge
    LAK = "LAK"  # Lao Kip
    LBP = "LBP"  # Lebanese Pound
    LKR = "LKR"  # Sri Lanka Rupee
    LRD = "LRD"  # Liberian Dollar
    LSL = "LSL"  # Loti
    LYD = "LYD"  # Libyan Dinar
    MAD = "MAD"  # Moroccan Dirham
    MDL = "MDL"  # Moldovan Leu
    MGA = "MGA"  # Malagasy Ariary
    MKD = "MKD"  # Denar
    MMK = "MMK"  # Kyat
    MNT = "MNT"  # Tugrik
    MOP = "MOP"  # Pataca
    MRU = "MRU"  # Ouguiya
    MUR = "MUR"  # Mauritius Rupee
    MVR = "MVR"  # Rufiyaa
    MWK = "MWK"  # Malawi Kwacha
    MXN = "MXN"  # Mexican Peso
    MXV = "MXV"  # Mexican Unidad de Inversion (UDI)
    MYR = "MYR"  # Malaysian Ringgit
    MZN = "MZN"  # Mozambique Metical
    NAD = "NAD"  # Namibia Dollar
    NGN = "NGN"  # Naira
    NIO = "NIO"  # Cordoba Oro
    NOK = "NOK"  # Norwegian Krone
    NPR = "NPR"  # Nepalese Rupee
    NZD = "NZD"  # New Zealand Dollar
    OMR = "OMR"  # Rial Omani
    PAB = "PAB"  # Balboa
    PEN = "PEN"  # Sol
    PGK = "PGK"  # Kina
    PHP = "PHP"  # Philippine Peso
    PKR = "PKR"  # Pakistan Rupee
    PLN = "PLN"  # Zloty
    PYG = "PYG"  # Guarani
    QAR = "QAR"  # Qatari Rial
    RON = "RON"  # Romanian Leu
    RSD = "RSD"  # Serbian Dinar
    RUB = "RUB"  # Russian Ruble
    RWF = "RWF"  # Rwanda Franc
    SAR = "SAR"  # Saudi Riyal
    SBD = "SBD"  # Solomon Islands Dollar
    SCR = "SCR"  # Seychelles Rupee
    SDG = "SDG"  # Sudanese Pound
    SEK = "SEK"  # Swedish Krona
    SGD = "SGD"  # Singapore Dollar
    SHP = "SHP"  # Saint Helena Pound
    SLE = "SLE"  # Sierra Leone (new valuation 2022)
    SOS = "SOS"  # Somali Shilling
    SRD = "SRD"  # Surinam Dollar
    SSP = "SSP"  # South Sudanese Pound
    STN = "STN"  # Dobra
    SVC = "SVC"  # El Salvador Colon
    SYP = "SYP"  # Syrian Pound
    SZL = "SZL"  # Lilangeni
    THB = "THB"  # Baht
    TJS = "TJS"  # Somoni
    TMT = "TMT"  # Turkmenistan New Manat
    TND = "TND"  # Tunisian Dinar
    TOP = "TOP"  # Pa'anga
    TRY = "TRY"  # Turkish Lira
    TTD = "TTD"  # Trinidad and Tobago Dollar
    TWD = "TWD"  # New Taiwan Dollar
    TZS = "TZS"  # Tanzanian Shilling
    UAH = "UAH"  # Hryvnia
    UGX = "UGX"  # Uganda Shilling
    USD = "USD"  # US Dollar
    USN = "USN"  # US Dollar (Next day)
    UYI = "UYI"  # Uruguay Peso en Unidades Indexadas (UI)
    UYU = "UYU"  # Peso Uruguayo
    UYW = "UYW"  # Unidad Previsional
    UZS = "UZS"  # Uzbekistan Sum
    VED = "VED"  # Bolívar Soberano, new valuation
    VES = "VES"  # Bolívar Soberano
    VND = "VND"  # Dong
    VUV = "VUV"  # Vatu
    WST = "WST"  # Tala
    XAF = "XAF"  # CFA Franc BEAC
    XAG = "XAG"  # Silver
    XAU = "XAU"  # Gold
    XBA = "XBA"  # Bond Markets Unit European Composite Unit (EURCO)
    XBB = "XBB"  # Bond Markets Unit European Monetary Unit (E.M.U.-6)
    XBC = "XBC"  # Bond Markets Unit European Unit of Account 9 (E.U.A.-9)
    XBD = "XBD"  # Bond Markets Unit European Unit of Account 17 (E.U.A.-17)
    XCD = "XCD"  # East Caribbean Dollar
    XDR = "XDR"  # SDR (Special Drawing Right)
    XOF = "XOF"  # CFA Franc BCEAO
    XPD = "XPD"  # Palladium
    XPF = "XPF"  # CFP Franc
    XPT = "XPT"  # Platinum
    XSU = "XSU"  # Sucre
    XTS = "XTS"  # Codes specifically reserved for testing purposes
    XUA = "XUA"  # ADB Unit of Account
    XXX = "XXX"  # The codes assigned for transactions where no currency is inv
    YER = "YER"  # Yemeni Rial
    ZAR = "ZAR"  # Rand
    ZMW = "ZMW"  # Zambian Kwacha
    ZWG = "ZWG"  # Zimbabwe Gold


# AUTOGEN END Currency


# AUTOGEN START Country
@enum.unique
class Country(enum.StrEnum):
    """ISO 3166-1 alpha-2 country code (BR-CL-14 / BR-CL-15).

    Source: ``Country`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    AD = "AD"  # Andorra
    AE = "AE"  # United Arab Emirates (the)
    AF = "AF"  # Afghanistan
    AG = "AG"  # Antigua and Barbuda
    AI = "AI"  # Anguilla
    AL = "AL"  # Albania
    AM = "AM"  # Armenia
    AO = "AO"  # Angola
    AQ = "AQ"  # Antarctica
    AR = "AR"  # Argentina
    AS = "AS"  # American Samoa
    AT = "AT"  # Austria
    AU = "AU"  # Australia
    AW = "AW"  # Aruba
    AX = "AX"  # Åland Islands
    AZ = "AZ"  # Azerbaijan
    BA = "BA"  # Bosnia and Herzegovina
    BB = "BB"  # Barbados
    BD = "BD"  # Bangladesh
    BE = "BE"  # Belgium
    BF = "BF"  # Burkina Faso
    BG = "BG"  # Bulgaria
    BH = "BH"  # Bahrain
    BI = "BI"  # Burundi
    BJ = "BJ"  # Benin
    BL = "BL"  # Saint Barthélemy
    BM = "BM"  # Bermuda
    BN = "BN"  # Brunei Darussalam
    BO = "BO"  # Bolivia (Plurinational State of)
    BQ = "BQ"  # Bonaire, Sint Eustatius and Saba
    BR = "BR"  # Brazil
    BS = "BS"  # Bahamas (The)
    BT = "BT"  # Bhutan
    BV = "BV"  # Bouvet Island
    BW = "BW"  # Botswana
    BY = "BY"  # Belarus
    BZ = "BZ"  # Belize
    CA = "CA"  # Canada
    CC = "CC"  # Cocos (Keeling) Islands (the)
    CD = "CD"  # Congo (the Democratic Republic of the)
    CF = "CF"  # Central African Republic (the)
    CG = "CG"  # Congo (the)
    CH = "CH"  # Switzerland
    CI = "CI"  # Côte d'Ivoire
    CK = "CK"  # Cook Islands (the)
    CL = "CL"  # Chile
    CM = "CM"  # Cameroon
    CN = "CN"  # China
    CO = "CO"  # Colombia
    CR = "CR"  # Costa Rica
    CU = "CU"  # Cuba
    CV = "CV"  # Cabo Verde
    CW = "CW"  # Curaçao
    CX = "CX"  # Christmas Island
    CY = "CY"  # Cyprus
    CZ = "CZ"  # Czechia
    DE = "DE"  # Germany
    DJ = "DJ"  # Djibouti
    DK = "DK"  # Denmark
    DM = "DM"  # Dominica
    DO = "DO"  # Dominican Republic (the)
    DZ = "DZ"  # Algeria
    EC = "EC"  # Ecuador
    EE = "EE"  # Estonia
    EG = "EG"  # Egypt
    EH = "EH"  # Western Sahara*
    ER = "ER"  # Eritrea
    ES = "ES"  # Spain
    ET = "ET"  # Ethiopia
    FI = "FI"  # Finland
    FJ = "FJ"  # Fiji
    FK = "FK"  # Falkland Islands (the) [Malvinas]
    FM = "FM"  # Micronesia (Federated States of)
    FO = "FO"  # Faroe Islands (the)
    FR = "FR"  # France
    GA = "GA"  # Gabon
    GB = "GB"  # United Kingdom of Great Britain and Northern Ireland (the)
    GD = "GD"  # Grenada
    GE = "GE"  # Georgia
    GF = "GF"  # French Guiana
    GG = "GG"  # Guernsey
    GH = "GH"  # Ghana
    GI = "GI"  # Gibraltar
    GL = "GL"  # Greenland
    GM = "GM"  # Gambia (the)
    GN = "GN"  # Guinea
    GP = "GP"  # Guadeloupe
    GQ = "GQ"  # Equatorial Guinea
    GR = "GR"  # Greece
    GS = "GS"  # South Georgia and the South Sandwich Islands
    GT = "GT"  # Guatemala
    GU = "GU"  # Guam
    GW = "GW"  # Guinea-Bissau
    GY = "GY"  # Guyana
    HK = "HK"  # Hong Kong
    HM = "HM"  # Heard Island and McDonald Islands
    HN = "HN"  # Honduras
    HR = "HR"  # Croatia
    HT = "HT"  # Haiti
    HU = "HU"  # Hungary
    ID = "ID"  # Indonesia
    IE = "IE"  # Ireland
    IL = "IL"  # Israel
    IM = "IM"  # Isle of Man
    IN = "IN"  # India
    IO = "IO"  # British Indian Ocean Territory (the)
    IQ = "IQ"  # Iraq
    IR = "IR"  # Iran (Islamic Republic of)
    IS = "IS"  # Iceland
    IT = "IT"  # Italy
    JE = "JE"  # Jersey
    JM = "JM"  # Jamaica
    JO = "JO"  # Jordan
    JP = "JP"  # Japan
    KE = "KE"  # Kenya
    KG = "KG"  # Kyrgyzstan
    KH = "KH"  # Cambodia
    KI = "KI"  # Kiribati
    KM = "KM"  # Comoros (the)
    KN = "KN"  # Saint Kitts and Nevis
    KP = "KP"  # Korea (the Democratic People's Republic of)
    KR = "KR"  # Korea (the Republic of)
    KW = "KW"  # Kuwait
    KY = "KY"  # Cayman Islands (the)
    KZ = "KZ"  # Kazakhstan
    LA = "LA"  # Lao People's Democratic Republic (the)
    LB = "LB"  # Lebanon
    LC = "LC"  # Saint Lucia
    LI = "LI"  # Liechtenstein
    LK = "LK"  # Sri Lanka
    LR = "LR"  # Liberia
    LS = "LS"  # Lesotho
    LT = "LT"  # Lithuania
    LU = "LU"  # Luxembourg
    LV = "LV"  # Latvia
    LY = "LY"  # Libya
    MA = "MA"  # Morocco
    MC = "MC"  # Monaco
    MD = "MD"  # Moldova (the Republic of)
    ME = "ME"  # Montenegro
    MF = "MF"  # Saint Martin (French part)
    MG = "MG"  # Madagascar
    MH = "MH"  # Marshall Islands (the)
    MK = "MK"  # North Macedonia
    ML = "ML"  # Mali
    MM = "MM"  # Myanmar
    MN = "MN"  # Mongolia
    MO = "MO"  # Macao
    MP = "MP"  # Northern Mariana Islands (the)
    MQ = "MQ"  # Martinique
    MR = "MR"  # Mauritania
    MS = "MS"  # Montserrat
    MT = "MT"  # Malta
    MU = "MU"  # Mauritius
    MV = "MV"  # Maldives
    MW = "MW"  # Malawi
    MX = "MX"  # Mexico
    MY = "MY"  # Malaysia
    MZ = "MZ"  # Mozambique
    NA = "NA"  # Namibia
    NC = "NC"  # New Caledonia
    NE = "NE"  # Niger (the)
    NF = "NF"  # Norfolk Island
    NG = "NG"  # Nigeria
    NI = "NI"  # Nicaragua
    NL = "NL"  # Netherlands (the)
    NO = "NO"  # Norway
    NP = "NP"  # Nepal
    NR = "NR"  # Nauru
    NU = "NU"  # Niue
    NZ = "NZ"  # New Zealand
    OM = "OM"  # Oman
    PA = "PA"  # Panama
    PE = "PE"  # Peru
    PF = "PF"  # French Polynesia
    PG = "PG"  # Papua New Guinea
    PH = "PH"  # Philippines (the)
    PK = "PK"  # Pakistan
    PL = "PL"  # Poland
    PM = "PM"  # Saint Pierre and Miquelon
    PN = "PN"  # Pitcairn
    PR = "PR"  # Puerto Rico
    PS = "PS"  # Palestine, State of
    PT = "PT"  # Portugal
    PW = "PW"  # Palau
    PY = "PY"  # Paraguay
    QA = "QA"  # Qatar
    RE = "RE"  # Réunion
    RO = "RO"  # Romania
    RS = "RS"  # Serbia
    RU = "RU"  # Russian Federation (the)
    RW = "RW"  # Rwanda
    SA = "SA"  # Saudi Arabia
    SB = "SB"  # Solomon Islands
    SC = "SC"  # Seychelles
    SD = "SD"  # Sudan (the)
    SE = "SE"  # Sweden
    SG = "SG"  # Singapore
    SH = "SH"  # Saint Helena, Ascension and Tristan da Cunha
    SI = "SI"  # Slovenia
    SJ = "SJ"  # Svalbard and Jan Mayen
    SK = "SK"  # Slovakia
    SL = "SL"  # Sierra Leone
    SM = "SM"  # San Marino
    SN = "SN"  # Senegal
    SO = "SO"  # Somalia
    SR = "SR"  # Suriname
    SS = "SS"  # South Sudan
    ST = "ST"  # Sao Tome and Principe
    SV = "SV"  # El Salvador
    SX = "SX"  # Sint Maarten (Dutch part)
    SY = "SY"  # Syrian Arab Republic (the)
    SZ = "SZ"  # Eswatini
    TC = "TC"  # Turks and Caicos Islands (the)
    TD = "TD"  # Chad
    TF = "TF"  # French Southern Territories (the)
    TG = "TG"  # Togo
    TH = "TH"  # Thailand
    TJ = "TJ"  # Tajikistan
    TK = "TK"  # Tokelau
    TL = "TL"  # Timor-Leste
    TM = "TM"  # Turkmenistan
    TN = "TN"  # Tunisia
    TO = "TO"  # Tonga
    TR = "TR"  # Türkiye
    TT = "TT"  # Trinidad and Tobago
    TV = "TV"  # Tuvalu
    TW = "TW"  # Taiwan (Province of China)
    TZ = "TZ"  # Tanzania, the United Republic of
    UA = "UA"  # Ukraine
    UG = "UG"  # Uganda
    UM = "UM"  # United States Minor Outlying Islands (the)
    US = "US"  # United States of America (the)
    UY = "UY"  # Uruguay
    UZ = "UZ"  # Uzbekistan
    VA = "VA"  # Holy See (the)
    VC = "VC"  # Saint Vincent and the Grenadines
    VE = "VE"  # Venezuela (Bolivarian Republic of)
    VG = "VG"  # Virgin Islands (British)
    VI = "VI"  # Virgin Islands (U.S.)
    VN = "VN"  # Viet Nam
    VU = "VU"  # Vanuatu
    WF = "WF"  # Wallis and Futuna
    WS = "WS"  # Samoa
    YE = "YE"  # Yemen
    YT = "YT"  # Mayotte
    ZA = "ZA"  # South Africa
    ZM = "ZM"  # Zambia
    ZW = "ZW"  # Zimbabwe
    CODE_1A = "1A"  # Kosovo
    XI = "XI"  # United Kingdom (Northern Ireland)


# AUTOGEN END Country


# AUTOGEN START UNTDID4461PaymentMeansCode
@enum.unique
class UNTDID4461PaymentMeansCode(enum.StrEnum):
    """UNTDID 4461 payment means code (BR-CL-16) — BT-81.

    Source: ``Payment`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    CODE_1 = "1"  # Instrument not defined
    CODE_2 = "2"  # Automated clearing house credit
    CODE_3 = "3"  # Automated clearing house debit
    CODE_4 = "4"  # ACH demand debit reversal
    CODE_5 = "5"  # ACH demand credit reversal
    CODE_6 = "6"  # ACH demand credit
    CODE_7 = "7"  # ACH demand debit
    CODE_8 = "8"  # Hold
    CODE_9 = "9"  # National or regional clearing
    CODE_10 = "10"  # In cash
    CODE_11 = "11"  # ACH savings credit reversal
    CODE_12 = "12"  # ACH savings debit reversal
    CODE_13 = "13"  # ACH savings credit
    CODE_14 = "14"  # ACH savings debit
    CODE_15 = "15"  # Bookentry credit
    CODE_16 = "16"  # Bookentry debit
    CODE_17 = "17"  # ACH demand cash concentration/disbursement (CCD) credit
    CODE_18 = "18"  # ACH demand cash concentration/disbursement (CCD) debit
    CODE_19 = "19"  # ACH demand corporate trade payment (CTP) credit
    CODE_20 = "20"  # Cheque
    CODE_21 = "21"  # Banker's draft
    CODE_22 = "22"  # Certified banker's draft
    CODE_23 = "23"  # Bank cheque (issued by a banking or similar establishment)
    CODE_24 = "24"  # Bill of exchange awaiting acceptance
    CODE_25 = "25"  # Certified cheque
    CODE_26 = "26"  # Local cheque
    CODE_27 = "27"  # ACH demand corporate trade payment (CTP) debit
    CODE_28 = "28"  # ACH demand corporate trade exchange (CTX) credit
    CODE_29 = "29"  # ACH demand corporate trade exchange (CTX) debit
    CODE_30 = "30"  # Credit transfer
    CODE_31 = "31"  # Debit transfer
    CODE_32 = "32"  # ACH demand cash concentration/disbursement plus (CCD+)
    CODE_33 = "33"  # ACH demand cash concentration/disbursement plus (CCD+)
    CODE_34 = "34"  # ACH prearranged payment and deposit (PPD)
    CODE_35 = "35"  # ACH savings cash concentration/disbursement (CCD) credit
    CODE_36 = "36"  # ACH savings cash concentration/disbursement (CCD) debit
    CODE_37 = "37"  # ACH savings corporate trade payment (CTP) credit
    CODE_38 = "38"  # ACH savings corporate trade payment (CTP) debit
    CODE_39 = "39"  # ACH savings corporate trade exchange (CTX) credit
    CODE_40 = "40"  # ACH savings corporate trade exchange (CTX) debit
    CODE_41 = "41"  # ACH savings cash concentration/disbursement plus (CCD+)
    CODE_42 = "42"  # Payment to bank account
    CODE_43 = "43"  # ACH savings cash concentration/disbursement plus (CCD+)
    CODE_44 = "44"  # Accepted bill of exchange
    CODE_45 = "45"  # Referenced home-banking credit transfer
    CODE_46 = "46"  # Interbank debit transfer
    CODE_47 = "47"  # Home-banking debit transfer
    CODE_48 = "48"  # Bank card
    CODE_49 = "49"  # Direct debit
    CODE_50 = "50"  # Payment by postgiro
    CODE_51 = "51"  # FR, norme 6 97-Telereglement CFONB (French Organisation for
    CODE_52 = "52"  # Urgent commercial payment
    CODE_53 = "53"  # Urgent Treasury Payment
    CODE_54 = "54"  # Credit card
    CODE_55 = "55"  # Debit card
    CODE_56 = "56"  # Bankgiro
    CODE_57 = "57"  # Standing agreement
    CODE_58 = "58"  # SEPA credit transfer
    CODE_59 = "59"  # SEPA direct debit
    CODE_60 = "60"  # Promissory note
    CODE_61 = "61"  # Promissory note signed by the debtor
    CODE_62 = "62"  # Promissory note signed by the debtor and endorsed by a bank
    CODE_63 = "63"  # Promissory note signed by the debtor and endorsed by a
    CODE_64 = "64"  # Promissory note signed by a bank
    CODE_65 = "65"  # Promissory note signed by a bank and endorsed by another
    CODE_66 = "66"  # Promissory note signed by a third party
    CODE_67 = "67"  # Promissory note signed by a third party and endorsed by a
    CODE_68 = "68"  # Online payment service
    CODE_69 = "69"  # Transfer Advice
    CODE_70 = "70"  # Bill drawn by the creditor on the debtor
    CODE_74 = "74"  # Bill drawn by the creditor on a bank
    CODE_75 = "75"  # Bill drawn by the creditor, endorsed by another bank
    CODE_76 = "76"  # Bill drawn by the creditor on a bank and endorsed by a
    CODE_77 = "77"  # Bill drawn by the creditor on a third party
    CODE_78 = "78"  # Bill drawn by creditor on third party, accepted and
    CODE_91 = "91"  # Not transferable banker's draft
    CODE_92 = "92"  # Not transferable local cheque
    CODE_93 = "93"  # Reference giro
    CODE_94 = "94"  # Urgent giro
    CODE_95 = "95"  # Free format giro
    CODE_96 = "96"  # Requested method for payment was not used
    CODE_97 = "97"  # Clearing between partners
    CODE_98 = "98"  # JP, Electronically Recorded Monetary Claims
    ZZZ = "ZZZ"  # Mutually defined


# AUTOGEN END UNTDID4461PaymentMeansCode


# AUTOGEN START UNTDID5189AllowanceReasonCode
@enum.unique
class UNTDID5189AllowanceReasonCode(enum.StrEnum):
    """UNTDID 5189 allowance reason code (BR-CL-19) — BT-98 / BT-140.

    Source: ``Allowance`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    CODE_41 = "41"  # Bonus for works ahead of schedule
    CODE_42 = "42"  # Other bonus
    CODE_60 = "60"  # Manufacturer's consumer discount
    CODE_62 = "62"  # Due to military status
    CODE_63 = "63"  # Due to work accident
    CODE_64 = "64"  # Special agreement
    CODE_65 = "65"  # Production error discount
    CODE_66 = "66"  # New outlet discount
    CODE_67 = "67"  # Sample discount
    CODE_68 = "68"  # End-of-range discount
    CODE_70 = "70"  # Incoterm discount
    CODE_71 = "71"  # Point of sales threshold allowance
    CODE_88 = "88"  # Material surcharge/deduction
    CODE_95 = "95"  # Discount
    CODE_100 = "100"  # Special rebate
    CODE_102 = "102"  # Fixed long term
    CODE_103 = "103"  # Temporary
    CODE_104 = "104"  # Standard
    CODE_105 = "105"  # Yearly turnover


# AUTOGEN END UNTDID5189AllowanceReasonCode


# AUTOGEN START UNTDID2475TaxPointDateCode
@enum.unique
class UNTDID2475TaxPointDateCode(enum.StrEnum):
    """UNTDID 2475 tax-point date code (BR-CL-06) — BT-8.

    Source: ``Time`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    CODE_2475_Code = "2475 Code"  # Value
    CODE_5 = "5"  # Date of invoice
    CODE_29 = "29"  # Date of delivery of goods to establishments/domicile/site
    CODE_72 = "72"  # Payment date


# AUTOGEN END UNTDID2475TaxPointDateCode


# AUTOGEN START EASCode
@enum.unique
class EASCode(enum.StrEnum):
    """EAS electronic address scheme id (BR-CL-25) — BT-34-1 / BT-49-1.

    Source: ``EAS`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    CODE_0002 = "0002"  # System Information et Repertoire des Entreprise et des Etabl
    CODE_0007 = "0007"  # Organisationsnummer
    CODE_0009 = "0009"  # SIRET-CODE
    CODE_0037 = "0037"  # LY-tunnus
    CODE_0060 = "0060"  # Data Universal Numbering System (D-U-N-S Number)
    CODE_0088 = "0088"  # EAN Location Code
    CODE_0096 = "0096"  # The Danish Business Authority - P-number (DK:P)
    CODE_0097 = "0097"  # FTI - Ediforum Italia, (EDIRA compliant)
    CODE_0106 = "0106"  # Vereniging van Kamers van Koophandel en Fabrieken in Nederla
    CODE_0130 = "0130"  # Directorates of the European Commission
    CODE_0135 = "0135"  # SIA Object Identifiers
    CODE_0142 = "0142"  # SECETI Object Identifiers
    CODE_0147 = "0147"  # Standard Company Code
    CODE_0151 = "0151"  # Australian Business Number (ABN) Scheme
    CODE_0154 = "0154"  # Identification number of economic subjects: (ICO)
    CODE_0158 = "0158"  # Identification number of economic subject (ICO) Act on State
    CODE_0170 = "0170"  # Teikoku Company Code
    CODE_0177 = "0177"  # Odette International Limited
    CODE_0183 = "0183"  # Numéro d'identification suisse des enterprises (IDE), Swiss
    CODE_0184 = "0184"  # DIGSTORG
    CODE_0188 = "0188"  # Corporate Number of The Social Security and Tax Number Syste
    CODE_0190 = "0190"  # Dutch Originator's Identification Number
    CODE_0191 = "0191"  # Centre of Registers and Information Systems of the Ministry
    CODE_0192 = "0192"  # Enhetsregisteret ved Bronnoysundregisterne
    CODE_0193 = "0193"  # UBL.BE party identifier
    CODE_0194 = "0194"  # KOIOS Open Technical Dictionary
    CODE_0195 = "0195"  # Singapore UEN identifier
    CODE_0196 = "0196"  # Kennitala - Iceland legal id for individuals and legal entit
    CODE_0198 = "0198"  # ERSTORG
    CODE_0199 = "0199"  # Global legal entity identifier (GLEIF)
    CODE_0200 = "0200"  # Legal entity code (Lithuania)
    CODE_0201 = "0201"  # Codice Univoco Unità Organizzativa iPA
    CODE_0202 = "0202"  # Indirizzo di Posta Elettronica Certificata
    CODE_0203 = "0203"  # eDelivery Network Participant identifier
    CODE_0204 = "0204"  # Leitweg-ID
    CODE_0205 = "0205"  # CODDEST
    CODE_0208 = "0208"  # Numero d'entreprise / ondernemingsnummer / Unternehmensnumme
    CODE_0209 = "0209"  # GS1 identification keys
    CODE_0210 = "0210"  # CODICE FISCALE
    CODE_0211 = "0211"  # PARTITA IVA
    CODE_0212 = "0212"  # Finnish Organization Identifier
    CODE_0213 = "0213"  # Finnish Organization Value Add Tax Identifier
    CODE_0215 = "0215"  # Net service ID
    CODE_0216 = "0216"  # OVTcode
    CODE_0217 = "0217"  # The Netherlands Chamber of Commerce and Industry establishme
    CODE_0218 = "0218"  # Unified registration number (Latvia)
    CODE_0221 = "0221"  # The registered number of the qualified invoice issuer
    CODE_0225 = "0225"  # FRCTC ELECTRONIC ADDRESS
    CODE_0230 = "0230"  # National e-Invoicing Framework
    CODE_0235 = "0235"  # UAE Tax Identification Number (TIN)
    CODE_0240 = "0240"  # Register of legal persons (in French : Répertoire des person
    CODE_0244 = "0244"  # Tax Identification (Tax ID), Nigeria
    CODE_9910 = "9910"  # Hungary VAT number
    CODE_9913 = "9913"  # Business Registers Network
    CODE_9914 = "9914"  # Österreichische Umsatzsteuer-Identifikationsnummer
    CODE_9915 = "9915"  # Österreichisches Verwaltungs bzw. Organisationskennzeichen
    CODE_9918 = "9918"  # SOCIETY FOR WORLDWIDE INTERBANK FINANCIAL, TELECOMMUNICATION
    CODE_9919 = "9919"  # Kennziffer des Unternehmensregisters
    CODE_9920 = "9920"  # Agencia Española de Administración Tributaria
    CODE_9922 = "9922"  # Andorra VAT number
    CODE_9923 = "9923"  # Albania VAT number
    CODE_9924 = "9924"  # Bosnia and Herzegovina VAT number
    CODE_9925 = "9925"  # Belgium VAT number
    CODE_9926 = "9926"  # Bulgaria VAT number
    CODE_9927 = "9927"  # Switzerland VAT number
    CODE_9928 = "9928"  # Cyprus VAT number
    CODE_9929 = "9929"  # Czech Republic VAT number
    CODE_9930 = "9930"  # Germany VAT number
    CODE_9931 = "9931"  # Estonia VAT number
    CODE_9932 = "9932"  # United Kingdom VAT number
    CODE_9933 = "9933"  # Greece VAT number
    CODE_9934 = "9934"  # Croatia VAT number
    CODE_9935 = "9935"  # Ireland VAT number
    CODE_9936 = "9936"  # Liechtenstein VAT number
    CODE_9937 = "9937"  # Lithuania VAT number
    CODE_9938 = "9938"  # Luxemburg VAT number
    CODE_9939 = "9939"  # Latvia VAT number
    CODE_9940 = "9940"  # Monaco VAT number
    CODE_9941 = "9941"  # Montenegro VAT number
    CODE_9942 = "9942"  # Macedonia, the former Yugoslav Republic of VAT number
    CODE_9943 = "9943"  # Malta VAT number
    CODE_9944 = "9944"  # Netherlands VAT number
    CODE_9945 = "9945"  # Poland VAT number
    CODE_9946 = "9946"  # Portugal VAT number
    CODE_9947 = "9947"  # Romania VAT number
    CODE_9948 = "9948"  # Serbia VAT number
    CODE_9949 = "9949"  # Slovenia VAT number
    CODE_9950 = "9950"  # Slovakia VAT number
    CODE_9951 = "9951"  # San Marino VAT number
    CODE_9952 = "9952"  # Turkey VAT number
    CODE_9953 = "9953"  # Holy See (Vatican City State) VAT number
    CODE_9957 = "9957"  # French VAT number
    CODE_9959 = "9959"  # Employer Identification Number (EIN, USA)
    AN = "AN"  # O.F.T.P. (ODETTE File Transfer Protocol)
    AQ = "AQ"  # X.400 address for mail text
    AS = "AS"  # AS2 exchange
    AU = "AU"  # File Transfer Protocol
    EM = "EM"  # Electronic mail (SMPT)


# AUTOGEN END EASCode


# AUTOGEN START VATEXCode
@enum.unique
class VATEXCode(enum.StrEnum):
    """CEF VATEX exemption-reason code (BR-CL-22) — BT-121.

    Source: ``VATEX`` sheet of the EN16931 code lists v16
    XLSX shipped with Factur-X 1.08 (autogenerated).
    """

    VATEX_EU_79_C = (
        "VATEX-EU-79-C"  # Exempt based on article 79, point c of Council Directive 200
    )
    VATEX_EU_132 = (
        "VATEX-EU-132"  # Exempt based on article 132 of Council Directive 2006/112/EC
    )
    VATEX_EU_132_1A = "VATEX-EU-132-1A"  # Exempt based on article 132, section 1 (a) of Council Direct
    VATEX_EU_132_1B = "VATEX-EU-132-1B"  # Exempt based on article 132, section 1 (b) of Council Direct
    VATEX_EU_132_1C = "VATEX-EU-132-1C"  # Exempt based on article 132, section 1 (c) of Council Direct
    VATEX_EU_132_1D = "VATEX-EU-132-1D"  # Exempt based on article 132, section 1 (d) of Council Direct
    VATEX_EU_132_1E = "VATEX-EU-132-1E"  # Exempt based on article 132, section 1 (e) of Council Direct
    VATEX_EU_132_1F = "VATEX-EU-132-1F"  # Exempt based on article 132, section 1 (f) of Council Direct
    VATEX_EU_132_1G = "VATEX-EU-132-1G"  # Exempt based on article 132, section 1 (g) of Council Direct
    VATEX_EU_132_1H = "VATEX-EU-132-1H"  # Exempt based on article 132, section 1 (h) of Council Direct
    VATEX_EU_132_1I = "VATEX-EU-132-1I"  # Exempt based on article 132, section 1 (i) of Council Direct
    VATEX_EU_132_1J = "VATEX-EU-132-1J"  # Exempt based on article 132, section 1 (j) of Council Direct
    VATEX_EU_132_1K = "VATEX-EU-132-1K"  # Exempt based on article 132, section 1 (k) of Council Direct
    VATEX_EU_132_1L = "VATEX-EU-132-1L"  # Exempt based on article 132, section 1 (l) of Council Direct
    VATEX_EU_132_1M = "VATEX-EU-132-1M"  # Exempt based on article 132, section 1 (m) of Council Direct
    VATEX_EU_132_1N = "VATEX-EU-132-1N"  # Exempt based on article 132, section 1 (n) of Council Direct
    VATEX_EU_132_1O = "VATEX-EU-132-1O"  # Exempt based on article 132, section 1 (o) of Council Direct
    VATEX_EU_132_1P = "VATEX-EU-132-1P"  # Exempt based on article 132, section 1 (p) of Council Direct
    VATEX_EU_132_1Q = "VATEX-EU-132-1Q"  # Exempt based on article 132, section 1 (q) of Council Direct
    VATEX_EU_135_1 = (
        "VATEX-EU-135-1"  # Exempt based on article 135, section 1 of Council Directive
    )
    VATEX_EU_143 = (
        "VATEX-EU-143"  # Exempt based on article 143 of Council Directive 2006/112/EC
    )
    VATEX_EU_143_1A = "VATEX-EU-143-1A"  # Exempt based on article 143, section 1 (a) of Council Direct
    VATEX_EU_143_1B = "VATEX-EU-143-1B"  # Exempt based on article 143, section 1 (b) of Council Direct
    VATEX_EU_143_1C = "VATEX-EU-143-1C"  # Exempt based on article 143, section 1 (c) of Council Direct
    VATEX_EU_143_1D = "VATEX-EU-143-1D"  # Exempt based on article 143, section 1 (d) of Council Direct
    VATEX_EU_143_1E = "VATEX-EU-143-1E"  # Exempt based on article 143, section 1 (e) of Council Direct
    VATEX_EU_143_1F = "VATEX-EU-143-1F"  # Exempt based on article 143, section 1 (f) of Council Direct
    VATEX_EU_143_1FA = "VATEX-EU-143-1FA"  # Exempt based on article 143, section 1 (fa) of Council Direc
    VATEX_EU_143_1G = "VATEX-EU-143-1G"  # Exempt based on article 143, section 1 (g) of Council Direct
    VATEX_EU_143_1H = "VATEX-EU-143-1H"  # Exempt based on article 143, section 1 (h) of Council Direct
    VATEX_EU_143_1I = "VATEX-EU-143-1I"  # Exempt based on article 143, section 1 (i) of Council Direct
    VATEX_EU_143_1J = "VATEX-EU-143-1J"  # Exempt based on article 143, section 1 (j) of Council Direct
    VATEX_EU_143_1K = "VATEX-EU-143-1K"  # Exempt based on article 143, section 1 (k) of Council Direct
    VATEX_EU_143_1L = "VATEX-EU-143-1L"  # Exempt based on article 143, section 1 (l) of Council Direct
    VATEX_EU_144 = (
        "VATEX-EU-144"  # Exempt based on article 144 of Council Directive 2006/112/EC
    )
    VATEX_EU_146_1E = "VATEX-EU-146-1E"  # Exempt based on article 146 section 1 (e) of Council Directi
    VATEX_EU_148 = (
        "VATEX-EU-148"  # Exempt based on article 148 of Council Directive 2006/112/EC
    )
    VATEX_EU_148_A = (
        "VATEX-EU-148-A"  # Exempt based on article 148, section (a) of Council Directiv
    )
    VATEX_EU_148_B = (
        "VATEX-EU-148-B"  # Exempt based on article 148, section (b) of Council Directiv
    )
    VATEX_EU_148_C = (
        "VATEX-EU-148-C"  # Exempt based on article 148, section (c) of Council Directiv
    )
    VATEX_EU_148_D = (
        "VATEX-EU-148-D"  # Exempt based on article 148, section (d) of Council Directiv
    )
    VATEX_EU_148_E = (
        "VATEX-EU-148-E"  # Exempt based on article 148, section (e) of Council Directiv
    )
    VATEX_EU_148_F = (
        "VATEX-EU-148-F"  # Exempt based on article 148, section (f) of Council Directiv
    )
    VATEX_EU_148_G = (
        "VATEX-EU-148-G"  # Exempt based on article 148, section (g) of Council Directiv
    )
    VATEX_EU_151 = (
        "VATEX-EU-151"  # Exempt based on article 151 of Council Directive 2006/112/EC
    )
    VATEX_EU_151_1A = "VATEX-EU-151-1A"  # Exempt based on article 151, section 1 (a) of Council Direct
    VATEX_EU_151_1AA = "VATEX-EU-151-1AA"  # Exempt based on article 151, section 1 (aa) of Council Direc
    VATEX_EU_151_1B = "VATEX-EU-151-1B"  # Exempt based on article 151, section 1 (b) of Council Direct
    VATEX_EU_151_1C = "VATEX-EU-151-1C"  # Exempt based on article 151, section 1 (c) of Council Direct
    VATEX_EU_151_1D = "VATEX-EU-151-1D"  # Exempt based on article 151, section 1 (d) of Council Direct
    VATEX_EU_151_1E = "VATEX-EU-151-1E"  # Exempt based on article 151, section 1 (e) of Council Direct
    VATEX_EU_153 = (
        "VATEX-EU-153"  # Exempt based on article 153 of Council Directive 2006/112/EC
    )
    VATEX_EU_159 = (
        "VATEX-EU-159"  # Exempt based on article 159 of Council Directive 2006/112/EC
    )
    VATEX_EU_309 = (
        "VATEX-EU-309"  # Exempt based on article 309 of Council Directive 2006/112/EC
    )
    VATEX_EU_AE = "VATEX-EU-AE"  # Reverse charge
    VATEX_EU_D = "VATEX-EU-D"  # Travel agents VAT scheme.
    VATEX_EU_F = "VATEX-EU-F"  # Intra-Community acquisition of second hand goods
    VATEX_EU_G = "VATEX-EU-G"  # Export outside the EU
    VATEX_EU_I = "VATEX-EU-I"  # Intra-Community acquisition of works of art
    VATEX_EU_IC = "VATEX-EU-IC"  # Intra-community supply
    VATEX_EU_J = (
        "VATEX-EU-J"  # Intra-Community acquisition of collectors items and antiques
    )
    VATEX_EU_O = "VATEX-EU-O"  # Not subject to VAT
    VATEX_FR_FRANCHISE = "VATEX-FR-FRANCHISE"  # France domestic VAT franchise in base
    VATEX_FR_CNWVAT = "VATEX-FR-CNWVAT"  # France domestic Credit Notes without VAT, due to supplier fo
    VATEX_FR_CGI261_1 = "VATEX-FR-CGI261-1"  # Exempt based on 1 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_2 = "VATEX-FR-CGI261-2"  # Exempt based on 2 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_3 = "VATEX-FR-CGI261-3"  # Exempt based on 3 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_4 = "VATEX-FR-CGI261-4"  # Exempt based on 4 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_5 = "VATEX-FR-CGI261-5"  # Exempt based on 5 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_7 = "VATEX-FR-CGI261-7"  # Exempt based on 7 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261_8 = "VATEX-FR-CGI261-8"  # Exempt based on 8 of article 261 of the Code Général des Imp
    VATEX_FR_CGI261A = "VATEX-FR-CGI261A"  # Exempt based on article 261 A of the Code Général des Impôts
    VATEX_FR_CGI261B = "VATEX-FR-CGI261B"  # Exempt based on article 261 B of the Code Général des Impôts
    VATEX_FR_CGI261C_1 = "VATEX-FR-CGI261C-1"  # Exempt based on 1° of article 261 C of the Code Général des
    VATEX_FR_CGI261C_2 = "VATEX-FR-CGI261C-2"  # Exempt based on 2° of article 261 C of the Code Général des
    VATEX_FR_CGI261C_3 = "VATEX-FR-CGI261C-3"  # Exempt based on 3° of article 261 C of the Code Général des
    VATEX_FR_CGI261D_1 = "VATEX-FR-CGI261D-1"  # Exempt based on 1° of article 261 D of the Code Général des
    VATEX_FR_CGI261D_1BIS = "VATEX-FR-CGI261D-1BIS"  # Exempt based on 1°bis of article 261 D of the Code Général d
    VATEX_FR_CGI261D_2 = "VATEX-FR-CGI261D-2"  # Exempt based on 2° of article 261 D of the Code Général des
    VATEX_FR_CGI261D_3 = "VATEX-FR-CGI261D-3"  # Exempt based on 3° of article 261 D of the Code Général des
    VATEX_FR_CGI261D_4 = "VATEX-FR-CGI261D-4"  # Exempt based on 4° of article 261 D of the Code Général des
    VATEX_FR_CGI261E_1 = "VATEX-FR-CGI261E-1"  # Exempt based on 1° of article 261 E of the Code Général des
    VATEX_FR_CGI261E_2 = "VATEX-FR-CGI261E-2"  # Exempt based on 2° of article 261 E of the Code Général des
    VATEX_FR_CGI277A = "VATEX-FR-CGI277A"  # Exempt based on article 277 A of the Code Général des Impôts
    VATEX_FR_CGI275 = "VATEX-FR-CGI275"  # Exempt based on article 275 of the Code Général des Impôts (
    VATEX_FR_298SEXDECIESA = "VATEX-FR-298SEXDECIESA"  # Exempt based on article 298 sexdecies A of the Code Général
    VATEX_FR_CGI295 = "VATEX-FR-CGI295"  # Exempt based on article 295 of the Code Général des Impôts (
    VATEX_FR_AE = (
        "VATEX-FR-AE"  # Exempt based on 2 of article 283 of the Code Général des Imp
    )


# AUTOGEN END VATEXCode


class LineStatusReasonCode(enum.StrEnum):
    """Subtype of invoice line item (BT-X-8); EXTENDED only.

    Discriminates ordinary "detail" lines (the normal case — full
    quantity / unit / amount / VAT requirements apply) from
    ``GROUP`` lines (subtotal headers carrying ``BT-131`` equal to
    the recursive sum of their child lines' net amounts) and
    ``INFORMATION`` lines (free-text only, no monetary contribution
    to the invoice totals).

    Carthorse hard-codes the three spec values rather than pulling
    from the broader UNTDID 1229 codelist — this is the closed set
    the EXTENDED CIUS recognises and the only one the per-category
    sum rules (§5.3 of EXTENDED.md) and the BR-FXEXT-2x line-level
    qualifications (§5.4) ever inspect.
    """

    DETAIL = "DETAIL"
    GROUP = "GROUP"
    INFORMATION = "INFORMATION"
