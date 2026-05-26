"""Cross-validate carthorse's EXTENDED rule emission against
``FACTUR-X_EXTENDED.sch`` — the single source of truth for "what's
left" in the EXTENDED migration (§7 step 2 of
``docs/PROFILES/EXTENDED.md``).

For each ``tests/samples/EXTENDED_*.xml`` sample we collect three
sets of error codes:

* **schematron_codes** — what ``FACTUR-X_EXTENDED.sch`` fires
  (evaluated via :mod:`tests._schematron`, which uses ``elementpath``
  to side-step ``lxml.isoschematron``'s XSLT-1 limitation).
* **carthorse_codes** — what ``Document.validate`` emits.
* **indeterminate** — schematron asserts whose XPath couldn't be
  evaluated (e.g. uses ``document('…_codedb.xml')``). Treated as
  neither pass nor fail.

The test asserts two things:

1. **No false positives** — every code carthorse emits is also
   fired (or indeterminate) in the schematron. A failure means
   carthorse is more strict than the spec — usually a real bug.
2. **No surprise coverage regressions** — the set of codes the
   schematron fires that carthorse does not is pinned per-sample in
   ``_EXPECTED_SCHEMATRON_ONLY``. Implementing a missing rule should
   shrink that set; introducing a new gap fails the test loudly so
   nothing slips in unintentionally.
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt
from lxml import etree

from carthorse.schema import Document
from carthorse.schema.element import ValidationErrors
from tests._schematron import evaluate_schematron

_SCH_PATH = (
    Path(__file__).parent
    / "schemas/4_Factur-X_1.08_EXTENDED/FACTUR-X_EXTENDED.sch"
)
_SAMPLES_DIR = Path(__file__).parent / "samples"
_SAMPLES = sorted(_SAMPLES_DIR.glob("EXTENDED_*.xml"))


# Per-sample allowlist of codes the schematron fires that carthorse
# does not (yet). Each entry corresponds to a §5 EXTENDED rule still
# on the implementation TODO list; closing one means removing it from
# here. New entries should never appear silently — the test fails
# with a diff so the gap can be explicitly acknowledged.
_EXPECTED_SCHEMATRON_ONLY: dict[str, frozenset[str]] = {
    # BR-FXEXT-CO-15 — *elementpath* false positive, not a carthorse
    # coverage gap. The .sch's test for CO-15 binds ``$Currency`` to
    # the ``ram:InvoiceCurrencyCode`` *node* and then uses it in
    # ``[@currencyID=$Currency]``; Saxon-class XSLT 2 processors do
    # an implicit string-cast on that comparison, but elementpath
    # returns an empty sequence (= assert failed). carthorse's
    # br_fxext_co_15 implementation evaluates the identity correctly
    # and both samples are clean per the spec. Move out of this dict
    # once we either swap evaluators or work around the cast (e.g.
    # rewrite the test expression's variable binding before evaling).
    "EXTENDED_factur-x-extended.xml": frozenset({"BR-FXEXT-CO-15"}),
    "EXTENDED_fremdwaehrung.xml": frozenset({"BR-FXEXT-CO-15"}),
    # BR-FXEXT-11 — parent-line ID resolution; pending §5.1 cross-line
    # walker (next sub-task). BR-FXEXT-CO-15 is the same elementpath
    # false-positive as above.
    "EXTENDED_zf24_SubInvoiceLines_Hardware.xml": frozenset(
        {"BR-FXEXT-11", "BR-FXEXT-CO-15"}
    ),
}


@pt.mark.parametrize("sample", _SAMPLES, ids=lambda p: p.name)
def test_extended_sample_matches_schematron(sample: Path) -> None:
    xml_root = etree.parse(str(sample)).getroot()
    sch_result = evaluate_schematron(_SCH_PATH, xml_root)

    doc = Document.from_xml(xml_root)
    try:
        doc.validate()
        carthorse_codes: frozenset[str] = frozenset()
    except ValidationErrors as exc:
        carthorse_codes = frozenset(v.code for v in exc.errors)

    # 1. No false positives — every carthorse-emitted code is either
    #    also fired by the schematron or lives in the indeterminate
    #    bucket (schematron couldn't evaluate it, so it's neither
    #    confirmed nor refuted).
    false_positives = (
        carthorse_codes - sch_result.violations - sch_result.indeterminate
    )
    assert not false_positives, (
        f"{sample.name}: carthorse emits codes the schematron neither "
        f"fires nor flags indeterminate: {sorted(false_positives)}."
    )

    # 2. Coverage gaps must match the pinned allowlist — surprise new
    #    gaps fail the test so they get acknowledged in
    #    _EXPECTED_SCHEMATRON_ONLY rather than slipping in silently.
    expected_gaps = _EXPECTED_SCHEMATRON_ONLY.get(sample.name, frozenset())
    actual_gaps = sch_result.violations - carthorse_codes
    assert actual_gaps == expected_gaps, (
        f"{sample.name}: schematron-vs-carthorse coverage drift.\n"
        f"  expected schematron-only: {sorted(expected_gaps)}\n"
        f"  actual schematron-only:   {sorted(actual_gaps)}\n"
        f"  added (need impl or doc): {sorted(actual_gaps - expected_gaps)}\n"
        f"  closed (drop from list):  {sorted(expected_gaps - actual_gaps)}"
    )
