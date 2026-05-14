"""Tests for :mod:`carthorse.cli` — the ``carthorse`` console script.

Exercises every exit-code branch by driving :func:`carthorse.cli.main`
with samples shipped under ``tests/samples`` plus two synthesised
inputs (malformed XML, non-CII XML).
"""

from __future__ import annotations

from pathlib import Path

import pytest as pt

from carthorse.cli import main

SAMPLES = Path(__file__).parent / "samples"
CLEAN_SAMPLE = SAMPLES / "EN16931_Einfach.cii.xml"
INVALID_SAMPLE = SAMPLES / "MINIMUM_facturFrMinimum.xml"  # trips BR-CO-16


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


def test_cli_no_args_prints_usage(capsys: pt.CaptureFixture[str]):
    with pt.raises(SystemExit) as excinfo:
        main([])
    # argparse exits with status 2 on missing positional argument.
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err.lower()
