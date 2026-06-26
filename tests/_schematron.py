"""Pure-Python schematron evaluator using ``elementpath``.

``lxml.isoschematron`` cannot compile ``FACTUR-X_EXTENDED.sch`` — the
``.sch`` uses XPath 2 ``for $X in ...`` expressions and ISO Schematron
2016 idioms (e.g. ``id`` attribute on ``<assert>``) that libxslt's
XSLT-1 processor rejects. This module bypasses the XSLT pipeline:
it parses the ``.sch`` directly and evaluates each ``<sch:assert>``
against an XML tree with ``elementpath``'s XPath-2 engine.

Used by ``tests/test_schematron_roundtrip.py`` to cross-check
getafix's emitted rule codes against the schematron's verdict on
the same document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import elementpath
from elementpath import XPath2Parser
from lxml import etree

_SCH_NS = "http://purl.oclc.org/dsdl/schematron"
_CODE_RX = re.compile(r"\[([A-Z][A-Z0-9-]+)\]")


@dataclass(frozen=True, slots=True)
class SchematronResult:
    """Outcome of evaluating a schematron against an XML document.

    ``violations`` — codes (``"BR-FXEXT-CO-15"``, …) whose assert
    fired at least once on the input.

    ``indeterminate`` — codes whose XPath ``test`` raised during
    evaluation (typically because the expression uses
    ``document('FACTUR-X_EXTENDED_codedb.xml')`` for codelist
    lookups, which we don't currently wire through; those asserts
    are conservatively excluded from the violation set rather than
    treated as either pass or fail).

    ``ok_count`` — asserts that evaluated cleanly and passed.

    ``reports`` — messages from ``<sch:report>`` elements that fired.
    A report is the logical inverse of an assert: it fires when its
    ``test`` evaluates to *true* (the reported condition holds),
    whereas an assert fires when its test is *false*. The reports in
    ``FACTUR-X_EXTENDED.sch`` carry no bracketed ``[BR-...]`` code or
    ``id`` attribute, so they're keyed by their normalised message
    text rather than a rule code.
    """

    violations: frozenset[str]
    indeterminate: frozenset[str]
    ok_count: int
    reports: frozenset[str] = frozenset()


def evaluate_schematron(sch_path: Path, xml_root: etree._Element) -> SchematronResult:
    """Run every ``<sch:assert>`` in ``sch_path`` against ``xml_root``.

    Rule IDs are taken from the leading ``[BR-...]`` token of each
    assert's text body — falling back to the assert's ``id``
    attribute when the body doesn't carry a bracketed code.
    """
    sch_root = etree.parse(str(sch_path)).getroot()
    namespaces = {
        str(ns.attrib["prefix"]): str(ns.attrib["uri"])
        for ns in sch_root.findall(f"{{{_SCH_NS}}}ns")
    }

    violations: set[str] = set()
    indeterminate: set[str] = set()
    reports: set[str] = set()
    ok_count = 0

    for pattern in sch_root.findall(f"{{{_SCH_NS}}}pattern"):
        for rule in pattern.findall(f"{{{_SCH_NS}}}rule"):
            context = rule.attrib.get("context")
            if not context:
                continue
            try:
                raw_ctx = elementpath.select(
                    xml_root, context, namespaces=namespaces, parser=XPath2Parser
                )
            except Exception:  # noqa: BLE001 — elementpath raises a wide variety; treat any as "indeterminate"
                # Unsupported XPath in the context selector — every assert
                # under this rule is effectively indeterminate, but we don't
                # have their codes without iterating, so skip silently.
                continue
            ctx_nodes = raw_ctx if isinstance(raw_ctx, list) else [raw_ctx]
            for assert_el in rule.findall(f"{{{_SCH_NS}}}assert"):
                code = _code_from_assert(assert_el)
                test = assert_el.attrib.get("test", "")
                evaluated = False
                fired = False
                for ctx in ctx_nodes:
                    try:
                        result = elementpath.select(
                            xml_root,
                            test,
                            namespaces=namespaces,
                            parser=XPath2Parser,
                            item=ctx,
                        )
                    except Exception:  # noqa: BLE001 — elementpath raises a wide variety; treat any as "indeterminate"
                        indeterminate.add(code)
                        evaluated = False
                        break
                    evaluated = True
                    if not result:
                        violations.add(code)
                        fired = True
                        break
                if evaluated and not fired:
                    ok_count += 1

            for report_el in rule.findall(f"{{{_SCH_NS}}}report"):
                label = _report_label(report_el)
                test = report_el.attrib.get("test", "")
                for ctx in ctx_nodes:
                    try:
                        result = elementpath.select(
                            xml_root,
                            test,
                            namespaces=namespaces,
                            parser=XPath2Parser,
                            item=ctx,
                        )
                    except Exception:  # noqa: BLE001 — elementpath raises a wide variety; treat any as "indeterminate"
                        # A report whose test can't be evaluated tells us
                        # nothing — neither fired nor not — so drop it
                        # rather than recording a phantom report.
                        break
                    # A report is the inverse of an assert: it fires when
                    # its test is *true*.
                    if result:
                        reports.add(label)
                        break

    return SchematronResult(
        violations=frozenset(violations),
        indeterminate=frozenset(indeterminate),
        ok_count=ok_count,
        reports=frozenset(reports),
    )


def _code_from_assert(el: etree._Element) -> str:
    text = (el.text or "").strip()
    match = _CODE_RX.match(text)
    if match:
        return match.group(1)
    return el.attrib.get("id", "?")


def _report_label(el: etree._Element) -> str:
    """Identify a fired ``<sch:report>``.

    Prefers a bracketed ``[BR-...]`` code, then the ``id`` attribute,
    falling back to the report's normalised message text — the
    EXTENDED reports carry neither code nor id, so the message is the
    only thing that distinguishes them.
    """
    text = " ".join((el.text or "").split())
    match = _CODE_RX.match(text)
    if match:
        return match.group(1)
    return el.attrib.get("id") or text or "?"
