# COMFORT (EN 16931) parity checklist

Tracking surface for the remaining work to bring `carthorse` to full
COMFORT (= EN 16931 = URN ``urn:cen.eu:en16931:2017``) conformance —
structures *and* business rules.

This file is the operational complement to:

* ``docs/STRUCTURES.md`` — field narrative and per-profile field
  surface;
* ``docs/VALIDATION.md`` — rule narrative, families and current
  status;
* ``docs/IMPLEMENTATION_PLAN.md §EN16931`` — cross-profile roadmap
  (line 126 onwards).

It is a checklist, not a re-derivation of the spec — every item links
back to a concrete file path, the Factur-X 1.08 main spec spreadsheet
row, or a clause in the ZUGFeRD 2.4 / Factur-X 1.08 technical appendix
"Profile EN16931" (pp. 3–10 for structures, pp. 62–74 for the named
rules).


## 1. Scope and reading order

COMFORT is the lowest profile that is bit-for-bit equivalent to the
European semantic invoice (CEN EN 16931-1) — it adds line-level
itemisation and the per-line / per-charge metadata that BASIC omits.

What "complete COMFORT" means here:

* every BT/BG named in the EN 16931 XSD
  (``tests/schemas/3_Factur-X_1.08_EN16931/FACTUR-X_EN_16931_*.xsd``)
  round-trips parse → render → re-parse without loss;
* every named EN 16931 business rule (178 in the technical appendix,
  pp. 62–74) is enforced by ``Element._validators`` or by
  ``Trade._validate_*`` at the right profile;
* every closed code list referenced by a ``BR-CL-*`` rule (24
  families) is typed as a ``StrEnum`` so construction- and parse-time
  reject out-of-list values;
* every ``BR-DEC-*`` decimal-precision rule (21 at COMFORT) is
  enforced by a single shared validator factory.

What's explicitly **not** in scope here — kept in
``IMPLEMENTATION_PLAN.md §EXTENDED`` and ``§5``:

* the EXTENDED CIUS overlay (``BG-X-*``, ``BT-X-*``, ``BR-FXEXT-*``,
  ``BR-FX-DE-*``);
* PDF/A-3 packaging (delegated to ``factur-x`` on PyPI);
* schematron-driven rule generation (own track).

Scorecard:

| Surface | Today | Target |
|---|---|---|
| Header structures (BT-1..BT-30) | ✓ | ✓ |
| BG-23 VAT breakdown including BT-7 / BT-114 | ✓ | ✓ |
| Line product groups (BG-32 / BG-33 / BG-34) | ✗ | ✓ |
| Line references (BT-128 / BT-132 / BT-133) | ✗ | ✓ |
| Header payment-means detail (BT-82 / BG-18 / BT-85 / BT-86) | ✗ | ✓ |
| Named EN 16931 rules — structural (`BR-*`) | partial | ✓ |
| Cross-field (`BR-CO-*`) | partial | ✓ |
| Per-VAT-category rate/sum (`BR-{S,Z,E,AE,G,IC,IG,IP,O}-5..10`) | ✗ | ✓ |
| `BR-DEC-*` (21 rules) | ✗ | ✓ |
| `BR-CL-*` (24 rules) | ✗ (only shape regex) | ✓ |


## 2. Already landed — explicit ✓ to anchor the open list

These items are done; flagged here so the open list below is not
misread as the whole COMFORT problem.

| Field / group | Source | Status |
|---|---|---|
| BT-7 TaxPointDate + ``BR-CO-3`` | ``schema/accounting.py`` ``ApplicableTradeTax.tax_point_date``; ``rules/accounting.py::br_co_3`` | ✓ |
| BT-114 RoundingAmount + ``BR-CO-16`` | ``schema/accounting.py:212``; ``rules/settlement.py::br_co_16`` | ✓ |
| BT-33 Seller description / BT-34 ElectronicAddress | ``schema/party.py`` ``SellerTradeParty`` | ✓ |
| BG-6 / BG-9 Contact (Seller / Buyer) | ``schema/party.py`` ``*.contact`` | ✓ |
| BT-14 Sales order ref / BG-24 Additional refs / BT-11 Project / BT-15 Receiving advice | ``schema/references.py`` | ✓ |
| BT-32 Seller FC tax registration (2nd `SpecifiedTaxRegistration`) | ``schema/party.py`` ``SellerTradeParty.tax_registrations`` | ✓ |
| BT-154 description / BT-155 seller id / BT-156 buyer id (line) | ``schema/line.py`` ``TradeProduct`` | ✓ |
| BT-147 price-level discount % and basis | ``schema/line.py:172`` ``AppliedTradeAllowanceCharge`` (already COMFORT-gated) | ✓ |
| `BR-CO-9` (VAT-ID country prefix) | ``rules/party.py::br_co_9`` | ✓ |
| `BR-CO-21..24` (reason ↔ reason-code coupling) | ``rules/trade.py`` | ✓ |
| `BR-CO-25`, `BR-CO-26` | ``rules/settlement.py``, ``rules/party.py`` | ✓ |
| `BR-{S,Z,E,AE,G,IC,IG,IP,O}-{2,3,4}` (required-party per category) | ``rules/trade.py`` (33 funcs) | ✓ |
| `TypeCode` enum (UNTDID 1001 subset for BT-3) | ``schema/types.py:65`` — 52 members | ◯ (needs 10 more) |
| `CategoryCode` enum (UNTDID 5305) | ``schema/types.py:164`` — 9 members | ✓ |
| `MIME` enum (RFC 6838 subset) | ``schema/types.py:154`` — 6 members | ✓ |


## 3. Missing structures

Each row gives BT/BG id, target file, dataclass to add or extend, XSD
sequence position relative to the technical-appendix structure tree
(pp. 3–10), and a one-line note.

### 3.1 Line-level product groups — ``schema/line.py``

| BT / BG | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BG-32 / BT-160 / BT-161 | ApplicableProductCharacteristic | new ``ProductCharacteristic``; list field ``TradeProduct.characteristics`` | 0..* | XSD: between ``Description`` (BT-154) and ``DesignatedProductClassification``. ``Description`` (BT-160) and ``Value`` (BT-161) both required ⇒ ``BR-54`` is implicit (◯). |
| BT-158-00 / BT-158 / BT-158-1 / BT-158-2 | DesignatedProductClassification | new ``ProductClassification``; list field ``TradeProduct.classifications`` | 0..* | XSD: after BG-32. ``listID`` required when ``ClassCode`` is set ⇒ ``BR-65`` is implicit (◯). ``listID`` typed as the ``UNTDID7143ItemClassSchemeID`` enum (§4.6) enforces ``BR-CL-13``. |
| BT-159-00 / BT-159 | OriginTradeCountry | new ``OriginCountry``; field ``TradeProduct.origin_country`` | 0..1 | XSD: last child of ``SpecifiedTradeProduct``. Single ``ID`` typed as ``Country`` enum (§4.6) enforces ``BR-CL-14/15``. |

### 3.2 Line-level references

| BT / BG | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BT-132-00 / BT-132 | BuyerOrderReferencedDocument (line) | new ``LineBuyerOrderReferencedDocument`` carrying only ``LineID``; field ``LineTradeAgreement.buyer_order_ref`` | 0..1 | Same element name as the header version (``schema/references.py:53``) but a different sequence — line variant only has ``LineID`` (BT-132). |
| BT-128-00 / BT-128 / BT-128-0 / BT-128-1 | AdditionalReferencedDocument (line, "invoice line object identifier") | new ``LineAdditionalReferencedDocument`` carrying ``IssuerAssignedID`` + ``TypeCode`` (always ``130``) + optional ``ReferenceTypeCode``; field on ``LineTradeSettlement.additional_references`` | 0..1 | Distinct dataclass because the header version (``schema/references.py:165``) carries the BG-24 supporting-document fields (URI, attachment, formatted issue date). ``ReferenceTypeCode`` typed as ``UNTDID1153ReferenceCode`` enum (§4.6) enforces ``BR-CL-07``. |
| BT-133-00 / BT-133 | ReceivableSpecifiedTradeAccountingAccount (line) | reuse existing ``schema/settlement.py::ReceivableAccountingAccount``; new field ``LineTradeSettlement.accounting_account`` | 0..1 | Header version is already wired; this is purely a placement extension. |

### 3.3 Header payment-means detail — ``schema/settlement.py``

| BT / BG | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BT-82 | PaymentMeans Information | new field ``PaymentMeans.information: str \| None`` | 0..1 | Free text on ``<ram:Information>``. XSD position: after ``TypeCode`` (BT-81), before ``ApplicableTradeSettlementFinancialCard``. |
| BG-18 / BT-87 / BT-88 | ApplicableTradeSettlementFinancialCard | new ``FinancialCard`` with ``ID`` (PAN, last 4–6 digits) + optional ``CardholderName``; field ``PaymentMeans.financial_card`` | 0..1 | Drives ``BR-51`` (§4.1). |
| BT-85 | PayeePartyCreditorFinancialAccount ``AccountName`` | new field ``PayeePartyCreditorFinancialAccount.account_name: str \| None`` | 0..1 | Add alongside the existing IBAN + Proprietary ID. |
| BT-86-00 / BT-86 | PayeeSpecifiedCreditorFinancialInstitution (BIC) | new ``CreditorFinancialInstitution`` with single ``BICID``; field ``PaymentMeans.creditor_institution`` | 0..1 | XSD position: after ``PayeePartyCreditorFinancialAccount``. |

### 3.4 Profile-gating cleanup for ``TradeAllowanceCharge``

The single ``TradeAllowanceCharge`` dataclass
(``schema/accounting.py:451``) is reused by:

* ``TradeSettlement.allowance_charge`` (``schema/settlement.py:374``)
  — BG-20 / BG-21 (BT-92..BT-101) **header**;
* ``LineTradeSettlement.allowance_charge`` (``schema/line.py:399``)
  — BG-27 / BG-28 (BT-136..BT-147) **line**.

The fields ``calculation_percent`` (BT-94 / BT-101 header;
BT-138 / BT-142 line) and ``basis_amount`` (BT-93 / BT-100 header;
BT-137 / BT-141 line) are currently gated ``Profile.BASIC_WL``
(``accounting.py:479,491``). That gate is correct for the header
context (BG-20/21 land at BASIC_WL) but **leaks at line level**:
line-level allowance/charge BT-138/142 (percent) and BT-137/141
(basis) only ship at COMFORT.

**Decision: keep the single dataclass and add a
``context: ClassVar[Literal["header", "line"]]`` flag, set by the
parent.** Concrete shape:

* Two thin sentinel subclasses ``HeaderTradeAllowanceCharge`` and
  ``LineTradeAllowanceCharge`` override only the class-level
  ``context``.
* Replace the per-field ``metadata["profile"]`` dict on
  ``calculation_percent`` and ``basis_amount`` with a small
  ``_effective_profile(field_name)`` method that returns
  ``BASIC_WL`` for ``context == "header"`` and ``COMFORT`` for
  ``context == "line"``.
* ``to_xml`` / ``from_xml`` already inspect ``profile``; the only
  change is the source of the per-field gate.
* Call sites:
  * ``schema/settlement.py:374`` → ``HeaderTradeAllowanceCharge``;
  * ``schema/line.py:399`` → ``LineTradeAllowanceCharge``.

Precedent exists: the file already routes ``BR-CO-21..24`` through
``Trade._validate_document_arithmetic`` rather than the per-class
validator tuple so the same class works in both contexts
(``accounting.py:535``).


## 4. Missing validators

Grouped by family. Each row gives rule id, lowest enforcing profile,
file path, target dataclass, brief shape. Items that depend on a
missing structure in §3 are flagged with a "blocked by" pointer.

### 4.1 Newly EN-16931-named rules (not yet enforced)

| Rule | Profile | Target | Shape | Blocked by |
|---|---|---|---|---|
| `BR-51` | BASIC | ``FinancialCard`` regex on ``id`` | ``re.fullmatch(r"\d{4,6}", id)`` | §3.3 BG-18 |
| `BR-52` | BASIC | ``AdditionalReferencedDocument.issuer_assigned_id`` required | promote existing ◯ to ✓ with explicit code comment naming the rule | — |
| `BR-54` | COMFORT | ``ProductCharacteristic`` both fields required | implicit ◯ via dataclass shape | §3.1 BG-32 |
| `BR-65` | COMFORT | ``ProductClassification.list_id`` required when ``class_code`` set | implicit ◯ via required field | §3.1 BT-158-1 |

### 4.2 ``BR-CO-*`` allowance/charge reason coherence (BR-CO-5/6/7/8)

The "both present must agree" half is enforced (``BR-CO-21..24``); the
"at least one of reason text or reason code" half is open.

| Rule | Profile | Target | Shape |
|---|---|---|---|
| `BR-CO-5` | BASIC_WL | header allowance | ``reason is not None or reason_code is not None`` |
| `BR-CO-6` | BASIC_WL | header charge | same |
| `BR-CO-7` | BASIC | line allowance | same |
| `BR-CO-8` | BASIC | line charge | same |

Single validator ``rules/accounting.py::br_co_5_6_7_8``, attached to
``TradeAllowanceCharge._validators``. The header vs line discrimination
needed for emitting the right rule code falls out of ``self.context``
introduced in §3.4.

### 4.3 ``BR-*`` structural (BASIC_WL-owed, still open at COMFORT)

| Rule | Profile | Target | Notes |
|---|---|---|---|
| `BR-48` | BASIC_WL | ``ApplicableTradeTax`` | VAT category rate (BT-119) required unless category == ``O``. Place next to existing ``bt_118_0_vat_only``. |
| `BR-61` | BASIC | ``PaymentMeans`` | If ``type_code`` ∈ {30, 58, ...} (credit transfer family) ⇒ ``payee_account.iban`` required. |
| `BR-62` | BASIC | ``URIUniversalCommunication`` | Seller (BT-34): ``scheme_id`` required. Already ◯ via dataclass shape — promote to ✓ in ``rules/party.py::br_62`` for surface-level coverage. |
| `BR-63` | BASIC | ``URIUniversalCommunication`` | Buyer (BT-49): same. ``rules/party.py::br_63``. |

### 4.4 Per-VAT-category rate / sum / reason rules (`-5/-6/-7/-8/-9/-10`)

54 rules across the nine categories. Shape is predictable enough for a
small table-driven validator:

```python
# rules/trade.py
_VAT_CATEGORY_CONSTRAINTS: dict[str, _CatRules] = {
    "S":  _CatRules(rate=lambda r: r is not None and r > 0,  ...),
    "Z":  _CatRules(rate=lambda r: r == 0, exemption=_FORBID, ...),
    "E":  _CatRules(rate=lambda r: r == 0, exemption=_REQUIRE, ...),
    "AE": _CatRules(rate=lambda r: r == 0, exemption=_REQUIRE, ...),
    "G":  _CatRules(rate=lambda r: r == 0, exemption=_REQUIRE, ...),
    "K":  _CatRules(rate=lambda r: r == 0, exemption=_REQUIRE, ...),
    "O":  _CatRules(rate=lambda r: r is None, exemption=_REQUIRE, ...),
    "L":  _CatRules(rate=lambda r: r is not None and r >= 0, ...),
    "M":  _CatRules(rate=lambda r: r is not None and r >= 0, ...),
}
```

One ``_validate_vat_category_constraints`` walk over ``Trade`` issues
all 54 ``ValidationError``s with the per-category code (``BR-S-5``,
``BR-Z-5``, …). Profile: BASIC for line / document allowance / charge
variants; BASIC_WL for breakdown sum variants. Already-enforced
``BR-O-11..14`` (single-rate restriction for category ``O``) stays
where it is.

### 4.5 ``BR-DEC-*`` decimal precision (21 rules at COMFORT)

Every rule has the same shape: named BT amount must have at most 2
decimal places. Implement as a single factory in
``rules/_types.py``:

```python
def max_decimals(code: str, *, field_name: str, max_places: int = 2) -> Validator:
    def _check(self, profile):
        v = getattr(self, field_name, None)
        if v is not None and -v.as_tuple().exponent > max_places:
            return [ValidationError(code, f"{field_name} has >{max_places} decimals")]
        return []
    return _check
```

Wire-up targets:

| Targets | Rules wired |
|---|---|
| ``MonetarySummation`` (BT-106, BT-108–115) | `BR-DEC-09..18` |
| ``ApplicableTradeTax`` (BT-116, BT-117) | `BR-DEC-19/20` |
| ``TradeAllowanceCharge`` header (BT-92, BT-93, BT-99, BT-100) | `BR-DEC-01/02/05/06` |
| ``TradeAllowanceCharge`` line (BT-136, BT-137, BT-141, BT-142) | `BR-DEC-24/25/27/28` |
| ``LineMonetarySummation`` (BT-131) | `BR-DEC-23` |
| ``TaxTotal`` (second total in accounting currency, BT-111) | `BR-DEC-15` |

### 4.6 ``BR-CL-*`` code-list registry (24 rules at COMFORT)

Implementation: vendor each closed code list as a ``StrEnum`` in
``src/carthorse/schema/types.py``. Re-type the affected model fields
to the enum. Construction- and parse-time then raise on out-of-list
values — that's the spec-required behaviour for ``BR-CL-*``. No
separate ``rules/codelists.py`` module and no JSON sidecar.

Member counts taken from the
``EN16931 code lists v16`` XLSX (used from 2025-11-15, ships with
Factur-X 1.08):

| Enum | XLSX sheet | Members | Rule(s) | Field re-typed |
|---|---|---|---|---|
| `TypeCode` (extend existing) | `1001` | 62 | `BR-CL-01` | ``Header.type_code`` (BT-3) |
| `UNTDID1153ReferenceCode` (new) | `1153` | 818 | `BR-CL-07` | scheme id on ``AdditionalReferencedDocument.reference_type_code`` (BT-18-1 / BT-128-1) |
| `UNTDID2475TaxPointDateCode` (new) | `Time` | 5 | `BR-CL-06` | ``ApplicableTradeTax.due_date_code`` (BT-8) — replaces the ``bt_8_code_shape`` regex |
| `UNTDID4451SubjectCode` (new) | `Text` | 402 | `BR-CL-08` | ``IncludedNote.subject_code`` (BT-21) |
| `UNTDID4461PaymentMeansCode` (new) | `Payment` | 84 | `BR-CL-16` | ``PaymentMeans.type_code`` (BT-81) — replaces the ``bt_81_code_shape`` regex |
| `CategoryCode` (existing) | `5305` | 9 | `BR-CL-17/18` | ``ApplicableTradeTax.category_code``, ``CategoryTradeTax.category_code`` |
| `UNTDID5189AllowanceReasonCode` (new) | `Allowance` | 19 | `BR-CL-19` | ``TradeAllowanceCharge.reason_code`` when ``indicator is False`` |
| `UNTDID7161ChargeReasonCode` (new) | `Charge` | 178 | `BR-CL-20` | ``TradeAllowanceCharge.reason_code`` when ``indicator is True`` |
| `MIME` (existing) | `MIME` | 6 | `BR-CL-24` | ``AttachmentBinaryObject.mime_code`` |
| `Country` (new) | `Country` | 251 | `BR-CL-14/15` | ``PostalTradeAddress.country_id`` (BT-40 / BT-55 / BT-80), ``OriginCountry.id`` (BT-159) |
| `Currency` (new) | `Currency` | 179 | `BR-CL-03/04/05` | ``TradeSettlement.currency_code`` (BT-5), ``TradeSettlement.tax_currency_code`` (BT-6), every ``Element.currency`` shadow |
| `ICDSchemeID` (new) | `ICD` | 239 | `BR-CL-10/11/21` | ``GlobalID.scheme_id`` (BT-29-0, BT-46-0, BT-60-0, BT-71-0, BT-157-1) |
| `UNTDID7143ItemClassSchemeID` (new) | `Item` | 185 | `BR-CL-13` | ``ProductClassification.list_id`` (BT-158-1) — blocked by §3.1 |
| `VATEXCode` (new) | `VATEX` | 88 | `BR-CL-22` | ``ApplicableTradeTax.exemption_reason_code`` (BT-121) |
| `EASCode` (new) | `EAS` | 98 | `BR-CL-25` | ``URIUniversalCommunication.scheme_id`` (BT-34-1 / BT-49-1) |
| `UnitCode` (new) | `Unit` | 2162 | `BR-CL-23` | ``Quantity.unit_code`` (BT-130 / BT-150) |

Reason-code multiplexing for ``TradeAllowanceCharge``: type the
``reason_code`` field as
``UNTDID5189AllowanceReasonCode | UNTDID7161ChargeReasonCode | None``
and cross-check against ``self.indicator`` in ``__post_init__``.

Pipeline for sourcing the enum members:

1. Add ``tools/extract_codelists.py``. Reads the
   ``EN16931 code lists v16`` XLSX and emits Python source into
   ``src/carthorse/schema/types.py`` between explicit
   ``# AUTOGEN START <name>`` / ``# AUTOGEN END <name>`` markers.
2. CI step re-runs the extraction and asserts the AUTOGEN regions
   are unchanged.
3. Member naming maps the spec column headers: ``Currency.EUR`` ⇒
   ``"EUR"`` from the ``Alphabetic Code`` column. Where the XLSX gives
   only a numeric code with no speakable name (e.g. UNTDID 1153 /
   4451 / 7161), fall back to ``CODE_<value>`` with the spec name as
   the docstring.

``UnitCode`` at 2162 members is the only enum that materially
inflates ``types.py``. Optional split: move it to
``src/carthorse/schema/codelists/unit.py`` if reviewer prefers
smaller files.

Note: enum-based enforcement is *stricter* than what the XSD itself
checks — the XSD types these fields as plain ``xs:token``. That
matches the spec: ``BR-CL-*`` is the layer that closes the gap.
Callers may still pass strings — ``StrEnum(value)`` accepts the
underlying string — but type checkers will require the enum form for
new code.


## 5. Tests and regression gates

* **Samples** — ``tests/samples/`` ships 11 EN16931 fixtures
  (``EN16931_*.cii.xml`` + 6 ``EN16931_zf24_*``). All currently pass
  the XSD-validity and round-trip gates. As the structural gaps in §3
  close, the round-trip should remain green; the new fields are
  populated where the fixtures carry them.

* **Hypothesis strategy** — ``tests/strategies.py`` (657 lines) builds
  invoices per profile via ``invoices_for(profile)``. Each structural
  item in §3 needs an additive change there:
  * §3.1 BG-32/33/34 — extend the ``TradeProduct`` strategy with
    optional ``characteristics`` / ``classifications`` / ``origin_country``;
  * §3.2 line refs — extend ``LineTradeAgreement`` /
    ``LineTradeSettlement`` strategies;
  * §3.3 payment-means detail — extend the ``PaymentMeans`` strategy.

* **Round-trip gate** — ``tests/test_hypothesis.py``:
  * ``test_generated_xml_is_xsd_valid`` runs the Hypothesis strategy
    output through the EN 16931 XSD. New fields must keep this green.
  * ``test_parse_and_regenerate`` round-trips strategy output. New
    fields must round-trip with no loss.

  Neither test currently uses ``xfail`` — failures from new fields
  surface as outright test failures, which is fine.

* **Validator gate** — new ``rules/`` modules pick up
  ``Trade.validate()`` automatically; the COMFORT samples must
  produce ``[]`` errors at profile ``COMFORT``.

* **Coverage** — ``make tests`` enforces 90 % line coverage. Each new
  validator needs at least one positive and one negative test under
  ``tests/test_*.py``.


## 6. Verification recipe

```bash
# Quick checks during development
uv run pytest tests/test_xml_tags.py
uv run pytest tests/test_samples.py -k EN16931
uv run pytest tests/test_hypothesis.py -k EN16931

# Full gate
make check       # ruff + basedpyright
make tests       # pytest + 90 % coverage

# Manual COMFORT round-trip spot-check
uv run python tools/comfort_smoke.py tests/samples/EN16931_Einfach.cii.xml
# Must print: structural parity ✓; round-trip ✓; XSD valid ✓; 0 ValidationErrors
```

``tools/comfort_smoke.py`` is part of the work — small script that
loads every ``tests/samples/EN16931_*.xml``, round-trips through
``Document.from_xml → to_xml().render() → from_xml`` and runs
``doc.validate()``, reporting per-sample pass/fail.


## 7. Suggested implementation order

1. §3.4 profile-gating cleanup on ``TradeAllowanceCharge`` (smallest;
   prevents wrong-profile rendering during the next steps).
2. §3.1 BG-32 / BG-33 / BG-34 product groups — unblocks `BR-54`,
   `BR-65`, `BR-CL-13`.
3. §3.2 line-level references (BT-132 / BT-128 / BT-133).
4. §3.3 header payment-means detail (BT-82 / BG-18 / BT-85 / BT-86) —
   unblocks `BR-51`, `BR-CL-25`.
5. §4.1 + §4.2 — wire the named rules and the document/line
   reason-code coherence rules.
6. §4.3 + §4.4 — `BR-48`, `BR-61..63`, plus the per-VAT-category
   table.
7. §4.5 `BR-DEC-*` — single factory, ~21 wire-ups.
8. §4.6 `BR-CL-*` — vendor the code lists, single factory, ~24
   wire-ups. Largest piece by data volume; defer last because it has
   the most churn and the least code complexity.
9. §5 tests — extend ``strategies.py`` after each structural
   addition; add ``tools/comfort_smoke.py``.


## 8. Out of scope (link out)

* **EXTENDED CIUS overlay** — ``BG-X-*``, ``BT-X-*``,
  ``BR-FXEXT-*``, ``BR-FX-DE-*``. See
  ``docs/IMPLEMENTATION_PLAN.md §EXTENDED`` and ``§5``.
* **PDF/A-3 packaging** — delegated to ``factur-x`` on PyPI; covered
  in ``README.md``.
* **Schematron-driven rule generation** — covered as a future track
  in ``docs/IMPLEMENTATION_PLAN.md §5``; would supersede the manual
  ``rules/`` layer but is orthogonal to COMFORT parity.
* **`BR-CL-26`** delivery-location scheme id — the field is only
  modelled at EXTENDED; flagged for the EXTENDED tracker.
