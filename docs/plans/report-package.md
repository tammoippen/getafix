# Plan — the `report` package

Status: **Phases 1–6 landed — the COMFORT surface is complete and
polished.** Every COMFORT-or-lower BT/BG in `docs/STRUCTURES.md` is
rendered, the shared formatting is factored, and a smoke test covers the
whole COMFORT sample corpus. What remains is EXTENDED-only coverage (some
of which already renders).
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
rows and the tax-representative panel; Phase 3 filled in the line detail
and the sub-line hierarchy; Phase 4 added the settlement / accounting
metadata and the supporting-documents table; Phase 5 completed the
ship-to party. This now covers every COMFORT-profile element.

| Section | Elements rendered today |
| --- | --- |
| Invoice (header) | BT-1, BT-2, BT-3, BT-24, BT-23 process, BT-X-2 name, BT-X-4 language, BT-6 VAT acct currency, BG-14 period, BT-10/13/14/12/11 refs, BT-19 booking ref, BT-25 preceding, BG-1 notes |
| Seller / Buyer | BT-27/44 name, BT-28/45 trade name, BT-29/46 id, BT-29-0/46-0 global ids, BT-30/47 legal reg, BT-33 legal info, BG-5/8 address, BG-6/9 contact (name/dept/email/phone), BT-34/49 e-address, BT-31/32/48 tax ids |
| Tax representative | BG-11 BT-62 name, BG-12 address, BT-63 VAT id |
| Delivery | BT-72 date, BG-13 ship-to (BT-70 name, BT-71/71-0 id, BG-15 address), BT-16 despatch, BT-15 receiving |
| Supporting documents | BG-24 BT-122/17/18 ref, BT-123 name, type code, BT-124 URL / BT-125 attachment |
| Line items | BT-153 name, BT-154 desc, BT-157/155/156 ids, BG-33 class, BG-32 chars, BG-34 origin, BT-127 note, BG-26 period, BG-27/28 alw/chg, BT-132/128/133 refs, BT-129/130 qty, BT-146 net (+BT-148/147/149 gross), BT-131 total, BG-30 line VAT; sub-lines nested |
| VAT breakdown | BG-23 category, rate, BT-116 basis, BT-117 tax, BT-120/121 exemption, BT-7/8 tax point |
| Allowances & charges | BG-20/21 indicator, reason, BT-92/99 amount, % · basis, BT-95/102 VAT |
| Totals | BG-22 BT-106…BT-115 |
| Payment | BG-10 payee (BT-59 name, BT-60/60-0 ids), BT-20/9/89 terms, BG-16 means (+BT-82 info), BT-84/85/86 account, BG-18 card, BT-91 debit, BT-83/90 refs |
| Logistics / Prepayments | BG-X-42 / BG-X-45 (EXTENDED — pre-existing) |
| Validation | rule code + message table |

## 4. Gap analysis — what's missing up to COMFORT

Checklists per module. Each unticked box is a COMFORT-or-lower BT/BG that
exists in the model but is not yet rendered. EXTENDED-only additions are
out of scope for this plan (some EXTENDED sections already exist and are
kept, but completing EXTENDED is a separate effort).

### `document.py` — done in Phase 4
- [x] BT-23 business process (`Context.business`) — MINIMUM+

### `party.py` — done in Phase 2
- [x] BT-29 / BT-46 party id, BT-29-0 / BT-46-0 global ids — BASIC_WL
- [x] BT-30 / BT-47 legal registration id (+ scheme) — `legal_organization.id`
- [x] BT-33 Seller additional legal info (`description`) — COMFORT
- [x] BT-41-0 / BT-56-0 contact department name — COMFORT
- [x] BG-11 Seller tax representative (BT-62 name, BG-12 address, BT-63 VAT id) — BASIC_WL
- [x] BT-60 / BT-60-0 Payee id / global id (Payee rows beyond name) — BASIC_WL

### `agreement.py` — done in Phase 4
- [x] BG-24 additional supporting documents — COMFORT
      (BT-122 id, BT-123 name, BT-124 URI, BT-125 attachment;
      BT-17 tender/lot, BT-18 invoiced-object, selected by type code)

### `delivery.py` — done in Phase 5
- [x] BG-15 ship-to **address** + BT-71 / BT-71-0 ship-to location id
      (only the name showed before) — BASIC_WL

### `settlement.py` — done in Phase 4
- [x] BT-6 VAT accounting currency (`tax_currency_code`) — BASIC_WL
- [x] BT-82 payment-means free-text information — COMFORT
- [x] BT-19 Buyer accounting reference (`accounting_account`) — BASIC_WL

### `accounting.py` — done in Phase 4
- [x] BT-7 tax point date / BT-8 due-date code on BG-23 rows — COMFORT

### `line.py` — done in Phase 3
- [x] BT-157 item standard id (`product.global_id`) — BASIC
- [x] BG-33 item classification (BT-158) — COMFORT
- [x] BT-148 gross price + BT-149/150 basis quantity, BT-147 price
      discount (`gross_price` / `applied_allowance_charge`) — BASIC
- [x] BG-27 / BG-28 line allowances & charges — BASIC / COMFORT
- [x] BG-26 line invoicing period (BT-134/135) — BASIC_WL
- [x] BT-127 line note — BASIC
- [x] BT-132 line buyer-order ref, BT-128 line object id — COMFORT
- [x] BT-133 line Buyer accounting reference — COMFORT

### `references.py` — done in Phase 4
- [x] BT-125 attachment summary (filename + MIME) for BG-24 — COMFORT

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

**Phase 3 — line detail (done).**
`line.py`: item standard id and classification in the item cell; gross
price / basis quantity / price discount as a dim derivation under the
net price (`net_price_cell`); line note, invoicing period, line
allowances/charges and line references (BT-132 / BT-128 / BT-133) as dim
follow-up lines in the item cell (flat table kept — a nested per-line
sub-table remains a non-goal). `trade.py`: sub-invoice-lines are now
ordered into a depth-first tree so each child renders directly under its
parent, and the line-id column is left-justified so the indentation is
actually visible (a right-justified column swallowed the leading spaces,
so the previous indentation never showed and children could appear above
their parent in document order).

**Phase 4 — settlement & accounting (done).**
`document.py`: BT-23 business process row in the Invoice panel.
`settlement.py`: BT-6 VAT accounting currency and BT-19 Buyer accounting
reference folded into the Invoice panel (`accounting_currency_row` /
`accounting_reference_rows`); BT-82 payment-means free text into the
Payment panel. `accounting.py`: BT-7 / BT-8 tax point as an extra
VAT-breakdown column, added only when a row carries it. `agreement.py` +
`references.py`: BG-24 supporting documents as their own table
(`supporting_documents_panel`), with BT-125 attachments summarised by
`format_attachment` as filename / MIME.

**Phase 5 — delivery (done).**
`delivery.py`: the ship-to party now renders its location id (BT-71) and
global id (BT-71-0) plus the full ship-to address (BG-15), reusing
`party.format_address` rather than duplicating it.

**Phase 6 — polish (done).**
Factored the duplicated formatting into `types.py`: `format_amount`
(totals), `format_period` (header BG-14 + line BG-26, previously copied),
and `dim` / `dim_paren` to centralise the muted `[dim]…[/dim]` markup
that had spread across seven sites (reason codes, scheme hints, note
subjects, the sub-line subtype tag, reference dates, attachment MIME).
Output is byte-identical — the existing assertions still pass. Added a
parametrised smoke test that renders every shipped COMFORT-or-lower
sample (35 invoices) and asserts non-empty output, guarding against any
populated field tripping the renderer.

### EXTENDED slice — item price allowances / charges (BT-147-00 / BT-X-302-00)

Pulled in ahead of the broader EXTENDED pass because the model was
silently dropping data on COMFORT/EXTENDED invoices. The gross price's
``AppliedTradeAllowanceCharge`` is now a **list** (was a single field, so
only the last of several survived parsing) and gained the EXTENDED
``reason`` / ``reason_code`` (BT-X-36 / BT-X-313 allowance, BT-X-303 /
BT-X-314 charge) alongside the existing percent / basis, all re-gated to
their correct EXTENDED profile and ordered per the XSD sequence. Three
internal validators encode the profile matrix from the appendix / xlsx:

* a price **charge** (``ChargeIndicator`` true, BT-X-302-00) is
  EXTENDED-only (`applied_price_charge_extended_only`);
* below EXTENDED the list is capped at one entry
  (`list_max_cardinality_below`);
* the percent / basis / reason / reason-code fields are EXTENDED-only
  (`fields_only_at`).

`net_price_cell` now renders one term per allowance / charge with its
reason, e.g. ``gross 1.50 -0.03 (Artikelrabatt 1) -0.02 (Artikelrabatt 2)``.

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
