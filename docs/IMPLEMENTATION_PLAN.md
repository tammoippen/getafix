# Implementation plan

This document tracks the gap between the carthorse model and the
Factur-X 1.08 / ZUGFeRD 2.4 specification (2026-01-15). It is a working
roadmap, not a release plan: priority is rough, scope is what the spec
requires, not what we promise.

The numbers in parentheses are the EN 16931 business term IDs (BT-*)
or business group IDs (BG-*). Anything prefixed `BT-X-` or `BG-X-`
is a Factur-X CIUS extension that exists only at EXTENDED. The vendored
reference XSDs live in `tests/schemas/<profile>/`; the technical
appendices we worked from are in `ZF24_EN/Documentation/` (gitignored
but available locally if you re-pull `origin/docs`).

## Conventions used in this document

| Marker | Meaning                                                                 |
|--------|-------------------------------------------------------------------------|
| ✓      | implemented and exercised by tests                                      |
| ◯      | structurally present (required field on a dataclass) but not validated  |
| ⚠      | bug — present but wrong (wrong attribute name, wrong tag, wrong type)   |
| ✗      | not modelled                                                            |

## 1. Code bugs to fix first

Small, isolated, mechanical fixes that unblock real-world parsing. Each
of these makes a Hypothesis-generated XML from `tests.strategies` parse
successfully. They should all land before any new structure is added.

| # | Where                                                  | Bug                                                                                                                                      | Fix | Status |
|---|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|-----|--------|
| 1 | `schema/party.py` — `SchemeID.{to_xml_internal,from_xml}` | Renders / reads `schemaID` (with `a`). The XSD spells the attribute `schemeID`. Every real ZUGFeRD CII identifier breaks parsing. | Rename in both directions. Drop the deprecated spelling — no legitimate sample uses it. | **fixed** |
| 2 | `schema/accounting.py` — `MonetarySummation.line_total`  | Required field, but at MINIMUM the XSD does not include `LineTotalAmount`. Round-tripping a real MINIMUM sample crashes the writer.       | Make `line_total` `Decimal \| None` and gate it on `>= BASIC_WL`. Validator BR-12 is what enforces presence at `>= BASIC_WL`. | open |
| 3 | `schema/accounting.py` — `ApplicableTradeTax.exemption_reason_code` | Field metadata `tag="ExemptionReason"` (copy-paste from the previous field). Should be `"ExemptionReasonCode"`. Right now it shadows BT-120 and BT-121 is never written. | Fix the tag literal. | open |
| 4 | `schema/accounting.py` — `TradeAllowanceCharge.basis_amount` | Field metadata `tag="CalculationPercent"` (copy-paste from previous field). BT-93/BT-100 is never written. | Fix to `"BasisAmount"`. | open |
| 5 | `schema/party.py` — `BuyerTradeParty.tax_registrations` | Single `SpecifiedTaxRegistration`, but the XSD permits 0..2 (one VA, one FC). Same on `PayeeTradeParty`. | Change to `list[SpecifiedTaxRegistration] \| None`. | open |
| 6 | `schema/accounting.py` — `MonetarySummation.tax_total`   | Single `TaxTotal`, but the XSD allows 0..2 (BT-110 invoice currency + BT-111 VAT accounting currency). Real samples with foreign-currency invoices cannot round-trip. | Change to `list[TaxTotal] \| None`. Add validator BR-53 (BT-6 set ⇒ second TaxTotal present). | open |
| 7 | `schema/element.py` — XML attribute parser                | `_parse_str` reads only the element body, throwing away any `currencyID` attribute on `udt:AmountType` elements. Round-tripping any real header-level amount loses the attribute. | Either model `currencyID` per amount field via field metadata, or wrap amounts in a tiny `Amount(value: Decimal, currency: str \| None)` element. | open |
| 8 | `schema/types.py` — `Profile.__lt__` only                 | Only `<` is overridden; `<=`, `>=`, `>` fall back to `StrEnum`'s lex compare and silently produce wrong answers. `Profile.BASIC_WL <= Profile.MINIMUM` returns `True`. This is why `TradeSettlement.validate_internal` raises `BR-CO-18` at MINIMUM. | Either implement all four comparators, or use `functools.total_ordering` with a single canonical `__lt__`. | **fixed** |
| 9 | `schema/party.py` — `SpecifiedTaxRegistration.id` element tag | `TaxSchemeId.tag` is `"GlobalID"`, but inside `SpecifiedTaxRegistration` the actual ram element is `<ram:ID>`. Real samples emit `<ram:ID schemeID="VA">…</ram:ID>`. | Drop the `tag` override on `TaxSchemeId`; inherit `tag = "ID"` from `SchemeID`. | **fixed** |

## 2. Missing structures by profile

The structural delta below lists ram elements that exist in the per-profile
XSD but have no carthorse dataclass field. Element ordering matches
`<xs:sequence>` in the corresponding XSD.

### MINIMUM (24-page appendix, 27 ram elements in the XSD)

The MINIMUM profile is essentially complete in carthorse — modulo the
bugs in §1. One modelling discrepancy:

| Element                                | Carthorse status | Notes |
|----------------------------------------|------------------|-------|
| `BuyerTradeParty/PostalTradeAddress`   | required (always emitted) | XSD: `0..1`. The MINIMUM appendix lists it as not present (no BR-10/BR-11 at MINIMUM). Make `BuyerTradeParty.address` optional and only required from BASIC_WL onwards. |
| `MonetarySummation/LineTotalAmount`    | required (BT-106) | XSD: not present in MINIMUM. See bug #2 above. |

### BASIC WL (52-page appendix, 90 ram elements)

What BASIC_WL adds over MINIMUM, grouped by container:

| Container                      | New elements (Carthorse status)                                                                                                   |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `ExchangedDocument`            | `IncludedNote` 0..* (BT-21/BT-22) ✓                                                                                               |
| `SellerTradeParty`             | `ID` 0..*, `GlobalID` 0..*, `URIUniversalCommunication` (BT-34) ✓; `LegalOrganization.TradingBusinessName` (BT-28) ✓                |
| `BuyerTradeParty`              | `ID` 0..1, `GlobalID` 0..1, `PostalTradeAddress`, `URIUniversalCommunication` (BT-49), `SpecifiedTaxRegistration` (BT-48) ◯ (single, see bug #5) |
| `SellerTaxRepresentativeTradeParty` (BG-11) | full party at BASIC_WL ✓                                                                                              |
| `ApplicableHeaderTradeAgreement` | `ContractReferencedDocument` (BT-12) ✓                                                                                          |
| `ApplicableHeaderTradeDelivery`  | `ShipToTradeParty` (BG-13), `ActualDeliverySupplyChainEvent` (BT-72), `DespatchAdviceReferencedDocument` (BT-16) ✓                |
| `ApplicableHeaderTradeSettlement` | `CreditorReferenceID` (BT-90), `PaymentReference` (BT-83), **`TaxCurrencyCode` (BT-6)** ✗, `PayeeTradeParty` (BG-10), `SpecifiedTradeSettlementPaymentMeans` (BG-16) 0..*, `ApplicableTradeTax` (BG-23) 1..*, **`BillingSpecifiedPeriod` (BG-14)** ✗, `SpecifiedTradeAllowanceCharge` (BG-20/BG-21) 0..*, `SpecifiedTradePaymentTerms` (BT-20) ✓, `InvoiceReferencedDocument` (BG-3) 0..* (carthorse models only one) ⚠, `ReceivableSpecifiedTradeAccountingAccount` (BT-19) ✓ |
| `MonetarySummation`            | `LineTotalAmount` (BT-106), `ChargeTotalAmount` (BT-108), `AllowanceTotalAmount` (BT-107), `TotalPrepaidAmount` (BT-113) ✓        |

Missing fields blocking BASIC_WL parity:
1. **`TaxCurrencyCode` (BT-6)** on `TradeSettlement`. Required when `MonetarySummation` carries a second `TaxTotalAmount` with `currencyID` differing from `InvoiceCurrencyCode`. Pair with bug #6 (TaxTotal as list).
2. **`BillingSpecifiedPeriod` (BG-14)** on `TradeSettlement` — invoice-level period start/end dates. Triggered by BR-CO-19 and BR-CO-26.
3. **`InvoiceReferencedDocument` 0..*** — carthorse declares a single `invoice_referenced_document`, the XSD allows unbounded.

### BASIC (64-page appendix, 111 ram elements)

What BASIC adds: line items. The line item container `IncludedSupplyChainTradeLineItem`
(BG-25) is **not modelled** in carthorse beyond an empty stub (`schema/trade.py`).
At BASIC, each line carries:

```
IncludedSupplyChainTradeLineItem (BG-25)            1..unbounded
  AssociatedDocumentLineDocument (BT-126-00)
    LineID (BT-126)                                 1..1
    IncludedNote (BT-127-00)                        0..1   { Content (BT-127) }
  SpecifiedTradeProduct (BG-31)
    GlobalID (BT-157) [schemeID req]                0..1
    Name (BT-153)                                   1..1
  SpecifiedLineTradeAgreement (BG-29)
    GrossPriceProductTradePrice (BT-148-00)         0..1
      ChargeAmount (BT-148)                         1..1
      BasisQuantity (BT-149-1) [unitCode BT-150-1]  0..1
      AppliedTradeAllowanceCharge <Price allowance> 0..1
        ChargeIndicator                             1..1
        ActualAmount (BT-147)                       1..1
    NetPriceProductTradePrice (BT-146-00)           1..1
      ChargeAmount (BT-146)                         1..1
      BasisQuantity (BT-149) [unitCode BT-150]      0..1
  SpecifiedLineTradeDelivery (BT-129-00)
    BilledQuantity (BT-129) [unitCode BT-130]       1..1
  SpecifiedLineTradeSettlement (BG-30-00)
    ApplicableTradeTax (BG-30)                      1..1
      TypeCode (BT-151-0)                           1..1   "VAT"
      CategoryCode (BT-151)                         1..1
      DueDateTypeCode (BT-X-589)                    0..1
      RateApplicablePercent (BT-152)                0..1
    BillingSpecifiedPeriod (BG-26)                  0..1   { Start/End }
    SpecifiedTradeAllowanceCharge <Allowance> (BG-27) 0..unbounded
    SpecifiedTradeAllowanceCharge <Charge> (BG-28)    0..unbounded
    SpecifiedTradeSettlementLineMonetarySummation (BT-131-00)
      LineTotalAmount (BT-131)                      1..1
```

This is the single largest piece of missing structure. A full BG-25
implementation needs:

1. `TradeLineItem`, `AssociatedDocumentLineDocument`, `IncludedNote` (line-level)
2. `TradeProduct` (BG-31): `GlobalID`, `Name`, plus EN16931 fields `SellerAssignedID`, `BuyerAssignedID`, `Description`, `ApplicableProductCharacteristic` (BG-32, EN16931+), `DesignatedProductClassification` (BG-33, EN16931+), `OriginTradeCountry` (BG-34, EN16931+).
3. `TradePrice` (gross + net), with line-level `AppliedTradeAllowanceCharge`.
4. `LineTradeAgreement`, `LineTradeDelivery`, `LineTradeSettlement`.
5. `BilledQuantity` carrying `unitCode` (mandatory attribute, UNTDID/UNECE Rec 20).

### EN 16931 / COMFORT (75-page appendix, 152 ram elements)

EN 16931 enriches what's already modelled rather than adding many new
top-level structures. Notable additions:

| Container                                       | New elements                                                                                  |
|-------------------------------------------------|-----------------------------------------------------------------------------------------------|
| `ExchangedDocument`                             | (none beyond BASIC)                                                                           |
| `SellerTradeParty` / `BuyerTradeParty`          | `Description` (BT-33 / BT-46?), `DefinedTradeContact` (BG-6 / BG-9) ✓                         |
| `ApplicableHeaderTradeAgreement`                | `SellerOrderReferencedDocument` (BT-14), `AdditionalReferencedDocument` 0..* (BG-24), `SpecifiedProcuringProject` (BT-11) ✓ |
| `ApplicableHeaderTradeDelivery`                 | `ReceivingAdviceReferencedDocument` (BT-15) ✓                                                 |
| `ApplicableHeaderTradeSettlement`               | `RoundingAmount` (BT-114) on `MonetarySummation` ✗; richer `TradeSettlementPaymentMeans` with `Information`, `ApplicableTradeSettlementFinancialCard` (BG-18), `PayeeSpecifiedCreditorFinancialInstitution` ✗ |
| `ApplicableTradeTax` (header + line)            | `TaxPointDate` (BT-7) — must NOT coexist with `DueDateTypeCode` (BR-CO-3) ✗                   |
| `LineTradeAgreement`                            | `BuyerOrderReferencedDocument` (line-level) ✗                                                 |
| `LineTradeSettlement`                           | `AdditionalReferencedDocument` (line-level), `ReceivableSpecifiedTradeAccountingAccount` (line-level) ✗ |
| `ReferencedDocument` (header-level Additional)  | Adds `URIID`, `LineID`, `TypeCode`, `Name`, `AttachmentBinaryObject`, `ReferenceTypeCode` ✓ (carthorse models all of these on `AdditionalReferencedDocument`) |

Major missing items at EN16931:
1. `MonetarySummation.rounding_amount` (BT-114) — used by BR-CO-16.
2. `ApplicableTradeTax.tax_point_date` (BT-7) — pair with BR-CO-3.
3. `PaymentMeans.financial_card` (BG-18) and `payee_financial_institution`.
4. `LineTradeSettlement.additional_references` and `accounting_account` — line-level versions of header-level fields.
5. Product-level groups: `ApplicableProductCharacteristic` (BG-32), `DesignatedProductClassification` (BG-33), `OriginTradeCountry` (BG-34).

### EXTENDED (214-page appendix, 265 ram elements)

EXTENDED is the Factur-X CIUS overlay: it adds many `BT-X-*` extensions,
relaxes some cardinalities, and replaces a handful of `BR-CO-*` rules
with tolerance-banded variants. Carthorse models a few EXTENDED-only
structures (`EmailURI`, `EffectivePeriod`, `BusinessDocument`,
`ProductEndUserTradeParty`, `ShipFromTradeParty`,
`UltimateShipToTradeParty`, `LogisticsTransportMovement`,
`SupplyChainConsignment`, `DeliveryNoteReferencedDocument`,
`UltimateCustomerOrderReferencedDocument`) but the bulk of EXTENDED is missing:

- `ExchangedDocumentContext`: `BusinessProcessSpecifiedDocumentContextParameter` becomes `1..1` at EXTENDED only (`0..1` everywhere else).
- `HeaderTradeAgreement` adds `SalesAgentTradeParty` (BG-X-49), `BuyerAgentTradeParty` (BG-X-62), `BuyerTaxRepresentativeTradeParty` (BG-X-54), header-level `BuyerOrderReferencedDocument` widened with `LineID`/`FormattedIssueDateTime`, `ApplicableTradeDeliveryTerms` (BG-X-22), `QuotationReferencedDocument` (BG-X-61), `UltimateCustomerOrderReferencedDocument` 0..* (BG-X-23).
- `HeaderTradeDelivery` adds `RelatedSupplyChainConsignment` (BG-X-24, modelled at the wrong level in carthorse today), `UltimateShipToTradeParty`, `ShipFromTradeParty`.
- `HeaderTradeSettlement` adds `InvoiceIssuerReference`, `InvoicerTradeParty` (BG-X-33), `InvoiceeTradeParty` (BG-X-36), `PayerTradeParty` (BG-X-73), `TaxApplicableTradeCurrencyExchange` (BG-X-41), `SpecifiedLogisticsServiceCharge` 0..* (BG-X-42), `SpecifiedTradePaymentTerms` becomes 0..unbounded with payment-term-specific Payee, `ApplicableTradePaymentPenaltyTerms` (BG-X-43), `ApplicableTradePaymentDiscountTerms` (BG-X-44), `SpecifiedAdvancePayment` 0..* (BG-X-45) carrying nested `IncludedTradeTax` (BG-X-46).
- `IncludedSupplyChainTradeLineItem` gains line-level Ship-To (BG-X-7), Ultimate-Ship-To (BG-X-10), sub-invoice-line semantics via `BT-X-7` (line status), `BT-X-8` (line subtype), `BT-X-304` (parent line ID), `SpecifiedTradeProduct.IncludedReferencedProduct` 0..* (BG-X-1), `IndividualTradeProductInstance` (BG-X-84), per-line deviating Seller (BG-X-90), and many leaf BT-X-* fields. The sub-invoice-line feature is what the Factur-X "SubInvoiceLine" example invoices in `origin/docs` use.

EXTENDED also reshapes the rule layer:

- `BR-FXEXT-CO-10..13` and `BR-FXEXT-CO-15` replace the `BR-CO-10..13/15` arithmetic identities with `≤ 0.01 × N` rounding tolerance and include `BT-X-272` (Logistics Service fee) in the charge sums.
- `BR-FXEXT-S-08/09`, `BR-FXEXT-AE-08`, `BR-FXEXT-AF-08` (`L` IGIC), `BR-FXEXT-AG-08` (`M` IPSI), `BR-FXEXT-IC-08`, `BR-FXEXT-G-08`, `BR-FXEXT-O-08`, `BR-FXEXT-E-08`, `BR-FXEXT-Z-08` are the per-VAT-category replacements.
- `BR-FXEXT-BR-22..27` and `BR-FXEXT-CO-04` add a "but only when `BT-X-8` is DETAIL or unspecified" qualifier, exempting GROUP and INFORMATION lines from line-level required-field rules.
- `BR-CO-17` is **dropped** at EXTENDED; the per-category tolerance variants subsume it.
- `BR-FX-DE-04` (German country variant) requires every line of a non-down-payment invoice to carry `BT-72` or `BG-14` or `BG-26`; without `BT-72`, `BT-80` must be present.
- `PEPPOL-EN16931-R008` (informational warning): document MUST NOT contain empty elements.

Recommendation: stop carthorse at EN 16931 for the time being. Building
out EXTENDED in a maintainable way needs a code-generation pipeline
driven by the XSD; hand-modelling every BT-X-* field is not sustainable
and the validator surface explodes (BR-FXEXT family alone would more
than double the rule count).

## 3. Validation rules to add

See `docs/VALIDATION.md` for the full BR-* catalogue with implementation
status. The validation rules that should land before any new structure
work are:

1. **BR-CO-9** — `Seller VAT identifier`, `Seller tax representative VAT identifier`, `Buyer VAT identifier` must start with an ISO 3166-1 alpha-2 country prefix (Greece may use `EL`). Add to `TaxSchemeId.validate_internal` for `scheme_id == "VA"`. *Lowest profile: MINIMUM.*
2. **BR-CO-25** — if `due_amount > 0` then `PaymentTerms.due` (BT-9) or `PaymentTerms.description` (BT-20) must be present. *MINIMUM.*
3. **BR-CO-26** — Seller automatic identification: at least one of `Seller.id` (BT-29), `Seller.legal_organization.id` (BT-30), `Seller.tax_registrations[VAT].id` (BT-31) must be present. *MINIMUM.*
4. **BR-CO-3** — `TaxPointDate` (BT-7) and `DueDateTypeCode` (BT-8) are mutually exclusive. Add as a `validate_internal` on `ApplicableTradeTax` once BT-7 is modelled. *EN16931.*
5. **BR-AE/BR-E/BR-G/BR-IC/BR-IG/BR-IP/BR-O/BR-S/BR-Z (the `-2/3/4` rules)** — VAT-category ⇒ required parties matrix. The matrix is uniform across categories and is documented in `docs/VALIDATION.md §3.2`; implement once on `Trade.validate_internal` after collecting the category set across lines, header allowances, and header charges. Watch for the spec quirk in `BR-O-2` (forbids buyer **ID** BT-46, while `BR-O-3/4` forbid buyer **VAT ID** BT-48).
6. **BR-IC-11 / BR-IC-12** — `K` (intra-community) ⇒ `BT-72` *or* `BG-14` and `BT-80` (deliver-to country) must be present. *BASIC_WL.*
7. **BR-O-11..14** — single-rate restriction for `O` (not subject to VAT). *BASIC_WL.*
8. **BR-CO-21..24 line side** (`TradeAllowanceCharge.validate_internal` already covers the doc-side) once line items are modelled.
9. **BR-29 / BR-30** — period start ≤ end. *Once BG-14 / BG-26 are modelled.*
10. **BR-CO-10..17** — sum/arithmetic identities on monetary totals. They need amounts and a working line-item model; defer until §2.BASIC is done.
11. **BR-62 / BR-63** — Seller / Buyer electronic address must have a `schemeID`. Today `URIID` is gated on the dataclass without enforcing the attribute presence. *BASIC_WL.*

Many `validate_internal` methods today either don't exist or live next to a
plain `raise ValueError`. Standardise on `ValidationError(code, message)`
where `code` is the BR-* id, so the README and `docs/VALIDATION.md` stay
referenceable.

## 4. Suggested ordering

1. **Bug-fix sweep** (§1, items #1–#9). Self-contained, mostly one-liner
   tag/attr/cardinality fixes. Each one removes an item from the
   `xfail` list of `tests/test_hypothesis.py::test_parse_and_regenerate`.
2. **Round-trip currencyID on amounts** (§1 #7). Touches `element.py` and
   every `Decimal` field with `currencyID`. Big enough to merit its own
   commit; small enough to ship before BG-25.
3. **TaxCurrencyCode + BillingSpecifiedPeriod + multi-TaxTotal** (BASIC_WL
   gaps). Unblocks header-level period rules and foreign-currency invoices.
4. **BR-CO-9, BR-CO-25, BR-CO-26, BR-CO-3** validators — small,
   focused, no new fields.
5. **BG-25 line-item structure** (BASIC). Largest piece. Unlocks
   BR-12, BR-21..28, BR-CO-4, BR-CO-10..17, every per-VAT-category
   "in an Invoice line where …" rule.
6. **EN 16931 enrichments** — `RoundingAmount`, `TaxPointDate`,
   product characteristics / classifications, line-level references.
7. **EXTENDED**: scope on demand only, driven by concrete sample
   invoices that need it.

## 5. Out of scope (today)

- **PDF/A-3 packaging.** Carthorse handles only the embedded
  `factur-x.xml`. Embedding it in a PDF/A-3 invoice (or extracting it
  from one) is delegated to `factur-x` (PyPI) or external tooling.
- **Schematron / business-rule generation from `.sch` files.** The
  per-profile `FACTUR-X_<PROFILE>.sch` schematron files are *not*
  vendored under `tests/schemas/` (only the XSDs are). If we want
  automated BR-* enforcement against the official rules, the
  schematron files are the source of truth.
- **EXTENDED CIUS** (`BT-X-*`, `BG-X-*`). Modelled selectively as
  needed; no plan for full coverage.
