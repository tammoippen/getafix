# 1. Reading the ZUGFeRD 2.4 / Factur-X 1.08 documentation kit

The vendored documentation lives under `ZF24_EN/`. It's gitignored —
to fetch it locally:

- got to the [ferd-net page](https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-24-english) and download the zip file. Unzip it into `ZF24_EN/`.

The kit ships eight files: one main spec PDF, five per-profile
"Technical Appendix" PDFs, and two XLSX workbooks. The XSDs the spec
ratifies are vendored separately under `tests/schemas/<profile>/`.

### 1.1 `ZF24_EN/Schema/<profile>/FACTUR-X_<PROFILE>.xsd` — the wire-level truth

The XSDs are the binding contract. They tell you which elements may
appear in which order with which cardinality. There are five of them
(MINIMUM, BASIC_WL, BASIC, EN16931, EXTENDED) plus a `5. CII D22B XSD/`
directory holding the full UN/CEFACT CII D22B XSD set (the unprofiled
superset — informational only).

Each profile XSD imports three sub-schemas:

* `..._ReusableAggregateBusinessInformationEntity_100.xsd` — the
  **BG-** group definitions (`TradePartyType`, `MonetarySummationType`,
  …). This is where you look up what fields a BG carries.
* `..._UnqualifiedDataType_100.xsd` — `IDType`, `AmountType`,
  `DateTimeType`, `TextType`. Tells you that `IDType` carries an
  optional `schemeID` attribute, that `AmountType` carries an optional
  `currencyID`, that `DateTimeType` wraps a single `DateTimeString`
  with a required `format` attribute.
* `..._QualifiedDataType_100.xsd` — code-list-typed values
  (`CountryIDType`, `CurrencyCodeType`, `DocumentCodeType`,
  `FormattedDateTimeType` — note the `qdt:` namespace).

To find out which fields a profile permits on a given BG, open the
profile's `…ReusableAggregate…` XSD and grep for the type name. A few
tricks:

* `<xs:element name="X" type="ram:Y" minOccurs="0" maxOccurs="2"/>` —
  optional, max two occurrences. The `maxOccurs` is what makes
  `BuyerTradeParty.tax_registrations` a list (bug sweep #5).
* `minOccurs` defaults to `1`, `maxOccurs` defaults to `1`. Required
  unless explicitly stated otherwise.
* The XSD complex types are *shared* across roles — `TradePartyType` is
  used for Seller, Buyer, Payee, Tax-rep and Ship-to alike. If you want
  to know which fields a *specific* role uses you need the appendix
  PDF (next section), not the XSD.

### 1.2 `ZF24_EN/Documentation/<n>_…_profile_<PROFILE>.pdf` — the per-profile narrative

Five appendix PDFs, one per profile. The same template each time:

* **Pages 1–3 ("Structure of CII schema")** — the indented tree view
  of every element in that profile, in XSD order, with `min..max`
  cardinality on the left margin and the `BG/BT-…` id on the right.
  This is the cheat sheet; print it if you're going to spend a day in
  the spec.
* **Mid-document ("Detailed documentation")** — every element in turn,
  with its data type, occurrence, EN 16931-ID, "Use" sentence, the
  "Used in:" matrix (which profiles include the field), and the
  business rules that touch it.
* **Last 20–60 pages ("List of Business Rules")** — every BR-* the
  profile inherits, full text. Same numbering across profiles; the
  text is identical at MINIMUM, BASIC_WL, BASIC and COMFORT, with
  `BR-FXEXT-*` overlays appearing only in the EXTENDED PDF.

To answer a specific question:

| Question | Where to look |
|---|---|
| Does profile P have BT-X? | The appendix tree on pages 1–3 of the P PDF, or the "Used in:" matrix on the BT-X section in any profile PDF. |
| What's the meaning of BT-X? | The "Use" sentence in the "Detailed documentation" section, any profile PDF. The narrative is identical across profiles. |
| What rules apply to BT-X? | The "Business rule:" list under the BT-X section. The full rule text is in the rule list at the back. |
| What does rule BR-Y mean? | The "List of Business Rules" appendix at the back of any profile PDF. |
| Is BT-X required at profile P? | Two things to check: (1) the cardinality (`1..1` vs `0..1`) at the top of the BT-X "Detailed documentation" section, plus any "Diverging cardinality" override per profile; (2) the "Used in:" matrix — an `X` means the field exists at that profile, blank means it doesn't. |
| Why does rule BR-X-2 exist? | The introduction in the appendix's "Geschäftsregeln" / "Business Rules" section explains the per-VAT-category rule families and how they map to UNTDID 5305 codes. |

### 1.3 `ZF24_EN/Documentation/0_FACTUR-X_1.08_…_EN.pdf` — the main spec

152 pages. Useful sections only:

* **Cover + table of contents** — orientation.
* **Chapter on profiles** (~p20) — overview of the five profiles, the
  CIUS layering rationale, the relationship to UN/CEFACT CII D22B.
* **Chapter on the EXTENDED profile** (~p40) — the `BR-FXEXT-*` overlay,
  the `BT-X-*` extension fields, the sub-line-item / IncludedReferencedProduct
  feature.
* **Change log** (~p244–326) — what changed from Factur-X 1.07 / ZUGFeRD
  2.3 (rule replacements at EXTENDED, dropped rules, etc.). The most
  important page if you're trying to understand *why* the EXTENDED
  rules look different.
* **List of business rules** (last ~30 pages) — the canonical rule list.
  Contains rules that don't appear in any per-profile appendix
  (`BR-FX-DE-*`, `BR-FX-EN-*`, `BR-HYBRID-*` etc.).

### 1.4 `ZF24_EN/Documentation/1_FACTUR-X 1.08 - … - VF.xlsx` — field cross-reference

A spreadsheet with one row per BT/BG and columns for each profile (X /
blank), the data type, the cardinality, the rule references. If you
need to mass-query "which BTs are introduced at profile P" or "what's
the data type of every BT in BG-23", this is faster than the PDFs.

Open in any spreadsheet app. Filter the profile column to find what's
new at a level; sort by BG/BT id to find a specific field.

### 1.5 `ZF24_EN/Documentation/2_EN16931 code lists values v16 - …xlsx` — code lists

The enumeration values for code-typed fields (UNTDID 1001 document
type, UNTDID 5305 VAT category, UNTDID 4461 payment means, ISO 3166-1
country, ISO 4217 currency, etc.). Useful when you need to confirm
that a code value is a legitimate enum entry rather than a free-form
string.

### 1.6 `ZF24_EN/Examples/…` — reference XML invoices

20+ real Factur-X 1.08 invoice XMLs (BASIC, BASIC WL, MINIMUM,
EN16931, EXTENDED) as PDFs and as raw XML. Use them as conformance
oracles: feed an XML through `Document.from_xml()` and round-trip it
to see whether getafix's parser preserves the meaningful content.

`tests/samples/` already vendors a smaller selection of these for the
test suite; the full set on `origin/docs` is broader (line items,
allowance/charge, sub-invoice lines, foreign currency, etc.) and worth
checking against ad-hoc when you suspect a parser bug.

## 2. How profile applicability works in the spec

Every BT / BG has a **"Used in:"** matrix on its detailed-documentation
page that looks like:

```
                   MINIMUM BASIC WL BASIC EN 16931 (COMFORT) EXTENDED
       Used in:       X        X      X         X                 X
```

An `X` means "this field is part of the profile". Blank means "not
part of the profile". The matrix is the authoritative source — the
XSDs sometimes permit fields the narrative restricts (the
`TradePartyType` complex type is shared across all five profiles, but
the appendix narrative for MINIMUM lists fewer fields than the
EXTENDED narrative — see `BuyerTradeParty.tax_registrations`).

When the cardinality changes between profiles, the appendix shows it
explicitly:

```
       Diverging                                                1..1
     cardinality:
```

That tells you: at the profile under that column the cardinality is
overridden (e.g. `BusinessProcessSpecifiedDocumentContextParameter`
becomes mandatory at EXTENDED).

In getafix this is encoded two ways:

1. The **class-level `profile: ClassVar[Profile]`** on each `Element`
   subclass — the lowest profile at which the *element* may appear.
2. The **field-level `metadata={"profile": Profile.X}`** on each
   `field()` — the lowest profile at which the *individual field* may
   appear inside that element.

`Element._children_xml` reads both and raises `ProfileMismatch` if a
field set on the dataclass requires a profile higher than the
document's. So if you see a model gate that doesn't match the spec
narrative, fix it via one of those two markers.

## 3. Cheat sheet: where to find what

| Need | File | How |
|---|---|---|
| Find BT-X's data type | profile XSD `…ReusableAggregate…` | Search for `name="X-name"` |
| Check BT-X's cardinality at profile P | `ZF24_EN/Documentation/<P>.pdf` p1-3 (tree) or detailed section | Tree shows `min..max`; per-element matrix shows profile applicability |
| Read rule BR-Y's full text | `ZF24_EN/Documentation/<any>.pdf` "List of Business Rules" appendix | Rule numbering is shared across profile PDFs |
| Find which getafix class models BG-X | `docs/STRUCTURES.md` § Field reference | Tables list every modelled field with its BT/BG id |
| Check whether BR-Y is enforced | `docs/VALIDATION.md` rule tables | Status column tells you ✓ enforced / — not yet / ⚠ buggy |
| See which EXTENDED fields are still missing | `docs/STRUCTURES.md §5` | EXTENDED coverage diff |
| Understand what changed in Factur-X 1.08 vs 1.07 | `ZF24_EN/Documentation/0_FACTUR-X_1.08_…_EN.pdf` change log (~p244) | Rule replacements at EXTENDED, etc. |
| Find a sample invoice for profile P | `ZF24_EN/Examples/<n>. <P>/…_<sample>.xml` | Several per profile; PDFs alongside |
