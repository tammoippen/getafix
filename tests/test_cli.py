"""Tests for :mod:`getafix.cli` — the ``getafix`` console script.

Exercises every exit-code branch by driving :func:`getafix.cli.main`
with samples shipped under ``tests/samples`` plus a few synthesised
inputs (malformed XML, non-CII XML, PDFs with and without embedded
factur-x.xml).
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt
from pypdf import PdfWriter

from getafix.cli import main
from getafix.pdf import attach_xml

SAMPLES = Path(__file__).parent / "samples"
CLEAN_SAMPLE = SAMPLES / "EN16931_Einfach.cii.xml"
INVALID_SAMPLE = SAMPLES / "MINIMUM_facturFrMinimum.xml"  # trips BR-CO-16


def _blank_pdf(path: Path) -> Path:
    writer = PdfWriter()
    _ = writer.add_blank_page(width=200, height=200)
    with path.open("wb") as fp:
        writer.write(fp)
    return path


def test_cli_clean_sample_exits_zero(capsys: pt.CaptureFixture[str]):
    assert main([str(CLEAN_SAMPLE)]) == 0
    captured = capsys.readouterr()
    assert "471102" in captured.out  # invoice number from the sample
    assert "No validation errors" in captured.out


def test_cli_validation_error_sample_exits_one(capsys: pt.CaptureFixture[str]):
    assert main([str(INVALID_SAMPLE)]) == 1
    captured = capsys.readouterr()
    assert "Validation errors" in captured.out
    assert "BR-CO-16" in captured.out


def test_cli_no_validate_skips_validation(capsys: pt.CaptureFixture[str]):
    """``--no-validate`` returns 0 even when the document would fail BR-*."""
    assert main([str(INVALID_SAMPLE), "--no-validate"]) == 0
    captured = capsys.readouterr()
    assert "Validation errors" not in captured.out
    assert "No validation errors" not in captured.out


def test_cli_missing_file_exits_two(tmp_path: Path, capsys: pt.CaptureFixture[str]):
    missing = tmp_path / "nope.xml"
    assert main([str(missing)]) == 2
    captured = capsys.readouterr()
    assert "Could not read" in captured.err


def test_cli_malformed_xml_exits_one(tmp_path: Path, capsys: pt.CaptureFixture[str]):
    bad = tmp_path / "bad.xml"
    bad.write_text("this is not xml")
    assert main([str(bad)]) == 1
    captured = capsys.readouterr()
    assert "XML syntax error" in captured.err


def test_cli_non_cii_xml_exits_one(tmp_path: Path, capsys: pt.CaptureFixture[str]):
    not_cii = tmp_path / "other.xml"
    not_cii.write_text("<root><child/></root>")
    assert main([str(not_cii)]) == 1
    captured = capsys.readouterr()
    assert "Could not parse" in captured.err


def test_cli_pdf_input_renders_embedded_xml(
    tmp_path: Path, capsys: pt.CaptureFixture[str]
):
    pdf = _blank_pdf(tmp_path / "invoice.pdf")
    attach_xml(pdf, CLEAN_SAMPLE)
    assert main([str(pdf)]) == 0
    captured = capsys.readouterr()
    assert "471102" in captured.out
    assert "No validation errors" in captured.out


def test_cli_pdf_without_xml_exits_one(tmp_path: Path, capsys: pt.CaptureFixture[str]):
    pdf = _blank_pdf(tmp_path / "empty.pdf")
    assert main([str(pdf)]) == 1
    captured = capsys.readouterr()
    assert "No Factur-X" in captured.err


def test_cli_pdf_with_malformed_embedded_xml_exits_one(
    tmp_path: Path, capsys: pt.CaptureFixture[str]
):
    pdf = _blank_pdf(tmp_path / "bad-xml.pdf")
    attach_xml(pdf, b"this is not xml")
    assert main([str(pdf)]) == 1
    captured = capsys.readouterr()
    assert "Embedded XML" in captured.err


def test_cli_no_args_prints_usage(capsys: pt.CaptureFixture[str]):
    with pt.raises(SystemExit) as excinfo:
        main([])
    # argparse exits with status 2 on missing positional argument.
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()
