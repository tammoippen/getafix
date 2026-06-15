"""Extract embedded supporting documents (BT-125) from real samples.

Four samples in ``tests/samples/`` carry an ``AttachmentBinaryObject``
with a base64 payload. These tests exercise
``AttachmentBinaryObject.binary_object`` end-to-end: parse the sample,
walk to every attachment, decode the payload and confirm the extracted
bytes are the PDF the attachment claims to be.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path

import pytest as pt

from getafix.schema.document import Document
from getafix.schema.element import Element
from getafix.schema.references import AttachmentBinaryObject
from getafix.schema.types import MIME
from tests._parsers import ParseFromFile

SAMPLES_DIR = Path(__file__).parent / "samples"

# sample file -> embedded attachment file names, in document order.
SAMPLE_ATTACHMENTS: dict[str, list[str]] = {
    "EN16931_zf24_Betriebskosten.xml": ["Betriebskostenabrechnung_2025.pdf"],
    "EN16931_zf24_Elektron.xml": ["Aufmass.pdf"],
    "EN16931_zf24_Reisekosten.xml": ["Hotelrechnung.pdf", "Taxi_Quittung.pdf"],
    "EXTENDED_zf24_Bau_Schlussrechnung.xml": ["Zahlungsaufstellung.pdf"],
}


def _walk_attachments(node: Element) -> Iterator[AttachmentBinaryObject]:
    """Yield every ``AttachmentBinaryObject`` under ``node``, depth-first."""
    for f in fields(node):
        value = getattr(node, f.name)
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, AttachmentBinaryObject):
                yield item
            elif isinstance(item, Element):
                yield from _walk_attachments(item)


@pt.mark.parametrize(
    ("sample", "expected_filenames"),
    list(SAMPLE_ATTACHMENTS.items()),
    ids=list(SAMPLE_ATTACHMENTS),
)
def test_extract_sample_attachments(
    sample: str,
    expected_filenames: list[str],
    parse_file: ParseFromFile,
    tmp_path: Path,
):
    """Decode every embedded attachment and write it back out as a file."""
    doc = Document.from_xml(parse_file(SAMPLES_DIR / sample))
    attachments = list(_walk_attachments(doc))

    assert sorted(a.filename for a in attachments) == sorted(expected_filenames)

    for attachment in attachments:
        assert attachment.mime_code is MIME.pdf
        payload = attachment.binary_object

        # The property decodes the base64 text to the raw file bytes …
        assert isinstance(payload, bytes)
        assert payload, f"{attachment.filename}: decoded payload is empty"
        # … which are the PDF the attachment claims (magic number).
        assert payload.startswith(b"%PDF-"), (
            f"{attachment.filename}: not a PDF (starts {payload[:8]!r})"
        )

        # Extracting to disk yields a usable, byte-identical file.
        out = tmp_path / attachment.filename
        out.write_bytes(payload)
        assert out.read_bytes() == payload
