# Plan — the `report` package

Status: **Phases 1–2 landed** (skeleton + rewrite; party identification).
Remaining phases below take it from "renders the subset the old
`report.py` did" to "renders **every COMFORT-profile element**".

## 1. Why

`report.py` had grown into a single 600-line module that mixed the
console orchestration, the per-section panel/table builders and the
little formatting helpers. It rendered a useful-but-partial slice of the
model and there was no obvious home for "the bit that renders a Buyer
order line reference" — you just scrolled.

The `rules` package solved the same shape of problem for validation: one
module per schema topic, each holding the free-standing functions that
act on the elements defined in the matching `schema/<topic>.py`. This
plan applies that structure to rendering.

## 2. Target architecture

Every `schema/<topic>.py` gets a `report/<topic>.py` that renders the
elements defined there. Shared machinery sits in `_types.py`; pure
code→string formatting sits in `types.py`.

```
src/getafix/report/
├── __init__.py      # render_invoice orchestrator + public re-exports
├── _types.py        # SectionRenderer alias, described_panel / describe_table
├── element.py       # render_validation_errors (schema/element.py)
├── types.py         # format_type_code, format_vat (schema/types.py enums)
├── document.py      # Invoice overview panel (schema/document.py)
├── party.py         # Seller / Buyer panels, address, tax ids (schema/party.py)
├── agreement.py     # order / contract / project rows (schema/agreement.py)
├── delivery.py      # Delivery panel (schema/delivery.py)
├── accounting.py    # VAT breakdown, allowances/charges, totals (schema/accounting.py)
├── settlement.py    # payment, prepayments, period rows (schema/settlement.py)
├── line.py          # item cell + line VAT cell (schema/line.py)
├── trade.py         # line-items table (schema/trade.py)
└── references.py    # format_reference (schema/references.py)
```

`schema/_numeric.py` intentionally has **no** counterpart — it is a
rounding helper, not a renderable element.

### Conventions

These hold for every section renderer; new code must preserve them.

- **One element family per module.** A renderer reads the element named
  in its schema twin and returns a Rich renderable, or `None` when there
  is nothing to show (so the orchestrator can skip an empty box). The
  canonical shape is `SectionRenderer` in `_types.py`; money-bearing
  renderers additionally take the document `currency`.
- **Every section is self-describing.** Panels get a one-line, dim
  description on top via `described_panel`; tables get the same as a
  dim subtitle line under the title via `describe_table`. The
  description says *what the section means* in plain language — a reader
  skimming the report should not need the spec open.
- **Label data with its BT/BG id.** Row labels read `Human name (BT-xx):`
  so the report doubles as a cross-reference back to the standard.
- **Dim the secondary, em-dash the absent.** Enrichments (descriptions,
  ids, derivations) render dim; a structurally-absent cell renders `—`.
- **No business logic.** Renderers read already-validated data; any
  arithmetic or rule lives in `rules/`, never here.

## 3. What's rendered today

Phase 1 preserved the old renderer's coverage exactly (same panels,
order and strings — the original `tests/test_report.py` still passes) and
added the section descriptions; Phase 2 added the party-identification
rows and the tax-representative panel.

| Section | Elements rendered today |
| --- | --- |
| Invoice (header) | BT-1, BT-2, BT-3, BT-24, BT-X-2 name, BT-X-4 language, BG-14 period, BT-10/13/14/12/11 refs, BT-25 preceding, BG-1 notes |
| Seller / Buyer | BT-27/44 name, BT-28/45 trade name, BT-29/46 id, BT-29-0/46-0 global ids, BT-30/47 legal reg, BT-33 legal info, BG-5/8 address, BG-6/9 contact (name/dept/email/phone), BT-34/49 e-address, BT-31/32/48 tax ids |
| Tax representative | BG-11 BT-62 name, BG-12 address, BT-63 VAT id |
| Delivery | BT-72 date, BG-13 ship-to **name**, BT-16 despatch, BT-15 receiving |
| Line items | BT-153 name, BT-154 desc, BT-155/156 ids, BG-32 chars, BG-34 origin, BT-129/130 qty, BT-146 net, BT-131 total, BG-30 line VAT |
| VAT breakdown | BG-23 category, rate, BT-116 basis, BT-117 tax, BT-120/121 exemption |
| Allowances & charges | BG-20/21 indicator, reason, BT-92/99 amount, % · basis, BT-95/102 VAT |
| Totals | BG-22 BT-106…BT-115 |
| Payment | BG-10 payee (BT-59 name, BT-60/60-0 ids), BT-20/9/89 terms, BG-16 means, BT-84/85/86 account, BG-18 card, BT-91 debit, BT-83/90 refs |
| Logistics / Prepayments | BG-X-42 / BG-X-45 (EXTENDED — pre-existing) |
| Validation | rule code + message table |

## 4. Gap analysis — what's missing up to COMFORT

Checklists per module. Each unticked box is a COMFORT-or-lower BT/BG that
exists in the model but is not yet rendered. EXTENDED-only additions are
out of scope for this plan (some EXTENDED sections already exist and are
kept, but completing EXTENDED is a separate effort).

### `document.py`
- [ ] BT-23 business process (`Context.business`) — MINIMUM+

### `party.py` — done in Phase 2
- [x] BT-29 / BT-46 party id, BT-29-0 / BT-46-0 global ids — BASIC_WL
- [x] BT-30 / BT-47 legal registration id (+ scheme) — `legal_organization.id`
- [x] BT-33 Seller additional legal info (`description`) — COMFORT
- [x] BT-41-0 / BT-56-0 contact department name — COMFORT
- [x] BG-11 Seller tax representative (BT-62 name, BG-12 address, BT-63 VAT id) — BASIC_WL
- [x] BT-60 / BT-60-0 Payee id / global id (Payee rows beyond name) — BASIC_WL

### `agreement.py`
- [ ] BG-24 additional supporting documents — COMFORT
      (BT-122 id, BT-123 name, BT-124 URI, BT-125 attachment;
      BT-17 tender/lot, BT-18 invoiced-object, selected by type code)

### `delivery.py`
- [ ] BG-15 ship-to **address** + BT-71 ship-to location id (only the
      name shows today) — BASIC_WL

### `settlement.py`
- [ ] BT-6 VAT accounting currency (`tax_currency_code`) — BASIC_WL
- [ ] BT-82 payment-means free-text information — COMFORT
- [ ] BT-19 Buyer accounting reference (`accounting_account`) — BASIC_WL

### `accounting.py`
- [ ] BT-7 tax point date / BT-8 due-date code on BG-23 rows — COMFORT

### `line.py`
- [ ] BT-157 item standard id (`product.global_id`) — BASIC
- [ ] BG-33 item classification (BT-158) — COMFORT
- [ ] BT-148 gross price + BT-149/150 basis quantity, BT-147 price
      discount (`gross_price` / `applied_allowance_charge`) — BASIC
- [ ] BG-27 / BG-28 line allowances & charges — BASIC / COMFORT
- [ ] BG-26 line invoicing period (BT-134/135) — BASIC_WL
- [ ] BT-127 line note — BASIC
- [ ] BT-132 line buyer-order ref, BT-128 line object id — COMFORT
- [ ] BT-133 line Buyer accounting reference — COMFORT

### `references.py`
- [ ] BT-125 attachment summary (filename + MIME) for BG-24 — COMFORT

## 5. Phased implementation

Order chosen so each phase is independently shippable and testable, and
so the highest-value gaps (party identification, line pricing detail)
land first.

**Phase 1 — skeleton + rewrite (done).**
Package created, existing logic moved in, section descriptions added.
`tests/test_report.py` passes unchanged.

**Phase 2 — party identification (done).**
`party.py`: party id + global ids, legal registration id, additional
legal info, contact department added to `party_panel` (BT-labelled rows);
BG-11 tax representative rendered by `tax_representative_panel` as its
own green panel after the Seller/Buyer row (chosen over inline Seller
rows — it has its own address + VAT id, so a panel reads cleaner and
reuses `format_address` / the tax-id formatter). Payee id / global id
added to the Payment panel. A `scheme_suffix` formatter in
`report/types.py` now renders the dim `(scheme XXX)` hint shared by
global id, legal registration id and electronic address.

**Phase 3 — line detail.**
`line.py` + `trade.py`: item standard id and classification in the item
cell; gross price / basis quantity / price discount as dim derivation
under the net price; line note as a dim follow-up line. Line-level
allowances/charges (BG-27/28) and the line period (BG-26): render as dim
follow-up lines in the item cell (keeps the flat table) — a nested
per-line sub-table is a non-goal.

**Phase 4 — settlement & accounting.**
`settlement.py`: BT-6 accounting currency and BT-82 means info into the
existing panels; BT-19 accounting reference (likely a row in Payment or
a small "Accounting" panel). `accounting.py`: BT-7/BT-8 tax point as an
extra VAT-breakdown column or dim row. `agreement.py` + `references.py`:
BG-24 supporting documents (a "References & attachments" panel) with
BT-125 attachments summarised by filename/MIME. `document.py`: BT-23.

**Phase 5 — delivery.**
`delivery.py`: full ship-to address + location id via
`party.format_address` (reuse, don't duplicate).

**Phase 6 — polish.**
Factor shared `format_amount(value, currency)` / `format_date` helpers
into `types.py` if duplication has crept in; sweep every section for the
BT/BG-labelling and description conventions; confirm a COMFORT sample
renders every populated field.

## 6. Testing

- Extend `tests/test_report.py` with one positive assertion per newly
  rendered BT/BG, driven off the existing `tests/samples/` corpus (the
  `EN16931_zf24_*` samples between them populate most COMFORT fields).
- Keep using a `record=True` Console and assert on `export_text()` so
  tests check content, not terminal-control bytes.
- A renderer that can return `None` needs both a populated case and an
  omitted case (mirrors the rule "positive + negative" convention).
- `make check` (ruff + basedpyright) and `make tests` (≥90 % coverage)
  gate every phase.

To eyeball a change, render any sample to an image with the dev helper::

    uv run python tools/render_report.py tests/samples/EN16931_zf24_Rabatte.xml -o /tmp/report.png

It accepts any CII XML and writes a PNG (default, via the ``cairosvg``
dev dependency) or an SVG (`-o foo.svg`, no extra dependency).

## 7. Definition of done

For each COMFORT-profile BT/BG in `docs/STRUCTURES.md`, either:

1. it is rendered by exactly one `report/<topic>.py` function with a
   BT/BG-labelled row/cell and at least one test asserting it; or
2. it is explicitly listed here as a deliberate non-goal (e.g.
   high-cardinality / debugging-only fields) with a one-line rationale.

EXTENDED-only elements remain out of scope until the COMFORT surface is
complete.
