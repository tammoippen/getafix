"""Dump every CII element from the EXTENDED technical appendix into a JSON sidecar.

The Factur-X / ZUGFeRD "technical appendix" PDF is a GEFEG.FX-generated
walk of the CII schema tree: one block per XML node, each carrying the
node's ``EN16931-ID`` (the BT/BG number), data type, cardinality, usage
prose and the per-profile X-mark matrix. This is the prose/per-element
counterpart to the workbook sidecar produced by
``tools/extract_business_terms.py`` — keyed the same way (BT/BG id) so the
two can be cross-checked or merged.

Layout facts this parser relies on (verified against the EXTENDED PDF):
    * Each entry starts with a bold, bulleted element-name span (left
      column, x≈120) plus a friendly label in the right column. The name
      row is the segment delimiter — one per ``EN16931-ID``.
    * Below the name come dotted ``. Label: value`` property rows. Prose
      values wrap to a continuation column (x≈180); inline code-list tables
      wrap further right (x≈230) and are ignored.
    * Each entry ends with a *footer* — an italic profile header
      ``MINIMUM  BASIC WL  BASIC  EN 16931 (COMFORT)  EXTENDED`` and a
      ``Used in:`` X-row. Crucially this matrix describes the element
      *above* it, so we attach it to the entry whose fields precede it (not
      the next name). Each ``X`` is mapped to its column by x-position.
    * The leading ``.`` bullet of the name row encodes XML nesting depth
      (~5pt per level); we reconstruct a (namespace-prefix-less) path from
      the indent stack. Lowercase element names are XML attributes.

Source:
    The vendored EXTENDED appendix at
    ``ZF24_EN/Documentation/7_Factur-X_1.08_ZUGFeRD_2.4_technical_appendix_profile_EXTENDED.pdf``;
    override via the positional CLI argument.

Output:
    ``tools/specs.json`` — flat JSON object keyed by BT/BG id. Override
    with ``--out``.

Run:
    uv run python tools/extract_specs.py
    uv run python tools/extract_specs.py path/to/EXTENDED.pdf --out specs.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PDF = (
    ROOT
    / "ZF24_EN/Documentation"
    / "7_Factur-X_1.08_ZUGFeRD_2.4_technical_appendix_profile_EXTENDED.pdf"
)
DEFAULT_OUT = ROOT / "tools/specs.json"

# Printed page range of the element catalogue (1-based, as shown in the
# PDF footer). The catalogue runs from the ExchangedDocument block to the
# last trade-line block.
DEFAULT_FIRST_PAGE = 33
DEFAULT_LAST_PAGE = 197

# Font-size buckets used to classify spans (points).
SIZE_HEADER = 8.0  # italic profile header + most field text
SIZE_NAME = 9.0  # bold element name + friendly label

# x bands (PDF user-space points, page width ≈ 595).
NAME_LEFT_MIN = 110.0  # element name column (excludes the x≈83 tree labels)
NAME_LEFT_MAX = 150.0  # element name lives left of here
NAME_RIGHT_MIN = 300.0  # friendly label lives right of here
CONT_MIN_X = 165.0  # prose continuation column lower bound
CONT_MAX_X = 215.0  # ... upper bound (code-table wraps sit at ≈230)

# Profile header label → canonical name emitted in ``profiles``.
PROFILE_CANON: dict[str, str] = {
    "MINIMUM": "MINIMUM",
    "BASIC WL": "BASIC WL",
    "BASIC": "BASIC",
    "EN 16931 (COMFORT)": "EN16931",
    "EXTENDED": "EXTENDED",
}
PROFILE_HEADER_TOL = 12.0  # max x-distance from an X to a column centre

# Property labels (text before the colon) → output key. ``EN16931-ID`` is
# pulled out separately as the dict key; ``Used in`` is handled via the
# X-mark matrix, not as text.
FIELD_LABELS: dict[str, str] = {
    "Data type": "data_type",
    "Occurrence": "occurrence",
    "Usage note": "usage_note",
    "Use": "use",
    "Synonyme": "synonyme",
    "To be used in case": "to_be_used_in_case",
    "Allowed mime codes": "allowed_mime_codes",
    "Diverging cardinality": "diverging_cardinality",
}
# Labels whose value may wrap onto bullet-less continuation lines.
PROSE_KEYS = frozenset(
    {"usage_note", "use", "synonyme", "to_be_used_in_case", "diverging_cardinality"}
)
# Business rules can repeat within one entry → collected into a list.
RULE_LABEL = "Business rule"

ID_RE = re.compile(r"^B[GT]-(X-)?\d+(-\d+)?(-\d+)?$")
LABEL_RE = re.compile(
    r"^(?P<label>Data type|Occurrence|Usage note|Use|Synonyme|EN16931-ID|"
    r"Business rule|To be used in case|Allowed mime codes|Used in|"
    r"Diverging cardinality)\s*:\s*(?P<value>.*)$"
)


def _norm(value: str | None) -> str | None:
    """Strip and collapse internal whitespace; ``None`` for empty cells."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value).strip()
    return text or None


class _Line:
    """A visual line: its spans, baseline y and joined helpers."""

    __slots__ = ("spans", "y")

    def __init__(self, y: float, spans: list[dict[str, Any]]):
        self.y = y
        self.spans = sorted(spans, key=lambda s: s["bbox"][0])

    @property
    def text(self) -> str:
        # Join everything except the dotted bullet markers (ArialMT ".").
        parts = [s["text"] for s in self.spans if s["text"].strip() != "."]
        return _norm(" ".join(parts)) or ""

    @property
    def first_text_x(self) -> float:
        for s in self.spans:
            if s["text"].strip() and s["text"].strip() != ".":
                return s["bbox"][0]
        return self.spans[0]["bbox"][0]


_LINE_TOL = 2.5  # spans within this many points of y share a visual line


def _page_lines(page: fitz.Page) -> list[_Line]:
    """Cluster a page's spans into visual lines, dropping header/footer."""
    spans: list[dict[str, Any]] = []
    text_dict = cast(dict[str, Any], page.get_text("dict"))
    for block in text_dict["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if not span["text"].strip():
                    continue
                y = span["bbox"][1]
                if y < 78 or y > 770:  # running title / footer band
                    continue
                spans.append(span)
    spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))

    lines: list[_Line] = []
    group: list[dict[str, Any]] = []
    ref_y = 0.0
    for span in spans:
        y = span["bbox"][1]
        if group and y - ref_y > _LINE_TOL:
            lines.append(_Line(ref_y, group))
            group = []
        if not group:
            ref_y = y
        group.append(span)
    if group:
        lines.append(_Line(ref_y, group))
    return lines


def _is_profile_header(line: _Line) -> bool:
    return any(
        "Italic" in s["font"]
        and abs(s["size"] - SIZE_HEADER) < 0.3
        and s["text"].strip() == "MINIMUM"
        for s in line.spans
    )


def _profile_columns(line: _Line) -> list[tuple[str, float]]:
    """(canonical name, x-centre) for each profile in the header line."""
    cols: list[tuple[str, float]] = []
    for s in line.spans:
        canon = PROFILE_CANON.get(s["text"].strip())
        if canon and "Italic" in s["font"]:
            cols.append((canon, (s["bbox"][0] + s["bbox"][2]) / 2))
    return cols


def _profiles_from_x(
    columns: list[tuple[str, float]], x_marks: list[float]
) -> list[str]:
    present: list[str] = []
    for canon, centre in columns:
        if any(abs(x - centre) <= PROFILE_HEADER_TOL for x in x_marks):
            present.append(canon)
    return present


def _name_span(line: _Line) -> dict[str, Any] | None:
    """The bold element-name span of a line, if it is an element-name row."""
    for s in line.spans:
        if (
            abs(s["size"] - SIZE_NAME) < 0.2
            and "Bold" in s["font"]
            and NAME_LEFT_MIN < s["bbox"][0] < NAME_LEFT_MAX
            and s["text"].strip()
        ):
            return s
    return None


def _is_entry_start(line: _Line) -> bool:
    """A name row that *begins* an entry: it carries the leading ``.``
    depth bullet. Wrapped element names (e.g. the second line of
    ``TaxTotalAmount <VAT currency>``) have no bullet and must not split
    the entry."""
    first = line.spans[0]
    return (
        _name_span(line) is not None
        and first["text"].strip() == "."
        and first["bbox"][0] < NAME_LEFT_MIN
    )


def _indent_x(name_line: _Line) -> float:
    """The element-row's leading bullet x — a monotonic proxy for XML
    nesting depth (each level shifts the bullet ~5pt right)."""
    return name_line.spans[0]["bbox"][0]


def _parse_entry(lines: list[_Line]) -> tuple[dict[str, Any], float] | None:
    """Build one entry dict from its segment of lines.

    A segment is one element: its bold name, dotted property rows and a
    trailing *footer* — the profile header plus ``Used in:`` X-row that
    sits below the fields and describes this element (not the next one).
    Returns ``(entry, indent_x)`` or ``None`` when the segment carries no
    valid ``EN16931-ID`` (e.g. the namespace-root ``CrossIndustryInvoice``).
    """
    name_line = lines[0]
    name_sp = _name_span(name_line)
    if name_sp is None:
        return None

    # The footer (profile header + Used-in row) trails the fields.
    footer_idx = next(
        (i for i, ln in enumerate(lines) if _is_profile_header(ln)), len(lines)
    )
    columns = _profile_columns(lines[footer_idx]) if footer_idx < len(lines) else []
    x_marks = [
        (s["bbox"][0] + s["bbox"][2]) / 2
        for line in lines[footer_idx:]
        for s in line.spans
        if s["text"].strip() == "X" and "Italic" not in s["font"]
    ]
    profiles = _profiles_from_x(columns, x_marks)

    # The bold name span may carry a "<…>" disambiguation annotation
    # (e.g. "TaxTotalAmount <VAT currency>"); keep only the XML element.
    element = re.split(r"[\s<]", _norm(name_sp["text"]) or "", maxsplit=1)[0] or None
    # Friendly label may wrap across the lines between name and fields.
    friendly_parts: list[str] = []
    for line in lines[:footer_idx]:
        if line is not name_line and LABEL_RE.match(line.text):
            break
        for s in line.spans:
            if (
                abs(s["size"] - SIZE_NAME) < 0.2
                and "Bold" in s["font"]
                and s["bbox"][0] >= NAME_RIGHT_MIN
            ):
                friendly_parts.append(s["text"])

    entry: dict[str, Any] = {
        "element": element,
        "is_attribute": bool(element and element[0].islower()),
        "name": _norm(" ".join(friendly_parts)),
        "profiles": profiles,
    }
    business_rules: list[str] = []
    # Where a bullet-less continuation line should be appended: a prose key,
    # the last business rule, or nowhere.
    cont: tuple[str, str] | None = None  # ("prose", key) | ("rule", "")

    for line in lines[1:footer_idx]:
        m = LABEL_RE.match(line.text)
        if m:
            label, value = m.group("label"), _norm(m.group("value"))
            cont = None
            if label == "Used in":
                pass
            elif label == "EN16931-ID":
                entry["id"] = value
            elif label == RULE_LABEL:
                if value:
                    business_rules.append(value)
                    cont = ("rule", "")
            else:
                key = FIELD_LABELS[label]
                entry[key] = value
                if key in PROSE_KEYS:
                    cont = ("prose", key)
        elif cont and CONT_MIN_X < line.first_text_x < CONT_MAX_X:
            # Continuation onto a bullet-less line. Rule ids that wrap break
            # on a hyphen ("BR-FXEXT-" + "CO-15") and rejoin without a space.
            if cont[0] == "rule":
                prev = business_rules[-1]
                sep = "" if prev.endswith("-") else " "
                business_rules[-1] = _norm(f"{prev}{sep}{line.text}") or prev
            else:
                key = cont[1]
                entry[key] = _norm(f"{entry.get(key) or ''} {line.text}")

    if business_rules:
        entry["business_rules"] = business_rules
    if "id" not in entry or not entry["id"] or not ID_RE.match(entry["id"]):
        return None
    return entry, _indent_x(name_line)


def extract(pdf: Path, first_page: int, last_page: int) -> dict[str, dict[str, Any]]:
    doc = fitz.open(pdf)
    last_page = min(last_page, doc.page_count)

    # Flatten the page range into one ordered stream of visual lines.
    stream: list[_Line] = []
    for page_no in range(first_page, last_page + 1):
        stream.extend(_page_lines(doc[page_no - 1]))

    # Segment on element-name rows: each bold, bulleted name starts an
    # entry, which then owns its property rows and the trailing footer
    # (profile header + Used-in row) up to the next name.
    segments: list[list[_Line]] = []
    for line in stream:
        if _is_entry_start(line):
            segments.append([line])
        elif segments:
            segments[-1].append(line)

    terms: dict[str, dict[str, Any]] = {}
    stack: list[tuple[float, str]] = []  # (indent x, path token)
    for segment in segments:
        parsed = _parse_entry(segment)
        if parsed is None:
            continue
        entry, indent_x = parsed

        # Reconstruct a (namespace-prefix-less) element path: deeper rows
        # sit further right, so pop ancestors at the same or greater indent.
        while stack and stack[-1][0] >= indent_x:
            stack.pop()
        token = entry["element"] or ""
        if entry["is_attribute"]:
            token = "@" + token
        stack.append((indent_x, token))
        entry["depth"] = len(stack)
        entry["path"] = "/" + "/".join(tok for _, tok in stack)

        terms[entry["id"]] = entry

    return terms


def _build_parser() -> argparse.ArgumentParser:
    assert __doc__
    parser = argparse.ArgumentParser(
        prog="extract_specs", description=__doc__.split("\n\n", maxsplit=1)[0]
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default=DEFAULT_PDF,
        type=Path,
        help=f"EXTENDED technical-appendix PDF. Defaults to {DEFAULT_PDF.relative_to(ROOT)}.",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=DEFAULT_OUT,
        type=Path,
        help=f"Output JSON path. Defaults to {DEFAULT_OUT.relative_to(ROOT)}.",
    )
    parser.add_argument(
        "--first-page",
        type=int,
        default=DEFAULT_FIRST_PAGE,
        help="First printed page (1-based).",
    )
    parser.add_argument(
        "--last-page",
        type=int,
        default=DEFAULT_LAST_PAGE,
        help="Last printed page (1-based).",
    )
    return parser


def _relative(path: Path) -> Path:
    if path.is_absolute() and path.is_relative_to(ROOT):
        return path.relative_to(ROOT)
    return path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pdf: Path = args.pdf

    if not pdf.is_file():
        print(f"error: cannot read PDF at {pdf}", file=sys.stderr)  # noqa: T201
        return 2

    terms = extract(pdf, args.first_page, args.last_page)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _ = args.out.write_text(json.dumps(terms, indent=2, sort_keys=True) + "\n")
    print(  # noqa: T201
        f"wrote {len(terms)} entries (pages {args.first_page}-{args.last_page}) "
        f"to {_relative(args.out)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
