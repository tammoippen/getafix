# Test schema provenance

The XSD and Schematron files in the per-profile subdirectories are
vendored unmodified from the official **Factur-X 1.08 / ZUGFeRD 2.4**
distribution maintained by [FNFE-MPE](https://fnfe-mpe.org/factur-x/)
and FeRD. They are used as fixtures for round-trip and conformance
tests — never modified, only consulted.

The upstream archive (`Factur-X_1.08_VF.zip`) is freely downloadable
from the FNFE-MPE website; the schematron `.sch` files and the
`*_codedb.xml` codelist tables ship alongside the XSDs.

## Per-profile origins

| Subdirectory | Source |
|---|---|
| `0_Factur-X_1.08_MINIMUM/` | `ZF24_EN/Schema/0_Factur-X_1.08_MINIMUM/` |
| `1_Factur-X_1.08_BASICWL/` | `ZF24_EN/Schema/1_Factur-X_1.08_BASICWL/` |
| `2_Factur-X_1.08_BASIC/`   | `ZF24_EN/Schema/2_Factur-X_1.08_BASIC/` |
| `3_Factur-X_1.08_EN16931/` | `ZF24_EN/Schema/3_Factur-X_1.08_EN16931/` |
| `4_Factur-X_1.08_EXTENDED/` | `ZF24_EN/Schema/4_Factur-X_1.08_EXTENDED/` (includes `FACTUR-X_EXTENDED.sch` + `FACTUR-X_EXTENDED_codedb.xml` for the schematron round-trip oracle in `tests/test_schematron_roundtrip.py`) |

## Updating

After fetching a new spec release, copy the matching files from the
`docs` branch over the ones here and run `pytest`. If the schematron
file gains or loses rules, expect movement in the round-trip oracle's
expected-gap list (`_EXPECTED_SCHEMATRON_ONLY` in
`tests/test_schematron_roundtrip.py`).
