"""Property-based parser tests against XSD-conformant Factur-X XML.

Each generated XML payload comes from a strategy in :mod:`tests.strategies`
that is independent of the getafix model and known XSD-valid against the
vendored Factur-X 1.08 / ZUGFeRD 2.4 schemas under ``tests/schemas/``.

Two checks per profile:

1. ``test_generated_xml_is_xsd_valid`` — sanity for the strategy itself
   (decoupled from getafix). If this regresses we have a strategy bug, not
   a parser bug.
2. ``test_parse_and_regenerate`` — feed the bytes into ``Document.from_xml``
   and then ``Document.to_xml`` again. Locked in as a strict pass: a new
   Hypothesis-generated regression must fix the parser, not relax the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt
from hypothesis import HealthCheck, given, settings

from getafix.schema import Document
from getafix.schema.types import Profile

# Strategy + XSD validation both require lxml — gate the whole module.
pt.importorskip("lxml", reason="hypothesis strategies and XSD validation require lxml")

import lxml.etree as etree

from tests.strategies import invoices_for

_SCHEMA_ROOT = Path(__file__).resolve().parent / "schemas"

# Per-profile XSD entry points — vendored Factur-X 1.08 schemas (XSDs only,
# stripped of the codedb/XSLT/XLSX assets that ship in the official kit).
_XSD_PATHS = {
    Profile.MINIMUM: _SCHEMA_ROOT / "0_Factur-X_1.08_MINIMUM/FACTUR-X_MINIMUM.xsd",
    Profile.BASIC_WL: _SCHEMA_ROOT / "1_Factur-X_1.08_BASICWL/FACTUR-X_BASIC-WL.xsd",
    Profile.BASIC: _SCHEMA_ROOT / "2_Factur-X_1.08_BASIC/FACTUR-X_BASIC.xsd",
    Profile.COMFORT: _SCHEMA_ROOT / "3_Factur-X_1.08_EN16931/FACTUR-X_EN16931.xsd",
    Profile.EXTENDED: _SCHEMA_ROOT / "4_Factur-X_1.08_EXTENDED/FACTUR-X_EXTENDED.xsd",
}


@pt.fixture(scope="module")
def xsd_validators() -> dict[Profile, etree.XMLSchema]:
    return {
        p: etree.XMLSchema(etree.parse(str(path))) for p, path in _XSD_PATHS.items()
    }


_PROFILES = list(Profile)
_PROFILE_IDS = [p.name for p in _PROFILES]


@pt.mark.parametrize("profile", _PROFILES, ids=_PROFILE_IDS)
def test_generated_xml_is_xsd_valid(
    profile: Profile, xsd_validators: dict[Profile, etree.XMLSchema]
) -> None:
    """The strategy by itself emits XML that validates against the profile XSD."""
    validator = xsd_validators[profile]

    @given(blob=invoices_for(profile))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    def _check(blob: bytes) -> None:
        root = etree.fromstring(blob)
        assert validator.validate(root), str(validator.error_log)

    _check()


@pt.mark.parametrize("profile", _PROFILES, ids=_PROFILE_IDS)
def test_parse_and_regenerate(profile: Profile) -> None:
    """Feed XSD-valid generated XML through ``from_xml`` then ``to_xml``."""

    @given(blob=invoices_for(profile))
    @settings(
        max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def _check(blob: bytes) -> None:
        root = etree.fromstring(blob)
        doc = Document.from_xml(root)
        # Regenerate. We deliberately do not assert structural equality with
        # the input XML — the parser silently drops fields it doesn't model
        # yet, so output is a strict subset. We only require that the
        # round-trip produces parseable XML.
        rendered = doc.to_xml().render(indent=True)
        Document.from_xml(etree.fromstring(rendered.encode()))

    _check()


@pt.mark.parametrize("profile", _PROFILES, ids=_PROFILE_IDS)
def test_strategy_decodes_as_utf8(profile: Profile) -> None:
    """Smoke-check the strategy resolves and produces a non-empty UTF-8 payload."""

    @given(blob=invoices_for(profile))
    @settings(max_examples=5, deadline=None)
    def _check(blob: bytes) -> None:
        # ``etree.tostring`` already commits to UTF-8; this just guards
        # against accidental encoding regressions in the strategy.
        text = blob.decode("utf-8")
        assert text.startswith("<?xml")
        assert text.rstrip().endswith("</rsm:CrossIndustryInvoice>")

    _check()
