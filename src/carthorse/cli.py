"""Command-line entry point for the ``carthorse`` console script.

Reads a Cross-Industry-Invoice XML file, parses it into a
:class:`carthorse.schema.Document`, runs the business-rule validators
and prints both the invoice and the validation result as a rich
console report.

Requires the optional ``cli`` extra (pulls in ``lxml`` and ``rich``)::

    pip install 'carthorse[cli]'

Exit codes:

* ``0`` — XML parsed cleanly and passed every validator.
* ``1`` — XML parsed but at least one validation rule fired
  (or the document tree could not be parsed as a CII invoice).
* ``2`` — usage / IO / missing dependency error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carthorse",
        description=(
            "Pretty-print a ZUGFeRD / Factur-X Cross-Industry-Invoice "
            "XML file and report business-rule violations."
        ),
    )
    parser.add_argument(
        "xml", type=Path, help="Path to the CII XML file (typically ``factur-x.xml``)."
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip running the BR-* business-rule validators.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    missing: list[str] = []
    try:
        from rich.console import Console
    except ImportError:
        missing.append("rich")
    try:
        import lxml.etree as etree
    except ImportError:
        missing.append("lxml")
    if missing:
        sys.stderr.write(
            f"carthorse CLI needs the optional dependencies: {', '.join(missing)}.\n"
            "Install with: pip install 'carthorse[cli]'\n"
        )
        return 2

    from carthorse.report import render_invoice, render_validation_errors
    from carthorse.schema import Document

    out = Console()
    err = Console(stderr=True)

    xml_path: Path = args.xml
    if not xml_path.is_file():
        err.print(f"[red]Could not read {xml_path}: not a file[/red]")
        return 2
    try:
        tree = etree.parse(str(xml_path))
    except OSError as exc:
        err.print(f"[red]Could not read {xml_path}: {exc}[/red]")
        return 2
    except etree.XMLSyntaxError as exc:
        err.print(f"[red]XML syntax error in {xml_path}: {exc}[/red]")
        return 1

    try:
        doc = Document.from_xml(tree.getroot())
    except (ValueError, TypeError, AssertionError) as exc:
        err.print(
            f"[red]Could not parse {xml_path} as a CII invoice: "
            f"{type(exc).__name__}: {exc}[/red]"
        )
        return 1

    render_invoice(doc, console=out)

    if args.no_validate:
        return 0

    profile = doc.context.guideline.id
    errors = doc.validate_internal(profile)
    render_validation_errors(errors, console=out)
    return 1 if errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
