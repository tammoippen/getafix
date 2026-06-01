"""Command-line entry point for the ``carthorse`` console script.

Reads a Cross-Industry-Invoice XML file — or a Factur-X / ZUGFeRD PDF
that has one embedded — parses it into a
:class:`carthorse.schema.Document`, runs the business-rule validators
and prints both the invoice and the validation result as a rich
console report.

Requires the optional ``cli`` extra (pulls in ``lxml`` and ``rich``).
PDF input additionally needs the ``pdf`` extra (pypdf)::

    pip install 'carthorse[cli,pdf]'

Exit codes:

* ``0`` — XML parsed cleanly and passed every validator.
* ``1`` — XML parsed but at least one validation rule fired
  (or the document tree could not be parsed as a CII invoice, or no
  Factur-X XML was found in the supplied PDF).
* ``2`` — usage / IO / missing dependency error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carthorse",
        description=(
            "Pretty-print a ZUGFeRD / Factur-X Cross-Industry-Invoice "
            "XML file and report business-rule violations."
        ),
    )
    _ = parser.add_argument(
        "source",
        type=Path,
        help=(
            "Path to a CII XML file (typically ``factur-x.xml``) or a "
            "Factur-X / ZUGFeRD PDF with one embedded."
        ),
    )
    _ = parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip running the BR-* business-rule validators.",
    )
    return parser


def _looks_like_pdf(path: Path) -> bool:
    """``True`` if ``path`` starts with the PDF magic header."""
    try:
        with path.open("rb") as fp:
            return fp.read(5) == b"%PDF-"
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        import lxml.etree as etree
        from rich.console import Console
    except ImportError as exc:
        _ = sys.stderr.write(
            f"carthorse CLI needs the optional 'cli' extra ({exc.name}): "
            f"{exc.msg}.\nInstall with: pip install 'carthorse[cli]'\n"
        )
        return 2

    from carthorse.report import render_invoice, render_validation_errors
    from carthorse.schema import Document

    out = Console()
    err = Console(stderr=True)

    source = cast("Path", args.source)
    no_validate = cast("bool", args.no_validate)
    if not source.is_file():
        err.print(f"[red]Could not read {source}: not a file[/red]")
        return 2

    if source.suffix.lower() == ".pdf" or _looks_like_pdf(source):
        try:
            from carthorse.pdf import extract_xml
        except ImportError:
            err.print(
                "[red]PDF input needs the optional 'pdf' dependency.[/red]\n"
                "[red]Install with: pip install 'carthorse[pdf]'[/red]"
            )
            return 2
        try:
            xml_payload = extract_xml(source)
        except (OSError, ValueError) as exc:
            err.print(f"[red]Could not read PDF {source}: {exc}[/red]")
            return 1
        if xml_payload is None:
            err.print(
                f"[red]No Factur-X / ZUGFeRD XML found in {source} "
                "(looked for the standard attachment names).[/red]"
            )
            return 1
        try:
            tree = etree.ElementTree(etree.fromstring(xml_payload))
        except etree.XMLSyntaxError as exc:
            err.print(f"[red]Embedded XML in {source} is malformed: {exc}[/red]")
            return 1
    else:
        try:
            tree = etree.parse(str(source))
        except OSError as exc:
            err.print(f"[red]Could not read {source}: {exc}[/red]")
            return 2
        except etree.XMLSyntaxError as exc:
            err.print(f"[red]XML syntax error in {source}: {exc}[/red]")
            return 1

    try:
        doc = Document.from_xml(tree.getroot())
    except (ValueError, TypeError, AssertionError) as exc:
        err.print(
            f"[red]Could not parse {source} as a CII invoice: "
            f"{type(exc).__name__}: {exc}[/red]"
        )
        return 1

    render_invoice(doc, console=out)

    if no_validate:
        return 0

    profile = doc.context.guideline.id
    errors = doc.validate_internal(profile)
    render_validation_errors(errors, console=out)
    return 1 if errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
