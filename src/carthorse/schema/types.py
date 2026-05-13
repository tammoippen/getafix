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
