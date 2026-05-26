# Validator refactor plan

Move every business-rule check from inline `validate_internal` method
bodies on `Element` subclasses to free-standing functions in a new
`carthorse.schema.rules` subpackage. Each function corresponds to one
`BR-*` rule, names it in the identifier, documents the rule text in
its docstring, decides its own profile gating, and returns
`list[ValidationError]`.

This document is the durable spec for the rework. A programmer
walking in cold should be able to pick up any unfinished step from
the TODO list at the end and continue.

## Why

* **Visibility.** Today the checks for a single rule are scattered
  inside large `validate_internal` bodies on dataclasses that already
  carry the modelling responsibility. Locating "where is BR-CO-15
  enforced?" requires grepping.
* **Symmetry.** The 24 per-VAT-category rules currently collapse into
  a data-driven table inside `Trade._validate_vat_category_required_parties`;
  the rest of the rules live one-per-`if` in `validate_internal`. The
  catalogue has no single representation.
* **Catalogue completeness.** `docs/VALIDATION.md` is hand-maintained
  and drifts. The eventual goal (out of scope for this refactor but
  enabled by it) is to generate that document from the validator
  registry plus the xlsx `Business Rules` sheet.

## Non-goals

* No new business rules.
* No change to runtime behaviour — the same `BR-*` codes fire on the
  same inputs as today.
* No auto-generated `docs/VALIDATION.md` (deferred).
* No changes to implicit `◯` rules (those enforced by required
  dataclass fields). They keep the implicit status.

## Source of truth

The xlsx `ZF24_EN/Documentation/1_FACTUR-X 1.08 - 2025 12 04 - EN FR -
VF.xlsx` sheet `Business Rules` is the canonical source for:

* the rule **id** (column 13 for general rules, column 3 for VAT-
  family rules);
* the **description** (column 14 / column 4) — copy verbatim into
  the docstring;
* the **target context** (column 15) — informational only;
* the **per-profile applies-to matrix** (columns 7..11 / 21..25; `X`
  = applies at that profile, `-` = does not apply).

To re-read it:

```python
import openpyxl
wb = openpyxl.load_workbook(
    "ZF24_EN/Documentation/1_FACTUR-X 1.08 - 2025 12 04 - EN FR - VF.xlsx",
    data_only=True, read_only=True,
)
ws = wb["Business Rules"]
# row 4 is the header; data starts at row 5
```

Columns of interest (1-based):

| col | meaning                              |
|-----|--------------------------------------|
| 3   | VAT-family BR id (e.g. `BR-S-2`)     |
| 4   | VAT-family description (EN)          |
| 7-11| VAT-family per-profile applies (X/−) |
| 13  | General BR id (e.g. `BR-CO-25`)      |
| 14  | General description (EN)             |
| 15  | Target context (e.g. `Invoice`)      |
| 16  | Business term / group                |
| 21-25 | General per-profile applies (X/−) |

For looking up canonical BT/BG descriptions (when a rule's docstring
needs more context), the sibling tool `tools/ingest_en16931_terms.py`
already extracts those from the same xlsx into a JSON sidecar at
`tools/en16931_terms.json` (gitignored — regenerate locally).

## Architecture

### Module layout

```
src/carthorse/
  rules/
    __init__.py     # re-exports Validator type alias
    _types.py       # Validator type alias
    accounting.py   # validators for TaxTotal, MonetarySummation,
                    # ApplicableTradeTax, CategoryTradeTax,
                    # TradeAllowanceCharge
    settlement.py   # validators for PayeePartyCreditorFinancialAccount,
                    # PaymentMeans, BillingSpecifiedPeriod,
                    # TradeSettlement
    party.py        # validators for TaxSchemeId, SellerTradeParty,
                    # BuyerTradeParty
    line.py         # validators for GrossTradePrice, NetTradePrice
    trade.py        # every cross-sibling rule on Trade
  schema/
    ...             # unchanged
```

The new ``rules`` package is a **sibling** of ``schema`` (not a
subpackage), and each ``schema.<topic>`` module imports the
validators it needs **directly** — there is no side-effecting
import in ``schema/__init__.py``.

### Validator type

`src/carthorse/rules/_types.py`:

```python
from collections.abc import Callable
from carthorse.schema.element import Element, ValidationError
from carthorse.schema.types import Profile

type Validator[T: Element] = Callable[[T, Profile], list[ValidationError]]
```

Bare callable — not a `Protocol`, not a class. PEP 695 `type`
statement requires Python 3.12+ which `pyproject.toml` already
enforces.

### Validator function

Each rule is one free-standing module-level function with the BR id
in the name (lower-cased, dashes → underscores). To avoid a
circular import (``schema.settlement`` imports the validators;
the validators need ``TradeSettlement`` for their type annotation),
each rule module starts with ``from __future__ import annotations``
so the annotations are strings — the runtime body uses only
attribute access on ``m`` and never references the element class
directly:

```python
# src/carthorse/rules/settlement.py
from __future__ import annotations

from typing import TYPE_CHECKING

from carthorse.schema.element import ValidationError
from carthorse.schema.types import Profile

if TYPE_CHECKING:
    from carthorse.schema.settlement import TradeSettlement


def br_co_25(m: TradeSettlement, profile: Profile) -> list[ValidationError]:
    """BR-CO-25: In case the Amount due for payment (BT-115) is
    positive, either the Payment due date (BT-9) or the Payment terms
    (BT-20) shall be present.

    Applies: BASIC_WL+ (the source fields BT-9 / BT-20 live in
    SpecifiedTradePaymentTerms which the MINIMUM XSD does not include).
    """
    if profile < Profile.BASIC_WL:
        return []
    if m.monetary_summation.due_amount <= 0:
        return []
    if m.terms is not None and (
        m.terms.due is not None or m.terms.description is not None
    ):
        return []
    return [ValidationError("BR-CO-25", "…")]
```

Rules:

* **Name**: `br_<lowercased_id_with_underscores>`. Examples:
  `BR-1` → `br_1`, `BR-CO-25` → `br_co_25`, `BR-AE-2` → `br_ae_2`,
  `BR-IC-11` → `br_ic_11`, `BR-O-11` → `br_o_11`.
* **Docstring**: first line is `<BR-id>: <description verbatim from
  xlsx>.`. Optional second paragraph beginning `Applies: <profile>+`
  documents the gate. Further paragraphs explain spec quirks (e.g.
  the BR-CO-25 gate above is a carthorse-specific concession).
* **Signature**: `(m: T, profile: Profile) -> list[ValidationError]`
  where `T` is the concrete element type the rule reads.
* **Self-gating**: the function returns `[]` at the top when it
  doesn't apply (wrong profile, the precondition data isn't present,
  ...). The element invokes it unconditionally.
* **Non-BR error codes**: a few existing checks (`"BT-118-0"`,
  `"BT-95-0/BT-102-0"`, `"BT-8"`, `"BT-81"`, `"BR-5"` shape) keep
  their existing error codes for back-compat. Function names:
  `bt_118_0_vat_only`, `bt_8_code_shape`, `bt_81_code_shape`,
  `br_5_currency_shape`.

### Element wiring

Each ``schema.<topic>`` module imports its validators directly from
``carthorse.rules.<topic>`` and lists them in a ``_validators``
ClassVar on the element. ``validate_internal`` is a uniform 3-line
body:

```python
# src/carthorse/schema/settlement.py
from carthorse.rules import Validator
from carthorse.rules.settlement import (
    br_5_currency_shape,
    br_co_14,
    br_co_15,
    br_co_16,
    br_co_18,
    br_co_25,
    br_53,
)


class TradeSettlement(Element):
    _validators: ClassVar[tuple[Validator[TradeSettlement], ...]] = (
        br_5_currency_shape,
        br_co_18,
        br_53,
        br_co_25,
        br_co_14,
        br_co_15,
        br_co_16,
    )

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors = [e for v in self._validators for e in v(self, profile)]
        errors.extend(super().validate_internal(profile))
        return errors
```

The validators are first-class function objects — listing them in
``_validators`` does **not** invoke them; that happens at validation
time. So the import order is:

1. ``schema.settlement`` evaluates the module body.
2. The ``from carthorse.rules.settlement import …`` line runs,
   evaluating the rule module's top level (which contains only
   ``from __future__ import annotations`` and ``TYPE_CHECKING``
   imports — no class references at module level).
3. ``class TradeSettlement(Element)`` runs; the ``_validators``
   tuple is built from the imported function references.

No circular import because the rule module never references
``TradeSettlement`` at module evaluation time (the annotations are
strings under ``from __future__ import annotations``).

Cross-sibling rules live in ``carthorse.rules.trade`` and are wired
onto ``Trade._validators``. Helper predicates (``_has_vat_id``,
``_has_buyer_legal_id``, ``_iter_tax_registrations``) live next to
the validators in the same module.

Elements that today have **no** `validate_internal` body don't need
the `_validators` ClassVar — `Element.validate_internal` returns
`[]` by default and child-recursion is handled by the base class
already (verify in `element.py` before assuming).

### Per-VAT-category expansion

Today `Trade._validate_vat_category_required_parties` walks a
`families: list[tuple[CategoryCode, bool, str, tuple[str, str, str]]]`
table to emit `BR-{AE,E,G,IC,IG,IP,S,Z}-{2,3,4}` errors plus
`BR-O-{2,3,4}`, `BR-IC-11/12`, and `BR-O-11..14`. The new layout has
one function per BR id — **31 functions** in `rules/trade.py`:

| family | functions                                            |
|--------|------------------------------------------------------|
| AE     | `br_ae_2`, `br_ae_3`, `br_ae_4`                      |
| E      | `br_e_2`, `br_e_3`, `br_e_4`                         |
| G      | `br_g_2`, `br_g_3`, `br_g_4`                         |
| IC     | `br_ic_2`, `br_ic_3`, `br_ic_4`, `br_ic_11`, `br_ic_12` |
| AF     | `br_af_2`, `br_af_3`, `br_af_4`                      |
| AG     | `br_ag_2`, `br_ag_3`, `br_ag_4`                      |
| O      | `br_o_2`, `br_o_3`, `br_o_4`, `br_o_11`, `br_o_12`, `br_o_13`, `br_o_14` |
| S      | `br_s_2`, `br_s_3`, `br_s_4`                         |
| Z      | `br_z_2`, `br_z_3`, `br_z_4`                         |

Each is independent and reads from `m.items`, `m.settlement.allowance_charge`,
`m.settlement.trade_taxes`, `m.agreement.{seller,buyer,seller_tax_representative_party}`
as needed. Shared helpers stay module-private.

### Import direction

Imports flow **from** ``carthorse.schema`` **to** ``carthorse.rules``
— never the reverse at runtime. The rule modules carry only
``TYPE_CHECKING``-guarded element type imports for annotations, made
inert by ``from __future__ import annotations``.

``carthorse.schema.__init__`` does **not** import the rules
subpackage. ``carthorse.rules.__init__`` does **not** import any
rule submodule for side effects. Each schema module imports the
validators it cares about by name from the matching rule submodule.

## What does NOT change

* The `Element.validate_internal` contract (returns
  `list[ValidationError]`, never raises).
* The `Document.validate` aggregator (collects every error,
  raises a single `ValidationErrors` at the top level).
* The set of `BR-*` codes emitted, the error messages, the profile
  gates. (Refactor only — no behavioural drift.)
* `docs/VALIDATION.md` (still hand-maintained until the eventual
  auto-generation work).

## TODO

* [x] **Step 1 — scaffolding**: create `src/carthorse/rules/`
  (sibling of `schema/`) with `_types.py` defining the `Validator`
  type alias and `__init__.py` re-exporting it. No side-effect
  imports anywhere; rule submodules will be imported directly by
  the matching `schema.<topic>` module when their validators
  arrive. No validators moved yet; tests still green at
  `281 passed`.
* [x] **Step 2 — `rules/accounting.py`**: extract validators from
  `accounting.py`:
  * `br_5_currency_shape` (TaxTotal)
  * `br_12` (MonetarySummation, BT-106 required at BASIC_WL+)
  * `br_co_3` (ApplicableTradeTax, BT-7 vs BT-8 mutually exclusive)
  * `br_co_17` (ApplicableTradeTax, BT-117 rounding identity)
  * `bt_8_code_shape` (UNTDID 2475 code shape on BT-8)
  * `bt_118_0_vat_only` (TypeCode != VAT outside EXTENDED)
  * `bt_95_0_102_0_vat_only` (CategoryTradeTax, combined error code
    `"BT-95-0/BT-102-0"` for back-compat with existing tests)
  * **Pyright cycle gotcha**: pyright's `reportImportCycles` flags
    the architectural cycle (`schema/accounting.py` runtime-imports
    rule functions; `rules/accounting.py` TYPE_CHECKING-imports
    schema types). Tried `from schema.accounting import …`, `from
    schema import accounting as _acc`, runtime import without
    TYPE_CHECKING — all forms hit at least one cycle. Settled on
    file-level `# pyright: reportImportCycles=false` + the `_acc`
    qualifier form for readability. Apply the same pattern in
    every subsequent rules submodule.
* [x] **Step 3 — `rules/settlement.py`**: extract validators from
  `settlement.py`:
  * `br_50` (PayeePartyCreditorFinancialAccount, IBAN or proprietary
    id required)
  * `bt_81_code_shape` (PaymentMeans.type_code UNTDID 4461 shape)
  * `br_co_19` + `br_29` (BillingSpecifiedPeriod — at least one
    endpoint; end >= start when both present. Two functions.)
  * `br_5_currency_shape_on_trade_settlement` (the BT-5 currency
    shape check on `TradeSettlement.currency_code` — already exists
    in `TradeSettlement.validate_internal`. Function name and code
    needs deciding — see "carry-over" note in step 2.)
  * `br_co_18` (≥ 1 trade_taxes row at BASIC_WL+)
  * `br_53` (BT-6 set ⇒ a TaxTotal with currency_id == BT-6)
  * `br_co_25` (positive BT-115 ⇒ BT-9 or BT-20)
  * `br_co_14` (BT-110 = sum(BT-117) across BG-23 rows)
  * `br_co_15` (BT-112 = BT-109 + BT-110)
  * `br_co_16` (BT-115 = BT-112 - BT-113 + BT-114)
* [x] **Step 4 — `rules/party.py`**: extract validators from
  `party.py`:
  * `bt_31_0_scheme_id` (TaxSchemeId schemeID ∈ {VA, FC})
  * `br_co_9` (TaxSchemeId, ISO 3166-1 alpha-2 prefix on VAT ids)
  * `br_co_26` (SellerTradeParty, BT-29 OR BT-30 OR BT-31)
  * `br_10` (BuyerTradeParty, address required from BASIC_WL+)
* [x] **Step 5 — `rules/line.py`**: extract validators from
  `line.py`:
  * `br_27` (NetTradePrice, BT-146 >= 0)
  * `br_28` (GrossTradePrice, BT-148 >= 0)
* [x] **Step 6 — `rules/trade.py`**: the big one. Move every
  cross-sibling rule and expand the per-VAT-category families:
  * `br_16` (BASIC+ requires ≥ 1 line item)
  * `br_co_10`, `br_co_11`, `br_co_12`, `br_co_13` (sum identities)
  * `br_co_21`, `br_co_22` (header allowance/charge reason coupling)
  * `br_co_23`, `br_co_24` (line allowance/charge reason coupling)
  * 24 per-VAT-category `br_{ae,e,g,ic,ig,ip,s,z}_{2,3,4}` and
    `br_o_{2,3,4}`
  * `br_ic_11`, `br_ic_12` (intra-community delivery date / country)
  * `br_o_11`, `br_o_12`, `br_o_13`, `br_o_14` (O single-rate)
* [x] **Step 7 — collapse the override**: once every Element
  subclass that validates anything has migrated to the uniform
  three-line ``validate_internal`` body, hoist that body to
  :class:`~carthorse.schema.element.Element` itself. Each
  subclass then only declares::

      _validators: ClassVar[tuple[Validator[<Self>], ...]] = (...)

  no ``validate_internal`` override at all. The base class default
  ``_validators = ()`` makes element types without rules work
  out-of-the-box. Save the ``super(<Cls>, self).validate_internal(profile)``
  call inside the base method (it already recurses into child
  elements). Sanity-check that the recursion through nested
  elements (which today happens in
  :meth:`Element.validate_internal`) still kicks in after the
  collapse.

After each step: `make tests` should report `281 passed`. Tests
themselves don't change.

## Verification checklist per step

For every step:

1. `uv run ruff check src/ tests/` is clean.
2. `uv run basedpyright src/carthorse/schema/` reports **no new**
   errors (the 10 pre-existing `_Element` vs `ETElement` errors in
   `tests/` stay).
3. `uv run pytest -q` reports `281 passed`.
4. The element class's `validate_internal` body shrinks to the
   3-line `_validators` loop + `super()` call.
5. No `BR-*` error code that previously surfaced under a test
   silently disappears (cross-check by running the negative-case
   tests in `tests/test_vat_categories.py`, `tests/test_payment.py`,
   etc.).

## Open questions for follow-up

* Do we want a stable iteration order for `_validators`? Today the
  natural choice is "declaration order in the rules module" — fine
  for now; revisit if it ever needs to be deterministic across
  rebuilds.
* The `_validators` ClassVar attach mutates a tuple. If we ever
  want plugin-style validator extension, switch to `list` and add
  with `_validators.extend(...)`. Out of scope today.
* Auto-generated `docs/VALIDATION.md` (out of scope per the request).
  When that lands, the generator can walk `rules/*` modules,
  introspect each validator's docstring + `Applies:` line, and
  cross-reference the xlsx for the X-mark matrix. The validator
  identifiers (`br_co_25`, …) become the public API of the rule
  catalogue.
