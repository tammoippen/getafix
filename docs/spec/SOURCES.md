# Vendored Factur-X spec workbooks

These two XLSX files are the canonical Factur-X 1.08 / ZUGFeRD 2.4
reference for the business-term and codelist surfaces carthorse models.
The carthorse extractors at ``tools/extract_business_terms.py``,
``tools/extract_business_rules.py`` and ``tools/extract_codelists.py``
read them; the CI ``ids-check`` Makefile target re-generates the JSON
sidecars and verifies every ``BT-``/``BG-``/``BR-`` citation in the
codebase resolves against the canonical lists.

## Files

| File | Sheets used by carthorse |
|---|---|
| ``1_FACTUR-X 1.08 - 2025 12 04 - EN FR - VF.xlsx`` | ``Factur-X CII D22B {MINIMUM,BASIC WL,BASIC,EN16931,EXTENDED}`` (BT/BG cross-reference), ``Business Rules`` (BR-*, BR-CO-*, BR-CL-*, BR-DEC-*, BR-FXEXT-*, per-VAT-category families), ``Business Rules HYBRID`` (BR-HYBRID-*). |
| ``2_EN16931 code lists values v16 - used from 2025-11-15 - Fx 1.08.xlsx`` | ``Currency`` / ``Country`` / ``Payment`` / ``Allowance`` / ``Time`` / ``EAS`` / ``VATEX`` sheets — codelist enumerations vendored into ``StrEnum`` classes via ``tools/extract_codelists.py``. |

## Provenance and license

Both workbooks are published by [FNFE-MPE](https://fnfe-mpe.org/factur-x/)
and the [Forum elektronische Rechnung Deutschland (FeRD)](https://www.ferd-net.de/standards/zugferd)
as part of the Factur-X 1.08 / ZUGFeRD 2.4 release kit. They are
distributed free of charge under the conditions documented on the
[FeRD download page](https://www.ferd-net.de/publikationen-produkte/publikationen/detailseite/zugferd-24-english).
The XML schemas (XSD), schematron (.sch), per-profile technical-
appendix PDFs and the example invoices that accompany the
workbook tree are NOT vendored here — they live on the gitignored
``ZF24_EN/`` worktree (see ``docs/READING_OFFICIAL_DOCS.md`` for the
full kit layout and how to fetch it locally).

When the upstream kit is updated, refresh both files in place and
regenerate the sidecars (``make ids-check`` covers it).
