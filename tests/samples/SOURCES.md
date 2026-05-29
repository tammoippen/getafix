# Test sample provenance

The XML files in this directory are real-world Cross-Industry-Invoice (CII) /
Factur-X documents drawn from two upstream collections. They are vendored here
unmodified so the parser can be exercised against authentic specimens — the
files round-trip through validators run by the upstream maintainers, so any
parse failure points to a gap on **our** side, not the sample.

Both upstream projects are licensed under **Apache License 2.0**, which is
compatible with redistribution as long as attribution is preserved (this file).

## Sources

| File | Profile | Upstream |
|------|---------|----------|
| `MINIMUM_facturFrMinimum.xml` | MINIMUM | [ZUGFeRD/mustangproject `cii/facturFrMinimum.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/cii/facturFrMinimum.xml) |
| `MINIMUM_zf24_Rechnung.xml` | MINIMUM | ZF24 distribution `Examples/0. MINIMUM/MINIMUM_Rechnung` (commercial invoice, TypeCode=380; FeRD specification) |
| `MINIMUM_zf24_Buchungshilfe.xml` | MINIMUM | ZF24 distribution `Examples/0. MINIMUM/MINIMUM_Buchungshilfe` (accounting voucher, TypeCode=751; FeRD specification) |
| `BASICWL_zf24_Einfach.xml` | BASIC_WL | ZF24 distribution `Examples/1. BASIC WL/BASIC-WL_Einfach` (simple invoice; FeRD specification) |
| `BASICWL_zf24_Buchungshilfe.xml` | BASIC_WL | ZF24 distribution `Examples/1. BASIC WL/BASIC-WL_Buchungshilfe` (accounting voucher; FeRD specification) |
| `BASIC_Factur-X_basic.xml` | BASIC | [ZUGFeRD/mustangproject `cii/Factur-X_basic.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/cii/Factur-X_basic.xml) |
| `BASIC_zf24_Einfach.xml` | BASIC | ZF24 distribution `Examples/2. BASIC/BASIC_Einfach` (simple one-line invoice, GS1 GTIN; FeRD specification) |
| `BASIC_zf24_Taxifahrt.xml` | BASIC | ZF24 distribution `Examples/2. BASIC/BASIC_Taxifahrt` (two lines with distinct unit codes H87/KMT; FeRD specification) |
| `BASIC_zf24_Rechnungskorrektur.xml` | BASIC | ZF24 distribution `Examples/2. BASIC/BASIC_Rechnungskorrektur` (corrected invoice, TypeCode=384; FeRD specification) |
| `EN16931_zf24_Rabatte.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Rabatte` (multi-rate VAT, document-level allowance + charge; FeRD specification) |
| `EN16931_zf24_Innergemeinschaftliche.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Innergemeinschaftliche_Lieferungen` (VAT category K intra-community; FeRD specification) |
| `EN16931_zf24_Auslandslieferung.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_steuerbefreite Auslandslieferung` (VAT category E export outside EU; FeRD specification) |
| `EN16931_zf24_Kleinunternehmer.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Kleinunternehmer_ohne_USt_ID` (§19 UStG small business, BT-32 only; FeRD specification) |
| `EN16931_zf24_ElektronischeAdresse.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_ElektronischeAdresse` (BT-34 with GS1 GLN schemeID; FeRD specification) |
| `EN16931_zf24_OEPNV.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_OEPNV` (public transport; exercises empty self-closing elements; FeRD specification) |
| `EN16931_zf24_Teilrechnung1.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_1_Teilrechnung` (1st partial invoice in a sequence; FeRD specification) |
| `EN16931_zf24_Teilrechnung2.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_2_Teilrechnung` (2nd partial invoice referencing the first; FeRD specification) |
| `EN16931_zf24_Betriebskosten.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Betriebskostenabrechnung` (operating-cost settlement; FeRD specification) |
| `EN16931_zf24_Einfach_DueDate.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Einfach_DueDate` (BT-9 payment due date with default-due-date discount terms; FeRD specification) |
| `EN16931_zf24_Einfach_NegativeDue.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Einfach_negativePaymentDue` (negative BT-115 — buyer credit balance; FeRD specification) |
| `EN16931_zf24_Elektron.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Elektron` (file `EN16931_Elektron_Anlage_XML.xml`, electronic-component invoice; FeRD specification) |
| `EN16931_zf24_Haftpflicht.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Haftpflichtversicherung_Versicherungssteuer` (liability insurance with insurance tax / non-VAT TypeCode; FeRD specification) |
| `EN16931_zf24_Kraftfahr.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Kraftfahrversicherung_Bruttopreise` (motor insurance with gross-price line items; FeRD specification) |
| `EN16931_zf24_Miete.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Miete` (rent invoice with billing period BG-14; FeRD specification) |
| `EN16931_zf24_Photovoltaik.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Photovoltaik` (PV plant invoice with §13b reverse-charge AE; FeRD specification) |
| `EN16931_zf24_Physiotherapeut.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Physiotherapeut` (physiotherapist services, tax-exempt under §4 Nr. 14 UStG; FeRD specification) |
| `EN16931_zf24_RechnungsUebertragung.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_RechnungsUebertragung` (invoice transmission scenario; FeRD specification) |
| `EN16931_zf24_Reisekosten.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Reisekostenabrechnung` (travel-expense reimbursement with multiple cost lines; FeRD specification) |
| `EN16931_zf24_Sachversicherung.xml` | COMFORT (EN 16931) | ZF24 distribution `Examples/3. EN16931/EN16931_Sachversicherung_berechneter_Steuersatz` (property insurance with computed tax rate; FeRD specification) |
| `EN16931_factur-x.xml` | COMFORT (EN 16931) | [ZUGFeRD/mustangproject `factur-x.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/factur-x.xml) |
| `EN16931_Einfach.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Einfach.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Einfach.cii.xml) |
| `EN16931_Gutschrift.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Gutschrift.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Gutschrift.cii.xml) |
| `EN16931_Rechnungskorrektur.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Rechnungskorrektur.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Rechnungskorrektur.cii.xml) |
| `EN16931_AbweichenderZahlungsempf.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_AbweichenderZahlungsempf.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_AbweichenderZahlungsempf.cii.xml) |
| `EN16931_SEPA_Prenotification.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_SEPA_Prenotification.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_SEPA_Prenotification.cii.xml) |
| `EXTENDED_factur-x-extended.xml` | EXTENDED | [ZUGFeRD/mustangproject `factur-x-extended.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/factur-x-extended.xml) |
| `EXTENDED_fremdwaehrung.xml` | EXTENDED | [ZUGFeRD/mustangproject `Extended_fremdwaehrung.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/Extended_fremdwaehrung.xml) |
| `EXTENDED_zf24_SubInvoiceLines_Hardware.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/SubInvoiceLines Hardware Bsp 2` (two GROUP lines each with two DETAIL children — exercises BT-X-7/-8/-304 sub-invoice-line semantics + the cross-line walker in §5.1 / §5.4; FeRD specification) |
| `EXTENDED_zf24_Abschlagsrechnung_SubInvoiceLines.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Abschlagsrechnung SubInvoiceLine Bsp 1` (down-payment invoice combined with sub-invoice-line tree + Leistungsverzeichnis reference; FeRD specification) |
| `EXTENDED_zf24_Bau_Schlussrechnung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Bau Teil- & Schlussrechnungen mit Steuerzusammenstellung` final-invoice variant (`Extended_einfach_Bau_Schlussrechnung_mit_Steuer_Zusammenstellung`); FeRD specification |
| `EXTENDED_zf24_Bau_Abschlag1.xml` | EXTENDED | ZF24 distribution same folder, 1st partial-payment variant (`Extended_einfach_Bau__1_Abschlagsrechnung`); FeRD specification |
| `EXTENDED_zf24_Bau_Abschlag2.xml` | EXTENDED | ZF24 distribution same folder, 2nd partial-payment variant (`Extended_einfach_Bau__2_Abschlagsrechnung`); FeRD specification |
| `EXTENDED_zf24_Fremdwaehrung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_Fremdwaehrung` (USD invoice with TaxApplicableTradeCurrencyExchange — distinct from the mustangproject `EXTENDED_fremdwaehrung.xml` which is GBP); FeRD specification |
| `EXTENDED_zf24_InnergemLieferung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_InnergemeinschLieferungMehrereBestellungen` (intra-community supply with multiple referenced purchase orders); FeRD specification |
| `EXTENDED_zf24_Kostenrechnung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_Kostenrechnung` (cost-accounting invoice); FeRD specification |
| `EXTENDED_zf24_Projektabschluss.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_Projektabschlussrechnung` (project completion invoice with cumulated totals); FeRD specification |
| `EXTENDED_zf24_Rechnungskorrektur.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_Rechnungskorrektur` (corrected invoice, TypeCode 384); FeRD specification |
| `EXTENDED_zf24_Warenrechnung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/EXTENDED_Warenrechnung` (goods invoice with full party/ship-to detail); FeRD specification |
| `EXTENDED_zf24_Herkunftsland.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Herkunftsland Zolltarif-Nr_HS_UNSPSC_TST_eClass_STQ` (line products tagged with Zolltarif-Nummer / HS / UNSPSC / TST / eCl@ss / STQ classifications — exercises BG-X-1 / BT-X-21..24 product classification fields); FeRD specification |
| `EXTENDED_zf24_Kleinunternehmer.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Kleinunternehmer ohne USt_ID` (EXTENDED variant of §19 UStG small-business invoice without VAT ID); FeRD specification |
| `EXTENDED_zf24_Maschinen_Serial.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Maschinen Serial-Nr` (machinery line item carrying BT-X-307 serial number via IndividualTradeProductInstance, BG-X-84); FeRD specification |
| `EXTENDED_zf24_Sammelrechnung.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/Sammel_Rechnung_3 Bestellungen` (collective invoice — multiple lines each referencing a different purchase order via per-line BuyerOrderReferencedDocument with IssuerAssignedID + FormattedIssueDateTime); FeRD specification |
| `EXTENDED_zf24_SubInvoiceLines_Buero.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/SubInvoiceLine Büromaterial Bsp 3` (office-supplies sub-invoice-line example); FeRD specification |
| `EXTENDED_zf24_SubInvoiceLines_Fallschutz.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/SubInvoiceLines Fallschutzset Bsp 5` (fall-protection-set bundle as sub-invoice-line tree); FeRD specification |
| `EXTENDED_zf24_SubInvoiceLines_Kaffee.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/SubInvoiceLines_Kaffee_Bundle_Set_Bsp4_fx_validation_report.pdf` folder (coffee bundle/set — GROUP lines that legitimately omit `<ApplicableTradeTax>`, exercising the EXTENDED relaxation in `LineTradeSettlement.applicable_trade_tax`); FeRD specification |
| `EXTENDED_zf24_Steuerfreie_IG.xml` | EXTENDED | ZF24 distribution `Examples/4. EXTENDED/steuerfreie Innergemeinschaftliche Lieferung` (tax-exempt intra-community supply at EXTENDED profile); FeRD specification |

## Synthetic samples (`EXTENDED_synth_*.xml`)

The vendored corpus above does not populate every EXTENDED-only field
carthorse models. The `EXTENDED_synth_*.xml` files fill those gaps: each
is a carthorse-authored canonical invoice that attaches a thematic group
of otherwise-unexercised structures onto the mustangproject
`EXTENDED_factur-x-extended.xml` base (Apache-2.0), generated by
`tools/build_synth_samples.py`. Every file is asserted **XSD-valid**
(`FACTUR-X_EXTENDED.xsd`) and **schematron-clean** (the `tests/_schematron.py`
oracle) at generation time and again in the test suite; the generator and
the committed copies are kept in lock-step by `test_synth_samples_in_sync`
in `tests/test_extended_structures.py`.

| File | Exercises |
|------|-----------|
| `EXTENDED_synth_agent_parties.xml` | §4.1 header agent parties — `SalesAgentTradeParty` (BG-X-49), `BuyerTaxRepresentativeTradeParty` (BG-X-54), `BuyerAgentTradeParty` (BG-X-62) — plus `ApplicableTradeDeliveryTerms` (BG-X-22, `FCA` + `RelevantTradeLocation`) and the header `QuotationReferencedDocument` (BG-X-61) |
| `EXTENDED_synth_settlement_parties.xml` | §4.3 settlement parties + advance payment — `InvoiceIssuerReference` (BT-X-204), `InvoicerTradeParty` (BG-X-33), `InvoiceeTradeParty` (BG-X-36), `PayerTradeParty` (BG-X-73), `SpecifiedAdvancePayment` (BG-X-45/46 + prepayment-invoice ref BG-X-85), and a term-specific `PayeeTradeParty` (BG-X-77) — a factoring + prepayment scenario |

Because they derive from the Apache-2.0 mustangproject base, the synthetic
files inherit that licence. To regenerate after a schema bump or a builder
change: `uv run python tools/build_synth_samples.py` (add `--check` for a
non-mutating CI diff).

## Updating

To refresh, re-download from the URLs above. They are intentionally pinned to
upstream `master` — bump only when something interesting changes.

The `*_zf24_*` files come from the official FeRD ZUGFeRD 2.4 / Factur-X 1.08
distribution; refresh them from the `ZF24_EN/Examples/` directory of the
distribution archive. They have dedicated assertions in
`tests/test_zf24_examples.py` that pin the BT-* / BG-* values each example
was crafted to demonstrate.

## Where the samples come from upstream

* [ZUGFeRD/mustangproject](https://github.com/ZUGFeRD/mustangproject) — the
  reference Java implementation. Its `library/src/test/resources/` tree
  contains hand-curated Factur-X / ZUGFeRD CII XMLs, used by Mustang's own
  validation tests, so they are known-conformant.
* [ZUGFeRD/corpus](https://github.com/ZUGFeRD/corpus) — a community-curated
  collection of real and synthetic invoices in CII, UBL and Factur-X formats.
  We pull from `XML-Rechnung/CII/` which holds the FeRD "Infopaket" reference
  invoices extracted to plain CII XML.
