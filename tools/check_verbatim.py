"""Audit schema docstrings for text copied verbatim from the Factur-X
workbook.

The Factur-X 1.08 workbook text (business-term descriptions, usage
notes, business-rule prose) is the publisher's copyrighted wording —
getafix docstrings must paraphrase it, not copy it. This tool indexes
every word n-gram of the English text columns in the two workbook
sidecars (``tools/business_terms.json``: ``name`` / ``description`` /
``usage_note`` / ``cius_note``; ``tools/business_rules.json``: rule
texts) and slides the same window across every ``Element`` subclass
and field docstring in ``getafix.schema`` (extracted statically via
:func:`check_schema_docs._load_schema`). Any shared run of
:data:`NGRAM` or more consecutive words fails the audit.

Wording that legitimately matches the workbook is allow-listed in
:data:`ALLOWED_RUNS` by its normalised phrase — official
business-term names cited next to their BT/BG ids (the schema-docs
audit *requires* those citations), code-list entries (UNTDID code
names, MIME types), legal references (Directive 2006/112/EC
articles), and proper nouns (SEPA field names, standards bodies).
A flagged run passes when an allowed phrase covers it on word
boundaries with fewer than :data:`NGRAM` residual words — so the
term heading plus a word of sentence spill-over passes, while
copying *more* spec prose around an allow-listed phrase still
fails.

Run:
    uv run python tools/check_verbatim.py
    uv run python tools/check_verbatim.py --ngram 8
    uv run python tools/check_verbatim.py --show-allowed

CI:
    Wired into ``make ids-check`` after the schema-docs audit, so the
    sidecars are freshly regenerated when this runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Sibling-module import: the tools directory is not a package, so put
# it on sys.path before pulling in the schema extractor.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_schema_docs import _load_schema

ROOT = Path(__file__).resolve().parent.parent
TERMS_SIDECAR = ROOT / "tools/business_terms.json"
RULES_SIDECAR = ROOT / "tools/business_rules.json"

# Minimum shared word-run length that counts as verbatim copying.
NGRAM = 6

WORD_RE = re.compile(r"[a-z0-9']+")

# Normalised phrases that are allowed to match the workbook text.
# Two categories only — anything else must be paraphrased:
#
# * official business-term names cited with their BT/BG id;
# * code-list entries, legal / standards citations and proper nouns
#   (facts with no alternative wording).
#
# A flagged run is tolerated when one of these phrases covers it on
# word boundaries and the run carries fewer than NGRAM words beyond
# the phrase (see ``_is_allowed``).
ALLOWED_RUNS: frozenset[str] = frozenset(
    {
        # Official term names next to their BT/BG citation.
        "amount due for payment bt 115",
        "contractual due date of the invoice",
        "invoice line net amount bt 131",
        "invoice total amount with vat bt 112",
        "invoice total amount without vat bt 109",
        "invoice total vat amount bt 110",
        "invoicing period end date bt 74",
        "invoicing period start date bt 73",
        "payment means type code bt 81",
        "seller tax representative party bg 11",
        "sum of allowances on document level bt 107",
        "sum of charges on document level bt 108",
        "sum of invoice line net amounts",
        "tax representative postal address bg 12",
        "tax representative vat identifier bt 63",
        "unit of measure code bt 130",
        "value added tax point date bt 7",
        "value added tax point date code bt 8",
        "vat accounting currency code bt 6",
        "vat category tax amount bt 117",
        "vat category taxable amount bt 116",
        "vat exemption reason code bt 121",
        # Code-list entries, legal citations, proper nouns.
        "751 invoice information for accounting purposes",
        "application pdf image png image jpeg text csv application vnd",
        "spreadsheetml sheet application vnd oasis opendocument spreadsheet",
        "articles 226 items 11 to 15",
        "maintained by the connecting europe facility",
        "structured remittance information creditor reference field",
        "unstructured remittance information field",
        "the call for tender or lot",
        "the iso iec 6523 maintenance agency",
    }
)


def _is_allowed(run: str, n: int) -> bool:
    """Does an ALLOWED_RUNS phrase cover ``run``?

    The phrase must appear in the run on word boundaries, and the
    run may carry at most ``n - 1`` words beyond the phrase — enough
    slack for a term heading to spill into the next sentence, not
    enough to smuggle another copied clause past the audit.
    """
    run_len = len(run.split())
    padded = f" {run} "
    for phrase in ALLOWED_RUNS:
        if f" {phrase} " in padded and run_len - len(phrase.split()) < n:
            return True
    return False


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def _load_sidecar(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(  # noqa: T201
            f"error: missing {path.relative_to(ROOT)} — run "
            "`make ids-check` (or the extract_* tools) first.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return json.loads(path.read_text())


def _spec_corpus() -> list[tuple[str, list[str]]]:
    """Every English workbook text as ``(source_label, tokens)``.

    Sources are the per-term ``name`` / ``description`` / ``usage_note``
    / ``cius_note`` columns and every string column of the rule
    sidecar; texts shorter than the n-gram window can never match and
    are dropped up front.
    """
    corpus: list[tuple[str, list[str]]] = []
    terms = _load_sidecar(TERMS_SIDECAR)
    for term_id, entry in terms.items():
        for column in ("name", "description", "usage_note", "cius_note"):
            text = entry.get(column)
            if isinstance(text, str):
                tokens = _words(text)
                if len(tokens) >= NGRAM:
                    corpus.append((f"{term_id}.{column}", tokens))
    rules = _load_sidecar(RULES_SIDECAR)
    for rule_id, entry in rules.items():
        if not isinstance(entry, dict):
            continue
        for column, text in entry.items():
            if isinstance(text, str):
                tokens = _words(text)
                if len(tokens) >= NGRAM:
                    corpus.append((f"{rule_id}.{column}", tokens))
    return corpus


def _ngram_index(
    corpus: list[tuple[str, list[str]]], n: int
) -> dict[tuple[str, ...], list[tuple[int, int]]]:
    """``n``-gram -> list of (corpus index, token offset) positions."""
    index: dict[tuple[str, ...], list[tuple[int, int]]] = {}
    for corpus_i, (_, tokens) in enumerate(corpus):
        for offset in range(len(tokens) - n + 1):
            gram = tuple(tokens[offset : offset + n])
            index.setdefault(gram, []).append((corpus_i, offset))
    return index


class Finding:
    __slots__ = ("length", "run", "source", "where")

    def __init__(self, where: str, source: str, run: str, length: int):
        self.where: str = where
        self.source: str = source
        self.run: str = run
        self.length: int = length


def _matching_runs(
    tokens: list[str],
    corpus: list[tuple[str, list[str]]],
    index: dict[tuple[str, ...], list[tuple[int, int]]],
    n: int,
) -> list[tuple[str, str, int]]:
    """Maximal shared runs between ``tokens`` and the spec corpus.

    Greedy scan: at each docstring position with an indexed n-gram,
    extend every hit as far as it goes and keep the longest; then jump
    past the matched run (overlapping sub-runs of the same copy are
    noise, distinct copies later in the docstring still get found).
    Returns ``(source_label, run_text, length)`` triples.
    """
    runs: list[tuple[str, str, int]] = []
    i = 0
    while i <= len(tokens) - n:
        hits = index.get(tuple(tokens[i : i + n]))
        if not hits:
            i += 1
            continue
        best_len = 0
        best_source = ""
        for corpus_i, offset in hits:
            src_tokens = corpus[corpus_i][1]
            length = n
            while (
                i + length < len(tokens)
                and offset + length < len(src_tokens)
                and tokens[i + length] == src_tokens[offset + length]
            ):
                length += 1
            if length > best_len:
                best_len = length
                best_source = corpus[corpus_i][0]
        runs.append((best_source, " ".join(tokens[i : i + best_len]), best_len))
        i += best_len - n + 1
    return runs


def _audit(n: int) -> tuple[list[Finding], list[Finding]]:
    """Scan every schema docstring; return (violations, allowed)."""
    corpus = _spec_corpus()
    index = _ngram_index(corpus, n)
    classes, _parents = _load_schema()

    violations: list[Finding] = []
    allowed: list[Finding] = []
    for cls in classes:
        docstrings = [(f"{cls.module}:{cls.name}", cls.docstring)]
        docstrings += [
            (f"{cls.module}:{cls.name}.{f.name}", f.docstring) for f in cls.fields
        ]
        for where, doc in docstrings:
            if not doc:
                continue
            tokens = _words(doc)
            if len(tokens) < n:
                continue
            for source, run, length in _matching_runs(tokens, corpus, index, n):
                finding = Finding(where, source, run, length)
                if _is_allowed(run, n):
                    allowed.append(finding)
                else:
                    violations.append(finding)
    return violations, allowed


def _report(
    violations: list[Finding], allowed: list[Finding], show_allowed: bool
) -> int:
    if show_allowed:
        for f in sorted(allowed, key=lambda f: f.where):
            print(f"allowed  {f.where}  [{f.length} words from {f.source}]")  # noqa: T201
            print(f"         {f.run!r}")  # noqa: T201
    if not violations:
        print(  # noqa: T201
            f"ok: no schema docstring shares {NGRAM}+ unallowed words "
            f"with the workbook text ({len(allowed)} allow-listed runs)."
        )
        return 0
    for f in sorted(violations, key=lambda f: (-f.length, f.where)):
        print(f"error  {f.where}: {f.length}-word run copied from {f.source}")  # noqa: T201
        print(f"       {f.run!r}")  # noqa: T201
    print(  # noqa: T201
        f"\n{len(violations)} verbatim run(s) found. Reword the docstring "
        "to paraphrase the workbook text; only official term names, "
        "code-list entries and legal citations belong in ALLOWED_RUNS."
    )
    return 1


def _build_parser() -> argparse.ArgumentParser:
    assert __doc__
    parser = argparse.ArgumentParser(
        prog="check_verbatim", description=__doc__.split("\n\n", maxsplit=1)[0]
    )
    parser.add_argument(
        "--ngram",
        type=int,
        default=NGRAM,
        help=f"Minimum shared word-run length to flag (default {NGRAM}).",
    )
    parser.add_argument(
        "--show-allowed",
        action="store_true",
        help="Also print every allow-listed run that matched, for "
        "reviewing whether ALLOWED_RUNS entries are still exercised.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    violations, allowed = _audit(args.ngram)
    return _report(violations, allowed, show_allowed=args.show_allowed)


if __name__ == "__main__":
    raise SystemExit(main())
