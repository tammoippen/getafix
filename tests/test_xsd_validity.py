"""XSD wire-conformance for the renderer.

Every sample under ``tests/samples/*.xml`` is parsed via
``Document.from_xml`` and re-rendered via
``Document.to_xml().render(indent=True)``. The re-rendered document
must validate against the Factur-X 1.08 XSD for the sample's declared
profile.

This test is the quality gate for the "field order matches XSD
``<xs:sequence>``" fix. Earlier the dataclasses had arbitrary field
declaration order, so ``Element._children_xml`` (which iterates over
``dataclasses.fields()``) produced XML that lxml's
``XMLSchema.assertValid`` rejected with
``Element ... This element is not expected. Expected is ...``.

Skip / xfail policy
-------------------

A handful of samples touch features the renderer does not yet emit
(MINIMUM samples that omit ``BG-25`` line items entirely, EXTENDED
samples that need ``BG-25`` with line-level fields beyond the BASIC
slice). Those are marked ``xfail(strict=False)`` with a precise reason.
"""

from __future__ import annotations

from pathlib import Path

import lxml.etree as etree
import pytest as pt

from carthorse.schema import Document
from carthorse.schema.types import Profile

SAMPLES_DIR = Path(__file__).parent / "samples"
SCHEMAS_DIR = Path(__file__).parent / "schemas"


_PROFILE_TO_XSD: dict[Profile, Path] = {
    Profile.MINIMUM: SCHEMAS_DIR / "0_Factur-X_1.08_MINIMUM" / "FACTUR-X_MINIMUM.xsd",
    Profile.BASIC_WL: SCHEMAS_DIR / "1_Factur-X_1.08_BASICWL" / "FACTUR-X_BASIC-WL.xsd",
    Profile.BASIC: SCHEMAS_DIR / "2_Factur-X_1.08_BASIC" / "FACTUR-X_BASIC.xsd",
    Profile.COMFORT: SCHEMAS_DIR / "3_Factur-X_1.08_EN16931" / "FACTUR-X_EN16931.xsd",
    Profile.EXTENDED: SCHEMAS_DIR
    / "4_Factur-X_1.08_EXTENDED"
    / "FACTUR-X_EXTENDED.xsd",
}


_SAMPLES = sorted(SAMPLES_DIR.glob("*.xml"))


# Samples whose round-trip is not yet XSD-valid for reasons unrelated to
# field order (e.g. line-level fields we don't model). Each entry maps
# the sample filename to a precise reason; the test is xfail(strict=False)
# so it can flip to XPASS without a CI break as coverage grows. Empty
# today — every shipped sample is XSD-valid after the field-order fix.
_XFAIL_REASONS: dict[str, str] = {}


_SCHEMA_CACHE: dict[Profile, etree.XMLSchema] = {}


def _load_schema(profile: Profile) -> etree.XMLSchema:
    """Cache lxml ``XMLSchema`` instances; compilation is the slow bit."""
    schema = _SCHEMA_CACHE.get(profile)
    if schema is None:
        xsd_path = _PROFILE_TO_XSD[profile]
        schema = etree.XMLSchema(etree.parse(str(xsd_path)))
        _SCHEMA_CACHE[profile] = schema
    return schema


@pt.mark.parametrize("sample", _SAMPLES, ids=[s.name for s in _SAMPLES])
def test_rendered_xml_validates_against_xsd(sample: Path) -> None:
    """Parse, re-render, then validate against the profile XSD."""
    if sample.name in _XFAIL_REASONS:
        pt.xfail(_XFAIL_REASONS[sample.name])

    tree = etree.parse(str(sample))
    doc = Document.from_xml(tree.getroot())
    profile = doc.context.guideline.id
    rendered = doc.to_xml().render(indent=True)

    schema = _load_schema(profile)
    parsed = etree.fromstring(rendered.encode())
    try:
        schema.assertValid(parsed)
    except etree.DocumentInvalid as exc:  # pragma: no cover - diagnostic
        raise AssertionError(
            f"{sample.name}: re-rendered XML does not validate against "
            f"{_PROFILE_TO_XSD[profile].name}:\n{exc}"
        ) from exc
