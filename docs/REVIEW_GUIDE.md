# Reviewing this PR

This branch is large — three weeks of cumulative work spanning a parser bug
sweep, BG-25 line-item modelling, ten or so cross-field validators, a full
property-based test suite driven off the official Factur-X 1.08 XSDs, and
three reference documents. This guide is for whoever has to review it: where
to start, what to load into your head before you open `git diff`, and how to
read the source-of-truth (the ZUGFeRD 2.4 / Factur-X 1.08 documentation kit
under `ZF24_EN/`) so you can spot-check what the code claims.

## 1. What's in the PR, and the order to read it

You have ~30 commits. Read them in the same chronological order they were
written — every commit message states *why* and most include before/after
test counts. Don't try to parse the squashed diff cold; it's hard.

### 1.1 The five reference documents to load first

Before reading any code, open these in order. They explain the constraints
the code is meant to satisfy and use the same vocabulary:

1. **`docs/STRUCTURES.md`** — module map, every dataclass field with its
   `BT-…` / `BG-…` id, profile-applicability matrix, and the wire
   conventions (where `udt:` vs `qdt:` namespace shows up, how
   `currencyID` round-trips, what `format="102"` means on dates).
2. **`docs/VALIDATION.md`** — the full BR-* catalogue with implementation
   status (✓ enforced / ◯ implicit / △ partial / ⚠ buggy / — not enforced).
   Five recurring cross-field patterns are summarised at the bottom.
3. **`docs/IMPLEMENTATION_PLAN.md`** — the gap list and the order the work
   was tackled. The "bug sweep §1" table at the top is a compact change-log
   of the nine wire-format / model bugs that opened the PR.
4. **`README.md`** — quick-start, sample fixtures, known gaps. Light read.
5. **`tests/strategies.py` docstring** — explains the property-based
   test setup at the top of the file. Worth skimming before you dive
   into the tests.

### 1.2 Walk the commits in this order

The PR's git history is the best diff. From `git log --oneline` on the
branch:

```
docs branch merge & ZF24_EN docs in tests/schemas/   ← scaffolding
Hypothesis strategies (XSD-driven)                   ← test infrastructure
Bug sweep #1..9 (eight commits)                       ← parser correctness
docs/STRUCTURES.md, VALIDATION.md, IMPLEMENTATION_PLAN ← reference docs
BASIC_WL gap-fill (BT-6, BG-14, …)                   ← structural additions
BG-25 line items (schema/line.py)                    ← biggest structural change
BR-CO-9 / BR-CO-25 / BR-CO-26                        ← single-class validators
BR-AE → BR-O families (8 cycles)                     ← cross-field VAT matrix
BR-CO-3 / BR-CO-10..17                               ← arithmetic identities
BR-CO-23 / BR-CO-24                                  ← line-level reason coupling
```

Each block hangs together. Reviewing one block at a time is the only
sustainable way through this PR.

## 2. What to look at carefully

The diff is large but the commits split cleanly. By layer:

### 2.1 The wire-format bugs (commits in the "bug sweep")

These are isolated, mechanical fixes — a renamed XML attribute, a
copy-paste tag, a single → list cardinality. Each has a regression test
in `tests/test_document.py` or `tests/test_types.py` named after the rule
or bug it pins. Spot check: each commit message lists the bug-sweep
number; cross-reference against `docs/IMPLEMENTATION_PLAN.md §1` which
tracks status per item.

The one non-mechanical bug is **#7** (currencyID round-trip): it adds a
private `Element._xml_attrs` dict and threads it through render/parse so
unmodelled attributes survive a round-trip. Read
`src/carthorse/schema/element.py` end-to-end for this one — it's the
only commit that changes the base class shape.

### 2.2 The structural additions

* **`src/carthorse/schema/line.py` (new module)** — BG-25 line items.
  Read end-to-end. Every dataclass cites its EN 16931 id in the
  docstring and the field order matches the XSD `<xs:sequence>`. The
  BASIC profile's BG-25 sub-tree from `docs/IMPLEMENTATION_PLAN.md
  §2.BASIC` is the spec source.
* **`src/carthorse/schema/settlement.py`** — adds `BillingSpecifiedPeriod`
  (BG-14 / BG-26), `tax_currency_code` (BT-6), `description` on
  `PaymentTerms` (BT-20). Plus several validators: BR-CO-15, BR-CO-16,
  BR-CO-14, BR-CO-25, BR-53.
* **`src/carthorse/schema/trade.py`** — `Trade._validate_document_arithmetic`
  is the new home for the cross-line / cross-allowance arithmetic (BR-CO-10
  through BR-CO-13 plus the BR-CO-21..24 reason-coupling). The data-driven
  family table for the per-VAT-category required-party rules is here too:
  search for `families: list[tuple[…]]`.

### 2.3 The validators

Two patterns:

* **Local rules** live in the relevant class's `validate_internal`.
  Examples: `TaxSchemeId.validate_internal` (BR-CO-9 country prefix),
  `BillingSpecifiedPeriod.validate_internal` (BR-29 / BR-CO-19),
  `ApplicableTradeTax.validate_internal` (BR-CO-3 / BR-CO-17).
* **Cross-cutting rules** live in `Trade.validate_internal` because they
  need access to several siblings. The file documents which method
  holds which rule via inline comments (search for `BR-`).

If a rule fires the *wrong* code in a corner case, the test in
`tests/test_vat_categories.py` will tell you exactly which one. The
helper `_make_doc()` in that file is parameterised so each test
twists *one* knob and asserts *one* code.

### 2.4 The tests

* **`tests/test_document.py`** — fixture-driven round-trip tests +
  per-rule unit tests. The two big fixtures (`minimum_doc`, `full_doc`)
  exercise the entire serialiser / parser surface; the per-rule tests
  are appended at the bottom of the file. The expected-XML strings in
  the fixture tests are verbose but they catch element-ordering bugs
  the round-trip equality wouldn't.
* **`tests/test_vat_categories.py`** — every cross-field validator with
  a deliberately-broken setup followed by the matching fix. Read
  `_make_doc()` first — it's the foundation for every test in the file.
* **`tests/test_hypothesis.py`** — three properties per profile:
  *(a)* the strategy's output validates against the official XSD,
  *(b)* `Document.from_xml(generated)` followed by `Document.to_xml()`
  doesn't crash, and *(c)* the rendered bytes start with `<?xml`. The
  XSD-validity test is the most useful: if (a) regresses, the strategy
  doesn't match the spec any more.
* **`tests/test_samples.py`** — round-trip the real Factur-X 1.08
  reference XML files vendored under `tests/samples/`. Started as
  10 xfails, now 9 xpass / 1 xfail (a date format edge case).

### 2.5 What to spot-check by hand

Run these locally:

```bash
make tests        # 116 passed, 1 xfailed, 14 xpassed (all green)
make check        # ruff + pyright; 0 errors, ~64 warnings (mostly typing noise)
```

Then manually:

```bash
# Try the README quickstart end-to-end:
uv run python -c "$(sed -n '/^```python/,/^```$/p' README.md \
                    | sed '/^```/d' | head -60)"

# Validate a sample real invoice:
uv run python -c "
import lxml.etree as etree
from carthorse.schema import Document
doc = Document.from_xml(etree.parse('tests/samples/EN16931_Einfach.cii.xml').getroot())
doc.validate()  # may raise ValidationError if a BR-* fires
print('parsed:', type(doc).__name__)
"
```

If `validate()` raises a `BR-…` error on a sample real invoice, that's
either a genuine spec violation in the sample (some FeRD samples don't
satisfy BR-CO-9 for instance — they predate that rule) or a false-positive
in a validator. `docs/VALIDATION.md` records which rules are currently
enforced.

### 2.6 What I deliberately didn't do

Listed in the implementation plan but not addressed in this PR:

* `BR-*-8 / -9 / -10` per-VAT-category sum identities.
* `BR-FXEXT-*` EXTENDED CIUS overlay.
* PDF/A-3 packaging.
* EN 16931 enrichments to BG-25 (BG-32 product characteristics, BG-33
  classification, BG-34 origin country, line-level
  `BuyerOrderReferencedDocument` / `AdditionalReferencedDocument`).

## 3. Reading the ZUGFeRD 2.4 / Factur-X 1.08 documentation kit

The vendored documentation lives under `ZF24_EN/`. It's gitignored —
to fetch it locally:

```bash
git fetch origin docs
git checkout origin/docs -- ZF24_EN
```

The kit ships eight files: one main spec PDF, five per-profile
"Technical Appendix" PDFs, and two XLSX workbooks. The XSDs the spec
ratifies are vendored separately under `tests/schemas/<profile>/`.

### 3.1 `ZF24_EN/Schema/<profile>/FACTUR-X_<PROFILE>.xsd` — the wire-level truth

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

### 3.2 `ZF24_EN/Documentation/<n>_…_profile_<PROFILE>.pdf` — the per-profile narrative

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

### 3.3 `ZF24_EN/Documentation/0_FACTUR-X_1.08_…_EN.pdf` — the main spec

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
  (`BR-DE-*`, etc.).

### 3.4 `ZF24_EN/Documentation/1_FACTUR-X 1.08 - … - VF.xlsx` — field cross-reference

A spreadsheet with one row per BT/BG and columns for each profile (X /
blank), the data type, the cardinality, the rule references. If you
need to mass-query "which BTs are introduced at profile P" or "what's
the data type of every BT in BG-23", this is faster than the PDFs.

Open in any spreadsheet app. Filter the profile column to find what's
new at a level; sort by BG/BT id to find a specific field.

### 3.5 `ZF24_EN/Documentation/2_EN16931 code lists values v16 - …xlsx` — code lists

The enumeration values for code-typed fields (UNTDID 1001 document
type, UNTDID 5305 VAT category, UNTDID 4461 payment means, ISO 3166-1
country, ISO 4217 currency, etc.). Useful when you need to confirm
that a code value is a legitimate enum entry rather than a free-form
string.

### 3.6 `ZF24_EN/Examples/…` — reference XML invoices

20+ real Factur-X 1.08 invoice XMLs (BASIC, BASIC WL, MINIMUM,
EN16931, EXTENDED) as PDFs and as raw XML. Use them as conformance
oracles: feed an XML through `Document.from_xml()` and round-trip it
to see whether carthorse's parser preserves the meaningful content.

`tests/samples/` already vendors a smaller selection of these for the
test suite; the full set on `origin/docs` is broader (line items,
allowance/charge, sub-invoice lines, foreign currency, etc.) and worth
checking against ad-hoc when you suspect a parser bug.

## 4. How profile applicability works in the spec

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

In carthorse this is encoded two ways:

1. The **class-level `profile: ClassVar[Profile]`** on each `Element`
   subclass — the lowest profile at which the *element* may appear.
2. The **field-level `metadata={"profile": Profile.X}`** on each
   `field()` — the lowest profile at which the *individual field* may
   appear inside that element.

`Element._children_xml` reads both and raises `ProfileMismatch` if a
field set on the dataclass requires a profile higher than the
document's. So if you see a model gate that doesn't match the spec
narrative, fix it via one of those two markers.

## 5. Cheat sheet: where to find what

| Need | File | How |
|---|---|---|
| Find BT-X's data type | profile XSD `…ReusableAggregate…` | Search for `name="X-name"` |
| Check BT-X's cardinality at profile P | `ZF24_EN/Documentation/<P>.pdf` p1-3 (tree) or detailed section | Tree shows `min..max`; per-element matrix shows profile applicability |
| Read rule BR-Y's full text | `ZF24_EN/Documentation/<any>.pdf` "List of Business Rules" appendix | Rule numbering is shared across profile PDFs |
| Find which carthorse class models BG-X | `docs/STRUCTURES.md` § Field reference | Tables list every modelled field with its BT/BG id |
| Check whether BR-Y is enforced | `docs/VALIDATION.md` rule tables | Status column tells you ✓ enforced / — not yet / ⚠ buggy |
| See the implementation plan for missing fields | `docs/IMPLEMENTATION_PLAN.md` | Per-profile tables and ordered roadmap |
| Understand what changed in Factur-X 1.08 vs 1.07 | `ZF24_EN/Documentation/0_FACTUR-X_1.08_…_EN.pdf` change log (~p244) | Rule replacements at EXTENDED, etc. |
| Find a sample invoice for profile P | `ZF24_EN/Examples/<n>. <P>/…_<sample>.xml` | Several per profile; PDFs alongside |

## 6. Minimum-effort pass

If you only have an hour:

1. Read `docs/IMPLEMENTATION_PLAN.md §1` (bug sweep). 5 minutes.
2. Read `docs/VALIDATION.md` rule tables. 15 minutes.
3. Run `make check && make tests`. 1 minute (auto).
4. Skim `git log --oneline` and read the commit messages. 10 minutes.
5. Open `src/carthorse/schema/trade.py`, read
   `Trade.validate_internal` and `_validate_document_arithmetic` and
   `_validate_vat_category_required_parties`. 20 minutes — this is
   where most of the new validation work landed.
6. Open `src/carthorse/schema/line.py`. 5 minutes — it's well-documented
   and BG-25 is the only place where a new module appeared.

## 7. Questions worth asking

* Are the BR-*-error message strings reasonable? They mix English and
  German because the appendix narrative is German. If your project
  prefers single-language errors, that's a small follow-up.
* Should `Trade.validate_internal` raise on the *first* failure or
  collect them all? Today it short-circuits on the first one. The spec
  treats each rule as independent, so a one-shot validator that returns
  *every* failing BR-* may be more useful for downstream consumers.
* Are profile gates *too* permissive in places? The strategy → carthorse
  parse-then-render fix was to loosen several `profile=EXTENDED` gates
  to `BASIC_WL` because the XSD permitted those fields earlier. The
  appendix narrative is sometimes stricter; if you want spec-narrative
  compliance instead of XSD-permissiveness, several gates need to flip
  back.
* `Element._xml_attrs` — opinions on hidden state for round-trip
  fidelity? It works, it's invisible to the public API, but it does
  add a slot to every dataclass instance.
* Test fixtures in `tests/test_document.py` carry a lot of expected XML
  inline. They catch element-ordering bugs but they're also fragile.
  If you'd prefer parametric round-trip tests over byte-level diffs,
  that's a reasonable refactor.
