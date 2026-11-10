"""Cross-validate getafix's EXTENDED rule emission against
``FACTUR-X_EXTENDED.sch`` — the single source of truth for "what's
left" in EXTENDED rule coverage.

For each ``tests/samples/EXTENDED_*.xml`` sample we collect three
sets of error codes:

* **schematron_codes** — what ``FACTUR-X_EXTENDED.sch`` fires
  (evaluated via :mod:`tests._schematron`, which uses ``elementpath``
  to side-step ``lxml.isoschematron``'s XSLT-1 limitation).
* **getafix_codes** — what ``Document.validate`` emits.
* **indeterminate** — schematron asserts whose XPath couldn't be
  evaluated (e.g. uses ``document('…_codedb.xml')``). Treated as
  neither pass nor fail.

The test asserts two things:

1. **No false positives** — every code getafix emits is also
   fired (or indeterminate) in the schematron. A failure means
   getafix is more strict than the spec — usually a real bug.
2. **No surprise coverage regressions** — the set of codes the
   schematron fires that getafix does not is pinned per-sample in
   ``_EXPECTED_SCHEMATRON_ONLY``. Implementing a missing rule should
   shrink that set; introducing a new gap fails the test loudly so
   nothing slips in unintentionally.

Fired ``<sch:report>`` elements (the inverse of asserts —
informational "marked as not used in the given context" notices) are
surfaced as :class:`SchematronReportWarning` rather than asserted on,
so they show up in pytest's warnings summary without failing the run.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest as pt
from lxml import etree

from getafix.errors import ValidationErrors
from getafix.schema.document import Document
from tests._schematron import evaluate_schematron

_SCH_PATH = (
    Path(__file__).parent / "schemas/4_Factur-X_1.08_EXTENDED/FACTUR-X_EXTENDED.sch"
)
_SAMPLES_DIR = Path(__file__).parent / "samples"
_SAMPLES = sorted(_SAMPLES_DIR.glob("EXTENDED_*.xml"))


# Per-sample allowlist for *genuine* getafix coverage gaps —
# rules the schematron fires that getafix doesn't implement yet.
# Currently empty: the schematron and getafix agree on every
# sample in the current EXTENDED corpus.
_EXPECTED_SCHEMATRON_ONLY: dict[str, frozenset[str]] = {}


class SchematronReportWarning(UserWarning):
    """A ``<sch:report>`` fired on a sample.

    Reports are the inverse of asserts: they flag conditions the
    schematron wants to *surface* (here, "marked as not used in the
    given context") rather than reject. They're informational, so we
    raise them as warnings — visible in pytest's summary — instead of
    failing the test.
    """


@pt.mark.parametrize("sample", _SAMPLES, ids=lambda p: p.name)
def test_extended_sample_matches_schematron(sample: Path) -> None:
    xml_root = etree.parse(str(sample)).getroot()
    sch_result = evaluate_schematron(_SCH_PATH, xml_root)

    # Reports never fail the test — surface them as warnings so a
    # newly-tripped report shows up in the run without turning red.
    if sch_result.reports:
        warnings.warn(
            f"{sample.name}: schematron reports fired:\n  "
            + "\n  ".join(sorted(sch_result.reports)),
            SchematronReportWarning,
            stacklevel=2,
        )

    doc = Document.from_xml(xml_root)
    try:
        doc.validate()
        getafix_codes: frozenset[str] = frozenset()
    except ValidationErrors as exc:
        getafix_codes = frozenset(v.code for v in exc.errors)

    # 1. No false positives — every getafix-emitted code is either
    #    also fired by the schematron or lives in the indeterminate
    #    bucket (schematron couldn't evaluate it, so it's neither
    #    confirmed nor refuted).
    false_positives = getafix_codes - sch_result.violations - sch_result.indeterminate
    assert not false_positives, (
        f"{sample.name}: getafix emits codes the schematron neither "
        f"fires nor flags indeterminate: {sorted(false_positives)}."
    )

    # 2. Coverage gaps must match the pinned allowlist — surprise new
    #    gaps fail the test so they get acknowledged in
    #    _EXPECTED_SCHEMATRON_ONLY rather than slipping in silently.
    expected_gaps = _EXPECTED_SCHEMATRON_ONLY.get(sample.name, frozenset())
    actual_gaps = sch_result.violations - getafix_codes
    assert actual_gaps == expected_gaps, (
        f"{sample.name}: schematron-vs-getafix coverage drift.\n"
        f"  expected schematron-only: {sorted(expected_gaps)}\n"
        f"  actual schematron-only:   {sorted(actual_gaps)}\n"
        f"  added (need impl or doc): {sorted(actual_gaps - expected_gaps)}\n"
        f"  closed (drop from list):  {sorted(expected_gaps - actual_gaps)}"
    )
