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
| `EN16931_factur-x.xml` | COMFORT (EN 16931) | [ZUGFeRD/mustangproject `factur-x.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/factur-x.xml) |
| `EN16931_Einfach.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Einfach.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Einfach.cii.xml) |
| `EN16931_Gutschrift.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Gutschrift.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Gutschrift.cii.xml) |
| `EN16931_Rechnungskorrektur.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_Rechnungskorrektur.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_Rechnungskorrektur.cii.xml) |
| `EN16931_AbweichenderZahlungsempf.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_AbweichenderZahlungsempf.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_AbweichenderZahlungsempf.cii.xml) |
| `EN16931_SEPA_Prenotification.cii.xml` | COMFORT (EN 16931) | [ZUGFeRD/corpus `XML-Rechnung/CII/EN16931_SEPA_Prenotification.cii.xml`](https://github.com/ZUGFeRD/corpus/blob/master/XML-Rechnung/CII/EN16931_SEPA_Prenotification.cii.xml) |
| `EXTENDED_factur-x-extended.xml` | EXTENDED | [ZUGFeRD/mustangproject `factur-x-extended.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/factur-x-extended.xml) |
| `EXTENDED_fremdwaehrung.xml` | EXTENDED | [ZUGFeRD/mustangproject `Extended_fremdwaehrung.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/Extended_fremdwaehrung.xml) |

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
