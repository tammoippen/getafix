# AGENTS.md

Internal notes for contributors and coding agents working on
**getafix**. End-user material lives in `README.md`; everything below
assumes you have a checkout and want to extend the model, fix a bug,
or add a business-rule validator.

## Repository layout

```
src/getafix/
├── __init__.py
├── cli.py                 # console script entry point
├── pdf.py                 # PDF/A-3 attachment helpers (pypdf)
├── report/                # rich console pretty-printer (one module per schema topic)
│   ├── __init__.py        # render_invoice orchestrator + public re-exports
│   ├── _types.py          # SectionRenderer alias + described_panel / describe_table
│   ├── element.py         # render_validation_errors
│   ├── types.py           # code formatters (format_type_code, format_vat)
│   ├── document.py        # Invoice overview panel
│   ├── party.py           # Seller / Buyer panels, address, tax ids
│   ├── agreement.py       # order / contract / project rows
│   ├── delivery.py        # Delivery panel
│   ├── accounting.py      # VAT breakdown, allowances/charges, totals
│   ├── settlement.py      # payment, prepayments, period rows
│   ├── line.py            # item cell + line VAT cell
│   ├── trade.py           # line-items table
│   └── references.py      # format_reference
├── schema/                # the CII data model (dataclasses)
│   ├── element.py         # Element base, ProfileMismatch, ValidationError(s)
│   ├── types.py           # enums: Profile, Namespace, TypeCode, …
│   ├── document.py        # Document / Context / Header  (BG-0 / BG-2 / BT-1-00)
│   ├── trade.py           # Trade (BG-25-00), TradeLineItem (BG-25)
│   ├── agreement.py       # TradeAgreement (BT-10-00)
│   ├── delivery.py        # TradeDelivery (BG-13-00)
│   ├── settlement.py      # TradeSettlement (BG-19) + payment means / terms
│   ├── accounting.py      # MonetarySummation, ApplicableTradeTax, TradeAllowanceCharge
│   ├── party.py           # SellerTradeParty, BuyerTradeParty, …
│   ├── references.py      # *ReferencedDocument, AttachmentBinaryObject
│   ├── line.py            # BG-25 line sub-tree (TradeProduct, LineTradeAgreement, …)
│   └── _numeric.py        # half-away-from-zero rounding helper
└── rules/                 # validator functions (one per BR-*)
    ├── _types.py          # Validator type alias + max_decimals factory
    ├── accounting.py
    ├── line.py
    ├── party.py
    ├── settlement.py
    ├── trade.py           # cross-sibling rules (per-VAT-category families, arithmetic)
    └── extended.py        # BR-FXEXT-* CIUS overlay

docs/
├── STRUCTURES.md          # module → BG/BT field map, profile applicability, EXTENDED gap diff
├── VALIDATION.md          # every BR-*/BR-CO-*/BR-X-* rule + status, BR-CL-* / BR-DEC-* wirings
└── READING_OFFICIAL_DOCS.md  # where to find what in the ZF24_EN kit

ZF24_EN/                   # vendored spec (gitignored); see docs/READING_OFFICIAL_DOCS.md
tests/                     # pytest suite, sample corpus, hypothesis strategies
tools/                     # one-shot scripts (codelist regen, sample fetch,
                           #   render_report.py: XML → PNG/SVG of the report)
```

## How the model is structured

Every schema class inherits from `getafix.schema.element.Element`, a
`@dataclass(kw_only=True, slots=True)` mixin that knows three things:

- **`tag` / `namespace`** (`ClassVar`) — the qualified XML tag the
  element emits (`ram:`, `rsm:`, `udt:`, `qdt:`). The default namespace
  is `Namespace.ram`; override on subclasses that emit `rsm:`.
- **`profile`** (`ClassVar[Profile]`) — the lowest Factur-X profile at
  which the *element* may appear. Rendering at a lower profile raises
  `ProfileMismatch`.
- A pair of methods, `to_xml_internal(profile)` and `from_xml(elem)`,
  that walk the dataclass fields. Each field's `metadata` dict carries
  `tag`, optional `ns`, optional `profile`, and the `"amount": True`
  flag that triggers `currencyID` stamping.

### Field metadata keys

| Key        | Type                       | Used by              | Notes |
|------------|----------------------------|----------------------|-------|
| `tag`      | `str`                      | leaf renderers       | XML element name for `str`/`Decimal`/`bool`/`date` fields. Not needed on `Element`-typed fields (the child uses its class `tag`). |
| `ns`       | `Namespace`                | leaf renderers       | Override the default `ram:` namespace on this field. |
| `profile`  | `Profile`                  | `Element._children_xml` | Field-level minimum profile gate. |
| `amount`   | `bool`                     | `Element._children_xml` | When `True`, the sibling `currency: str \| None` field stamps `currencyID` onto this element. |

### Profile gating, two layers

The Factur-X "Used in:" matrix is encoded in two places:

1. **Class-level `profile: ClassVar[Profile]`** on each `Element`
   subclass — the lowest profile at which the *element* may appear.
2. **Field-level `metadata={"profile": Profile.X}`** on each `field()`
   — the lowest profile at which the *individual field* may appear
   inside that element.

`Element._children_xml` reads both and raises `ProfileMismatch` if a
field that is set on the dataclass requires a profile higher than the
document's.

`Element._field_profile(name)` is the override hook for fields whose
gate depends on instance state — see
`TradeAllowanceCharge._field_profile`, which gates `calculation_percent`
and `basis_amount` differently for header vs line.

### Currency on amounts

Every amount-bearing dataclass (`MonetarySummation`, `TaxTotal`,
`ApplicableTradeTax`, `TradeAllowanceCharge`, `GrossTradePrice`,
`NetTradePrice`, `AppliedTradeAllowanceCharge`, `LineMonetarySummation`,
`LogisticsServiceCharge`, `AdvancePayment`, `AdvancePaymentTradeTax`,
`PaymentPenaltyTerms`, `PaymentDiscountTerms`) carries a sibling
`currency: str | None` field. On render, `_children_xml` stamps it onto
every `"amount": True` field's `currencyID` attribute; on parse,
`from_xml` captures the first `currencyID` it sees back into
`currency`. The field is excluded from XML iteration and validation
walks.

### Profile enum ordering

`Profile` is a `StrEnum` whose member order encodes ordinal rank
(`MINIMUM < BASIC_WL < BASIC < COMFORT < EXTENDED`). All four order
comparators (`__lt__` / `__le__` / `__gt__` / `__ge__`) are overridden
to use that ordinal — the inherited `StrEnum` lexicographic compare
would give wrong answers (`BASIC_WL <= MINIMUM` would be `True`).

## Validator architecture

Each business rule is a free-standing function with signature
`Validator[T] = Callable[[T, Profile], list[ValidationError]]`. The
function:

- self-gates on profile and on the precondition data;
- returns `list[ValidationError]` (empty on success);
- never raises.

Element classes wire validators in via a `ClassVar` tuple:

```python
@dataclass(kw_only=True, slots=True)
class TradeSettlement(Element):
    _validators: ClassVar[tuple[Validator["TradeSettlement"], ...]] = (
        br_5_currency_shape,
        br_co_18,
        br_53,
        br_co_25,
        br_co_14,
        br_co_15,
        br_co_16,
    )
```

`Element.validate_internal(profile)` runs every registered validator on
`self`, then recurses into every child `Element` reachable through
dataclass fields, returning the merged error list. The public entry
point is `Document.validate()`, which collects every violation in one
pass and raises a single `ValidationErrors` aggregate.

Validator modules live in `getafix.rules.<topic>` mirroring the
schema modules they validate against. Cross-sibling rules (per-VAT-
category required parties, document arithmetic, sub-line walker) live
in `getafix.rules.trade` and `getafix.rules.extended` because they
need to read across the agreement / settlement / line items in one
pass.

### Import cycle

Each `schema/<topic>.py` runtime-imports the validator functions from
`getafix.rules.<topic>` to wire them onto `_validators`; each
`rules/<topic>.py` imports element types from `schema.<topic>` for the
function annotations only. The runtime graph has no cycle —
annotations are kept inert with `from __future__ import annotations`
and the schema imports sit under a `TYPE_CHECKING` guard. Pyright
still walks the static cycle and reports it, so every rule module
opens with `# pyright: reportImportCycles=false`. Use the same
pattern when adding a new `rules/<topic>.py`.

### Per-VAT-category families

The eight VAT categories that demand a required-party check
(`AE` / `E` / `G` / `IC` / `IG` / `IP` / `S` / `Z`) plus the inverted
`O` family expand into one `br_<cat>_<n>` function per BR id —
31 functions total in `rules/trade.py`. Shared helpers
(`_seller_predicate_*`, `_has_vat_id`, `_iter_tax_registrations`,
`_line_has_category`, `_alw_has_category`, `_chg_has_category`) sit
next to the validators. The rate (`-5/-6/-7`) and exemption-reason
(`-10`) constraints across the same nine categories collapse into
two table-driven dispatchers
(:func:`getafix.rules.trade.vat_category_rates` and
:func:`getafix.rules.trade.vat_category_exemption_reason`).

### EXTENDED short-circuits

EXTENDED replaces seven EN 16931 arithmetic identities
(`BR-CO-4 / -10 / -11 / -12 / -13 / -15` plus `BR-CO-17`) with
tolerance-banded variants in `rules/extended.py`. The replaced rule
in `rules/<topic>.py` short-circuits with
`if profile >= Profile.EXTENDED: return []`; the EXTENDED variant
guards with the inverse. Both end up on the same element's
`_validators` tuple; profile gating in each function picks the
right one to fire.

For the full BR-* catalogue with implementation status see
`docs/VALIDATION.md`.

## Report architecture

`getafix.report` mirrors the schema the same way `getafix.rules` does:
one `report/<topic>.py` per `schema/<topic>.py`, each holding the
free-standing functions that render the elements defined there. A
section renderer reads its element and returns a Rich renderable (or
`None` to skip an empty section); `render_invoice` in `report/__init__.py`
composes them top-to-bottom. Shared framing (`described_panel`,
`describe_table`, the `SectionRenderer` alias) lives in
`report/_types.py`; code→string formatters in `report/types.py`. Every
section carries a short dim description of what it means, and rows are
labelled with their BT/BG id.

## Adding a new BT / BG field

1. Find the spec entry — `docs/READING_OFFICIAL_DOCS.md` is the
   cheat sheet for navigating `ZF24_EN/`.
2. Locate the right dataclass under `src/getafix/schema/`.
3. Add the `field()` declaration, in XSD `<xs:sequence>` order:
   ```python
   new_field: str | None = field(
       default=None, metadata={"tag": "NewField", "profile": Profile.BASIC_WL}
   )
   """Docstring with the BT id and a short narrative."""
   ```
4. If the field is monetary, add `"amount": True` to the metadata and
   make sure the enclosing dataclass has a `currency: str | None` field.
5. Run `make tests`. `tests/test_xsd_validity.py` will catch ordering
   regressions automatically by re-rendering every shipped sample and
   validating against the profile XSD.

## Adding a new BR-* validator

1. Add the function to the right `rules/<topic>.py` (or `rules/trade.py`
   if it needs cross-sibling access). Match the `Validator[T]` shape:
   ```python
   def br_42(m: _line.TradeAllowanceCharge, profile: Profile) -> list[ValidationError]:
       """BR-42: …spec text…"""
       if profile < Profile.BASIC:
           return []
       if <ok>:
           return []
       return [ValidationError("BR-42", "…message…")]
   ```
2. Wire it into the target element's `_validators` ClassVar tuple.
3. Add a row to `docs/VALIDATION.md` with status `✓` and the rule's
   enforcement location.
4. Add at least one positive (rule fires) and one negative (rule
   passes) test under `tests/`.

## Wire conventions

These hold across every dataclass; new code MUST preserve them.

- **Field order matches the XSD `<xs:sequence>`.** `_children_xml`
  iterates `dataclasses.fields()` in declaration order. The EN16931
  (COMFORT) XSD is the master reference; lower profiles drop fields
  but never reorder. `tests/test_xsd_validity.py` enforces this by
  re-rendering every sample.
- **`udt:DateTimeType` carries `format="102"`** (CCYYMMDD). The
  parser rejects any other format. The single exception is
  `qdt:FormattedDateTimeType` (for `FormattedIssueDateTime` and
  `FormattedReceivedDateTime`), which uses the `qdt:` namespace but
  the same `format="102"` payload.
- **`udt:AmountType` carries an optional `currencyID` attribute** —
  see the "Currency on amounts" section above.
- **`udt:IndicatorType`** wraps `<udt:Indicator>true|false</udt:Indicator>`.
- **Empty / self-closing string elements** (e.g. `<ram:LineTwo/>`,
  `<ram:BICID/>`) parse as `None` for the corresponding optional
  field. PEPPOL-EN16931-R008 warns against empty elements, but
  real-world ZUGFeRD samples ship them anyway, so the parser is
  lenient. On render the field is simply omitted.

## Development workflow

```bash
uv sync                 # create .venv and install dev deps

make tests              # pytest + 90 % coverage gate
make check              # ruff format check + ruff lint + basedpyright
make fmt                # auto-format + auto-fix lint

make synth-check        # rebuild EXTENDED samples and diff against committed copies
make ids-check          # regenerate BT/BR sidecars + run BT/BR + schema-docs audits
make docs-coverage      # same as ids-check but also prints "XSD child not modelled" notes
```

CI runs `make check` then `make synth-check`, `make ids-check`, then
`make tests` on Linux / macOS / Windows (`.github/workflows/CI.yml`).
Tagging `v*` triggers `Publish.yml` to push to PyPI.

### Spec-conformance tooling

The `tools/` directory carries four scripts that together keep the
schema docstrings in sync with the Factur-X 1.08 workbook
(`docs/spec/1_FACTUR-X 1.08 - … - VF.xlsx`):

| Tool | Purpose |
|------|---------|
| `extract_business_terms.py` | Reads every per-profile sheet and emits two sidecars — flat `tools/business_terms.json` (keyed by BT/BG id) and `tools/business_terms_tree.json` (xpath-segment tree). Sidecars are gitignored; regenerated on every `make ids-check`. |
| `extract_business_rules.py` | Emits `tools/business_rules.json` covering BR-* / BR-CO-* / BR-CL-* / BR-DEC-* / BR-FXEXT-* / BR-HYBRID-* / per-VAT-category families. |
| `check_schema_docs.py` | Statically walks every `Element` subclass (via `griffe`) and fails if a class or field is missing a docstring or BT/BG citation, or if its `profile` gate would render the term below the earliest profile the workbook admits it on (XSD-vs-EN-semantic divergences are allow-listed in `KNOWN_PROFILE_EXCEPTIONS`). With `--check-citations` (used by `make ids-check`) it additionally cross-checks every `BT-` / `BG-` / `BR-` citation in `src/`, `docs/`, `README.md` and `AGENTS.md` against the sidecars, failing on a typo or hallucinated id. With `--show-missing` also lists every XSD-allowed child not yet modelled (informational; surfaced through `make docs-coverage`). |

The audit runs as part of `make ids-check` and CI.

The test suite includes:

- `tests/test_*.py` — unit tests for each schema module and rule
  family.
- `tests/test_samples.py` — parser checks against real-world samples
  in `tests/samples/`; provenance + license (Apache 2.0) in
  `tests/samples/SOURCES.md`.
- `tests/test_zf24_examples.py` — parser checks against the official
  Factur-X 1.08 examples shipped under `ZF24_EN/Examples/` (skipped
  when the kit is not present).
- `tests/test_xsd_validity.py` — re-renders every sample and validates
  the output against the profile XSD. Guards the field-ordering
  invariant.
- `tests/test_hypothesis.py` — round-trips Hypothesis-generated
  documents. Failing examples surface modelling gaps that the static
  samples miss.

## Out of scope (today)

- **PDF/A-3 conformance.** `getafix.pdf` attaches XML to an existing
  PDF using pypdf, but does not upgrade the host PDF to PDF/A-3 — the
  formal compliance requirement for Factur-X. Pair with a dedicated
  converter when full conformance is needed.
- **Schematron `.sch` rules.** The per-profile schematron files are
  not vendored. If we want automated BR-* enforcement against the
  official rules, those are the source of truth — today the BR-*
  checks are hand-coded.
- **EXTENDED CIUS full coverage.** Every top-level EXTENDED
  structure is modelled; the residual leaf attributes and line-level
  twins of header references are enumerated in
  `docs/STRUCTURES.md §5` and added on demand.

## See also

- `docs/READING_OFFICIAL_DOCS.md` — how to navigate the vendored
  Factur-X 1.08 / ZUGFeRD 2.4 documentation kit.
- `docs/STRUCTURES.md` — module → BG/BT field map with profile
  applicability, wire conventions and the EXTENDED gap diff.
- `docs/VALIDATION.md` — every business rule, with enforcement status
  and the function that implements it; also the `BR-CL-*` codelist
  enum registry and the `BR-DEC-*` decimal-precision wirings.
