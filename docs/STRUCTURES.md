# Structures and fields

A walk through the getafix dataclass tree alongside the EN 16931 /
Factur-X 1.08 / ZUGFeRD 2.4 spec. Every dataclass attribute is annotated
with its EN 16931 business term (`BT-…`) or business group (`BG-…`)
identifier in the source docstrings; this document collects the same
information in tabular form so you can see profile applicability at a
glance.

For the `BR-*` business rules referenced here, see
`docs/VALIDATION.md`. The remaining EXTENDED coverage gaps are
enumerated in [§5](#5-extended-coverage-diff) of this file.

## 1. Profile primer

Five profiles, ordered by completeness:

| `Profile` value | Spec name      | XSD complex types | Carries line items |
|-----------------|----------------|-------------------|--------------------|
| `MINIMUM`       | MINIMUM        | 27                | ✗                  |
| `BASIC_WL`      | BASIC WITHOUT LINES | 90           | ✗                  |
| `BASIC`         | BASIC          | 111               | ✓                  |
| `COMFORT`       | EN 16931 / COMFORT | 152           | ✓                  |
| `EXTENDED`      | EXTENDED (Factur-X CIUS) | 265     | ✓ + sub-lines      |

`Profile` is a `StrEnum` whose value is the URN that goes into
`<ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>…</ram:ID></ram:GuidelineSpecifiedDocumentContextParameter>`.

All four order comparators (`__lt__` / `__le__` / `__gt__` /
`__ge__`) are overridden on `Profile` to use ordinal compare based on
member declaration order, so e.g. `Profile.BASIC_WL <= Profile.MINIMUM`
returns `False` (the inherited `StrEnum` lexicographic compare would
have answered `True`).

## 1a. Per-profile field-coverage summary

Getafix models **every field** that MINIMUM, BASIC_WL, BASIC and
EN 16931 (COMFORT) permit. EXTENDED coverage is broad — every
top-level structure is modelled — with the residual gaps
enumerated in [§5](#5-extended-coverage-diff).

| Profile   | Coverage | Open gaps |
|-----------|----------|-----------|
| MINIMUM   | 100%     | —         |
| BASIC_WL  | 100%     | —         |
| BASIC     | 100%     | —         |
| COMFORT   | 100%     | —         |
| EXTENDED  | structurally complete | leaf attributes on shared types and line-level twins of header references (see §6) |

> **Wire conformance.** Every dataclass with XML children declares its
> fields in the same order as the corresponding XSD complexType
> ``<xs:sequence>``; ``tests/test_xsd_validity.py`` parses each shipped
> sample, re-renders it via ``Document.to_xml()`` and validates the
> output against the matching Factur-X 1.08 ``.xsd``. See §4.

## 2. Top-level shape

```
Document            (rsm:CrossIndustryInvoice, BG-0)
├── context         (rsm:ExchangedDocumentContext, BG-2)
│   ├── business    (BusinessProcessSpecifiedDocumentContextParameter, BT-23-00) — optional, EXTENDED-mandatory
│   └── guideline   (GuidelineSpecifiedDocumentContextParameter, BT-24-00) — required
├── header          (rsm:ExchangedDocument, BT-1-00)
└── trade           (rsm:SupplyChainTradeTransaction, BG-25-00)
    ├── items[]     (IncludedSupplyChainTradeLineItem, BG-25)
    ├── agreement   (ApplicableHeaderTradeAgreement, BT-10-00)
    ├── delivery    (ApplicableHeaderTradeDelivery, BG-13-00)
    └── settlement  (ApplicableHeaderTradeSettlement, BG-19)
```

Module map:

| Python module                  | Section it owns                                                        |
|--------------------------------|------------------------------------------------------------------------|
| `schema/types.py`              | enums (`Profile`, `Namespace`, `TypeCode`, `CategoryCode`, `MIME`)     |
| `schema/element.py`            | base `Element`, generic XML render/parse, `ProfileMismatch`, `ValidationError` |
| `schema/document.py`           | `Document`, `Header`, `Context`, `IncludedNote`, `EffectivePeriod`, `BusinessDocument`, `GuidelineDocument` |
| `schema/party.py`              | every `*TradeParty`, `PostalTradeAddress`, `LegalOrganization`, `TradeContact`, `URIUniversalCommunication`, `SchemeID` family |
| `schema/agreement.py`          | `TradeAgreement` (BT-10-00)                                            |
| `schema/delivery.py`           | `TradeDelivery` (BG-13-00), `SupplyChainEvent`, `SupplyChainConsignment`, `LogisticsTransportMovement` |
| `schema/settlement.py`         | `TradeSettlement` (BG-19), `PaymentMeans`, `PaymentTerms`, financial accounts, `ReceivableAccountingAccount` |
| `schema/accounting.py`         | `MonetarySummation`, `TaxTotal`, `ApplicableTradeTax`, `CategoryTradeTax`, `TradeAllowanceCharge` |
| `schema/references.py`         | every `*ReferencedDocument`, `AdditionalReferencedDocument`, `AttachmentBinaryObject`, `ProcuringProject` |
| `schema/trade.py`              | `Trade` (top-level transaction wrapper) and `TradeLineItem` (BG-25); cross-sibling validators live in :mod:`getafix.rules.trade` |
| `schema/line.py`               | line-level sub-tree: `DocumentLineDocument`, `TradeProduct`, `LineTradeAgreement` (with `GrossTradePrice`, `NetTradePrice`, `AppliedTradeAllowanceCharge`, `Quantity`, `BasisQuantity`), `LineTradeDelivery`, `LineTradeSettlement`, `LineMonetarySummation`, `LineIncludedNote` |

## 3. Field reference

Each table lists the modelled fields of a dataclass, the `BT-`/`BG-` id,
the lowest profile that allows the field per the appendix, and the
getafix-side gating (declared via `metadata={"profile": Profile.…}`
on the field, or via the field's element class `ClassVar`).

### 3.1 `Document`, `Context`, `Header`

| Field                                  | EN 16931 id   | XSD min profile | getafix min profile | Notes |
|----------------------------------------|---------------|-----------------|-----------------------|-------|
| `Document.context`                     | BG-2          | MINIMUM         | required              | |
| `Document.header`                      | BT-1-00       | MINIMUM         | required              | |
| `Document.trade`                       | BG-25-00      | MINIMUM         | required              | |
| `Context.test_indicator`               | BT-X-1        | EXTENDED        | EXTENDED              | Getafix leaf metadata `profile=EXTENDED` |
| `Context.guideline.id`                 | BT-24         | MINIMUM         | required              | |
| `Context.business.id`                  | BT-23         | MINIMUM         | EXTENDED              | Required `1..1` only at EXTENDED — see appendix `BT-23-00 Diverging cardinality` |
| `Header.id`                            | BT-1          | MINIMUM         | required              | |
| `Header.type_code`                     | BT-3          | MINIMUM         | required              | UNTDID 1001 |
| `Header.issue_date`                    | BT-2          | MINIMUM         | required              | rendered as `udt:DateTimeString format="102"` |
| `Header.name`                          | BT-X-2        | EXTENDED        | EXTENDED              | Re-gated to EXTENDED to match the XSD. |
| `Header.copyright_indicator`           | BT-X-3        | EXTENDED        | EXTENDED              | |
| `Header.language_id`                   | BT-X-4        | EXTENDED        | EXTENDED              | |
| `Header.notes`                         | BG-1          | BASIC_WL        | BASIC_WL              | Single `IncludedNote` element class, repeated. ``IncludedNote.profile = BASIC_WL`` now matches the spec. |
| `Header.effective_period`              | BT-X-6        | EXTENDED        | EXTENDED              | |

`IncludedNote.content_code` (BT-X-5) is EXTENDED-only.

### 3.2 Parties (`SellerTradeParty`, `BuyerTradeParty`)

```
SellerTradeParty (BG-4)
  Name                                BT-27   MINIMUM   required
  ID*                                 BT-29   BASIC_WL  optional
  GlobalID*                           BT-29-0 BASIC_WL  list
  Description                         BT-33   EN16931   COMFORT
  SpecifiedLegalOrganization          BT-30-00
    ID                                BT-30   MINIMUM
      schemeID                        BT-30-1 MINIMUM
    TradingBusinessName               BT-28   BASIC_WL
    PostalTradeAddress (legal)        BG-X-14 EXTENDED  (not modelled)
  DefinedTradeContact                 BG-6    EN16931   COMFORT
    PersonName                        BT-41
    DepartmentName                    BT-41-0
    TelephoneUniversalCommunication   BT-42
    EmailURIUniversalCommunication    BT-43   EXTENDED  (getafix: EmailURI gated EXTENDED)
  PostalTradeAddress                  BG-5    MINIMUM   required
    PostcodeCode                      BT-38   BASIC_WL
    LineOne                           BT-35   BASIC_WL
    LineTwo                           BT-36   BASIC_WL
    LineThree                         BT-162  BASIC_WL
    CityName                          BT-37   BASIC_WL
    CountryID                         BT-40   MINIMUM   required
    CountrySubDivisionName            BT-39   BASIC
  URIUniversalCommunication           BT-34-00 BASIC_WL
    URIID                             BT-34   BASIC_WL
      schemeID                        BT-34-1 BASIC_WL  required
  SpecifiedTaxRegistration[VAT]       BT-31-00 MINIMUM
    ID                                BT-31
      schemeID="VA"                   BT-31-0 required
  SpecifiedTaxRegistration[FC]        BT-32-00 MINIMUM
    ID                                BT-32
      schemeID="FC"                   BT-32-0 required
```

`BuyerTradeParty` (BG-7) mirrors the same structure, with
``PostalTradeAddress`` (BG-8) typed as ``PostalTradeAddressExtended | None``:
the MINIMUM Factur-X XSD makes the address optional on every
``TradePartyType``, and the MINIMUM appendix does NOT list BG-8 as
required. ``BR-10`` (Buyer postal address required) is enforced from
BASIC_WL upwards in :meth:`BuyerTradeParty.validate_internal`.
``SpecifiedTaxRegistration`` is now ``list[SpecifiedTaxRegistration] |
None`` (matching the XSD ``maxOccurs="2"`` for VA + FC entries side by
side).

### 3.3 Tax representative, payee, ship-to

| Element                                         | EN 16931 id | Lowest profile | Getafix  |
|-------------------------------------------------|-------------|----------------|------------|
| `SellerTaxRepresentativeTradeParty`             | BG-11       | BASIC_WL       | ✓          |
| `PayeeTradeParty`                               | BG-10       | BASIC_WL       | ✓          |
| `ShipToTradeParty`                              | BG-13       | BASIC_WL       | ✓          |
| `UltimateShipToTradeParty`                      | BG-X-27     | EXTENDED       | ✓          |
| `ShipFromTradeParty`                            | BG-X-30     | EXTENDED       | ✓          |
| `ProductEndUserTradeParty`                      | BG-X-18     | EXTENDED       | ✓          |
| `BuyerAgentTradeParty`                          | BG-X-62     | EXTENDED       | ✓          |
| `SalesAgentTradeParty`                          | BG-X-49     | EXTENDED       | ✓          |
| `BuyerTaxRepresentativeTradeParty`              | BG-X-54     | EXTENDED       | ✓          |
| `InvoicerTradeParty`                            | BG-X-33     | EXTENDED       | ✓          |
| `InvoiceeTradeParty`                            | BG-X-36     | EXTENDED       | ✓          |
| `PayerTradeParty`                               | BG-X-73     | EXTENDED       | ✓          |
| `ItemSellerTradeParty`                          | BG-X-90     | EXTENDED       | ✓ (on line) |

### 3.4 Header trade agreement

```
TradeAgreement (BT-10-00)
  BuyerReference                   BT-10  MINIMUM   getafix: MINIMUM ✓
  SellerTradeParty                 BG-4   MINIMUM   required
  BuyerTradeParty                  BG-7   MINIMUM   required
  SellerTaxRepresentativeTradeParty BG-11 BASIC_WL  optional
  SellerOrderReferencedDocument    BT-14  EN16931   COMFORT
  BuyerOrderReferencedDocument     BT-13-00 MINIMUM
  ContractReferencedDocument       BT-12-00 BASIC_WL
  AdditionalReferencedDocument*    BG-24  EN16931   COMFORT
  SpecifiedProcuringProject        BT-11-00 EN16931 COMFORT
  UltimateCustomerOrderReferencedDocument BG-X-23 EXTENDED
  ProductEndUserTradeParty         BG-X-18 EXTENDED  optional
```

### 3.5 Header trade delivery

```
TradeDelivery (BG-13-00)
  ShipToTradeParty                 BG-13  BASIC_WL
  UltimateShipToTradeParty         BG-X-27 EXTENDED
  ShipFromTradeParty               BG-X-30 EXTENDED
  ActualDeliverySupplyChainEvent   BT-72-000 BASIC_WL
    OccurrenceDateTime             BT-72  BASIC_WL
  DespatchAdviceReferencedDocument BT-16-00 BASIC_WL
  ReceivingAdviceReferencedDocument BT-15-00 EN16931
  DeliveryNoteReferencedDocument   BT-X EXTENDED
  RelatedSupplyChainConsignment    BG-X-24 EXTENDED  carries LogisticsTransportMovement (BT-X-152)
```

### 3.6 Header trade settlement

```
TradeSettlement (BG-19)
  CreditorReferenceID              BT-90    BASIC_WL  optional
  PaymentReference                 BT-83    BASIC_WL  optional
  TaxCurrencyCode                  BT-6     BASIC_WL  drives ``BR-53`` enforcement
  InvoiceCurrencyCode              BT-5     MINIMUM   required
  InvoiceIssuerReference           BT-X-204 EXTENDED  optional
  InvoicerTradeParty               BG-X-33  EXTENDED  optional
  InvoiceeTradeParty               BG-X-36  EXTENDED  optional
  PayeeTradeParty                  BG-10    BASIC_WL  optional
  PayerTradeParty                  BG-X-73  EXTENDED  optional
  TaxApplicableTradeCurrencyExchange BG-X-41 EXTENDED  optional
  SpecifiedTradeSettlementPaymentMeans* BG-16 BASIC_WL list (0..*)
  ApplicableTradeTax+              BG-23    BASIC_WL  list, ≥1 (enforces ``BR-CO-18``)
  BillingSpecifiedPeriod           BG-14    BASIC_WL  enforces ``BR-29`` and ``BR-CO-19``
  SpecifiedTradeAllowanceCharge*   BG-20/21 BASIC_WL  list (0..*)
  SpecifiedLogisticsServiceCharge* BG-X-42  EXTENDED  list (0..*)
  SpecifiedTradePaymentTerms*      BT-20-00 BASIC_WL  list capped to 1 below EXTENDED
  SpecifiedTradeSettlementHeaderMonetarySummation BG-22 MINIMUM required
  InvoiceReferencedDocument*       BG-3     BASIC_WL  list (0..*)
  ReceivableSpecifiedTradeAccountingAccount* BT-19-00 BASIC_WL  list (0..*)
  SpecifiedAdvancePayment*         BG-X-45  EXTENDED  list (0..*)
```

### 3.7 Monetary summation (BG-22)

| Field                  | BT id  | XSD min profile | Getafix           |
|------------------------|--------|-----------------|---------------------|
| `line_total`           | BT-106 | BASIC_WL        | optional `BASIC_WL`; BR-12 raises when missing at BASIC_WL+ |
| `charge_total`         | BT-108 | BASIC_WL        | optional `BASIC_WL` |
| `allowance_total`      | BT-107 | BASIC_WL        | optional `BASIC_WL` |
| `tax_basis_total`      | BT-109 | MINIMUM         | required            |
| `tax_total`            | BT-110 / BT-111 | MINIMUM | ✓ `list[TaxTotal] \| None`; element 1 is BT-110 with `currencyID == BT-5`, element 2 is BT-111 with `currencyID == BT-6` when BT-6 set (`BR-53`) |
| `rounding_amount`      | BT-114 | EN16931         | ✓ optional `COMFORT`; participates in BR-CO-16 (`BT-115 = BT-112 - BT-113 + BT-114`) |
| `grand_total`          | BT-112 | MINIMUM         | required            |
| `prepaid_total`        | BT-113 | BASIC_WL        | optional `BASIC_WL` |
| `due_amount`           | BT-115 | MINIMUM         | required            |

### 3.8 Tax breakdown (BG-23 / BG-30)

```
ApplicableTradeTax (header BG-23, line BG-30)
  CalculatedAmount                 BT-117  BASIC_WL  required
  TypeCode                         BT-118-0 BASIC_WL  required, "VAT" everywhere except EXTENDED
  ExemptionReason                  BT-120  BASIC_WL  optional
  BasisAmount                      BT-116  BASIC_WL  required
  CategoryCode                     BT-118  BASIC_WL  required
  ExemptionReasonCode              BT-121  BASIC_WL  optional
  TaxPointDate                     BT-7    EN16931   optional `COMFORT`; mutually exclusive with BT-8 via BR-CO-3
  DueDateTypeCode                  BT-8    BASIC_WL  optional
  RateApplicablePercent            BT-119  BASIC_WL  optional
```

### 3.9 Allowance / charge (BG-20 / BG-21 / BG-27 / BG-28)

```
TradeAllowanceCharge
  ChargeIndicator                  BG-20-0 / BG-21-0  required (false=allowance, true=charge)
  CalculationPercent               BT-94 / BT-101    optional
  BasisAmount                      BT-93 / BT-100    optional
  ActualAmount                     BT-92 / BT-99     required
  ReasonCode                       BT-98 / BT-105    optional, paired with text via BR-CO-21/22
  Reason                           BT-97 / BT-104    optional
  CategoryTradeTax                 BT-95-00 / BT-102-00  required at BASIC_WL, optional from BASIC
    TypeCode                       BT-95-0 / BT-102-0  "VAT"
    CategoryCode                   BT-95   / BT-102
    RateApplicablePercent          BT-96   / BT-103
```

### 3.10 Payment

```
PaymentMeans (BG-16)
  TypeCode                         BT-81  required (UNTDID 4461; BR-49 / BT-81 code-shape guard)
  Information                      BT-82  COMFORT+
  ApplicableTradeSettlementFinancialCard (BG-18) COMFORT+  enforces BR-51 (4..6 digit PAN)
    ID                             BT-87
    CardholderName                 BT-88
  PayerPartyDebtorFinancialAccount (BT-91-00) BASIC_WL
    IBANID                         BT-91
  PayeePartyCreditorFinancialAccount (BG-17) BASIC_WL  enforces BR-50 (IBAN or proprietary id)
    IBANID                         BT-84  (BR-61 enforces presence for credit-transfer type codes)
    AccountName                    BT-85  COMFORT+
    ProprietaryID                  BT-84-0
  PayeeSpecifiedCreditorFinancialInstitution (BT-86) COMFORT+
    BICID                          BT-86  optional; renderer always emits the wrapper to keep XSD validity
```

`PaymentTerms` (BT-20-00) is modelled as a list. EXTENDED widens
the XSD cardinality from 0..1 to 0..unbounded; below EXTENDED
``list_max_cardinality_below(Profile.EXTENDED, max_count=1, ...)``
caps the list at one entry.

### 3.11 References

| Class                                   | EN 16931 id | Lowest profile | Getafix |
|-----------------------------------------|-------------|----------------|-----------|
| `BuyerOrderReferencedDocument`          | BT-13       | MINIMUM        | ✓         |
| `SellerOrderReferencedDocument`         | BT-14       | EN16931        | ✓         |
| `ContractReferencedDocument`            | BT-12       | BASIC_WL       | ✓         |
| `DespatchAdviceReferencedDocument`      | BT-16       | BASIC_WL       | ✓         |
| `ReceivingAdviceReferencedDocument`     | BT-15       | EN16931        | ✓         |
| `DeliveryNoteReferencedDocument`        | BT-X        | EXTENDED       | ✓         |
| `InvoiceReferencedDocument`             | BG-3        | BASIC_WL       | ✓ list                 |
| `AdditionalReferencedDocument`          | BG-24       | EN16931        | ✓         |
| `ProcuringProject`                      | BT-11-00    | EN16931        | ✓         |
| `UltimateCustomerOrderReferencedDocument`| BG-X-23   | EXTENDED       | ✓         |
| `AttachmentBinaryObject`                | BT-125      | EN16931        | ✓         |

### 3.12 Line items (BG-25)

Getafix models the full line shape across BASIC, COMFORT and
EXTENDED in `schema/line.py`: product enrichments (BG-32 / BG-33 /
BG-34), line-level references / accounting account, and the
EXTENDED sub-line hierarchy (parent/child via `BT-X-304`),
`IncludedReferencedProduct` (BG-X-1), `IndividualTradeProductInstance`
(BG-X-84), and the per-line deviating seller (BG-X-90, via
`ItemSellerTradeParty`). EXTENDED leaves the line-level
ship-to (BG-X-7) and ultimate-ship-to (BG-X-10) hooks in place
too. Residual EXTENDED line-level references missing per [§5.1](#51-line-level-twins-of-header-references).

```
TradeLineItem (BG-25)                                profile = BASIC
  AssociatedDocumentLineDocument        BT-126-00    DocumentLineDocument
    LineID                              BT-126        required
    ParentLineID                        BT-X-304     EXTENDED only — sub-invoice-line parent
    LineStatusCode                      BT-X-7       EXTENDED only
    LineStatusReasonCode                BT-X-8       EXTENDED only (DETAIL / GROUP / INFORMATION)
    IncludedNote                        BT-127-00    LineIncludedNote, optional
      Content                           BT-127       required if note present
  SpecifiedTradeProduct                 BG-31        TradeProduct
    GlobalID                            BT-157       optional (schemeID required, BR-64)
    SellerAssignedID                    BT-155       COMFORT+
    BuyerAssignedID                     BT-156       COMFORT+
    IndustryAssignedID                  BT-X-532     EXTENDED only
    ModelID                             BT-X-533     EXTENDED only
    Name                                BT-153       required
    Description                         BT-154       COMFORT+
    BatchID*                            BT-X-534     EXTENDED only (list)
    BrandName                           BT-X-535     EXTENDED only
    ModelName                           BT-X-536     EXTENDED only
    ApplicableProductCharacteristic*    BG-32        COMFORT+ — BR-54 implicit
    DesignatedProductClassification*    BG-33        COMFORT+ — BR-65 implicit via required list_id
    IndividualTradeProductInstance*     BG-X-84      EXTENDED only
    OriginTradeCountry                  BG-34        COMFORT+
    IncludedReferencedProduct*          BG-X-1       EXTENDED only (sub-product bundle)
  SpecifiedLineTradeAgreement           BG-29        LineTradeAgreement
    BuyerOrderReferencedDocument        BT-132-00    COMFORT+
    QuotationReferencedDocument         BG-X-47      EXTENDED only
    GrossPriceProductTradePrice         BT-148-00    GrossTradePrice, optional
      ChargeAmount                      BT-148       required if gross price present (BR-28: ≥ 0)
      BasisQuantity                     BT-149-1     optional
      AppliedTradeAllowanceCharge       BT-147-00    optional (allowance only)
        ChargeIndicator                 false        required
        ActualAmount                    BT-147       required
        CalculationPercent              BT-X         COMFORT+
        BasisAmount                     BT-X         COMFORT+
    NetPriceProductTradePrice           BT-146-00    NetTradePrice, required (BR-27: ≥ 0)
      ChargeAmount                      BT-146       required
      BasisQuantity                     BT-149       optional
    ItemSellerTradeParty                BG-X-90      EXTENDED only
  SpecifiedLineTradeDelivery            BT-129-00    LineTradeDelivery
    BilledQuantity                      BT-129       required (with BT-130 unitCode)
    ChargeFreeQuantity                  BT-X-46      EXTENDED only
    PackageQuantity                     BT-X-47      EXTENDED only
    PerPackageUnitQuantity              BT-X-561     EXTENDED only
    ShipToTradeParty                    BG-X-7       EXTENDED only
    UltimateShipToTradeParty            BG-X-10      EXTENDED only
  SpecifiedLineTradeSettlement          BG-30-00     LineTradeSettlement
    ApplicableTradeTax                  BG-30        required (TypeCode, CategoryCode, rate)
    BillingSpecifiedPeriod              BG-26        optional (BR-30 / BR-CO-20)
    SpecifiedTradeAllowanceCharge*      BG-27/28     list (BR-CO-23 / BR-CO-24)
    SpecifiedTradeSettlementLineMonetarySummation BT-131-00 required
      LineTotalAmount                   BT-131       required
    AdditionalReferencedDocument*       BT-128-00    COMFORT+ (line invoice-object id)
    ReceivableSpecifiedTradeAccountingAccount BT-133-00 COMFORT+
```

## 4. Wire conventions enforced today

* **Child element order matches the XSD `<xs:sequence>`** for every
  dataclass with XML fields. ``Element._children_xml`` renders in
  ``dataclasses.fields()`` order, and each ``@dataclass`` declares its
  fields in canonical order taken from
  ``tests/schemas/{profile}/FACTUR-X_*_ReusableAggregateBusinessInformationEntity_100.xsd``.
  The EN 16931 (COMFORT) schema is the master reference since it
  carries the most fields; lower profiles drop fields but never
  reorder. The ``tests/test_xsd_validity.py`` quality gate validates
  every shipped sample's re-rendered XML against the profile XSD.
* **`udt:DateTimeType` always carries `format="102"`** (CCYYMMDD). The
  parser rejects any other format.
* **`udt:IDType` carries an optional `schemeID` attribute** when the
  spec marks the parent ID with one.
* **`udt:AmountType` carries an optional `currencyID` attribute** for
  every monetary BT. Implemented via the ``"amount": True`` field
  metadata and a sibling ``currency: str | None`` attribute on every
  amount-bearing dataclass (``MonetarySummation``, ``TaxTotal``,
  ``ApplicableTradeTax``, ``TradeAllowanceCharge``, ``GrossTradePrice``,
  ``NetTradePrice``, ``AppliedTradeAllowanceCharge``,
  ``LineMonetarySummation``). ``Element._children_xml`` reads
  ``self.currency`` and stamps it onto every amount field's
  ``currencyID`` attribute; ``Element.from_xml`` captures the first
  parsed ``currencyID`` back into ``currency``.
* **`udt:IndicatorType`** wraps `<udt:Indicator>true|false</udt:Indicator>`.
* **Empty / self-closing string elements** (e.g. ``<ram:LineTwo/>``,
  ``<ram:BICID/>``) parse as the same value as a *missing* element —
  i.e. ``None`` for the corresponding optional field. PEPPOL-EN16931-R008
  warns against empty elements but real-world ZUGFeRD samples ship
  them, so the parser is lenient. On render the field is simply
  omitted.

## 5. EXTENDED coverage diff

Getafix models the EXTENDED profile broadly — see the README
"Status and known gaps" section for the headline structures that
are present. This section enumerates every EXTENDED-permitted
field that is **not** yet on a getafix dataclass, grouped by the
XSD complex type that declares it. Each entry is the XSD element
name; the BT id (often `BT-X-*`) lives in the per-profile appendix
PDF.

### 5.1 Line-level twins of header references

The EXTENDED profile allows the line sub-tree to carry per-line
overrides of references that the header normally provides. Modelled
selectively today; full set:

| Complex type            | Missing element                              | Equivalent header field |
|-------------------------|----------------------------------------------|--------------------------|
| `LineTradeAgreementType`| `ApplicableTradeDeliveryTerms`               | `TradeAgreement.delivery_terms` (BG-X-22) |
| `LineTradeAgreementType`| `SellerOrderReferencedDocument`              | `TradeAgreement.seller_order` (BT-14-00) |
| `LineTradeAgreementType`| `ContractReferencedDocument`                 | `TradeAgreement.contract` (BT-12-00) |
| `LineTradeAgreementType`| `UltimateCustomerOrderReferencedDocument` (0..*) | `TradeAgreement.customer_order` (BG-X-23) |
| `LineTradeDeliveryType` | `ActualDeliverySupplyChainEvent`             | `TradeDelivery.event` (BT-72-000) |
| `LineTradeDeliveryType` | `DespatchAdviceReferencedDocument`           | `TradeDelivery.despatch_advice` (BT-16-00) |
| `LineTradeDeliveryType` | `ReceivingAdviceReferencedDocument`          | `TradeDelivery.receiving_advice` (BT-15-00) |
| `LineTradeSettlementType`| `InvoiceReferencedDocument`                 | `TradeSettlement.invoice_referenced_document` (BG-3) |

### 5.2 Leaf attributes on shared complex types

EXTENDED widens several shared complex types with optional leaf
attributes. Adding them is mechanical — declare a new `field()` in
XSD-sequence order, gated `Profile.EXTENDED`.

| Complex type                          | Missing element              | Notes |
|---------------------------------------|------------------------------|-------|
| `TradePartyType` (every party role)   | `RoleCode`                   | `qdt:PartyRoleCodeType` slot for the party's role in the transaction. |
| `TradePartyType`                      | `Description`                | Free-text description of the party. |
| `TradeContactType` (BG-6 / BG-9)      | `TypeCode`                   | `qdt:ContactTypeCodeType` — distinguishes responsibility / department / etc. |
| `TradeProductType` (BG-31)            | `ID`                         | Per-line product local identifier (separate from `GlobalID`). |
| `ProductCharacteristicType` (BG-32)   | `TypeCode`                   | Item-attribute classification code. |
| `ProductCharacteristicType` (BG-32)   | `ValueMeasure`               | Numeric attribute value with `unitCode`. |
| `TradeAllowanceChargeType` (BG-20/21/27/28) | `SequenceNumeric`      | Numeric ordering hint when multiple allowance/charge entries apply. |
| `TradeAllowanceChargeType`            | `BasisQuantity`              | Quantity-based base for the percentage calculation. |
| `TradePriceType` (BT-146-00 / BT-148-00) | `IncludedTradeTax`         | VAT included in the unit price. |
| `TradeSettlementHeaderMonetarySummationType` (BG-22) | `TotalAllowanceChargeAmount` | Net of all document-level allowances and charges. |

### 5.3 Cardinality widenings already modelled

For reference, the EXTENDED-only cardinality widenings that *are*
honoured by the runtime gates:

* `SpecifiedTradePaymentTerms` — singleton at BASIC_WL..COMFORT,
  0..unbounded at EXTENDED. Capped by
  `list_max_cardinality_below(Profile.EXTENDED, max_count=1, ...)`
  on `TradeSettlement.terms`.
* `AppliedTradeAllowanceCharge` on `TradePriceType` — 0..1 at
  BASIC..COMFORT, 0..unbounded at EXTENDED. Modelled as a list on
  `GrossTradePrice.applied_allowance_charge`, capped to one entry below
  EXTENDED by `list_max_cardinality_below`; a price *charge*
  (`ChargeIndicator` true, BT-X-302-00) is EXTENDED-only via
  `applied_price_charge_extended_only`, and the BT-X-34/35/36/313 leaf
  fields are gated EXTENDED.

## 6. Out of scope

These intentionally live outside getafix's surface:

* **PDF/A-3 packaging.** ``getafix.pdf`` can attach the embedded
  ``factur-x.xml`` to and extract it from any PDF (``pypdf``-based),
  but it does **not** upgrade the host PDF to PDF/A-3 — the formal
  compliance requirement for Factur-X. Pair with a dedicated
  converter (``factur-x`` on PyPI, Mustangproject, …) when full
  conformance is needed.
* **Schematron rule generation.** The per-profile
  ``FACTUR-X_<PROFILE>.sch`` schematron files are not vendored under
  ``tests/schemas/`` (only the XSDs are). Getafix's BR-* validators
  are hand-written from the appendix narratives; auto-generating
  them from the schematron is a separate project.

## 7. Where to look next

* For new field work, start from the relevant section above to confirm
  the EN 16931 id, then add the field to the matching dataclass in
  XSD-``<xs:sequence>`` order.
* For new validators, register the BR-* code in ``docs/VALIDATION.md``
  and add a function to ``getafix.rules.<topic>`` returning
  ``list[ValidationError]`` — see ``AGENTS.md`` for the contract.
* The vendored XSDs under ``tests/schemas/`` are the structural source
  of truth; any modelling change must keep
  ``tests/test_hypothesis.py::test_generated_xml_is_xsd_valid`` green.
