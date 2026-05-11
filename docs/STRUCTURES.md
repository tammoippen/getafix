# Structures and fields

A walk through the carthorse dataclass tree alongside the EN 16931 /
Factur-X 1.08 / ZUGFeRD 2.4 spec. Every dataclass attribute is annotated
with its EN 16931 business term (`BT-…`) or business group (`BG-…`)
identifier in the source docstrings; this document collects the same
information in tabular form so you can see profile applicability at a
glance.

For the `BR-*` business rules referenced here, see
`docs/VALIDATION.md`. For the gaps, see `docs/IMPLEMENTATION_PLAN.md`.

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

> **Caveat.** `Profile.__lt__` is overridden to ordinal compare, but
> `__le__`, `__gt__`, `__ge__` aren't — they fall back to `StrEnum`'s
> lexicographic compare and produce wrong answers (e.g.
> `Profile.BASIC_WL <= Profile.MINIMUM` returns `True`). See
> `docs/IMPLEMENTATION_PLAN.md §1 #8`.

## 1a. Per-profile field-coverage summary

Counts of EN 16931 fields that are *modelled* by carthorse (either as a
dataclass attribute or as a sub-`Element`) compared to the total number
of fields the spec lists for that profile, taken from the field tables
in §3 of this document. EXTENDED-only fields (`BG-X-*`, `BT-X-*`) are
counted only against the EXTENDED column. The ratios are approximate
indicators rather than a bit-exact audit; each gap is described
inline.

| Profile   | Header + Context | Parties (BG-4/7/10/11/13) | Agreement + Delivery + Settlement | Monetary + Tax (BG-22/23) | Allowance/charge + payment | Line items (BG-25 / BG-26..30) | Total modelled / expected |
|-----------|------------------|---------------------------|-----------------------------------|---------------------------|----------------------------|---------------------------------|---------------------------|
| MINIMUM   | 7 / 7            | 11 / 11                   | 4 / 4                             | 5 / 5                     | n/a                        | n/a                             | 27 / 27 (100%)            |
| BASIC_WL  | 9 / 9            | 25 / 26                   | 17 / 17                           | 11 / 12                   | 16 / 17                    | n/a                             | 78 / 81 (96%)             |
| BASIC     | 9 / 9            | 25 / 26                   | 17 / 17                           | 11 / 12                   | 16 / 17                    | 14 / 14                         | 92 / 95 (97%)             |
| COMFORT   | 9 / 11           | 28 / 33                   | 19 / 21                           | 12 / 13                   | 17 / 20                    | 17 / 21                         | 102 / 119 (86%)           |
| EXTENDED  | 11 / 14          | 31 / 60                   | 21 / 30                           | 13 / 15                   | 17 / 24                    | 17 / 60                         | 110 / 203 (54%)           |

Notes on the totals:
* The single missing item at BASIC_WL/BASIC is the BG-22 `RoundingAmount`
  (BT-114) — see §3.7. The "Allowance/charge + payment" gap is BG-18
  (financial card) which is EN 16931+ anyway.
* COMFORT gaps are mostly `AdditionalReferencedDocument` repetition
  edge cases and the optional payment-means information line (BT-82).
* EXTENDED counts only top-level groups carthorse exposes
  (`UltimateShipToTradeParty`, `ShipFromTradeParty`,
  `ProductEndUserTradeParty`, `EffectivePeriod`, `LogisticsTransportMovement`,
  `BillingSpecifiedPeriod`); sub-line hierarchy, IncludedReferencedProduct,
  line-level deviating parties, advance-payment groups, and per-line
  logistics service charges are unmodelled. See
  `docs/IMPLEMENTATION_PLAN.md §5`.

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
| `schema/trade.py`              | `Trade` (top-level transaction wrapper), `TradeLineItem` (BG-25), and `Trade._validate_document_arithmetic` / `Trade._validate_vat_category_required_parties` |
| `schema/line.py`               | line-level sub-tree: `DocumentLineDocument`, `TradeProduct`, `LineTradeAgreement` (with `GrossTradePrice`, `NetTradePrice`, `AppliedTradeAllowanceCharge`, `Quantity`, `BasisQuantity`), `LineTradeDelivery`, `LineTradeSettlement`, `LineMonetarySummation`, `LineIncludedNote` |

## 3. Field reference

Each table lists the modelled fields of a dataclass, the `BT-`/`BG-` id,
the lowest profile that allows the field per the appendix, and the
carthorse-side gating (declared via `metadata={"profile": Profile.…}`
on the field, or via the field's element class `ClassVar`).

### 3.1 `Document`, `Context`, `Header`

| Field                                  | EN 16931 id   | XSD min profile | carthorse min profile | Notes |
|----------------------------------------|---------------|-----------------|-----------------------|-------|
| `Document.context`                     | BG-2          | MINIMUM         | required              | |
| `Document.header`                      | BT-1-00       | MINIMUM         | required              | |
| `Document.trade`                       | BG-25-00      | MINIMUM         | required              | |
| `Context.test_indicator`               | BT-X-1        | EXTENDED        | EXTENDED              | Carthorse leaf metadata `profile=EXTENDED` |
| `Context.guideline.id`                 | BT-24         | MINIMUM         | required              | |
| `Context.business.id`                  | BT-23         | MINIMUM         | EXTENDED              | Required `1..1` only at EXTENDED — see appendix `BT-23-00 Diverging cardinality` |
| `Header.id`                            | BT-1          | MINIMUM         | required              | |
| `Header.type_code`                     | BT-3          | MINIMUM         | required              | UNTDID 1001 |
| `Header.issue_date`                    | BT-2          | MINIMUM         | required              | rendered as `udt:DateTimeString format="102"` |
| `Header.name`                          | BT-X-2        | EXTENDED        | BASIC                 | ⚠ carthorse gates this on BASIC, but the appendix lists `Name` only at EXTENDED. Re-gate to EXTENDED. |
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
    EmailURIUniversalCommunication    BT-43   EXTENDED  (carthorse: EmailURI gated EXTENDED)
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

`BuyerTradeParty` (BG-7) mirrors the same structure with single
`SpecifiedTaxRegistration` (BT-48) — see implementation plan `§1 #5`
for the cardinality bug.

### 3.3 Tax representative, payee, ship-to

| Element                                         | EN 16931 id | Lowest profile | Carthorse  |
|-------------------------------------------------|-------------|----------------|------------|
| `SellerTaxRepresentativeTradeParty`             | BG-11       | BASIC_WL       | ✓          |
| `PayeeTradeParty`                               | BG-10       | BASIC_WL       | ✓ (partial — no address/contact/electronic_address yet) |
| `ShipToTradeParty`                              | BG-13       | BASIC_WL       | ✓ (now gated `BASIC_WL`) |
| `UltimateShipToTradeParty`                      | BG-X-27     | EXTENDED       | ✓          |
| `ShipFromTradeParty`                            | BG-X-30     | EXTENDED       | ✓          |
| `ProductEndUserTradeParty`                      | BG-X-18     | EXTENDED       | ✓          |
| `BuyerAgentTradeParty`                          | BG-X-62     | EXTENDED       | ✗          |
| `SalesAgentTradeParty`                          | BG-X-49     | EXTENDED       | ✗          |
| `BuyerTaxRepresentativeTradeParty`              | BG-X-54     | EXTENDED       | ✗          |
| `InvoicerTradeParty`                            | BG-X-33     | EXTENDED       | ✗          |
| `InvoiceeTradeParty`                            | BG-X-36     | EXTENDED       | ✗          |
| `PayerTradeParty`                               | BG-X-73     | EXTENDED       | ✗          |

### 3.4 Header trade agreement

```
TradeAgreement (BT-10-00)
  BuyerReference                   BT-10  MINIMUM   carthorse: MINIMUM ✓
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
  RelatedSupplyChainConsignment    BG-X-24 EXTENDED  (carthorse models a stripped-down version)
```

### 3.6 Header trade settlement

```
TradeSettlement (BG-19)
  CreditorReferenceID              BT-90    BASIC_WL  optional
  PaymentReference                 BT-83    BASIC_WL  optional
  TaxCurrencyCode                  BT-6     BASIC_WL  ✓ modelled as ``tax_currency_code``;
                                                     drives ``BR-53`` enforcement
  InvoiceCurrencyCode              BT-5     MINIMUM   required
  PayeeTradeParty                  BG-10    BASIC_WL  optional
  SpecifiedTradeSettlementPaymentMeans* BG-16 BASIC_WL list
  ApplicableTradeTax+              BG-23    BASIC_WL  list, ≥1 (enforces ``BR-CO-18``)
  BillingSpecifiedPeriod           BG-14    BASIC_WL  ✓ modelled (``BillingSpecifiedPeriod``);
                                                     enforces ``BR-29`` and ``BR-CO-19``
  SpecifiedTradeAllowanceCharge*   BG-20/21 BASIC_WL  list
  SpecifiedTradePaymentTerms       BT-20-00 BASIC_WL  carthorse: single (EXTENDED allows list of payment-term blocks)
  SpecifiedTradeSettlementHeaderMonetarySummation BG-22 MINIMUM required
  InvoiceReferencedDocument*       BG-3     BASIC_WL  ✓ ``list[InvoiceReferencedDocument] | None``
  ReceivableSpecifiedTradeAccountingAccount* BT-19-00 BASIC_WL  list
  SpecifiedAdvancePayment*         BG-X-45  EXTENDED  ✗
  SpecifiedLogisticsServiceCharge* BG-X-42  EXTENDED  ✗
```

### 3.7 Monetary summation (BG-22)

| Field                  | BT id  | XSD min profile | Carthorse           |
|------------------------|--------|-----------------|---------------------|
| `line_total`           | BT-106 | BASIC_WL        | required at MINIMUM ⚠ |
| `charge_total`         | BT-108 | BASIC_WL        | optional `BASIC_WL` |
| `allowance_total`      | BT-107 | BASIC_WL        | optional `BASIC_WL` |
| `tax_basis_total`      | BT-109 | MINIMUM         | required            |
| `tax_total`            | BT-110 / BT-111 | MINIMUM | ✓ `list[TaxTotal] \| None`; element 1 is BT-110 with `currencyID == BT-5`, element 2 is BT-111 with `currencyID == BT-6` when BT-6 set (`BR-53`) |
| (rounding)             | BT-114 | EN16931         | ✗ NOT MODELLED       |
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
  ExemptionReasonCode              BT-121  BASIC_WL  optional ⚠ field tag bug — see plan §1 #3
  TaxPointDate                     BT-7    EN16931   ✗ NOT MODELLED
  DueDateTypeCode                  BT-8    BASIC_WL  optional
  RateApplicablePercent            BT-119  BASIC_WL  optional
```

### 3.9 Allowance / charge (BG-20 / BG-21 / BG-27 / BG-28)

```
TradeAllowanceCharge
  ChargeIndicator                  BG-20-0 / BG-21-0  required (false=allowance, true=charge)
  CalculationPercent               BT-94 / BT-101    optional
  BasisAmount                      BT-93 / BT-100    optional ⚠ wrong tag in carthorse (#4)
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
  TypeCode                         BT-81  required (UNTDID 4461)
  Information                      BT-82  EN16931  ✗ NOT MODELLED
  ApplicableTradeSettlementFinancialCard (BG-18) EN16931 ✗
  PayerPartyDebtorFinancialAccount (BT-91-00) BASIC_WL ✓
    IBANID                         BT-91
  PayeePartyCreditorFinancialAccount (BG-17) BASIC_WL ✓
    IBANID                         BT-84
    AccountName                    BT-85  EN16931  ✗
    ProprietaryID                  BT-84-0
  PayeeSpecifiedCreditorFinancialInstitution (BT-86) EN16931 ✗
```

`PaymentTerms` (BT-20-00) is currently single. EXTENDED allows
0..unbounded — needed only when emitting EXTENDED documents.

### 3.11 References

| Class                                   | EN 16931 id | Lowest profile | Carthorse |
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

Carthorse models the full BASIC line shape in `schema/line.py`. EN 16931
enrichments (product characteristics, classification, origin country,
line-level references / accounting account) and the EXTENDED sub-line
hierarchy (parent/child via `BT-X-304`), `IncludedReferencedProduct`,
line-level deviating parties, and per-line logistics service charges
are *not* modelled — see `docs/IMPLEMENTATION_PLAN.md §5`.

```
TradeLineItem (BG-25)                                profile = BASIC
  AssociatedDocumentLineDocument        BT-126-00    DocumentLineDocument
    LineID                              BT-126        required
    IncludedNote                        BT-127-00    LineIncludedNote, optional
      Content                           BT-127        required if note present
  SpecifiedTradeProduct                 BG-31        TradeProduct
    GlobalID                            BT-157       optional (schemeID required, BR-64)
    SellerAssignedID                    BT-155       COMFORT+
    BuyerAssignedID                     BT-156       COMFORT+
    Name                                BT-153       required
    Description                         BT-154       COMFORT+
  SpecifiedLineTradeAgreement           BG-29        LineTradeAgreement
    GrossPriceProductTradePrice         BT-148-00    GrossTradePrice, optional
      ChargeAmount                      BT-148       required if gross price present
      BasisQuantity                     BT-149-1     optional
      AppliedTradeAllowanceCharge       BT-147-00    optional (allowance only)
        ChargeIndicator                 false        required
        ActualAmount                    BT-147       required
        CalculationPercent              BT-X         COMFORT+
        BasisAmount                     BT-X         COMFORT+
    NetPriceProductTradePrice           BT-146-00    NetTradePrice, required
      ChargeAmount                      BT-146       required (BR-27: ≥ 0 not yet enforced)
      BasisQuantity                     BT-149       optional
  SpecifiedLineTradeDelivery            BT-129-00    LineTradeDelivery
    BilledQuantity                      BT-129       required (with BT-130 unitCode)
  SpecifiedLineTradeSettlement          BG-30-00     LineTradeSettlement
    ApplicableTradeTax                  BG-30        required (TypeCode, CategoryCode, rate)
    BillingSpecifiedPeriod              BG-26        optional (BR-30 / BR-CO-20)
    SpecifiedTradeAllowanceCharge*      BG-27/28     list (BR-CO-23 / BR-CO-24)
    SpecifiedTradeSettlementLineMonetarySummation BT-131-00 required
      LineTotalAmount                   BT-131       required
```

## 4. Wire conventions enforced today

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

## 5. Where to look next

* For new field work, start from the relevant section above to confirm
  the EN 16931 id, then update `docs/IMPLEMENTATION_PLAN.md` to record
  the change.
* For new validators, register the BR-* code in `docs/VALIDATION.md`
  and prefer appending `ValidationError(code="BR-…", message=…)` to
  the ``errors`` list returned by ``validate_internal`` (no raising in
  child validators — the ``Document.validate`` root wraps the collected
  list in a :class:`ValidationErrors` aggregate). The contract is::

      def validate_internal(self, profile: Profile) -> list[ValidationError]:
          errors: list[ValidationError] = []
          if ...:
              errors.append(ValidationError("BR-…", "…"))
          errors.extend(super().validate_internal(profile))
          return errors

* The vendored XSDs under `tests/schemas/` are the structural source
  of truth; any modelling change must keep
  `tests/test_hypothesis.py::test_generated_xml_is_xsd_valid` green.
