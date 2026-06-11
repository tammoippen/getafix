"""Generate ``StrEnum`` source for the EN 16931 closed code lists.

Reads the ``EN16931_code_lists_values_v16__used_from_20251115__Fx_1.08.xlsx``
spreadsheet that ships with Factur-X 1.08 and prints Python source
that can be pasted into ``src/getafix/schema/types.py``. Each enum
is bracketed by ``# AUTOGEN START <Name>`` / ``# AUTOGEN END <Name>``
markers so CI can re-run the script and diff the output to detect
drift.

Usage::

    uv run python tools/extract_codelists.py <path-to-xlsx> [<EnumName> ...]

If no enum names are given, every supported list is emitted. The
supported list names match the sheet names: ``Currency``, ``Country``,
``Payment``, ``Allowance``, ``Charge``, ``Time``, ``Text``, ``EAS``,
``ICD``, ``Item``, ``VATEX``, ``MIME``, ``Unit``, ``1001``, ``1153``,
``5305``.

The output is just the enum body (``ClassName(...)`` block). The
top-level ``import enum`` line lives in ``types.py``.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# Ambiguous Unicode codepoints that appear in real-world XLSX cell
# descriptions and trip ruff's RUF003 check on the generated comments.
# Spelled with ``\uXXXX`` escapes so this source file itself stays
# RUF001-clean.
_UNICODE_TO_ASCII: dict[int, str] = {
    0x2018: "'",  # LEFT SINGLE QUOTATION MARK
    0x2019: "'",  # RIGHT SINGLE QUOTATION MARK
    0x201C: '"',  # LEFT DOUBLE QUOTATION MARK
    0x201D: '"',  # RIGHT DOUBLE QUOTATION MARK
    0x2013: "-",  # EN DASH
    0x2014: "-",  # EM DASH
}


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    strings: list[str] = []
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml").decode())  # noqa: S314 — trusted local file
    except KeyError:
        return strings
    for si in root.findall("s:si", _NS):
        # ``<si><t>...</t></si>`` or ``<si><r><t>...</t></r>...</si>``
        chunks = [t.text or "" for t in si.iter() if t.tag.endswith("}t")]
        strings.append("".join(chunks))
    return strings


def _parse_sheet(
    z: zipfile.ZipFile, path: str, shared: list[str]
) -> list[dict[int, object]]:
    root = ET.fromstring(z.read(path).decode())  # noqa: S314 — trusted local file
    sheet_data = root.find("s:sheetData", _NS)
    if sheet_data is None:
        return []
    rows: list[dict[int, object]] = []
    for row in sheet_data.findall("s:row", _NS):
        idx = int(row.attrib["r"]) - 1
        while len(rows) <= idx:
            rows.append({})
        for cell in row.findall("s:c", _NS):
            ref = cell.attrib["r"]
            col = 0
            for ch in re.match(r"[A-Z]+", ref).group():  # type: ignore[union-attr]
                col = col * 26 + (ord(ch) - 64)
            col -= 1
            ctype = cell.attrib.get("t")
            value_el = cell.find("s:v", _NS)
            if value_el is None or value_el.text is None:
                continue
            raw = value_el.text
            if ctype == "s":
                rows[idx][col] = shared[int(raw)]
            elif ctype == "inlineStr":
                inline = cell.find("s:is", _NS)
                rows[idx][col] = (
                    "".join(t.text or "" for t in inline.iter() if t.tag.endswith("}t"))
                    if inline is not None
                    else ""
                )
            else:
                rows[idx][col] = raw
    return rows


@dataclass(slots=True)
class _ListSpec:
    sheet: str  # XLSX sheet name
    code_col: int  # 0-based column with the code value
    name_col: int | None  # column with the human description (or None)
    enum_class: str
    docstring: str
    # Markdown link to the published code list, emitted as a
    # ``Code list: …`` docstring line.
    code_list: str
    member_prefix: str = ""
    # Skip rows whose code matches this regex (e.g. group separators).
    skip_re: re.Pattern[str] | None = None


_LISTS: dict[str, _ListSpec] = {
    "Currency": _ListSpec(
        sheet="Currency",
        code_col=1,
        name_col=0,
        enum_class="Currency",
        docstring="ISO 4217 currency code (BR-CL-03 / BR-CL-04 / BR-CL-05).",
        code_list="[ISO 4217](https://www.iso.org/iso-4217-currency-codes.html)",
    ),
    "Country": _ListSpec(
        sheet="Country",
        code_col=1,
        name_col=0,
        enum_class="Country",
        docstring="ISO 3166-1 alpha-2 country code (BR-CL-14 / BR-CL-15).",
        code_list="[ISO 3166-1 alpha-2](https://www.iso.org/iso-3166-country-codes.html)",
    ),
    "Payment": _ListSpec(
        sheet="Payment",
        code_col=0,
        name_col=1,
        enum_class="UNTDID4461PaymentMeansCode",
        docstring="UNTDID 4461 payment means code (BR-CL-16) — BT-81.",
        code_list="[UNTDID 4461](https://service.unece.org/trade/untdid/d16b/tred/tred4461.htm)",
    ),
    "Allowance": _ListSpec(
        sheet="Allowance",
        code_col=0,
        name_col=1,
        enum_class="UNTDID5189AllowanceReasonCode",
        docstring="UNTDID 5189 allowance reason code (BR-CL-19) — BT-98 / BT-140.",
        code_list="[UNTDID 5189](https://service.unece.org/trade/untdid/d16b/tred/tred5189.htm)",
    ),
    "Time": _ListSpec(
        sheet="Time",
        code_col=2,
        name_col=3,
        enum_class="UNTDID2475TaxPointDateCode",
        docstring="UNTDID 2475 tax-point date code (BR-CL-06) — BT-8.",
        code_list="[UNTDID 2475](https://service.unece.org/trade/untdid/d16b/tred/tred2475.htm)",
    ),
    "EAS": _ListSpec(
        sheet="EAS",
        code_col=0,
        name_col=1,
        enum_class="EASCode",
        docstring="EAS electronic address scheme id (BR-CL-25) — BT-34-1 / BT-49-1.",
        code_list="[EAS](https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/)",
    ),
    "VATEX": _ListSpec(
        sheet="VATEX",
        code_col=0,
        name_col=1,
        enum_class="VATEXCode",
        docstring="CEF VATEX exemption-reason code (BR-CL-22) — BT-121.",
        code_list="[VATEX](https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/)",
    ),
}


def _zfill_name(code: str) -> str:
    """Pythonic enum-member name derived from the code.

    Pure-digit codes (UNTDID payment means, UNTDID time, …) become
    ``CODE_<value>``; alpha codes (ISO 4217, EAS) keep the code as the
    member name with any non-identifier characters stripped.
    """
    if code.isdigit():
        return f"CODE_{code}"
    cleaned = re.sub(r"[^0-9A-Z_a-z]", "_", code)
    if cleaned and cleaned[0].isdigit():
        cleaned = "CODE_" + cleaned
    return cleaned or f"CODE_{code}"


def _emit(spec: _ListSpec, rows: list[dict[int, object]]) -> str:
    members: list[tuple[str, str, str]] = []
    seen_names: set[str] = set()
    for row in rows[1:]:  # skip header row
        code = row.get(spec.code_col)
        if not isinstance(code, str) or not code.strip():
            continue
        code = code.strip()
        if spec.skip_re is not None and spec.skip_re.fullmatch(code):
            continue
        name = _zfill_name(code)
        if name in seen_names:
            # Suffix with the code in case of collisions
            name = f"{name}_{len(seen_names)}"
        seen_names.add(name)
        desc = (
            str(row.get(spec.name_col, "")).strip() if spec.name_col is not None else ""
        )
        # XLSX cells can contain embedded newlines and exotic Unicode
        # quotation marks (e.g. multi-line registry descriptions or
        # ``Pa'anga`` with U+2019). Strip newlines and replace U+2019
        # / U+2018 / U+201C / U+201D so the generated comment stays on
        # a single line and passes ruff's RUF003 ambiguous-character
        # check.
        desc = re.sub(r"\s+", " ", desc)
        # Replace Unicode quotation/dash characters with ASCII so the
        # generated comments pass ruff's RUF003 ambiguous-character
        # check.
        desc = desc.translate(_UNICODE_TO_ASCII)
        members.append((name, code, desc))
    lines: list[str] = []
    lines.append(f"# AUTOGEN START {spec.enum_class}")
    lines.append("@enum.unique")
    lines.append(f"class {spec.enum_class}(enum.StrEnum):")
    lines.append(f'    """{spec.docstring}')
    lines.append("")
    lines.append(f"    Code list: {spec.code_list}.")
    lines.append("")
    lines.append(f"    Source: ``{spec.sheet}`` sheet of the EN16931 code lists v16")
    lines.append("    XLSX shipped with Factur-X 1.08 (autogenerated).")
    lines.append('    """')
    lines.append("")
    for name, code, desc in members:
        if desc:
            lines.append(f'    {name} = "{code}"  # {desc[:60]}')
        else:
            lines.append(f'    {name} = "{code}"')
    lines.append(f"# AUTOGEN END {spec.enum_class}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write(f"Usage: {sys.argv[0]} <xlsx-path> [<list-name> ...]\n")
        return 2
    xlsx_path = sys.argv[1]
    selected = sys.argv[2:] or list(_LISTS)
    with zipfile.ZipFile(xlsx_path) as z:
        shared = _load_shared_strings(z)
        # Build sheet-name -> worksheet path map
        wb = ET.fromstring(z.read("xl/workbook.xml").decode())  # noqa: S314
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels").decode())  # noqa: S314
        rid_to_target = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in rels.findall(
                "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
            )
        }
        sheet_paths: dict[str, str] = {}
        for s in wb.find("s:sheets", _NS).findall("s:sheet", _NS):  # type: ignore[union-attr]
            rid = s.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            sheet_paths[s.attrib["name"]] = "xl/" + rid_to_target[rid]

        out_blocks: list[str] = []
        for key in selected:
            if key not in _LISTS:
                sys.stderr.write(f"unknown list {key!r}; skipping\n")
                continue
            spec = _LISTS[key]
            rows = _parse_sheet(z, sheet_paths[spec.sheet], shared)
            out_blocks.append(_emit(spec, rows))
        sys.stdout.write("\n\n\n".join(out_blocks) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
