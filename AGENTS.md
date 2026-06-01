# AGENTS.md

Internal notes for contributors and coding agents working on
**carthorse**. End-user material lives in `README.md`; everything below
assumes you have a checkout and want to extend the model, fix a bug,
or add a business-rule validator.

## Repository layout

```
src/carthorse/
├── __init__.py
├── cli.py                 # console script entry point
├── pdf.py                 # PDF/A-3 attachment helpers (pypdf)
├── report.py              # rich console pretty-printer
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
├── STRUCTURES.md          # module → BG/BT field map, profile applicability
├── VALIDATION.md          # every BR-*/BR-CO-*/BR-X-* rule + status
├── IMPLEMENTATION_PLAN.md # gap list and ordered roadmap
├── READING_OFFICIAL_DOCS.md  # where to find what in the ZF24_EN kit
└── PROFILES/              # per-profile parity checklists (COMFORT, EXTENDED)

ZF24_EN/                   # vendored spec (gitignored); see docs/READING_OFFICIAL_DOCS.md
tests/                     # pytest suite, sample corpus, hypothesis strategies
tools/                     # one-shot scripts (codelist regen, sample fetch)
```

## How the model is structured

Every schema class inherits from `carthorse.schema.element.Element`, a
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

Validator modules live in `carthorse.rules.<topic>` mirroring the
schema modules they validate against. Cross-sibling rules (per-VAT-
category required parties, document arithmetic, sub-line walker) live
in `carthorse.rules.trade` and `carthorse.rules.extended` because they
need to read across the agreement / settlement / line items in one
pass.

For the full BR-* catalogue with implementation status see
`docs/VALIDATION.md`.

## Adding a new BT / BG field

1. Find the spec entry — `docs/READING_OFFICIAL_DOCS.md` is the
   cheat sheet for navigating `ZF24_EN/`.
2. Locate the right dataclass under `src/carthorse/schema/`.
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
```

CI runs `make check` then `make tests` on Linux / macOS / Windows
(`.github/workflows/CI.yml`). Tagging `v*` triggers `Publish.yml` to
push to PyPI.

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

- **PDF/A-3 conformance.** `carthorse.pdf` attaches XML to an existing
  PDF using pypdf, but does not upgrade the host PDF to PDF/A-3 — the
  formal compliance requirement for Factur-X. Pair with a dedicated
  converter when full conformance is needed.
- **Schematron `.sch` rules.** The per-profile schematron files are
  not vendored. If we want automated BR-* enforcement against the
  official rules, those are the source of truth — today the BR-*
  checks are hand-coded.
- **EXTENDED CIUS full coverage.** Selective EXTENDED structures
  (sub-line hierarchy, logistics charges, advance payments, deviating
  parties) are modelled; the long tail of `BT-X-*` extension fields
  is added on demand. See `docs/IMPLEMENTATION_PLAN.md §5`.

## See also

- `docs/READING_OFFICIAL_DOCS.md` — how to navigate the vendored
  Factur-X 1.08 / ZUGFeRD 2.4 documentation kit.
- `docs/STRUCTURES.md` — module → BG/BT field map with profile
  applicability and wire conventions.
- `docs/VALIDATION.md` — every business rule, with enforcement status
  and the function that implements it.
- `docs/IMPLEMENTATION_PLAN.md` — gap list and ordered roadmap.
- `docs/PROFILES/COMFORT.md` and `docs/PROFILES/EXTENDED.md` —
  per-profile parity checklists.
