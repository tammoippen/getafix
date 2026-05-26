# EXTENDED (Factur-X 1.08 CIUS) parity checklist

Tracking surface for the work to bring `carthorse` to full **EXTENDED**
(= Factur-X CIUS = URN
``urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended``)
conformance — structures *and* business rules.

This file is the operational complement to:

* ``docs/PROFILES/COMFORT.md`` — the EN 16931 baseline; everything here
  builds on it.
* ``docs/STRUCTURES.md`` — field narrative and per-profile surface.
* ``docs/VALIDATION.md`` — rule narrative.

Source of truth: ``ZF24_EN/Schema/4_Factur-X_1.08_EXTENDED/``
(``FACTUR-X_EXTENDED.xsd``, ``FACTUR-X_EXTENDED.sch``), the EXTENDED
technical appendix
(``ZF24_EN/Documentation/7_Factur-X_1.08_ZUGFeRD_2.4_technical_appendix_profile_EXTENDED.pdf``),
and the canonical rulebook
``ZF24_EN/Documentation/1_FACTUR-X 1.08 - 2025 12 04 - EN FR - VF.xlsx``
(sheet ``Business Rules``). When the ``.sch`` text and the XLSX
disagree, the XLSX wins — the ``.sch`` carries a couple of
copy-paste artefacts (the ``BR-FXEXT-BR-*`` double-prefix, a stray
"Zero rated" qualifier on CO-10/12/13 text). The whole ``ZF24_EN/``
tree lives on the ``docs`` branch, not on ``main`` — fetch it
separately (``git worktree add /tmp/carthorse-docs origin/docs``).


## 1. Scope, in numbers

| Aspect | EN16931 | EXTENDED | Delta |
|---|---:|---:|---:|
| Distinct ``<xs:element>`` in the BAE XSD | 122 | 191 | **+69** EXTENDED-only |
| Schematron ``<assert>`` rules | 428 | 901 | **+473** |
| Unique ``BR-*`` rule codes | 178 | 194 | **+28** ``BR-FXEXT-*`` asserted in the ``.sch`` (plus **+6** XLSX-only ``BR-FXEXT-05/07/09/10/12/24`` — see §5.1 / §5.4); **−7** ``BR-CO-*`` replaced; 6 dropped at EXTENDED, 1 (``BR-CO-17``) removed entirely |
| Per-VAT-category families touched | 9 | 9 | tolerance-banded variants only |

EXTENDED adds **no new ``BR-DEC-*`` rule** (still 21) and **no new
``BR-CL-*`` rule** beyond what COMFORT already enforces. The growth is
all new structures plus the ``BR-FXEXT-*`` family.


## 2. Already landed — anchor for the open list

These items are done; flagged here so the open list isn't misread as
the whole EXTENDED problem.

| Field / group | Source | Status |
|---|---|---|
| BT-X-2 ``TestIndicator`` on ``ExchangedDocumentContext`` | ``schema/document.py:108`` | ✓ |
| BT-X-3 ``BusinessProcessSpecifiedDocumentContextParameter`` | ``schema/document.py`` | ✓ |
| BT-X-4 ``LanguageID``, BT-X-5 ``ContentCode`` on ``IncludedNote`` | ``schema/document.py:135,251`` | ✓ |
| BT-X-6 ``EffectiveSpecifiedPeriod.CompleteDateTime`` | ``schema/document.py:174,177`` | ✓ |
| BT-X-1 ``CopyIndicator`` | ``schema/document.py:243`` | ✓ |
| BG-X-18 ``ProductEndUserTradeParty`` (BT-X-144 etc.) | ``schema/party.py:633`` | ✓ |
| BG-X-30 ``ShipFromTradeParty`` | ``schema/party.py:723`` | ✓ |
| BG-X-27 ``UltimateShipToTradeParty`` | ``schema/party.py:664`` | ✓ |
| BG-X-23 ``UltimateCustomerOrderReferencedDocument`` | ``schema/references.py:102`` | ✓ |
| BT-X-202-00 ``DeliveryNoteReferencedDocument`` | ``schema/references.py:325`` | ✓ |
| BG-X-24 ``RelatedSupplyChainConsignment`` | ``schema/delivery.py`` | ✓ |
| ``SpecifiedLogisticsTransportMovement`` (``ModeCode``) | ``schema/delivery.py`` | ✓ |
| Seller / Buyer ``FaxUniversalCommunication`` | ``schema/party.py:282`` | ✓ |

That covers **15 of 69** EXTENDED-only XSD elements. The remaining 54
fall into the buckets in §4 below.


## 3. Prep work (lands before any new BT-X-* or BR-FXEXT-*)

Two small plumbing items unblock everything else. Neither needs a new
dispatch mechanism — both reuse hooks that already exist.

### 3.1 Profile-aware rule short-circuits using the existing ``profile`` parameter

Every ``Validator`` already receives ``(self, profile)``. EXTENDED
replaces seven EN 16931 identities with tolerance-banded variants
(``BR-CO-4/10/11/12/13/15``) and **removes ``BR-CO-17`` entirely** in
favour of nine per-category variants. The plumbing for that is:

* in the **EN 16931 rule** that gets replaced (e.g.
  ``rules/trade.py::br_co_13``), add ``if profile >= Profile.EXTENDED:
  return []`` at the top so it stays silent on EXTENDED documents.
* in the **EXTENDED variant** (new ``rules/extended.py::br_fxext_co_13``),
  guard with ``if profile < Profile.EXTENDED: return []`` so it stays
  silent below.
* register both on the same element's ``_validators`` tuple. The
  ``Element.validate_internal`` walker calls each with the current
  profile; the guards do the right-vs-wrong-profile filtering.

This keeps the existing two-step (``_validators`` + per-rule
``profile`` argument) intact — no new dispatch hook, no metaclass
magic. The pattern is already used at
``rules/accounting.py:111`` / ``196`` / ``274``.

### 3.2 Generic ``StrEnum`` coercion in ``Element.from_xml``

``_parse_str`` already calls ``curr_type(el.text.strip())`` for any
``str``-typed field (``schema/element.py:401``), so any field annotated
as a ``StrEnum`` subclass already auto-coerces — that's how ``MIME``,
``Country``, ``Currency``, ``UNTDID4461PaymentMeansCode``, etc. work.

Two follow-ups make this fully general for EXTENDED:

* **Attribute reads in custom ``from_xml`` overrides** (``TaxTotal``,
  ``ProductClassification``, ``AttachmentBinaryObject``, ``URIID``, …)
  read code values from an XML attribute rather than element text and
  pass plain ``str`` into the dataclass constructor. Add a small
  helper ``_coerce_enum(value, field_type)`` in ``schema/element.py``
  that inspects the field annotation via ``get_type_hints`` and calls
  ``cls(value)`` if it's a ``StrEnum`` subclass. Custom overrides call
  it on every attribute they read. Single helper, ~10 LOC.
* When a new EXTENDED dataclass needs a custom ``from_xml`` (e.g.
  ``TaxApplicableTradeCurrencyExchange`` reading two currency-code
  attributes), it uses the same helper from the start.

### 3.3 Rename ``BR-IG-*`` / ``BR-IP-*`` → ``BR-AF-*`` / ``BR-AG-*``

The spec — both EN16931 and EXTENDED schematron — uses ``BR-AF-*`` for
the **L** "IGIC" category and ``BR-AG-*`` for the **M** "IPSI"
category. ``rules/trade.py:1018`` currently maps:

```python
_VAT_RULE_PREFIX[CategoryCode.T_L] = "IG"   # carthorse-specific
_VAT_RULE_PREFIX[CategoryCode.T_M] = "IP"   # carthorse-specific
```

Switch to spec naming:

```python
_VAT_RULE_PREFIX[CategoryCode.T_L] = "AF"
_VAT_RULE_PREFIX[CategoryCode.T_M] = "AG"
```

Touches the comments in ``schema/types.py:179-180`` and the literal
assertions in ``tests/test_vat_required_parties.py:207-256`` and
``tests/test_vat_category_rates.py:148,168``. Trivial; lands before the
EXTENDED arithmetic variants so the diff against
``FACTUR-X_EXTENDED.sch`` is meaningful.


## 4. Missing structures

Order matches the BAE XSD ``<xs:sequence>`` so the dataclass field
order doesn't drift. Each block is small; together they're the bulk
of the work.

### 4.1 ``HeaderTradeAgreement`` — agent parties and quotation refs (``schema/agreement.py``)

| BT-X / BG-X | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BG-X-49 | ``SalesAgentTradeParty`` | new ``SalesAgentTradeParty`` in ``schema/party.py``; field on ``TradeAgreement.sales_agent`` | 0..1 | XSD position: after ``SellerTaxRepresentativeTradeParty``. Follows the same shape as ``SellerTaxRepresentativeTradeParty`` (``Name`` + ``PostalTradeAddress`` + ``SpecifiedTaxRegistration``). |
| BG-X-54 | ``BuyerTaxRepresentativeTradeParty`` | new ``BuyerTaxRepresentativeTradeParty`` | 0..1 | XSD position: after ``BuyerTradeParty``. Same shape as seller tax rep. |
| BG-X-62 | ``BuyerAgentTradeParty`` | new ``BuyerAgentTradeParty`` | 0..1 | XSD position: after ``BuyerTaxRepresentativeTradeParty``. |
| BG-X-61 | ``QuotationReferencedDocument`` | new ``QuotationReferencedDocument`` in ``schema/references.py`` carrying ``IssuerAssignedID`` + ``FormattedIssueDateTime`` | 0..1 | XSD position: between ``BuyerOrderReferencedDocument`` and ``ContractReferencedDocument``. |
| BG-X-22 | ``ApplicableTradeDeliveryTerms`` | new ``TradeDeliveryTerms`` in ``schema/agreement.py`` with ``DeliveryTypeCode`` (UNTDID 4053, ``StrEnum``) | 0..1 | XSD position: last child of ``HeaderTradeAgreement``. |
| BT-X-29-1 | Header ``BuyerOrderReferencedDocument`` widening | extend existing ``BuyerOrderReferencedDocument`` (``schema/references.py:51``) with optional ``LineID``, ``FormattedIssueDateTime`` | — | These are EXTENDED-only optional children; gated at the field metadata via ``profile`` key. |

### 4.2 ``HeaderTradeDelivery`` — already 90 % covered

Remaining work is cardinality / metadata:

* ``ShipToTradeParty.id`` becomes ``0..*`` (list) at EXTENDED.
* No new elements.

### 4.3 ``HeaderTradeSettlement`` — the biggest container (``schema/settlement.py``)

| BT-X / BG-X | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BT-X-217 | ``InvoiceIssuerReference`` | new field ``TradeSettlement.invoice_issuer_reference: str \| None`` | 0..1 | XSD position: first child of ``HeaderTradeSettlement``. |
| BG-X-33 | ``InvoicerTradeParty`` | new ``InvoicerTradeParty`` | 0..1 | XSD position: between ``InvoiceIssuerReference`` and ``InvoiceeTradeParty``. |
| BG-X-36 | ``InvoiceeTradeParty`` | new ``InvoiceeTradeParty`` | 0..1 | XSD position: after ``InvoicerTradeParty``. Distinct from ``Buyer`` for factoring / payer-pays-third-party flows. |
| BG-X-73 | ``PayerTradeParty`` | new ``PayerTradeParty`` | 0..1 | XSD position: between ``PayeeTradeParty`` and ``TaxApplicableTradeCurrencyExchange``. |
| BG-X-41 | ``TaxApplicableTradeCurrencyExchange`` | new ``TaxCurrencyExchange`` with ``SourceCurrencyCode`` + ``TargetCurrencyCode`` (both ``Currency`` enum) + ``ConversionRate: Decimal`` + ``ConversionRateDateTime: date \| None`` | 0..1 | XSD position: after ``PayerTradeParty``, before ``ApplicableTradeTax``. Drives BT-X-260..264. |
| BG-X-42 | ``SpecifiedLogisticsServiceCharge`` | new ``LogisticsServiceCharge`` with ``Description``, ``AppliedAmount`` (BT-X-272), ``AppliedTradeTax`` (mini ``ApplicableTradeTax``: ``TypeCode``, ``CategoryCode``, ``RateApplicablePercent``) | 0..* | XSD position: after ``BillingSpecifiedPeriod``, before ``SpecifiedTradeAllowanceCharge``. **This is the element behind the BR-CO-12/13 false-positive on ``tests/samples/EXTENDED_factur-x-extended.xml``.** Its ``AppliedAmount`` must flow into every charge-sum accumulator (``BR-FXEXT-CO-12/13/15`` and every ``BR-FXEXT-{cat}-08``). |
| BG-X-43 | ``ApplicableTradePaymentPenaltyTerms`` | new ``PaymentPenaltyTerms`` with ``BasisDateTime``, ``BasisPeriodMeasure``, ``BasisAmount``, ``CalculationPercent``, ``ActualPenaltyAmount`` | 0..1 | Nested on ``PaymentTerms``. |
| BG-X-44 | ``ApplicableTradePaymentDiscountTerms`` | new ``PaymentDiscountTerms`` with the same shape but ``ActualDiscountAmount`` | 0..1 | Nested on ``PaymentTerms``. |
| BG-X-45 / BG-X-46 | ``SpecifiedAdvancePayment`` + nested ``IncludedTradeTax`` | new ``AdvancePayment`` with ``PaidAmount``, ``FormattedReceivedDateTime``, list of ``IncludedTradeTax`` (``TypeCode``, ``CategoryCode``, ``RateApplicablePercent``, ``CalculatedAmount``) | 0..* | XSD position: after ``SpecifiedTradeSettlementHeaderMonetarySummation``. |
| — | ``SpecifiedTradePaymentTerms`` cardinality | widen ``TradeSettlement.terms`` from ``PaymentTerms \| None`` to ``list[PaymentTerms] \| None`` at EXTENDED; add optional per-term ``PayeeTradeParty`` and ``PartialPaymentAmount`` | 0..* | The list widening is the breaking part — handle via context-aware ``_field_profile`` like ``TradeAllowanceCharge``. |
| BT-X-273 | ``MonetarySummation.TotalAllowanceChargeAmount`` | new field ``MonetarySummation.total_allowance_charge_amount: Decimal \| None`` | 0..1 | XSD position: after ``TaxTotal``, before ``RoundingAmount``. |

### 4.4 ``ApplicableTradeTax`` extensions (header VAT breakdown)

| BT-X | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BT-X-262 | ``LineTotalBasisAmount`` | new field ``ApplicableTradeTax.line_total_basis_amount: Decimal \| None`` | 0..1 | EXTENDED-only enrichment of BG-23. |
| BT-X-263 | ``AllowanceChargeBasisAmount`` | new field ``ApplicableTradeTax.allowance_charge_basis_amount: Decimal \| None`` | 0..1 | Same. |

### 4.5 ``IncludedSupplyChainTradeLineItem`` — sub-invoice-line semantics (``schema/line.py``, ``schema/trade.py``)

The deepest change. EXTENDED lets a line be a *category header*
(``GROUP``), a *regular detail line* (``DETAIL``), or an *informational
note* (``INFORMATION``), and lets lines reference a parent.

| BT-X / BG-X | Name | Target | Card. | Notes |
|---|---|---|---|---|
| BT-X-7 | ``LineStatusCode`` on ``DocumentLineDocument`` | new field ``DocumentLineDocument.status_code: LineStatusCode \| None`` | 0..1 | UNTDID-derived ``StrEnum`` (``DETAIL``/``GROUP``/``INFORMATION``). |
| BT-X-8 | ``LineStatusReasonCode`` | new field ``DocumentLineDocument.status_reason_code: LineStatusReasonCode \| None`` | 0..1 | Same enum (subtype). Drives **every** ``BR-FXEXT-2x`` and ``BR-FXEXT-CO-04`` qualification. |
| BT-X-304 | ``ParentLineID`` | new field ``DocumentLineDocument.parent_line_id: str \| None`` | 0..1 | References another line's ``LineID`` (BT-126). |
| — | ``SequenceNumeric`` | new field on ``TradeLineItem`` | 0..1 | Display ordering hint. |
| BG-X-1 | ``IncludedReferencedProduct`` | recursive ``IncludedReferencedProduct`` on ``TradeProduct`` | 0..* | Sub-products inside a bundle. |
| BG-X-84 | ``IndividualTradeProductInstance`` | new ``IndividualTradeProductInstance`` with ``BatchID`` (BT-X-310) + ``SupplierAssignedSerialID`` (BT-X-311) | 0..* | Per-unit serial / batch tracking. |
| BG-X-90 | ``ItemSellerTradeParty`` | new field ``TradeProduct.item_seller: ItemSellerTradeParty \| None`` | 0..1 | Per-line deviating Seller. |
| BT-X-21..28 | ``ModelID``, ``ModelName``, ``BrandName``, ``ClassName``, ``IndustryAssignedID``, ``ValueMeasure`` | flat optional fields on ``TradeProduct`` | 0..1 each | Product detail leaves. |
| BG-X-7 / BG-X-10 | Line-level ``ShipToTradeParty`` / ``UltimateShipToTradeParty`` | new fields on ``LineTradeDelivery`` | 0..1 | Separate from the header-level parties. |
| — | ``ChargeFreeQuantity``, ``PackageQuantity``, ``PerPackageUnitQuantity``, ``UnitQuantity`` | new optional fields on ``LineTradeDelivery`` | 0..1 each | Per-line quantity refinements. |


## 5. Missing business rules

28 net-new ``BR-FXEXT-*`` ids asserted in
``FACTUR-X_EXTENDED.sch``, plus 6 more documented in the canonical
XLSX rulebook (``BR-FXEXT-05/07/09/10/12/24``) that the ``.sch``
doesn't enforce — listed alongside the .sch-asserted rules in §5.1
and §5.4 below, marked **(XLSX-only)**. Most of the XLSX-only entries
are realised implicitly (the DETAIL-or-unset qualifier on §5.4 rules,
the XSD codelist on BT-X-8) and don't need a separate ``_err`` emit;
the table flags the ones that do. The substitutions are mechanical;
the hard part is the cross-line walker needed for sub-invoice-line
arithmetic.

### 5.1 ``BR-FXEXT-*`` standalone (7 .sch-asserted + 5 XLSX-only) — ``rules/extended.py``

| Code | What it checks | Field(s) |
|---|---|---|
| ``BR-FXEXT-01`` | If BT-21 ``SubjectCode`` set ⇒ BT-X-5 ``ContentCode`` or BT-22 ``Content`` (or both, same meaning). | ``IncludedNote`` |
| ``BR-FXEXT-02`` | Same coupling on line-level note (BT-X-10 / BT-X-9 / BT-127). | ``LineIncludedNote`` |
| ``BR-FXEXT-03`` | Only a VAT-registration id (``schemeID="VA"``) — not FC — may appear on every BT-X-* party (line ship-to, sales agent, buyer tax rep, product end user, buyer agent, header ship-to, ship-from, invoicer, invoicee, document payee, payer, term-specific payee). | every new party |
| ``BR-FXEXT-04`` | BT-X-18 ``IndustryAssignedID`` codelist (UNTDED 6313 + Factur-X extension). | ``TradeProduct.industry_assigned_id`` |
| ``BR-FXEXT-05`` *(XLSX-only)* | BT-X-8 value must come from the Line Status Reason codelist. | enforced implicitly by the ``LineStatusReasonCode`` ``StrEnum`` from §5.6 — no separate ``_err`` emit. |
| ``BR-FXEXT-06`` | BT-X-8 must be set when the line has a ``ParentLineID`` (BT-X-304) **or** is referenced as parent by another line. | cross-line walker on ``Trade`` |
| ``BR-FXEXT-07`` *(XLSX-only)* | If BT-X-8 = ``GROUP`` ⇒ BT-129 / BT-130 / BT-131 / BT-146 and BG-30 become optional. | realised as the DETAIL-or-unset qualifier on the §5.4 rules and on ``BR-FXEXT-CO-04`` — no separate emit. |
| ``BR-FXEXT-08`` | If BT-X-8 = ``GROUP`` and BT-131 set ⇒ BT-131 equals the sum of all child lines' BT-131 (recursive over the ``ParentLineID`` tree, excluding ``INFORMATION``). | ``Trade._validate_subinvoice_line_sums`` |
| ``BR-FXEXT-09`` *(XLSX-only)* | If BT-X-8 = ``INFORMATION`` ⇒ same fields as ``BR-FXEXT-07`` become optional. | same as ``BR-FXEXT-07`` — covered by the DETAIL-or-unset qualifier. |
| ``BR-FXEXT-10`` *(XLSX-only)* | ``BG-X-1 IncludedReferencedProduct`` (nested sub-products inside a bundle) is excluded from the invoice calculation. | constrains the cross-line walker's sum accumulation; no emitted rule. |
| ``BR-FXEXT-11`` | Every ``ParentLineID`` resolves to an existing line's ``LineID`` (BT-126). | cross-line walker on ``Trade`` |
| ``BR-FXEXT-12`` *(XLSX-only)* | If a ``GROUP`` line carries BT-131, every nested ``GROUP`` child line must also carry BT-131. | companion to ``BR-FXEXT-08`` in ``Trade._validate_subinvoice_line_sums``; emits its own ``_err``. |

### 5.2 ``BR-FXEXT-CO-*`` arithmetic-with-tolerance (6 rules) — ``rules/extended.py``

Each replaces an EN 16931 identity with ``|diff| ≤ 0.01 × N`` slack;
the tolerance count ``N`` is rule-specific (see per-row formulas
below — most use ``#BT-131 + #BT-92 + #BT-99 + #BT-X-272``, but
``BR-FXEXT-CO-10/11/13`` use narrower counts). Lines whose ``BT-X-8``
is ``GROUP`` or ``INFORMATION`` are excluded from every ``Σ BT-131``
(per the rule text).

| Code | Replaces | Notes |
|---|---|---|
| ``BR-FXEXT-CO-04`` | ``BR-CO-4`` | BT-151 required only when BT-X-8 is ``DETAIL`` or unset. |
| ``BR-FXEXT-CO-10`` | ``BR-CO-10`` | ``\|BT-106 − Σ BT-131\| ≤ 0.01 × #BT-131``. |
| ``BR-FXEXT-CO-11`` | ``BR-CO-11`` | ``\|BT-107 − Σ BT-92\| ≤ 0.01 × #BT-92``. |
| ``BR-FXEXT-CO-12`` | ``BR-CO-12`` | ``\|BT-108 − (Σ BT-99 + Σ BT-X-272)\| ≤ 0.01 × (#BT-99 + #BT-X-272)``. |
| ``BR-FXEXT-CO-13`` | ``BR-CO-13`` | ``\|BT-109 − Σ BT-131 + Σ BT-92 − Σ BT-99\| ≤ 0.01 × (#BT-131 + #BT-92 + #BT-99)``. **No** ``Σ BT-X-272`` on either side — confirmed against both the XLSX rulebook and the ``.sch``; logistics charges already flow into BT-108 and are checked by ``BR-FXEXT-CO-12``. |
| ``BR-FXEXT-CO-15`` | ``BR-CO-15`` | ``\|BT-112 − BT-109 − BT-110\| ≤ 0.01 × (#BT-131 + #BT-92 + #BT-99 + #BT-X-272)``. |

Each EN16931 rule short-circuits at ``profile >= Profile.EXTENDED``;
each EXTENDED variant short-circuits at ``profile <
Profile.EXTENDED`` (see §3.1).

### 5.3 Per-VAT-category arithmetic-with-tolerance (9 rules) — ``rules/extended.py``

| Code | Replaces (or supplements) | Category |
|---|---|---|
| ``BR-FXEXT-S-08`` / ``BR-FXEXT-S-09`` | ``BR-CO-17`` (S) | Standard rated |
| ``BR-FXEXT-Z-08`` | ``BR-CO-17`` (Z) | Zero rated |
| ``BR-FXEXT-E-08`` | ``BR-CO-17`` (E) | Exempt |
| ``BR-FXEXT-AE-08`` | ``BR-CO-17`` (AE) | Reverse charge |
| ``BR-FXEXT-G-08`` | ``BR-CO-17`` (G) | Export |
| ``BR-FXEXT-IC-08`` | ``BR-CO-17`` (IC ↔ ``K``) | Intra-community |
| ``BR-FXEXT-AF-08`` | new at EXTENDED | IGIC (``L``) |
| ``BR-FXEXT-AG-08`` | new at EXTENDED | IPSI (``M``) |
| ``BR-FXEXT-O-08`` | ``BR-CO-17`` (O) | Not subject to VAT |

Shape per category: ``|BT-116 − (Σ BT-131 − Σ BT-92 + Σ BT-99 +
Σ BT-X-272)| ≤ 0.01 × N`` restricted to the rows that carry that
category and rate. All nine route through one helper that takes the
category predicate, mirroring the ``vat_category_rates`` dispatcher at
``rules/trade.py:1096``.

``BR-CO-17`` itself is **removed at EXTENDED** — the EN16931
implementation short-circuits as in §3.1.

### 5.4 Subtype-qualified line rules (4 .sch-asserted + 1 XLSX-only) — ``rules/extended.py``

EN16931 ``BR-22`` / ``BR-23`` / ``BR-24`` / ``BR-26`` / ``BR-27``
require BT-129 / BT-130 / BT-131 / BT-146 / BT-146≥0 on every BG-25
line. The EXTENDED variants gate each on the line's BT-X-8 subtype —
``GROUP`` and ``INFORMATION`` lines are exempt. (EN16931 ``BR-21``
"Invoice line identifier" and ``BR-25`` "Item name" remain unchanged
at EXTENDED.)

The ``.sch`` spells these IDs with a double ``BR-FXEXT-BR-`` prefix
(``[BR-FXEXT-BR-22]`` etc.) — treat that as a copy-paste artefact in
the schematron; the canonical XLSX rulebook uses ``BR-FXEXT-22``,
``BR-FXEXT-23``, ``BR-FXEXT-26``, ``BR-FXEXT-27`` (single prefix). The
implementation follows the XLSX; any ``.sch`` round-trip diff in §7
step 2 has to normalize the extra ``BR-`` away.

| Code | Replaces | Qualifier |
|---|---|---|
| ``BR-FXEXT-22`` | ``BR-22`` (BT-129 invoiced quantity) | only when BT-X-8 is ``DETAIL`` or unset |
| ``BR-FXEXT-23`` | ``BR-23`` (BT-130 unit of measure) | same |
| ``BR-FXEXT-24`` *(XLSX-only)* | ``BR-24`` (BT-131 invoice line net amount) | same — not asserted in ``FACTUR-X_EXTENDED.sch`` but enforced per the XLSX |
| ``BR-FXEXT-26`` | ``BR-26`` (BT-146 item net price) | same |
| ``BR-FXEXT-27`` | ``BR-27`` (BT-146 ≥ 0) | additionally: if BT-146 is omitted, no check. |

### 5.5 Date format extension — ``schema/element.py``

| Code | What it checks |
|---|---|
| ``BR-FXEXT-CII-DT-097a`` | ``<…DateTimeString format="205">`` must match ``YYYYMMDDHHMMSS`` (14 digits). |

One extra branch in the date renderer/parser; pairs with
``CompleteDateTime`` (BT-X-6) already modelled.

### 5.6 Codelist tightenings (``schema/types.py`` + ``tools/extract_codelists.py``)

| New ``StrEnum`` | Source | Used by |
|---|---|---|
| ``LineStatusReasonCode`` | hard-coded (3 members: ``DETAIL``, ``GROUP``, ``INFORMATION``) | BT-X-8 |
| ``LineStatusCode`` | UNTDID 1229 subset | BT-X-7 |
| ``DeliveryTypeCode`` | UNTDID 4053 subset | BG-X-22 |
| ``RoleCode`` | UNTDID 3035 subset | BG-X-4 logistics role |
| ``UNTDED6313IndustryClassCode`` | UNTDED 6313 + Factur-X extension | BT-X-18 / BR-FXEXT-04 |


## 6. CLI surfacing — ``src/carthorse/report.py``

Three additive panels matching the COMFORT enrichments already shipped:

1. **Logistics charges panel** — sibling to the document-level
   allowance/charge table; one row per ``SpecifiedLogisticsServiceCharge``
   (description, applied amount, VAT category + rate).
2. **Advance payments panel** — one row per ``SpecifiedAdvancePayment``
   (received date, paid amount, included tax breakdown).
3. **Line subtype rendering** — show BT-X-7 status (``DETAIL`` /
   ``GROUP`` / ``INFORMATION``) next to the line number in
   ``_lines_table``; indent child lines under their ``ParentLineID``
   for the ``GROUP`` hierarchy.

All three are guarded so BASIC / COMFORT documents print unchanged.


## 7. Suggested ordering

Each bullet is one PR-sized commit; the largest is the sub-invoice-line
piece in §4.5 / §5.1.

1. **§3.1 + §3.2 + §3.3 prep work** — profile short-circuits in the
   handful of EN16931 rules that get replaced, the ``_coerce_enum``
   helper in ``element.py``, and the BR-IG → BR-AF / BR-IP → BR-AG
   rename. Single commit, ~80 LOC + test rewrites.
2. **EXTENDED schematron round-trip fixture** — copy
   ``FACTUR-X_EXTENDED.sch`` into ``tests/schemas/``, add a test that
   runs every ``tests/samples/EXTENDED_*.xml`` through
   ``lxml.isoschematron`` and asserts carthorse's emitted error-code
   set equals the schematron's. Single source of truth for "what's
   left".
3. **§4.3 ``SpecifiedLogisticsServiceCharge`` alone** — unblocks the
   BR-CO-12/13 false-positive the user already hit. Smallest possible
   first vertical slice through new structure + new accumulator wiring.
4. **§5.2 + §5.3 (the tolerance variants and per-category replacements)**
   — every existing arithmetic identity gets its EXTENDED partner.
   Routed through the dispatcher at ``rules/trade.py:1096``.
5. **§4.5 + §5.1 + §5.4 sub-invoice-line semantics** — biggest single
   commit (~600 LOC). BT-X-7/-8/-304 fields, the cross-line walker on
   ``Trade``, the §5.1 ``BR-FXEXT-0x`` rules (7 .sch-asserted +
   ``BR-FXEXT-12`` companion to ``-08``), the five ``BR-FXEXT-2x``
   qualifications (incl. XLSX-only ``BR-FXEXT-24``). Needs a real
   sample (pull a sub-invoice-line example from
   ``ZF24_EN/Examples/4. EXTENDED`` on the ``docs`` branch into
   ``tests/samples/`` first — ``SubInvoiceLines Hardware Bsp 2`` is
   the cleanest single-feature pick; ``Abschlagsrechnung
   SubInvoiceLine Bsp 1`` combines sub-invoice-lines with advance
   payments and exercises two §4.3 pieces in one fixture).
6. **§4.3 remainder** — ``TaxApplicableTradeCurrencyExchange``,
   ``ApplicableTradePaymentPenaltyTerms`` /
   ``ApplicableTradePaymentDiscountTerms``, ``SpecifiedAdvancePayment``,
   widening ``terms`` to ``list``, ``TotalAllowanceChargeAmount``. One
   commit per group.
7. **§4.1 agent parties** — sales agent, buyer tax rep, buyer agent,
   quotation ref, delivery terms. One commit.
8. **§4.5 product enrichments** — ``IncludedReferencedProduct``,
   ``IndividualTradeProductInstance``, ``ItemSellerTradeParty``, leaf
   attributes. One commit.
9. **§4.4 + §5.5 VAT breakdown extras and date format** — small,
   landed last.
10. **§6 CLI** — opportunistic alongside the structure commits.

After step 5 the test loop is meaningful: any EXTENDED sample under
``tests/samples/EXTENDED_*.xml`` round-trips with no schematron
divergence. Steps 6-10 are mostly bookkeeping.
