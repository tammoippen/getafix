# Validation rules

Catalogue of every EN 16931 / Factur-X 1.08 / ZUGFeRD 2.4 business rule
referenced in the technical appendices, together with carthorse's
current enforcement status.

The naming follows the spec:

| Family       | Topic                                                                                |
|--------------|--------------------------------------------------------------------------------------|
| `BR-1..65`   | Structural / required-field rules (one rule per BT presence requirement)             |
| `BR-CO-3..26`| Cross-field arithmetic and conditional rules                                         |
| `BR-AE-*`    | VAT category "Reverse charge" (UNTDID 5305 = `AE`)                                   |
| `BR-E-*`     | VAT category "Exempt from VAT" (`E`)                                                 |
| `BR-G-*`     | VAT category "Export outside the EU" (`G`)                                           |
| `BR-IC-*`    | VAT category "Intra-community supply" (`K`)                                          |
| `BR-IG-*`    | VAT category "IGIC" — Canary Islands (`L`)                                           |
| `BR-IP-*`    | VAT category "IPSI" — Ceuta/Melilla (`M`)                                            |
| `BR-O-*`     | VAT category "Not subject to VAT" (`O`)                                              |
| `BR-S-*`     | VAT category "Standard rated" (`S`)                                                  |
| `BR-Z-*`     | VAT category "Zero rated" (`Z`)                                                      |
| `BR-FXEXT-*` | Factur-X EXTENDED CIUS overlay; replaces some `BR-CO-*` and adds tolerance bands     |
| `BR-FX-DE-*` | Country-coded variant (Germany)                                                      |

A rule's **lowest enforcing profile** is the lowest profile that has all
elements the rule references. A rule may technically appear in every
profile's appendix but only become *checkable* when the referenced fields
are part of the schema for that profile.

Status legend:

* **✓** — `validate_internal` raises a `ValidationError(code, message)`
  with the BR-* code as the error code.
* **◯** — implicit: required field on the dataclass means an instance can
  only exist if the value is supplied. Missing-field violation is
  reported by Python's dataclass machinery (`__init__` raises) before
  validation runs.
* **△** — partial: some shape of the rule is checked (e.g. token shape)
  but the cross-field condition isn't.
* **—** — not enforced.

## 1. Structural and required-field rules (`BR-*`)

| Rule  | Lowest profile | Status | Where carthorse enforces                         |
|-------|----------------|--------|--------------------------------------------------|
| BR-1  | MINIMUM        | ◯      | `Context.guideline.id: Profile` (required)        |
| BR-2  | MINIMUM        | ◯      | `Header.id: str` (required)                       |
| BR-3  | MINIMUM        | ◯      | `Header.issue_date: date` (required)              |
| BR-4  | MINIMUM        | ◯      | `Header.type_code: TypeCode` (required)           |
| BR-5  | MINIMUM        | △      | `TradeSettlement.validate_internal` checks the alpha-3 uppercase shape, not the ISO 4217 registry |
| BR-6  | MINIMUM        | ◯      | `SellerTradeParty.name` (required)                |
| BR-7  | MINIMUM        | ◯      | `BuyerTradeParty.name` (required)                 |
| BR-8  | MINIMUM        | ◯      | `SellerTradeParty.address` (required)             |
| BR-9  | MINIMUM        | ◯      | `PostalTradeAddress.country_id` (required)        |
| BR-10 | BASIC_WL       | ⚠      | `BuyerTradeParty.address` is required at MINIMUM too — see implementation plan §1 |
| BR-11 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id`                   |
| BR-12 | BASIC_WL       | ⚠      | `MonetarySummation.line_total` required even at MINIMUM (where BT-106 is not part of the XSD) |
| BR-13 | MINIMUM        | ◯      | `MonetarySummation.tax_basis_total`               |
| BR-14 | MINIMUM        | ◯      | `MonetarySummation.grand_total`                   |
| BR-15 | MINIMUM        | ◯      | `MonetarySummation.due_amount`                    |
| BR-16 | BASIC          | ✓      | `Trade.validate_internal` raises `BR-16` when `len(items) == 0` and `profile > BASIC_WL`  |
| BR-17 | BASIC_WL       | ◯      | `PayeeTradeParty.name` required when `payee` is set |
| BR-18 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.name`          |
| BR-19 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.address`       |
| BR-20 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id`                   |
| BR-21 | BASIC          | —      | line items not modelled                           |
| BR-22 | BASIC          | —      | line items                                        |
| BR-23 | BASIC          | —      | line items                                        |
| BR-24 | BASIC          | —      | line items                                        |
| BR-25 | BASIC          | —      | line items                                        |
| BR-26 | BASIC          | —      | line items                                        |
| BR-27 | BASIC          | —      | line items: `BT-146 ≥ 0`                          |
| BR-28 | BASIC          | —      | line items: `BT-148 ≥ 0`                          |
| BR-29 | BASIC_WL       | —      | period start/end ordering — BG-14 not modelled    |
| BR-30 | BASIC          | —      | line period — line items not modelled             |
| BR-31 | BASIC_WL       | ◯      | `TradeAllowanceCharge.actual_amount`              |
| BR-32 | BASIC_WL       | ◯      | `CategoryTradeTax.category_code`                  |
| BR-33 | BASIC_WL       | ✓      | `TradeAllowanceCharge.validate_internal` (allowance side)  |
| BR-36 | BASIC_WL       | ◯      | `TradeAllowanceCharge.actual_amount`              |
| BR-37 | BASIC_WL       | ◯      | `CategoryTradeTax.category_code`                  |
| BR-38 | BASIC_WL       | ✓      | `TradeAllowanceCharge.validate_internal` (charge side)     |
| BR-41 | BASIC          | —      | line allowance — line items not modelled          |
| BR-42 | BASIC          | —      | line allowance reason coupling                    |
| BR-43 | BASIC          | —      | line charge                                       |
| BR-44 | BASIC          | —      | line charge reason coupling                       |
| BR-45 | BASIC_WL       | ◯      | `ApplicableTradeTax.basis_amount`                 |
| BR-46 | BASIC_WL       | ◯      | `ApplicableTradeTax.calculated_amount`            |
| BR-47 | BASIC_WL       | ◯      | `ApplicableTradeTax.category_code`                |
| BR-48 | BASIC_WL       | —      | rate-required-unless-not-subject not enforced     |
| BR-49 | BASIC_WL       | ◯      | `PaymentMeans.type_code`                          |
| BR-50 | BASIC_WL       | ✓      | `PayeePartyCreditorFinancialAccount.validate_internal` |
| BR-51 | EN16931        | —      | financial card not modelled                       |
| BR-52 | EN16931        | ◯      | `AdditionalReferencedDocument.issuer_assigned_id` |
| BR-53 | BASIC_WL       | —      | requires multi-`TaxTotal` model + BT-6 field      |
| BR-54 | EN16931        | —      | `ApplicableProductCharacteristic` not modelled    |
| BR-55 | BASIC_WL       | ◯      | `InvoiceReferencedDocument.issuer_assigned_id`    |
| BR-56 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.tax_registrations` (required) |
| BR-57 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id` on ship-to        |
| BR-61 | BASIC_WL       | —      | Type-code → IBAN coupling not enforced            |
| BR-62 | BASIC_WL       | —      | electronic-address scheme id required             |
| BR-63 | BASIC_WL       | —      | electronic-address scheme id required             |
| BR-64 | BASIC          | —      | line items                                        |
| BR-65 | EN16931        | —      | product classification not modelled               |

## 2. Cross-field arithmetic / conditional rules (`BR-CO-*`)

| Rule       | Lowest profile | Status | Notes                                                                                       |
|------------|----------------|--------|---------------------------------------------------------------------------------------------|
| BR-CO-3    | EN16931        | —      | `TaxPointDate` (BT-7) and `DueDateTypeCode` (BT-8) mutually exclusive — BT-7 not modelled    |
| BR-CO-4    | BASIC          | —      | line item must have `BT-151` — line items not modelled                                       |
| BR-CO-5    | BASIC_WL       | —      | reason ↔ reason-code coherence on document-level allowance                                   |
| BR-CO-6    | BASIC_WL       | —      | same for document-level charge                                                               |
| BR-CO-7    | BASIC          | —      | line allowance                                                                               |
| BR-CO-8    | BASIC          | —      | line charge                                                                                  |
| BR-CO-9    | MINIMUM        | ✓      | `TaxSchemeId.validate_internal` enforces the ISO 3166-1 alpha-2 country prefix on `VA`-scheme identifiers (with `EL` allowed for Greece). |
| BR-CO-10   | BASIC          | —      | `BT-106 = ΣBT-131` — needs line items                                                        |
| BR-CO-11   | BASIC_WL       | —      | `BT-107 = ΣBT-92`                                                                            |
| BR-CO-12   | BASIC_WL       | —      | `BT-108 = ΣBT-99`                                                                            |
| BR-CO-13   | BASIC          | —      | `BT-109 = ΣBT-131 − BT-107 + BT-108` — needs line items                                       |
| BR-CO-14   | BASIC_WL       | —      | `BT-110 = ΣBT-117`                                                                           |
| BR-CO-15   | MINIMUM        | —      | `BT-112 = BT-109 + BT-110`                                                                   |
| BR-CO-16   | MINIMUM        | —      | `BT-115 = BT-112 − BT-113 + BT-114` (`BT-114` only from EN16931)                             |
| BR-CO-17   | BASIC_WL       | —      | `BT-117 = round(BT-116 × BT-119 / 100, 2)` per VAT breakdown row. **Dropped at EXTENDED**, replaced by per-category `BR-FXEXT-S-09` etc. |
| BR-CO-18   | MINIMUM        | ✓      | `TradeSettlement.validate_internal` raises `BR-CO-18` when no `trade_taxes` at `>= BASIC_WL`. **Note:** the comparator bug in `Profile.__lt__` makes this fire at MINIMUM as well today, see `docs/IMPLEMENTATION_PLAN.md §1 #8`. |
| BR-CO-19   | BASIC_WL       | —      | if BG-14 used then BT-73 or BT-74 must be filled                                             |
| BR-CO-20   | BASIC          | —      | line period analogue                                                                         |
| BR-CO-21   | BASIC_WL       | ✓      | `TradeAllowanceCharge.validate_internal` (allowance reason or reason-code or both)            |
| BR-CO-22   | BASIC_WL       | ✓      | same for charge                                                                              |
| BR-CO-23   | BASIC          | —      | line allowance                                                                               |
| BR-CO-24   | BASIC          | —      | line charge                                                                                  |
| BR-CO-25   | MINIMUM        | ✓      | `TradeSettlement.validate_internal` checks that positive `due_amount` (BT-115) is paired with `terms.due` (BT-9) or `terms.description` (BT-20). |
| BR-CO-26   | MINIMUM        | ✓      | `SellerTradeParty.validate_internal` raises if neither `id` (BT-29), `legal_organization.id` (BT-30) nor a VAT-scheme `tax_registrations[*]` (BT-31) is present. |

## 3. VAT-category families

The seven non-trivial VAT categories all share a common rule layout (rules
1..10). The columns marked **R** (required), **F** (forbidden), **=0**
(value must be zero), **>0** (value must be positive) and **≥0** (value
non-negative) summarise the field-level constraints they impose.

### 3.1 Common rule shape per category

For category `X` ∈ {`AE`, `E`, `G`, `IC` (`K`), `IG` (`L`), `IP` (`M`), `O`, `S`, `Z`}:

| Rule    | Subject                                                                                          |
|---------|--------------------------------------------------------------------------------------------------|
| `BR-X-1`| BG-23 must contain at least one breakdown row for category `X` if any line/allowance/charge uses `X` |
| `BR-X-2`| Line `X` ⇒ Seller VAT ID (or tax-rep) [+ Buyer VAT ID for `AE`, `IC`]                            |
| `BR-X-3`| Document-level allowance `X` ⇒ same Seller (and Buyer for `AE`, `IC`) IDs                        |
| `BR-X-4`| Document-level charge `X` ⇒ same                                                                 |
| `BR-X-5`| Line VAT rate constraint per `X`                                                                 |
| `BR-X-6`| Document-level allowance VAT rate constraint                                                     |
| `BR-X-7`| Document-level charge VAT rate constraint                                                        |
| `BR-X-8`| BT-116 sum identity: `ΣBT-131 + ΣBT-99 − ΣBT-92` over rows of category `X`                       |
| `BR-X-9`| BT-117 (the row's tax amount) constraint                                                         |
| `BR-X-10`| Exemption reason text/code requirement per category                                             |

### 3.2 Per-category required-party + rate matrix

| Category (BT-118)        | Seller VAT IDs          | Buyer IDs             | Rate    | Exemption reason  |
|---------------------------|-------------------------|-----------------------|---------|-------------------|
| `AE` Reverse charge       | BT-31 \| BT-32 \| BT-63 (R) | BT-48 \| BT-47 (R) | =0      | text or code "Reverse charge" (R) |
| `E` Exempt from VAT       | BT-31 \| BT-32 \| BT-63 (R) | —                     | =0      | text or code (R)              |
| `G` Export outside EU     | BT-31 \| BT-63 (R) — note BT-32 explicitly excluded | — | =0 | text or code (R) |
| `K` Intra-community       | BT-31 \| BT-63 (R)      | BT-48 (R)             | =0      | text or code (R)              |
| `L` IGIC                  | BT-31 \| BT-32 \| BT-63 (R) | —                     | ≥0      | text and code (F)             |
| `M` IPSI                  | BT-31 \| BT-32 \| BT-63 (R) | —                     | ≥0      | text and code (F)             |
| `O` Not subject to VAT    | BT-31, BT-63 (F); BT-46 (F) — note `BR-O-2` says BT-46 (Buyer **ID**), `BR-O-3/4` say BT-48 (Buyer **VAT** ID); spec quirk | BT-46 / BT-48 (F) | n/a | text or code (R) |
| `S` Standard rated        | BT-31 \| BT-32 \| BT-63 (R) | —                     | >0      | text and code (F)             |
| `Z` Zero rated            | BT-31 \| BT-32 \| BT-63 (R) | —                     | =0      | text and code (F)             |

Also:

* `BR-IC-11` — `K` ⇒ `BT-72` (actual delivery date) **or** `BG-14`
  (invoicing period) must be present. *Lowest enforcing profile:
  BASIC_WL.*
* `BR-IC-12` — `K` ⇒ `BT-80` (deliver-to country code) must be
  present. *Lowest enforcing profile: BASIC_WL.*
* `BR-O-11..14` — `O` is single-rate: an invoice with one BG-23 row of
  category `O` must not contain any other BG-23 row, nor any line
  (BG-25), document-level allowance (BG-20) or document-level charge
  (BG-21) with a category code other than `O`.

None of the per-category families are currently enforced by carthorse.

## 4. EXTENDED (`BR-FXEXT-*`, `BR-FX-DE-*`)

EXTENDED introduces a CIUS-specific rule overlay. Rules in this family
either replace `BR-CO-*` / `BR-S-*` / per-category counterparts, adding
a `≤ 0.01 × N` rounding tolerance, or model new constraints on the
EXTENDED-only sub-line-item structure (`BT-X-8` line subtype,
`BT-X-304` parent line ID, `BG-X-1` IncludedReferencedProduct,
`BT-X-272` Logistics Service fees).

| Rule          | Replaces / new | Effect                                                                                                                            |
|---------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `BR-FXEXT-01` | New (BT-21+BT-22 coupling)    | If `BT-21` set, `BT-X-5` or `BT-22` must be present; if both, same meaning |
| `BR-FXEXT-02` | New (line-level analogue)     | `BT-X-10` ⇒ `BT-X-9` or `BT-127`                                            |
| `BR-FXEXT-03` | New (deviating-party VAT-only)| 14 EXTENDED-only deviating-party blocks may carry only a VAT registration ID |
| `BR-FXEXT-04` | New                           | Item attribute values from `UNTDED 6313`+Factur-X extension code list      |
| `BR-FXEXT-05` | New                           | `BT-X-8` value from Line Status Reason code list                            |
| `BR-FXEXT-06` | New                           | `BT-X-304` ⇒ `BT-X-8` set on every BG-25                                   |
| `BR-FXEXT-07..09` | New                       | Optionality of `BT-146/BT-129/BT-130/BG-30` depends on `BT-X-8` value (DETAIL / GROUP / INFORMATION) |
| `BR-FXEXT-08` | New                           | If `BT-X-8` = GROUP and `BT-131` set, the `BT-131` of the group equals the sum over child DETAIL/GROUP lines' `BT-131` |
| `BR-FXEXT-10` | New                           | `BG-X-1 IncludedReferencedProduct` content excluded from invoice math       |
| `BR-FXEXT-11` | New                           | Each `BT-X-304` references an existing `BT-126`                             |
| `BR-FXEXT-BR-22..27`, `BR-FXEXT-CO-04` | replaces `BR-22..27`, `BR-CO-4` | "but only when `BT-X-8` is DETAIL or unspecified" — GROUP/INFORMATION lines exempt |
| `BR-FXEXT-CO-10..13`, `BR-FXEXT-CO-15` | replaces `BR-CO-10..13` and `BR-CO-15` | Adds `≤ 0.01 × N` rounding tolerance and includes `BT-X-272` (Logistics Service fee) in charge sums |
| `BR-FXEXT-S-08/09`, `BR-FXEXT-AE-08`, `BR-FXEXT-AF-08` (`L`/IGIC), `BR-FXEXT-AG-08` (`M`/IPSI), `BR-FXEXT-IC-08`, `BR-FXEXT-G-08`, `BR-FXEXT-O-08`, `BR-FXEXT-E-08`, `BR-FXEXT-Z-08` | replaces `BR-S-08/09`, `BR-AE-08`, `BR-IC-08`, … | Same tolerance + `BT-X-272` inclusion + DETAIL-only filter |
| `BR-CO-17`     | **Dropped** at EXTENDED       | Per-row math is replaced by the per-category `*-09` family above             |
| `BR-FX-DE-04`  | New (DE)                      | Non-down-payment invoice (`BT-3` ≠ `386`) must include `BT-72` or `BG-14` or `BG-26` on every line; without `BT-72`, `BT-80` (deliver-to country) must be present |
| `PEPPOL-EN16931-R008` | Informational (warning) | Document MUST NOT contain empty elements                                      |

EXTENDED-specific rules are not in carthorse's roadmap (see
`docs/IMPLEMENTATION_PLAN.md §5`).

## 5. Cross-field validation patterns

The catalogue collapses into five recurring classes. Each new validator
should declare which of these it instantiates so we can review them
collectively.

### 5.1 Tax-category ⇒ required parties

VAT category code on a line, document-level allowance, or document-level
charge dictates which seller/buyer identifier(s) must (or must not) be
present at header level. Implemented as a single pass over
`(line items, allowances, charges) → set of categories` followed by
`Trade.validate_internal` walking the seller/buyer party blocks.
Rules: `BR-AE-2..4`, `BR-E-2..4`, `BR-G-2..4`, `BR-IC-2..4`, `BR-IG-2..4`,
`BR-IP-2..4`, `BR-O-2..4`, `BR-S-2..4`, `BR-Z-2..4`,
`BR-IC-11`, `BR-IC-12`, `BR-O-11..14`.

### 5.2 Currency code coupling

`BT-5` (invoice currency) and `BT-6` (VAT accounting currency) drive the
shape of `BG-22`: when `BT-6` is set there must be a second
`TaxTotalAmount` (BT-111) with `currencyID == BT-6`; the first
`TaxTotalAmount` (BT-110) carries `currencyID == BT-5`.
Additionally `BT-31`, `BT-63`, `BT-48` must each start with an ISO
3166-1 alpha-2 country code (Greece may use `EL`).
Rules: `BR-CO-9`, `BR-53`, `BR-FXEXT-CO-15` (currency match guard).

### 5.3 Period date ordering

Whenever a BG carries both a start and an end date, the end date must
be on or after the start. The rule applies to header invoicing period
(BG-14), line invoicing period (BG-26), and (in EXTENDED) per-line
delivery period.
Rules: `BR-29`, `BR-30`, `BR-CO-19`, `BR-CO-20`, `BR-FX-DE-04`.

### 5.4 Indicator / reason coupling

Allowance/charge groups (BG-20, BG-21, BG-27, BG-28) require either a
free-text reason or a coded reason or both, and when both are present
they must agree.
Rules: `BR-31..33`, `BR-36..38`, `BR-41..44`, `BR-CO-5..8`,
`BR-CO-21..24`. carthorse implements the "or both" half of `BR-CO-21/22`
in `TradeAllowanceCharge.validate_internal`.

### 5.5 Sums and arithmetic identities

The monetary totals on `BG-22` are sums of line-level and document-level
totals. Per-VAT-row identities apply within `BG-23`. EXTENDED widens
these to `≤ 0.01 × N` tolerance and adds `BT-X-272` (Logistics Service
fees).
Rules: `BR-CO-10..17`, `BR-AE-8/9`, `BR-E-8/9`, `BR-G-8/9`,
`BR-IC-8/9`, `BR-IG-8/9`, `BR-IP-8/9`, `BR-O-8/9`, `BR-S-8/9`,
`BR-Z-8/9`, `BR-FXEXT-CO-10..13/15`, `BR-FXEXT-{S,AE,AF,AG,IC,G,O,E,Z}-08/09`.

## 6. Summary

* MINIMUM rules currently enforceable: 9 of 13. Two structural divergences (BR-10 forced by required field, BR-12 likewise).
* BASIC_WL rules currently enforceable: 14 of 47. Most missing rules need either the multi-`TaxTotal` model (BR-53), the BG-14 period (BR-29 / BR-CO-19), or category-aware cross-field checks (BR-AE/BR-E/… families).
* BASIC and EN16931: ~0% — depend on line items being modelled.
* EXTENDED: out of scope.

The `tests/test_hypothesis.py::test_parse_and_regenerate` xfails
exercise both the structural gaps (line items, currency-aware totals)
and the bugs listed in `docs/IMPLEMENTATION_PLAN.md §1`. As gaps close,
individual examples flip from xfail to pass without test changes.
