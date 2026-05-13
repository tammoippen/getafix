"""Extract canonical EN 16931 / Factur-X 1.08 term descriptions from the
official xlsx workbook into a JSON sidecar.

Source:
    ``ZF24_EN/Documentation/1_FACTUR-X 1.08 - 2025 12 04 - EN FR - VF.xlsx``

The "Factur-X CII D22B EXTENDED" sheet is the superset — every BT/BG of
every lower profile is present there with the same English Description /
Usage Note text. We use it as the canonical source.

Output:
    ``tools/en16931_terms.json`` — ``{id: {...}}`` keyed by BT-/BG- id.

Run:
    uv run python tools/ingest_en16931_terms.py
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "ZF24_EN/Documentation/1_FACTUR-X 1.08 - 2025 12 04 - EN FR - VF.xlsx"
OUT = ROOT / "tools/en16931_terms.json"

# Column indices (1-based) in the "Factur-X CII D22B EXTENDED" sheet,
# header row = row 4.
COL_BLOCK = 5
COL_ID = 6
COL_CARDINALITY = 9
COL_NAME = 10
COL_DESCRIPTION = 11
COL_USAGE_NOTE = 12
COL_CIUS = 13
COL_BUSINESS_RULES = 14
COL_DATA_TYPE = 15
COL_XML_CARDINALITY = 16
COL_XPATH = 19
COL_PROFILE_MIN = 26
COL_PROFILE_BASIC_WL = 27
COL_PROFILE_BASIC = 28
COL_PROFILE_EN16931 = 29
COL_PROFILE_EXTENDED = 32
COL_PROFILE_FACTURX = 34

PROFILE_COLS: dict[str, int] = {
    "MINIMUM": COL_PROFILE_MIN,
    "BASIC_WL": COL_PROFILE_BASIC_WL,
    "BASIC": COL_PROFILE_BASIC,
    "COMFORT": COL_PROFILE_EN16931,
    "EXTENDED": COL_PROFILE_EXTENDED,
}

ID_RE = re.compile(r"^B[GT]-(X-)?\d+(-\d+)?(-\d+)?$")


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    # Collapse repeated whitespace inside a cell but preserve newline
    # breaks that separate paragraphs in Description / Usage Note.
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in text.split("\n")]
    paragraphs = [p for p in paragraphs if p]
    return "\n".join(paragraphs) or None


def _profiles_present(row: Iterable[Any], cols: dict[str, int]) -> list[str]:
    cells = list(row)
    present: list[str] = []
    for name, col_idx in cols.items():
        value = cells[col_idx - 1]
        if value is None:
            continue
        if str(value).strip().upper() == "X":
            present.append(name)
    return present


def extract() -> dict[str, dict[str, Any]]:
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb["Factur-X CII D22B EXTENDED"]

    terms: dict[str, dict[str, Any]] = {}

    for row in ws.iter_rows(min_row=5, values_only=True):
        bt_id_raw = row[COL_ID - 1]
        if not bt_id_raw:
            continue
        bt_id = str(bt_id_raw).strip()
        if not ID_RE.match(bt_id):
            continue

        name = _norm(row[COL_NAME - 1])
        description = _norm(row[COL_DESCRIPTION - 1])
        usage_note = _norm(row[COL_USAGE_NOTE - 1])
        cius_note = _norm(row[COL_CIUS - 1])
        cardinality = _norm(row[COL_CARDINALITY - 1])
        data_type = _norm(row[COL_DATA_TYPE - 1])
        xpath = _norm(row[COL_XPATH - 1])
        business_rules = _norm(row[COL_BUSINESS_RULES - 1])
        block = _norm(row[COL_BLOCK - 1])

        profiles = _profiles_present(row, PROFILE_COLS)
        factur_x_lowest = _norm(row[COL_PROFILE_FACTURX - 1])

        entry: dict[str, Any] = {
            "id": bt_id,
            "name": name,
            "description": description,
            "usage_note": usage_note,
            "cius_note": cius_note,
            "cardinality": cardinality,
            "data_type": data_type,
            "xpath": xpath,
            "business_rules": business_rules,
            "block": block,
            "profiles": profiles,
            "factur_x_lowest": factur_x_lowest,
        }
        # A BT may appear several times (header / line / different roles).
        # Keep the first occurrence — that's the header-level / canonical
        # row in the EXTENDED sheet's ordering — but record subsequent
        # xpaths so consumers can disambiguate by role.
        if bt_id in terms:
            existing = terms[bt_id]
            occurrences = existing.setdefault("occurrences", [])
            occurrences.append({"xpath": xpath, "cardinality": cardinality})
        else:
            terms[bt_id] = entry

    return terms


def main() -> None:
    terms = extract()
    OUT.write_text(json.dumps(terms, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(terms)} terms to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
