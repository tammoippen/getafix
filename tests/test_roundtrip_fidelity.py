"""Source-vs-render fidelity — every sample must re-render 1:1.

getafix models every MINIMUM / BASIC_WL / BASIC / COMFORT field and is
structurally complete at EXTENDED, so parsing a real sample with
``Document.from_xml`` and re-rendering it with
``Document.to_xml()`` must reproduce the source **element for element** —
apart from one exception: **empty source elements** (e.g.
``<ram:LineTwo/>``, ``<ram:Description/>``), which getafix normalises away
on parse (an empty element carries no data, and PEPPOL-EN16931-R008 warns
against them — see ``Element._parse_str``).

Anything else — a dropped, added, reordered or altered element / attribute
/ text — is a faithfulness regression. This complements
``test_xsd_validity`` (which only checks the re-render is *valid*, not that
it is *the same*) and ``test_zf24_examples`` (which round-trips
model→XML→model, blind to what the parser silently ignores).
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt

from getafix.schema.document import Document

pt.importorskip("lxml", reason="round-trip fidelity needs lxml")

import lxml.etree as etree

SAMPLES_DIR = Path(__file__).parent / "samples"
_SAMPLES = sorted(SAMPLES_DIR.glob("*.xml"))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _norm(text: str | None) -> str:
    """Collapse insignificant whitespace; XML text whitespace is not data."""
    return " ".join((text or "").split())


def _is_empty(el: etree._Element) -> bool:
    """An element carrying no data: no text, no child elements, no attributes."""
    children = [c for c in el if isinstance(c.tag, str)]
    return not _norm(el.text) and not children and not el.attrib


def _diff(
    orig: etree._Element, rend: etree._Element, path: str, out: list[str]
) -> None:
    """Append a human-readable note for every divergence under ``path``."""
    if _norm(orig.text) != _norm(rend.text):
        out.append(f"TEXT     {path}: {_norm(orig.text)!r} -> {_norm(rend.text)!r}")
    if dict(orig.attrib) != dict(rend.attrib):
        out.append(f"ATTR     {path}: {dict(orig.attrib)} -> {dict(rend.attrib)}")
    oc = [c for c in orig if isinstance(c.tag, str)]
    rc = [c for c in rend if isinstance(c.tag, str)]
    i = j = 0
    while i < len(oc) or j < len(rc):
        if i < len(oc) and j < len(rc) and oc[i].tag == rc[j].tag:
            _diff(oc[i], rc[j], f"{path}/{_local(oc[i].tag)}", out)
            i += 1
            j += 1
        elif i < len(oc) and oc[i].tag not in {x.tag for x in rc[j:]}:
            if not _is_empty(oc[i]):
                out.append(f"DROPPED  {path}/{_local(oc[i].tag)}")
            i += 1
        elif j < len(rc) and rc[j].tag not in {x.tag for x in oc[i:]}:
            out.append(f"INVENTED {path}/{_local(rc[j].tag)}")
            j += 1
        else:
            out.append(f"REORDER  {path}/{_local(oc[i].tag)}")
            i += 1
            j += 1


@pt.mark.parametrize("sample", _SAMPLES, ids=[s.name for s in _SAMPLES])
def test_sample_renders_one_to_one(sample: Path) -> None:
    """Parse → re-render → diff against the source; only empty source
    elements may differ."""
    original = etree.parse(str(sample)).getroot()
    rendered = etree.fromstring(Document.from_xml(original).to_xml().render().encode())
    diffs: list[str] = []
    _diff(original, rendered, _local(original.tag), diffs)
    assert not diffs, (
        f"{sample.name}: re-render is not 1:1 with the source:\n" + "\n".join(diffs)
    )
