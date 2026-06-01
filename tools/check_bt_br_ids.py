"""Cross-check every ``BT-``, ``BG-`` and ``BR-`` citation in the carthorse
sources, docstrings and docs against the JSON sidecars
``tools/business_terms.json`` and ``tools/business_rules.json``.

Run:

    uv run python tools/check_bt_br_ids.py

Exits non-zero on any unresolved citation. Suitable for CI.

Citation conventions the script tolerates:

* **EN 16931 base ids absent from the Factur-X xlsx.** ``BG-0`` (the
  invoice root), ``BG-33`` (item classification) and ``BG-34`` (item
  country of origin) are CEN EN 16931 ids; the Factur-X xlsx uses
  ``BT-158-00`` / ``BT-159-00`` etc. for the same wrapper elements.
  Both numberings are documented in the spec.
* **Family-name placeholders** like ``BR-CO``, ``BR-S``, ``BR-FXEXT``
  and ``BR-X-5`` / ``BR-Y`` (where ``X`` / ``Y`` is a placeholder for
  a per-VAT-category instantiation).
* **Zero-padding mismatch.** The XLSX rulebook uses two-digit
  zero-padded ids in some families (``BR-CO-03`` / ``BR-FXEXT-09``)
  and single-digit ids in others (``BR-S-1`` / ``BR-AE-8``).
  Carthorse uses unpadded across the board, matching the
  ``FACTUR-X_*.sch`` schematron. The script normalises both
  directions before lookup.
* **Schematron-only / known artifacts.** ``BR-FX-EN-04`` (in the
  ``.sch`` but not the XLSX rulebook) and the ``.sch`` double-prefix
  ``BR-FXEXT-BR-22..27`` artifact (canonical: ``BR-FXEXT-22..27``)
  are allow-listed here so CI doesn't fail on those documented
  inconsistencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS_JSON = ROOT / "tools/business_terms.json"
RULES_JSON = ROOT / "tools/business_rules.json"

# EN 16931 base-spec ids that don't appear in the Factur-X xlsx but are
# canonical in the European standard. Both numberings are documented.
KNOWN_BG_ALIASES: frozenset[str] = frozenset({"BG-0", "BG-33", "BG-34"})

# Family prefixes that show up as bare strings ("the BR-CO family") in
# narrative text. Accept without resolving to a specific rule.
KNOWN_FAMILIES: frozenset[str] = frozenset(
    {
        "BR",
        "BR-AE",
        "BR-AF",
        "BR-AG",
        "BR-B",
        "BR-CL",
        "BR-CO",
        "BR-DEC",
        "BR-E",
        "BR-FX-DE",
        "BR-FX-EN",
        "BR-FXEXT",
        "BR-FXEXT-CO",
        "BR-G",
        "BR-HYBRID",
        "BR-IC",
        "BR-O",
        "BR-S",
        "BR-Z",
    }
)

# Placeholder rule ids ("BR-X-5" means "BR-{cat}-5 for each VAT
# category"). Each per-category instantiation must exist in the
# sidecar — we accept the placeholder if at least one does.
PLACEHOLDERS: frozenset[str] = frozenset({"BR-X", "BR-Y"})
PLACEHOLDER_CATS: tuple[str, ...] = ("S", "Z", "E", "AE", "G", "IC", "AF", "AG", "O")

# Schematron-only or known-artifact ids that don't appear in the XLSX
# rulebook the sidecar reads from. These are intentional citations of
# documented spec inconsistencies.
KNOWN_RULE_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "BR-FX-EN-04",  # in FACTUR-X_EXTENDED.sch but not the XLSX
        "BR-FXEXT-BR-22",  # .sch double-prefix artifact (canonical: BR-FXEXT-22)
        "BR-FXEXT-BR-23",
        "BR-FXEXT-BR-24",
        "BR-FXEXT-BR-26",
        "BR-FXEXT-BR-27",
    }
)

BT_RE = re.compile(r"\bB[GT]-(?:X-)?[0-9]+(?:-[0-9]+)*\b")
BR_RE = re.compile(r"\bBR(?:-[A-Z0-9]+)+\b")


def _load_sidecars() -> tuple[
    dict[str, dict[str, object]], dict[str, dict[str, object]]
]:
    if not TERMS_JSON.is_file() or not RULES_JSON.is_file():
        sys.stderr.write(
            "error: sidecar(s) missing. Regenerate with:\n"
            "  uv run python tools/extract_business_terms.py\n"
            "  uv run python tools/extract_business_rules.py\n"
        )
        raise SystemExit(2)
    terms = json.loads(TERMS_JSON.read_text())
    rules = json.loads(RULES_JSON.read_text())
    return terms, rules


def _rule_known(rid: str, rules: dict[str, dict[str, object]]) -> bool:
    if rid in rules or rid in KNOWN_FAMILIES or rid in KNOWN_RULE_EXCEPTIONS:
        return True
    parts = rid.split("-")
    # Placeholder pattern: BR-X-5 → try BR-{cat}-5 for each VAT category.
    if len(parts) >= 2 and parts[1] == "X":
        for cat in PLACEHOLDER_CATS:
            candidate = "-".join([parts[0], cat, *parts[2:]])
            if candidate in rules:
                return True
    # Zero-padding mismatch: BR-CO-3 ↔ BR-CO-03.
    *prefix, last = parts
    if last.isdigit():
        for variant in {f"{int(last):02d}", str(int(last))}:
            if variant != last and "-".join([*prefix, variant]) in rules:
                return True
    return False


def _collect_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    src_root = root / "src/carthorse"
    if src_root.exists():
        sources.extend(src_root.rglob("*.py"))
    docs_root = root / "docs"
    if docs_root.exists():
        sources.extend(docs_root.rglob("*.md"))
    for top in ("README.md", "AGENTS.md"):
        p = root / top
        if p.is_file():
            sources.append(p)
    return sorted(sources)


def audit(root: Path = ROOT) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    terms, rules = _load_sidecars()
    bad_bt: dict[str, list[Path]] = {}
    bad_br: dict[str, list[Path]] = {}

    for path in _collect_sources(root):
        text = path.read_text()
        for bt in set(BT_RE.findall(text)):
            if bt in terms or bt in KNOWN_BG_ALIASES:
                continue
            bad_bt.setdefault(bt, []).append(path)
        for br in set(BR_RE.findall(text)):
            if br in PLACEHOLDERS:
                continue
            if _rule_known(br, rules):
                continue
            bad_br.setdefault(br, []).append(path)
    return bad_bt, bad_br


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_bt_br_ids", description=__doc__.split("\n\n", maxsplit=1)[0]
    )
    _ = parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    args = parser.parse_args(argv)

    bad_bt, bad_br = audit(args.root)
    if not bad_bt and not bad_br:
        print("ok: every BT-/BG-/BR- citation resolves against the sidecars.")  # noqa: T201
        return 0

    if bad_bt:
        print("Unknown BT/BG citations:")  # noqa: T201
        for bt in sorted(bad_bt):
            files = ", ".join(
                sorted({str(p.relative_to(args.root)) for p in bad_bt[bt]})
            )
            print(f"  {bt:25s}  {files}")  # noqa: T201
        print()  # noqa: T201
    if bad_br:
        print("Unknown BR citations:")  # noqa: T201
        for br in sorted(bad_br):
            files = ", ".join(
                sorted({str(p.relative_to(args.root)) for p in bad_br[br]})
            )
            print(f"  {br:25s}  {files}")  # noqa: T201
        print()  # noqa: T201
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
