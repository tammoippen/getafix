"""Render a Cross-Industry-Invoice XML to an image of the console report.

Dev-only helper. Parses a CII XML file into a
:class:`getafix.schema.Document`, renders it through
:func:`getafix.report.render_invoice` into a Rich console, and exports a
terminal-style image of the report:

* **PNG** (default) — rasterised from the SVG via ``cairosvg``;
* **SVG** — Rich's vector export, no extra dependency.

The output format is taken from the ``--output`` extension. Everything
needed is in the ``dev`` dependency group, so it just works under
``uv run``::

    uv run python tools/render_report.py tests/samples/EN16931_zf24_Rabatte.xml
    uv run python tools/render_report.py invoice.xml -o /tmp/report.svg
    uv run python tools/render_report.py invoice.xml -o out.png --width 120

Exit codes: ``0`` ok; ``1`` read / parse error; ``2`` usage / missing
dependency.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import cast

# Pixels per console column when rasterising the SVG to PNG; ~11 keeps
# the monospaced text crisp without producing an oversized file.
_PNG_PX_PER_COL = 11


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_report",
        description=(
            "Render a CII invoice XML to an image (PNG/SVG) of the "
            "getafix console report."
        ),
    )
    parser.add_argument(
        "source", type=Path, help="Path to a CII XML file (typically factur-x.xml)."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Output image path; format taken from the extension (.png or "
            ".svg). Defaults to <source-stem>.png in the current directory."
        ),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=120,
        help="Console width in columns (default: 100).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    source = cast("Path", args.source)
    width = cast("int", args.width)
    output = cast("Path | None", args.output) or Path(f"{source.stem}.png")

    if not source.is_file():
        _ = sys.stderr.write(f"render_report: not a file: {source}\n")
        return 2

    suffix = output.suffix.lower()
    if suffix not in (".png", ".svg"):
        _ = sys.stderr.write(
            f"render_report: unsupported output extension {suffix!r}; "
            "use .png or .svg\n"
        )
        return 2

    import lxml.etree as etree
    from rich.console import Console

    from getafix.report import render_invoice
    from getafix.schema import Document

    try:
        tree = etree.parse(str(source))
    except (OSError, etree.XMLSyntaxError) as exc:
        _ = sys.stderr.write(f"render_report: could not read {source}: {exc}\n")
        return 1
    try:
        doc = Document.from_xml(tree.getroot())
    except (ValueError, TypeError, AssertionError) as exc:
        _ = sys.stderr.write(
            f"render_report: {source} is not a CII invoice: "
            f"{type(exc).__name__}: {exc}\n"
        )
        return 1

    # Record to an in-memory buffer (not the real stdout) with colours
    # forced on, so the tool's only visible output is the "wrote …" line
    # while the SVG/PNG still captures the full styling.
    console = Console(record=True, width=width, force_terminal=True, file=io.StringIO())
    render_invoice(doc, console=console)
    title = f"getafix — {source.name}"

    if suffix == ".svg":
        console.save_svg(str(output), title=title)
    else:
        try:
            import cairosvg
        except ImportError:
            _ = sys.stderr.write(
                "render_report: PNG output needs 'cairosvg' (in the dev "
                "dependency group).\nRun 'uv sync' or choose an .svg output.\n"
            )
            return 2
        svg = console.export_svg(title=title)
        cairosvg.svg2png(
            bytestring=svg.encode(),
            write_to=str(output),
            output_width=width * _PNG_PX_PER_COL,
        )

    print(f"wrote {output}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
