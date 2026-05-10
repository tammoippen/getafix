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
| `BASIC_Factur-X_basic.xml` | BASIC | [ZUGFeRD/mustangproject `cii/Factur-X_basic.xml`](https://github.com/ZUGFeRD/mustangproject/blob/master/library/src/test/resources/cii/Factur-X_basic.xml) |
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

The BASIC_WL profile is currently **not represented**. Public BASIC_WL XML
samples are scarce (BASIC_WL is mostly a "without lines" subset of BASIC).
If/when one is found, drop it in here as `BASICWL_<name>.xml` and add a row
above.

## Where the samples come from upstream

* [ZUGFeRD/mustangproject](https://github.com/ZUGFeRD/mustangproject) — the
  reference Java implementation. Its `library/src/test/resources/` tree
  contains hand-curated Factur-X / ZUGFeRD CII XMLs, used by Mustang's own
  validation tests, so they are known-conformant.
* [ZUGFeRD/corpus](https://github.com/ZUGFeRD/corpus) — a community-curated
  collection of real and synthetic invoices in CII, UBL and Factur-X formats.
  We pull from `XML-Rechnung/CII/` which holds the FeRD "Infopaket" reference
  invoices extracted to plain CII XML.
