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
| `BR-AF-*`    | VAT category "IGIC" — Canary Islands (`L`)                                           |
| `BR-AG-*`    | VAT category "IPSI" — Ceuta/Melilla (`M`)                                            |
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

`Document.validate()` collects every violation in one pass and raises
:class:`carthorse.schema.element.ValidationErrors` whose ``errors``
attribute lists each :class:`ValidationError`. The recursive
``validate_internal(profile)`` contract returns the list and never
raises; only the public ``Document.validate`` entry point raises the
aggregate.

## Per-profile rule enforcement summary

Coverage counts every rule whose **lowest enforcing profile** is at or
below the row's profile and whose status is ✓ (explicit
``ValidationError``) or ◯ (implicit via required dataclass field).

| Profile   | BR-* structural (§1) | BR-CO-* arithmetic (§2) | VAT-category families (§3) | Outstanding |
|-----------|----------------------|--------------------------|----------------------------|-------------|
| MINIMUM   | 12 / 12              | 4 / 4                    | n/a                        | BR-5 only checks the alpha-3 uppercase shape, not the ISO 4217 registry |
| BASIC_WL  | 27 / 27              | 13 / 14                  | full required-party + rate + exemption-reason (`*-2/-3/-4/-5/-6/-7/-10`) | BR-CO-5 / -6 (document-level allowance / charge reason coherence) |
| BASIC     | 36 / 36              | 16 / 18                  | full required-party + rate + exemption-reason | BR-CO-7 / -8 (line-level allowance / charge reason coherence); BR-42 / BR-44 cover the "or both" half only |
| COMFORT   | 39 / 39              | 16 / 18                  | full required-party + rate + exemption-reason | same as BASIC plus `BR-*-8 / -9` (per-category sum identities at BG-23) |
| EXTENDED  | 39 / 39              | 16 / 18                  | full required-party + rate + exemption-reason + BR-FXEXT-{cat}-08/09 tolerance variants | BR-FXEXT-01..05/07/10 and BR-FX-DE-04 — feature flags carthorse parses but doesn't yet check |

Notes:

* The four uncovered `BR-CO-*` rules are `BR-CO-5..8` (reason ↔
  reason-code coherence). The free-text "or both" half is enforced
  via `BR-CO-21..24`; the "agree when both are present" coupling
  needs a code-list join carthorse doesn't ship.
* The §3 per-VAT-category sum identities `BR-*-8 / -9` are not
  enforced at MINIMUM..COMFORT. EXTENDED replaces them with
  `BR-FXEXT-{cat}-08 / -09` (tolerance-banded, logistics-fee aware),
  which **are** implemented in
  :mod:`carthorse.rules.extended.br_fxext_vat_category_sums`.
* The MINIMUM profile lacks `SpecifiedTradePaymentTerms`, so
  `BR-CO-25` is gated on BASIC_WL+.
* BR-5 only validates the alpha-3 uppercase shape of the currency
  code; the ISO 4217 registry is not consulted.

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
| BR-10 | BASIC_WL       | ✓      | `BuyerTradeParty.validate_internal` — ``address: PostalTradeAddressExtended \| None`` is optional at MINIMUM (matching the XSD) and the validator fires when ``profile > MINIMUM and self.address is None`` |
| BR-11 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id`                   |
| BR-12 | BASIC_WL       | ✓      | `MonetarySummation.validate_internal` — raises when ``profile >= BASIC_WL`` and ``line_total`` (BT-106) is None |
| BR-13 | MINIMUM        | ◯      | `MonetarySummation.tax_basis_total`               |
| BR-14 | MINIMUM        | ◯      | `MonetarySummation.grand_total`                   |
| BR-15 | MINIMUM        | ◯      | `MonetarySummation.due_amount`                    |
| BR-16 | BASIC          | ✓      | `Trade.validate_internal` raises `BR-16` when `len(items) == 0` and `profile > BASIC_WL`  |
| BR-17 | BASIC_WL       | ◯      | `PayeeTradeParty.name` required when `payee` is set |
| BR-18 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.name`          |
| BR-19 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.address`       |
| BR-20 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id`                   |
| BR-21 | BASIC          | ◯      | `DocumentLineDocument.line_id` required (BT-126)  |
| BR-22 | BASIC          | ◯      | `LineTradeDelivery.billed_quantity` required (BT-129) |
| BR-23 | BASIC          | ◯      | `Quantity.unit_code` required (BT-130)            |
| BR-24 | BASIC          | ◯      | `TradeProduct.name` required (BT-153)             |
| BR-25 | BASIC          | ◯      | `NetTradePrice.charge_amount` required (BT-146)   |
| BR-26 | BASIC          | ◯      | `LineMonetarySummation.line_total` required (BT-131) |
| BR-27 | BASIC          | ✓      | `NetTradePrice.validate_internal` — raises when ``charge_amount`` (BT-146) is negative |
| BR-28 | BASIC          | ✓      | `GrossTradePrice.validate_internal` — raises when ``charge_amount`` (BT-148) is negative |
| BR-29 | BASIC_WL       | ✓      | `BillingSpecifiedPeriod.validate_internal` — BT-74 ≥ BT-73 when both supplied |
| BR-30 | BASIC          | ✓      | same validator on BG-26 (line invoicing period) — inherited |
| BR-31 | BASIC_WL       | ◯      | `TradeAllowanceCharge.actual_amount`              |
| BR-32 | BASIC_WL       | ◯      | `CategoryTradeTax.category_code`                  |
| BR-33 | BASIC_WL       | ✓      | `TradeAllowanceCharge.validate_internal` (allowance side)  |
| BR-36 | BASIC_WL       | ◯      | `TradeAllowanceCharge.actual_amount`              |
| BR-37 | BASIC_WL       | ◯      | `CategoryTradeTax.category_code`                  |
| BR-38 | BASIC_WL       | ✓      | `TradeAllowanceCharge.validate_internal` (charge side)     |
| BR-41 | BASIC          | ◯      | `TradeAllowanceCharge.actual_amount` required on BG-27 (BT-136) |
| BR-42 | BASIC          | △      | `TradeAllowanceCharge.reason`/`reason_code` shape; coupling enforced as `BR-CO-23` |
| BR-43 | BASIC          | ◯      | `TradeAllowanceCharge.actual_amount` required on BG-28 (BT-141) |
| BR-44 | BASIC          | △      | line charge reason coupling — enforced as `BR-CO-24` |
| BR-45 | BASIC_WL       | ◯      | `ApplicableTradeTax.basis_amount`                 |
| BR-46 | BASIC_WL       | ◯      | `ApplicableTradeTax.calculated_amount`            |
| BR-47 | BASIC_WL       | ◯      | `ApplicableTradeTax.category_code`                |
| BR-48 | BASIC_WL       | ✓      | `carthorse.rules.accounting.br_48` — `RateApplicablePercent` (BT-119) required unless `CategoryCode == "O"` |
| BR-49 | BASIC_WL       | ◯      | `PaymentMeans.type_code` (required); shape guard `BT-81` |
| BR-50 | BASIC_WL       | ✓      | `PayeePartyCreditorFinancialAccount.validate_internal` |
| BR-51 | COMFORT        | ✓      | `carthorse.rules.settlement.br_51` — `FinancialCard.id` must be 4..6 digits |
| BR-52 | COMFORT        | ◯      | `AdditionalReferencedDocument.issuer_assigned_id` |
| BR-53 | BASIC_WL       | ✓      | `TradeSettlement.validate_internal` — when BT-6 (`tax_currency_code`) is set, the `tax_total` list must contain an entry with `currency_id == BT-6` |
| BR-54 | COMFORT        | ◯      | `ProductCharacteristic` requires both `description` (BT-160) and `value` (BT-161) — both non-Optional |
| BR-55 | BASIC_WL       | ◯      | `InvoiceReferencedDocument.issuer_assigned_id` (`list[InvoiceReferencedDocument]`) |
| BR-56 | BASIC_WL       | ◯      | `SellerTaxRepresentativeTradeParty.tax_registrations` (required) |
| BR-57 | BASIC_WL       | ◯      | `PostalTradeAddress.country_id` on ship-to        |
| BR-61 | BASIC_WL       | ✓      | `carthorse.rules.settlement.br_61` — credit-transfer type codes (UNTDID 4461 `30`/`42`/`58`) require IBAN |
| BR-62 | BASIC_WL       | ✓      | `carthorse.rules.party.br_62` — Seller electronic-address `URIID` must carry `schemeID` |
| BR-63 | BASIC_WL       | ✓      | `carthorse.rules.party.br_63` — Buyer electronic-address `URIID` must carry `schemeID` |
| BR-64 | BASIC          | ◯      | `TradeProduct.global_id: GlobalID \| None` — the `GlobalID` class requires `schemeID` when set |
| BR-65 | COMFORT        | ◯      | `ProductClassification.list_id` required (non-Optional `str`) |

## 2. Cross-field arithmetic / conditional rules (`BR-CO-*`)

| Rule       | Lowest profile | Status | Notes                                                                                       |
|------------|----------------|--------|---------------------------------------------------------------------------------------------|
| BR-CO-3    | EN16931        | ✓      | `ApplicableTradeTax.validate_internal` — BT-7 (TaxPointDate) and BT-8 (DueDateTypeCode) on a single row are mutually exclusive. |
| BR-CO-4    | BASIC          | ◯      | line item VAT category implicit via `LineTradeSettlement.applicable_trade_tax` (required) and `ApplicableTradeTax.category_code` (required) — BT-151 always set |
| BR-CO-5    | BASIC_WL       | —      | reason ↔ reason-code coherence on document-level allowance                                   |
| BR-CO-6    | BASIC_WL       | —      | same for document-level charge                                                               |
| BR-CO-7    | BASIC          | —      | line allowance                                                                               |
| BR-CO-8    | BASIC          | —      | line charge                                                                                  |
| BR-CO-9    | MINIMUM        | ✓      | `TaxSchemeId.validate_internal` enforces the ISO 3166-1 alpha-2 country prefix on `VA`-scheme identifiers (with `EL` allowed for Greece). |
| BR-CO-10   | BASIC          | ✓      | `carthorse.rules.trade` — `BT-106 = ΣBT-131`. Skipped when BT-106 absent or items list empty. |
| BR-CO-11   | BASIC_WL       | ✓      | `carthorse.rules.trade` — `BT-107 = ΣBT-92`.                                   |
| BR-CO-12   | BASIC_WL       | ✓      | `carthorse.rules.trade` — `BT-108 = ΣBT-99`.                                   |
| BR-CO-13   | BASIC          | ✓      | `carthorse.rules.trade` — `BT-109 = ΣBT-131 − ΣBT-92 + ΣBT-99`. |
| BR-CO-14   | BASIC_WL       | ✓      | `TradeSettlement.validate_internal` — BT-110 = sum of BT-117 across BG-23 rows.              |
| BR-CO-15   | MINIMUM        | ✓      | `TradeSettlement.validate_internal` — `BT-112 = BT-109 + BT-110`.                            |
| BR-CO-16   | MINIMUM        | ✓      | `TradeSettlement.validate_internal` — `BT-115 = BT-112 − BT-113 + BT-114`. BT-114 absent ⇒ treated as 0. |
| BR-CO-17   | BASIC_WL       | ✓      | `ApplicableTradeTax.validate_internal` — `BT-117 = round(BT-116 × BT-119 / 100, 2)` per BG-23 row. **Dropped at EXTENDED**, replaced by per-category `BR-FXEXT-S-09` etc. |
| BR-CO-18   | BASIC_WL       | ✓      | `TradeSettlement.validate_internal` raises `BR-CO-18` when no `trade_taxes` at `>= BASIC_WL`. |
| BR-CO-19   | BASIC_WL       | ✓      | `BillingSpecifiedPeriod.validate_internal` — at least one of BT-73 (start) or BT-74 (end) is required when BG-14 is present. |
| BR-CO-20   | BASIC          | ✓      | same validator applied to BG-26 (line invoicing period) — inherited |
| BR-CO-21   | BASIC_WL       | ✓      | `carthorse.rules.trade` — header allowance reason or reason-code (or both) |
| BR-CO-22   | BASIC_WL       | ✓      | same for header charge                                                                       |
| BR-CO-23   | BASIC          | ✓      | `carthorse.rules.trade` — line allowance (BG-27) reason coupling               |
| BR-CO-24   | BASIC          | ✓      | same for line charge (BG-28)                                                                 |
| BR-CO-25   | BASIC_WL       | ✓      | `TradeSettlement.validate_internal` — gated on ``profile >= BASIC_WL`` since the source fields BT-9 / BT-20 live in ``SpecifiedTradePaymentTerms`` which the MINIMUM XSD does not include. Checks that positive ``due_amount`` (BT-115) is paired with ``terms.due`` (BT-9) or ``terms.description`` (BT-20). |
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

**Enforcement status:**

* ✓ Required-party `-2/-3/-4` rules across **AE / E / G / IC / IG / IP /
  S / Z** — implemented in
  :mod:`carthorse.rules.trade` as the per-category ``br_{ae,e,g,ic,af,ag,s,z}_2/3/4`` family.
* ✓ `BR-O-2/-3/-4` (forbid identifier set) — same module.
* ✓ `BR-O-11..14` single-rate restriction.
* ✓ `BR-IC-11`, `BR-IC-12` (intra-community delivery date / period and
  deliver-to country).
* ✓ Rate constraints `BR-*-5/-6/-7` (line / allowance / charge VAT
  rate vs category) — :func:`carthorse.rules.trade.vat_category_rates`.
* ✓ Exemption-reason coupling `BR-*-10` (categories that levy VAT
  must NOT carry an exemption reason; categories that don't levy VAT
  must) — :func:`carthorse.rules.trade.vat_category_exemption_reason`.
* — Tax-amount math `BR-*-8/-9` (per-category sum identities at
  BG-23) is not enforced at MINIMUM..COMFORT. At EXTENDED the
  tolerance-banded ``BR-FXEXT-{cat}-08/09`` family supersedes it
  and is implemented in :mod:`carthorse.rules.extended`.

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

**Enforcement status (EXTENDED overlay):**

* ✓ `BR-FXEXT-06` / `BR-FXEXT-08` / `BR-FXEXT-11` — sub-invoice-line
  parent/child / status / sum walker, in
  :mod:`carthorse.rules.extended`.
* ✓ `BR-FXEXT-22..27` and `BR-FXEXT-CO-04` — DETAIL / unset filter
  variants of `BR-22..27` / `BR-CO-4`. Wired alongside the EN 16931
  versions that short-circuit at EXTENDED.
* ✓ `BR-FXEXT-CO-10..13` and `BR-FXEXT-CO-15` — tolerance-banded
  replacements for `BR-CO-10..13/15`, folding `BT-X-272`
  (logistics-service fees) into the charge sums.
* ✓ Per-category sum identities `BR-FXEXT-{S,Z,E,AE,G,IC,AF,AG,O}-08`
  and the rate-derivation check `BR-FXEXT-S-09` — implemented in
  :func:`carthorse.rules.extended.br_fxext_vat_category_sums`.
* — `BR-FXEXT-01..05`, `BR-FXEXT-07`, `BR-FXEXT-10`, `BR-FX-DE-04`
  and `PEPPOL-EN16931-R008` are not enforced today; their input
  fields exist in the model but the checks themselves have no
  observed sample-driven need yet.

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
Rules: `BR-AE-2..4`, `BR-E-2..4`, `BR-G-2..4`, `BR-IC-2..4`, `BR-AF-2..4`,
`BR-AG-2..4`, `BR-O-2..4`, `BR-S-2..4`, `BR-Z-2..4`,
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
`BR-CO-21..24`. Carthorse implements the "or both" half of all four
`BR-CO-21..24` rules in :mod:`carthorse.rules.trade`. The "agree
when both present" coupling (`BR-CO-5..8`) is not yet enforced.

### 5.5 Sums and arithmetic identities

The monetary totals on `BG-22` are sums of line-level and document-level
totals. Per-VAT-row identities apply within `BG-23`. EXTENDED widens
these to `≤ 0.01 × N` tolerance and adds `BT-X-272` (Logistics Service
fees).
Rules: `BR-CO-10..17`, `BR-AE-8/9`, `BR-E-8/9`, `BR-G-8/9`,
`BR-IC-8/9`, `BR-AF-8/9`, `BR-AG-8/9`, `BR-O-8/9`, `BR-S-8/9`,
`BR-Z-8/9`, `BR-FXEXT-CO-10..13/15`, `BR-FXEXT-{S,AE,AF,AG,IC,G,O,E,Z}-08/09`.

## 6. Code-list rules (`BR-CL-*`)

EN 16931's `BR-CL-*` family closes the gap between the XSD
(``xs:token`` for code-valued fields) and the spec narrative (each
field must come from a named code list). Carthorse vendors each
closed list as a :class:`enum.StrEnum` in
:mod:`carthorse.schema.types` and re-types the affected fields to the
enum so construction and parse-time reject out-of-list values.
Generation pipeline: ``tools/extract_codelists.py`` regenerates the
``# AUTOGEN START <name>`` / ``# AUTOGEN END <name>`` regions from
the ``EN16931 code lists v16`` XLSX.

| Rule        | Enum                              | Field(s) re-typed                                                  |
|-------------|-----------------------------------|--------------------------------------------------------------------|
| `BR-CL-01`  | :class:`TypeCode`                 | ``Header.type_code`` (BT-3)                                        |
| `BR-CL-03..05` | :class:`Currency`              | ``TradeSettlement.currency_code`` (BT-5), ``TradeSettlement.tax_currency_code`` (BT-6), ``TaxTotal.currency_id`` (BT-110-0 / BT-111-0), ``TaxCurrencyExchange.source_currency_code`` / ``.target_currency_code`` |
| `BR-CL-06`  | :class:`UNTDID2475TaxPointDateCode` | ``ApplicableTradeTax.due_date_code`` (BT-8)                       |
| `BR-CL-14/15` | :class:`Country`                | ``PostalTradeAddress.country_id`` (BT-40 / BT-55 / BT-69 / BT-80), ``RelevantTradeLocation.country_id`` |
| `BR-CL-16`  | :class:`UNTDID4461PaymentMeansCode` | ``PaymentMeans.type_code`` (BT-81)                                |
| `BR-CL-17/18` | :class:`CategoryCode`           | ``ApplicableTradeTax.category_code`` (BT-118 / BT-151), ``CategoryTradeTax.category_code`` (BT-95 / BT-102), ``AppliedTradeTax.category_code`` (BT-X-273), ``AdvancePaymentTradeTax.category_code`` |
| `BR-CL-19`  | :class:`UNTDID5189AllowanceReasonCode` | ``TradeAllowanceCharge.reason_code`` when the entry is an allowance (BT-98 / BT-140) |
| `BR-CL-22`  | :class:`VATEXCode`                | ``ApplicableTradeTax.exemption_reason_code`` (BT-121)              |
| `BR-CL-24`  | :class:`MIME`                     | ``AttachmentBinaryObject.mime_code`` (BT-125-1)                    |
| `BR-CL-25`  | :class:`EASCode`                  | ``schemeID`` on Seller / Buyer electronic-address ``URIID`` (BT-34-1 / BT-49-1) |
| `BR-FXEXT-04` | :class:`LineStatusReasonCode`   | ``DocumentLineDocument.status_reason_code`` (BT-X-8; closed 3-member set: DETAIL / GROUP / INFORMATION) |
| —           | :class:`Incoterms`                | ``TradeDeliveryTerms.delivery_type_code`` (BT-X-145)               |

Open `BR-CL-*` slots (closed code list named in the spec but not
yet vendored as a :class:`StrEnum`):

* `BR-CL-07` UNTDID 1153 reference qualifier — 818 members; would
  apply to ``AdditionalReferencedDocument.reference_type_code`` and
  ``LineAdditionalReferencedDocument.reference_type_code``.
* `BR-CL-08` UNTDID 4451 note subject — 402 members; would apply to
  ``IncludedNote.subject_code`` (BT-21).
* `BR-CL-10/11/21` ISO/IEC 6523 scheme ids — 239 members; would
  apply to every ``GlobalID.scheme_id`` and ``ISO6523SchemeId``
  subclass.
* `BR-CL-13` UNTDID 7143 item-classification scheme id — 185
  members; would apply to ``ProductClassification.list_id``
  (BT-158-1).
* `BR-CL-20` UNTDID 7161 charge reason — 178 members; would apply
  to ``TradeAllowanceCharge.reason_code`` when the entry is a
  charge (BT-105 / BT-145).
* `BR-CL-23` UN/ECE Rec. 20 / 21 unit codes — 2162 members; would
  apply to every ``Quantity.unit_code`` (BT-130 / BT-150). Bulk
  alone makes this the most disruptive to add.

## 7. Decimal-precision rules (`BR-DEC-*`)

Every monetary BT in EN 16931 caps at two decimal places. Carthorse
enforces this with a single factory
:func:`carthorse.rules._types.max_decimals` and wires one validator
per (rule, field) pair onto the carrying element's ``_validators``
tuple. All 21 COMFORT `BR-DEC-*` rules are enforced.

| Rule                              | Carrying element                                         | Field |
|-----------------------------------|----------------------------------------------------------|-------|
| `BR-DEC-01` / `BR-DEC-05`         | :class:`HeaderTradeAllowanceCharge` (allowance / charge) | ``actual_amount`` (BT-92 / BT-99) |
| `BR-DEC-02` / `BR-DEC-06`         | :class:`HeaderTradeAllowanceCharge`                      | ``basis_amount`` (BT-93 / BT-100) |
| `BR-DEC-09`                       | :class:`MonetarySummation`                               | ``line_total`` (BT-106) |
| `BR-DEC-10`                       | :class:`MonetarySummation`                               | ``allowance_total`` (BT-107) |
| `BR-DEC-11`                       | :class:`MonetarySummation`                               | ``charge_total`` (BT-108) |
| `BR-DEC-12`                       | :class:`MonetarySummation`                               | ``tax_basis_total`` (BT-109) |
| `BR-DEC-13` / `BR-DEC-15`         | :class:`TaxTotal`                                        | ``amount`` (BT-110 / BT-111) |
| `BR-DEC-14`                       | :class:`MonetarySummation`                               | ``grand_total`` (BT-112) |
| `BR-DEC-16`                       | :class:`MonetarySummation`                               | ``prepaid_total`` (BT-113) |
| `BR-DEC-17`                       | :class:`MonetarySummation`                               | ``rounding_amount`` (BT-114) |
| `BR-DEC-18`                       | :class:`MonetarySummation`                               | ``due_amount`` (BT-115) |
| `BR-DEC-19`                       | :class:`ApplicableTradeTax`                              | ``basis_amount`` (BT-116) |
| `BR-DEC-20`                       | :class:`ApplicableTradeTax`                              | ``calculated_amount`` (BT-117) |
| `BR-DEC-23`                       | :class:`LineMonetarySummation`                           | ``line_total`` (BT-131) |
| `BR-DEC-24` / `BR-DEC-27`         | :class:`LineTradeAllowanceCharge`                        | ``actual_amount`` (BT-136 / BT-141) |
| `BR-DEC-25` / `BR-DEC-28`         | :class:`LineTradeAllowanceCharge`                        | ``basis_amount`` (BT-137 / BT-142) |

## 8. Summary

See the *Per-profile rule enforcement summary* near the top of this
file for the per-profile counts. The remaining gaps are narrow:

* **Reason ↔ reason-code coherence** (`BR-CO-5..8`): only the "or
  both" half is enforced today via `BR-CO-21..24`; checking that the
  free text actually agrees with the coded value needs a codelist
  join carthorse doesn't ship.
* **Per-category sum identities** (`BR-{cat}-8/-9` at COMFORT, full
  per-row identities at EXTENDED): EXTENDED's tolerance-banded
  replacements (`BR-FXEXT-{cat}-08/-09`) are implemented; the strict
  COMFORT versions are not.
* **EXTENDED feature-flag rules** (`BR-FXEXT-01..05`, `-07`, `-10`,
  `BR-FX-DE-04`, `PEPPOL-EN16931-R008`): the input fields exist in
  the model but the checks themselves have no sample-driven need
  yet.

## 9. Wire-conformance entry

The XSD ``<xs:sequence>`` ordering for every CII complexType is a
*design* invariant rather than a runtime business rule, so it doesn't
get a ``BR-*`` code. It is enforced by structure: each
``@dataclass(kw_only=True, slots=True)`` declares its XML fields in
the same order as the corresponding XSD complexType, and
``Element._children_xml`` iterates that order at render time. The
quality gate is ``tests/test_xsd_validity.py``: every sample under
``tests/samples/*.xml`` is parsed via ``Document.from_xml``,
re-rendered via ``Document.to_xml().render(indent=True)``, and the
rendered XML is validated against the matching profile XSD using
``lxml.etree.XMLSchema``. Any structural drift between the dataclass
declarations and the XSD ``<xs:sequence>`` surfaces immediately as a
failed assertion. See ``docs/STRUCTURES.md §4``.
