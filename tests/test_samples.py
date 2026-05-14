"""Parser smoke-tests against real-world ZUGFeRD / Factur-X samples.

The XML files in ``tests/samples/`` are valid CII documents pulled from
upstream projects (see ``tests/samples/SOURCES.md``). They serve two purposes:

1.  *Sanity*: each sample remains well-formed XML in the expected
    ``CrossIndustryInvoice`` namespace and declares a profile we recognise.
2.  *Round-trip*: each sample feeds through ``Document.from_xml`` without
    raising. Locked in as a strict pass — adding a new sample that breaks
    the parser must fix the parser, not relax the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt

from carthorse.schema import Document
from carthorse.schema.types import Namespace, Profile
from tests._parsers import ParseFromFile

SAMPLES_DIR = Path(__file__).parent / "samples"

CII_NAMESPACE = Namespace.rsm.value
GUIDELINE_TAG = (
    "{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}"
    "ExchangedDocumentContext/"
    "{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}"
    "GuidelineSpecifiedDocumentContextParameter/"
    "{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}"
    "ID"
)


def _samples() -> list[Path]:
    return sorted(SAMPLES_DIR.glob("*.xml"))


SAMPLES = _samples()


def _expected_profile_from_filename(path: Path) -> Profile:
    prefix = path.name.split("_", 1)[0]
    # File-name prefix encodes the declared profile.
    return {
        "MINIMUM": Profile.MINIMUM,
        "BASICWL": Profile.BASIC_WL,
        "BASIC": Profile.BASIC,
        "EN16931": Profile.COMFORT,
        "COMFORT": Profile.COMFORT,
        "EXTENDED": Profile.EXTENDED,
    }[prefix]


def test_samples_directory_is_populated():
    assert SAMPLES, (
        "No sample XML files found. See tests/samples/SOURCES.md for download URLs."
    )


@pt.mark.parametrize("sample", SAMPLES, ids=[s.name for s in SAMPLES])
def test_sample_is_well_formed_cii(sample: Path, parse_file: ParseFromFile):
    """Each sample parses as XML and is a CrossIndustryInvoice document."""
    root = parse_file(sample)
    assert root.tag == f"{{{CII_NAMESPACE}}}CrossIndustryInvoice", (
        f"{sample.name} is not a CII document (root={root.tag})"
    )


@pt.mark.parametrize("sample", SAMPLES, ids=[s.name for s in SAMPLES])
def test_sample_declares_known_profile(sample: Path):
    """The declared guideline URN matches the file-name prefix and a known Profile."""
    import xml.etree.ElementTree as etree

    tree = etree.parse(str(sample))
    id_elem = tree.find(GUIDELINE_TAG)
    assert id_elem is not None, (
        f"{sample.name} has no GuidelineSpecifiedDocumentContextParameter/ID"
    )
    assert id_elem.text is not None, (
        f"{sample.name} has empty GuidelineSpecifiedDocumentContextParameter/ID"
    )
    declared = Profile(id_elem.text.strip())
    assert declared == _expected_profile_from_filename(sample), (
        f"{sample.name} declares {declared.name}, "
        f"expected {_expected_profile_from_filename(sample).name} from filename prefix"
    )


@pt.mark.parametrize("sample", SAMPLES, ids=[s.name for s in SAMPLES])
def test_sample_roundtrips_through_document(sample: Path, parse_file: ParseFromFile):
    """Full parser round-trip."""
    Document.from_xml(parse_file(sample))
