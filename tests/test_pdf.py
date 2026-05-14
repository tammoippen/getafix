"""Tests for :mod:`carthorse.pdf` — embed and extract XML in a PDF.

The fixtures synthesise a one-page blank PDF with pypdf so the tests
don't depend on shipping a binary sample file. Round-trip the
attachment under the default name, a custom name, and verify the
standard-locations fallback finds an attachment even when none of the
caller-specified candidates matches.
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt
from pypdf import PdfReader, PdfWriter

from carthorse.pdf import (
    DEFAULT_ATTACHMENT_NAME,
    STANDARD_LOCATIONS,
    attach_xml,
    extract_xml,
)

XML_PAYLOAD = b'<?xml version="1.0"?><invoice><id>INV-1</id></invoice>'


@pt.fixture
def blank_pdf(tmp_path: Path) -> Path:
    """A one-page blank PDF with no embedded files."""
    target = tmp_path / "blank.pdf"
    writer = PdfWriter()
    _ = writer.add_blank_page(width=200, height=200)
    with target.open("wb") as fp:
        writer.write(fp)
    return target


def test_attach_xml_default_name_roundtrips(blank_pdf: Path, tmp_path: Path):
    out = tmp_path / "with-default.pdf"
    written = attach_xml(blank_pdf, XML_PAYLOAD, pdf_out=out)
    assert written == out
    # Default name lands in the embedded files name tree.
    reader = PdfReader(str(out))
    assert DEFAULT_ATTACHMENT_NAME in reader.attachments
    assert extract_xml(out) == XML_PAYLOAD


def test_attach_xml_custom_name_uses_supplied_filename(blank_pdf: Path, tmp_path: Path):
    out = tmp_path / "zugferd1.pdf"
    attach_xml(
        blank_pdf, XML_PAYLOAD, pdf_out=out, attachment_name="ZUGFeRD-invoice.xml"
    )
    reader = PdfReader(str(out))
    assert "ZUGFeRD-invoice.xml" in reader.attachments
    # Case-insensitive standard-location lookup still wins.
    assert extract_xml(out) == XML_PAYLOAD


def test_attach_xml_reads_xml_from_path(blank_pdf: Path, tmp_path: Path):
    xml_path = tmp_path / "invoice.xml"
    xml_path.write_bytes(XML_PAYLOAD)
    out = tmp_path / "from-path.pdf"
    attach_xml(blank_pdf, xml_path, pdf_out=out)
    assert extract_xml(out) == XML_PAYLOAD


def test_attach_xml_in_place_rewrites_input_pdf(blank_pdf: Path):
    attach_xml(blank_pdf, XML_PAYLOAD)
    assert extract_xml(blank_pdf) == XML_PAYLOAD


def test_extract_xml_returns_none_for_pdf_without_attachments(blank_pdf: Path):
    assert extract_xml(blank_pdf) is None


def test_extract_xml_falls_back_through_standard_locations(
    blank_pdf: Path, tmp_path: Path
):
    """Default candidates probe legacy ZUGFeRD / XRechnung names too."""
    out = tmp_path / "xrechnung.pdf"
    attach_xml(blank_pdf, XML_PAYLOAD, pdf_out=out, attachment_name="xrechnung.xml")
    assert extract_xml(out) == XML_PAYLOAD
    # Same lookup chain returns None when candidates exclude it.
    assert extract_xml(out, candidates=("factur-x.xml",)) is None


def test_extract_xml_is_case_insensitive(blank_pdf: Path, tmp_path: Path):
    out = tmp_path / "uppercase.pdf"
    attach_xml(blank_pdf, XML_PAYLOAD, pdf_out=out, attachment_name="FACTUR-X.XML")
    assert extract_xml(out) == XML_PAYLOAD


def test_extract_xml_honours_candidate_priority(blank_pdf: Path, tmp_path: Path):
    out = tmp_path / "two-attachments.pdf"
    writer = PdfWriter(clone_from=str(blank_pdf))
    _ = writer.add_attachment("factur-x.xml", b"<factur-x/>")
    _ = writer.add_attachment("xrechnung.xml", b"<xrechnung/>")
    with out.open("wb") as fp:
        writer.write(fp)
    # Default order: factur-x wins.
    assert extract_xml(out) == b"<factur-x/>"
    # Flipping the priority returns the other one.
    assert (
        extract_xml(out, candidates=("xrechnung.xml", "factur-x.xml"))
        == b"<xrechnung/>"
    )


def test_standard_locations_contains_known_filenames():
    # Guardrail — the CLI's PDF-input path leans on these names.
    assert "factur-x.xml" in STANDARD_LOCATIONS
    assert "ZUGFeRD-invoice.xml" in STANDARD_LOCATIONS
    assert "xrechnung.xml" in STANDARD_LOCATIONS
