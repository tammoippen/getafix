"""Tests for the pure-Python schematron evaluator in :mod:`tests._schematron`.

The evaluator is the oracle ``test_schematron_roundtrip`` trusts, so
it needs its own guard. These tests pin the workaround for
``elementpath``'s shared-focus bug in ``for`` / ``some`` / ``every``
range bindings (see :class:`tests._schematron._IsolatedBindingContext`):

* the bare XPath constructs evaluate per the XPath 2.0 spec, and
* the two Factur-X rules the bug used to misfire on
  (``BR-FXEXT-CO-15``, ``BR-FXEXT-11``) pass on a valid sample *and*
  still fire on a broken one, so the fix cannot have made them pass
  vacuously.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest as pt
from lxml import etree

from tests._schematron import _select, evaluate_schematron

_SCH_PATH = (
    Path(__file__).parent / "schemas/4_Factur-X_1.08_EXTENDED/FACTUR-X_EXTENDED.sch"
)
_SAMPLES = Path(__file__).parent / "samples"

_NS = {"a": "urn:a"}
_TOY = etree.fromstring(
    b'<a:root xmlns:a="urn:a">'
    b"<a:sum><a:x>1</a:x><a:y>2</a:y></a:sum>"
    b"<a:code>EUR</a:code>"
    b"<a:line><a:id>1</a:id></a:line>"
    b"<a:line><a:id>2</a:id><a:parent>1</a:parent></a:line>"
    b"</a:root>"
)


def _sum_node() -> etree._Element:
    return _TOY.find("a:sum", _NS)


def test_for_later_binding_keeps_outer_focus() -> None:
    # ``a:y`` must resolve from ``a:sum`` (the focus), not from the
    # ``a:code`` node the first binding selected.
    result = _select(
        _TOY,
        "for $c in ../a:code, $y in a:y return concat($c, '-', $y)",
        _NS,
        item=_sum_node(),
    )
    assert result == ["EUR-2"]


def test_for_later_binding_sees_earlier_variable() -> None:
    result = _select(
        _TOY,
        "for $x in xs:decimal(a:x), $z in $x + xs:decimal(a:y) return $z",
        _NS,
        item=_sum_node(),
    )
    assert [str(v) for v in result] == ["3"]


def test_some_satisfies_keeps_outer_focus() -> None:
    # ``a:parent`` must resolve from the second ``a:line`` (the focus),
    # not from the last ``a:id`` the range expression visited.
    line2 = _TOY.findall("a:line", _NS)[1]
    expr = "some $p in //a:line/a:id satisfies string($p) = string(a:parent)"
    assert _select(_TOY, expr, _NS, item=line2) is True


def _load(name: str) -> etree._Element:
    return etree.parse(str(_SAMPLES / name)).getroot()


_RAM = (
    "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
)


@pt.mark.parametrize(
    "sample", ["EXTENDED_zf24_Warenrechnung.xml", "EXTENDED_fremdwaehrung.xml"]
)
def test_co15_passes_on_valid_and_fires_on_broken_total(sample: str) -> None:
    root = _load(sample)
    assert "BR-FXEXT-CO-15" not in evaluate_schematron(_SCH_PATH, root).violations

    grand = root.find(
        f".//{{{_RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation"
        f"/{{{_RAM}}}GrandTotalAmount"
    )
    assert grand is not None
    assert grand.text is not None
    grand.text = str(Decimal(grand.text) + 100)
    assert "BR-FXEXT-CO-15" in evaluate_schematron(_SCH_PATH, root).violations


def test_fxext11_passes_on_valid_and_fires_on_orphan_parent() -> None:
    root = _load("EXTENDED_zf24_SubInvoiceLines_Kaffee.xml")
    assert "BR-FXEXT-11" not in evaluate_schematron(_SCH_PATH, root).violations

    parent = root.find(f".//{{{_RAM}}}ParentLineID")
    assert parent is not None
    parent.text = "does-not-exist"
    assert "BR-FXEXT-11" in evaluate_schematron(_SCH_PATH, root).violations
