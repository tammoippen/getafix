"""Statically audit (via griffe) every ``Element`` subclass in
``src/carthorse/schema``.

Catches four classes of regression that hand-review keeps missing:

1. **Missing docstrings** — every ``Element`` subclass and every
   dataclass field on one must carry a docstring.
2. **Missing BT-/BG- citation** — every such docstring must reference
   the term it models (e.g. ``BT-31``, ``BG-X-49``), and each cited id
   must resolve against the workbook sidecar.
3. **Profile gate below the workbook minimum** — a class / field's
   effective ``profile`` gate (its own metadata, the inner Element's
   class profile, or the enclosing element's gate) must not render the
   term *below* the earliest profile the sidecar admits it on. A gate
   stricter than the minimum is fine (the schema may defer an optional
   element to a higher profile). Because the schema's gate tracks XSD
   structural permissibility while the sidecar tracks the EN 16931
   semantic appendix, the two legitimately diverge for a handful of
   elements; those are allow-listed in :data:`KNOWN_PROFILE_EXCEPTIONS`,
   each documented at the field itself.
4. **Missing XSD-allowed children** — for each class, look the class's
   ``namespace`` + ``tag`` up in the xpath tree
   (``tools/business_terms_tree.json``). Any direct child node that
   isn't backed by a declared field is reported, with its BT/BG id
   and per-profile coverage. The tool intentionally doesn't fail on
   missing children — the maintainer decides whether to model them
   (EXTENDED-only attributes are valid omissions until needed) — but
   the report makes the gap visible.

Checks 1-3 fail the audit; the fourth is informational.

``--check-citations`` adds a fourth, broader pass: it scans every ``BT-``,
``BG-`` **and** ``BR-`` citation across ``src/``, ``docs/``,
``README.md`` and ``AGENTS.md`` prose — not just schema docstrings —
and fails on any id that doesn't resolve against the
``tools/business_terms.json`` / ``tools/business_rules.json``
sidecars. This catches typos / hallucinated spec references in
narrative text and the business-rule citations the AST audit never
looks at. See :func:`_cross_check_citations` for the tolerated-id
conventions (EN 16931 base groups, BR family placeholders,
zero-padding, schematron-only artifacts).

Run:
    uv run python tools/check_schema_docs.py
    uv run python tools/check_schema_docs.py --show-missing
    uv run python tools/check_schema_docs.py --class PayeeTradeParty
    uv run python tools/check_schema_docs.py --check-citations

CI:
    Wired into ``make ids-check`` with ``--check-citations`` so the
    schema-docs audit and the BT/BG/BR citation cross-check run in a
    single invocation.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import griffe
from griffe import ExprBinOp, ExprCall, ExprDict, ExprKeyword, ExprName, ExprSubscript

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
TREE_SIDECAR = ROOT / "tools/business_terms_tree.json"
TERMS_SIDECAR = ROOT / "tools/business_terms.json"

# Submodules we skip entirely — the reflective core, primitives, and
# the enum / type vendoring module hold no Element subclasses worth
# auditing for BT/BG coverage.
SKIP_FILES: frozenset[str] = frozenset(
    {"__init__.py", "_numeric.py", "element.py", "types.py"}
)

# One pattern for every BT-/BG- citation, shared by the schema-docstring
# audit and the broad citation cross-check so the two can't drift.
BT_BG_RE = re.compile(r"\bB[GT]-(?:X-)?[0-9]+(?:-[0-9]+)*\b")


# ---------------------------------------------------------------------------
# Schema extraction (griffe)
#
# griffe statically loads the package — no import, no runtime side
# effects — and hands back Class / Attribute objects that already carry
# what hand-rolled AST walking had to reconstruct: class *and* attribute
# docstrings, resolved bases, and ClassVar / field values as navigable
# expression trees. We distil each Element subclass into the small
# ClassInfo / FieldInfo carriers the audit below consumes.
#
# The audit reads source rather than importing the package because the
# field docstrings it checks — the bare string after each field — are
# discarded by the interpreter at runtime and only ever exist in source.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FieldInfo:
    name: str
    type_str: str
    inner_class: str | None
    tag: str | None
    ns: str | None
    profile: str | None
    docstring: str | None


@dataclass(slots=True)
class ClassInfo:
    name: str
    module: str
    tag: str | None
    ns: str | None
    profile: str | None
    docstring: str | None
    fields: list[FieldInfo]


# Annotation leaves that can't name an Element subclass — keep
# ``inner_class`` only when it could be one.
_BUILTIN_TYPES: frozenset[str] = frozenset(
    {
        "str",
        "int",
        "bool",
        "float",
        "bytes",
        "Decimal",
        "date",
        "datetime",
        "None",
        "Any",
    }
)


def _base_simple_names(cls: griffe.Class) -> list[str]:
    """Unqualified names of ``cls``'s bases — ``mod.Element`` → ``Element``."""
    return [str(base).rsplit(".", maxsplit=1)[-1] for base in cls.bases]


def _element_subclass_names(candidates: list[griffe.Class]) -> set[str]:
    """Names of every ``Element`` subclass among ``candidates``, including
    transitive ones (``GlobalID(ISO6523SchemeId(SchemeID(Element)))``).

    Fixed-point: seed with ``"Element"`` (defined in the skipped
    reflective core) and keep adding any class with a base already in
    the set.
    """
    subclasses: set[str] = {"Element"}
    bases_by_name = [(c.name, _base_simple_names(c)) for c in candidates]
    changed = True
    while changed:
        changed = False
        for name, bases in bases_by_name:
            if name not in subclasses and any(b in subclasses for b in bases):
                subclasses.add(name)
                changed = True
    return subclasses


def _terminal_name(value: object) -> str | None:
    """``Profile.EXTENDED`` → ``"EXTENDED"``; ``Namespace.ram`` → ``"ram"``.

    griffe stringifies an attribute-access expression back to source, so
    the enum member is the segment after the last dot.
    """
    if value is None:
        return None
    return str(value).rsplit(".", maxsplit=1)[-1]


def _string_literal(value: object) -> str | None:
    """A griffe string constant arrives as its source repr (``"'ID'"``);
    evaluate it back to the bare ``ID``. Non-string / non-literal
    expressions yield ``None``.
    """
    if not isinstance(value, str):
        return None
    try:
        literal = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None
    return literal if isinstance(literal, str) else None


def _inner_class_name(annotation: object) -> str | None:
    """The (likely Element) class named by ``annotation``, stripping
    ``X | None`` unions and ``list[...]`` / ``Sequence[...]`` wrappers.

    Returns ``None`` for builtins, multi-class unions, or anything more
    exotic. Operates on griffe's expression tree.
    """
    if isinstance(annotation, ExprBinOp) and annotation.operator == "|":
        candidates = [
            name
            for name in (
                _inner_class_name(annotation.left),
                _inner_class_name(annotation.right),
            )
            if name and name != "None"
        ]
        return candidates[0] if len(candidates) == 1 else None
    if isinstance(annotation, ExprSubscript):
        return _inner_class_name(annotation.slice)
    if isinstance(annotation, ExprName):
        return annotation.name
    # The ``None`` arm of an optional union arrives as a bare string.
    if isinstance(annotation, str):
        return annotation if annotation == "None" else None
    return None


def _field_metadata(value: object) -> tuple[str | None, str | None, str | None]:
    """Pull ``(tag, ns, profile)`` out of a ``field(metadata={...})``
    expression. Returns all-``None`` for a plain default value.
    """
    if not isinstance(value, ExprCall) or str(value.function) != "field":
        return None, None, None
    tag: str | None = None
    ns: str | None = None
    profile: str | None = None
    for arg in value.arguments:
        if not isinstance(arg, ExprKeyword) or arg.name != "metadata":
            continue
        meta = arg.value
        if not isinstance(meta, ExprDict):
            continue
        for key_node, val_node in zip(meta.keys, meta.values, strict=False):
            key = _string_literal(key_node)
            if key == "tag":
                tag = _string_literal(val_node)
            elif key == "ns":
                ns = _terminal_name(val_node)
            elif key == "profile":
                profile = _terminal_name(val_node)
    return tag, ns, profile


def _is_classvar(attr: griffe.Attribute) -> bool:
    """A ClassVar lives at class level only — griffe never tags it as an
    instance attribute, whereas a dataclass field always is.
    """
    return "class-attribute" in attr.labels and "instance-attribute" not in attr.labels


def _extract_class(cls: griffe.Class) -> ClassInfo:
    tag: str | None = None
    ns: str | None = None
    profile: str | None = None
    fields: list[FieldInfo] = []

    # Own attributes only — griffe's ``.attributes`` view folds in
    # inherited fields, but the audit treats each class by what it
    # declares (inherited ClassVars are resolved separately in
    # :func:`_inherit_classvars`; inherited fields in :func:`_all_fields`).
    own_attributes = (m for m in cls.members.values() if m.is_attribute)
    for attr in own_attributes:
        name = attr.name
        # ``tag``/``namespace``/``profile`` ClassVars carry the XML
        # binding; griffe strips the ``ClassVar[...]`` wrapper, so read
        # the value expression directly.
        if _is_classvar(attr):
            if name == "tag":
                tag = _string_literal(attr.value)
            elif name == "namespace":
                ns = _terminal_name(attr.value)
            elif name == "profile":
                profile = _terminal_name(attr.value)
            continue

        # Skip private bookkeeping fields and the internal ``currency``
        # context-carrier (threads the document currency through amount
        # fields; not its own XML element, see ``Element._children_xml``).
        if name.startswith("_") or name == "currency":
            continue

        field_tag, field_ns, field_profile = _field_metadata(attr.value)
        inner_class = _inner_class_name(attr.annotation)
        if inner_class in _BUILTIN_TYPES:
            inner_class = None

        fields.append(
            FieldInfo(
                name=name,
                type_str=str(attr.annotation) if attr.annotation is not None else "",
                inner_class=inner_class,
                tag=field_tag,
                ns=field_ns,
                profile=field_profile,
                docstring=attr.docstring.value if attr.docstring else None,
            )
        )

    return ClassInfo(
        name=cls.name,
        module=cls.module.filepath.name,
        tag=tag,
        ns=ns,
        profile=profile,
        docstring=cls.docstring.value if cls.docstring else None,
        fields=fields,
    )


def _inherit_classvars(
    classes: list[ClassInfo], parents_by_name: dict[str, list[str]]
) -> None:
    """Resolve inherited ``tag`` / ``namespace`` / ``profile`` ClassVars
    for transitive subclasses (``GlobalID(ISO6523SchemeId)``) that don't
    re-declare them.
    """
    by_name = {c.name: c for c in classes}
    for cls in classes:
        if cls.tag is not None and cls.ns is not None and cls.profile is not None:
            continue
        for parent_name in parents_by_name.get(cls.name, []):
            parent = by_name.get(parent_name)
            if parent is None:
                continue
            if cls.tag is None:
                cls.tag = parent.tag
            if cls.ns is None:
                cls.ns = parent.ns
            if cls.profile is None:
                cls.profile = parent.profile


def _load_schema() -> tuple[list[ClassInfo], dict[str, list[str]]]:
    """Load every ``Element`` subclass in ``carthorse.schema`` via griffe.

    Returns the extracted :class:`ClassInfo` list and a
    ``name -> base-names`` map (used downstream to walk inherited
    fields). Modules in :data:`SKIP_FILES` and imported (aliased)
    classes are excluded.
    """
    package = griffe.load("carthorse", search_paths=[str(SRC_ROOT)])
    schema = package["schema"]
    # Sort modules by filename so the audit order is deterministic and
    # stable across griffe's internal module ordering.
    modules = sorted(
        (m for m in schema.modules.values() if m.filepath.name not in SKIP_FILES),
        key=lambda m: m.filepath.name,
    )
    candidates: list[griffe.Class] = [
        cls for module in modules for cls in module.classes.values() if not cls.is_alias
    ]
    subclasses = _element_subclass_names(candidates)
    classes: list[ClassInfo] = []
    parents_by_name: dict[str, list[str]] = {}
    for cls in candidates:
        if cls.name not in subclasses:
            continue
        parents_by_name[cls.name] = _base_simple_names(cls)
        classes.append(_extract_class(cls))
    _inherit_classvars(classes, parents_by_name)
    return classes, parents_by_name


# ---------------------------------------------------------------------------
# Sidecar lookups
# ---------------------------------------------------------------------------


def _load_sidecar(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(  # noqa: T201
            f"error: missing {path.relative_to(ROOT)} — run "
            "`uv run python tools/extract_business_terms.py` first.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return json.loads(path.read_text())


def _walk_tree(
    tree: dict[str, Any], path: tuple[str, ...] = ()
) -> Iterable[tuple[tuple[str, ...], dict[str, Any]]]:
    """Yield every (xpath-segments, node) pair in the tree."""
    for key, node in tree.items():
        full = (*path, key)
        yield full, node
        children = node.get("children")
        if children:
            yield from _walk_tree(children, full)


def _positions_for(
    tree: dict[str, Any], ns: str, tag: str
) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    """Every tree position whose last segment is ``/{ns}:{tag}``."""
    target = f"/{ns}:{tag}"
    return [(path, node) for path, node in _walk_tree(tree) if path[-1] == target]


def _collect_ids(nodes: Iterable[dict[str, Any]]) -> list[str]:
    """Distinct BT/BG ids across ``nodes``, in first-seen order.

    The tree carries only the short ``name``; we look the full name +
    description back up in the flat ``business_terms.json`` sidecar.
    De-duplicates by id so repeated occurrences of the same BT (the
    same term appearing on every profile sheet) collapse to one.
    """
    seen: list[str] = []
    for n in nodes:
        bt_id = n.get("id")
        if not bt_id or bt_id in seen:
            continue
        seen.append(bt_id)
    return seen


def _format_term(bt_id: str, terms: dict[str, Any]) -> str:
    """``BT-31 'Seller VAT identifier' — The Seller's VAT id…``.

    Pulls the ``name`` + ``description`` out of the flat sidecar so
    the audit message tells the maintainer *what* the field should
    say, not just the id. Description is clipped to a single line.
    """
    entry = terms.get(bt_id, {})
    name = entry.get("name") or ""
    description = entry.get("description") or ""
    # Single line — collapse paragraph breaks to spaces so the audit
    # output stays one error per line.
    if description:
        description = " ".join(description.split())
    if name and description:
        return f"{bt_id} {name!r} — {description}"
    if name:
        return f"{bt_id} {name!r}"
    return bt_id


def _format_suggestion(ids: list[str], terms: dict[str, Any]) -> str:
    if not ids:
        return ""
    if len(ids) == 1:
        return f" — expected {_format_term(ids[0], terms)}"
    pieces = [_format_term(i, terms) for i in ids]
    joined = "\n    " + "\n    ".join(pieces)
    return f" — expected one of:{joined}"


# EN 16931 base groups dropped or renamed by Factur-X, kept here so
# existing prose referencing them doesn't fail the audit. Shared by
# the per-docstring audit and the broad citation cross-check below.
TOLERATED_MISSING_IDS: frozenset[str] = frozenset({"BG-0", "BG-33", "BG-34"})


def _xpath_index(terms: dict[str, Any]) -> dict[str, str]:
    """``bt_id -> primary xpath``. Picks the first (lowest-profile)
    occurrence to disambiguate when the same id is at multiple
    positions; used by :func:`_audit_citations` to decide whether a
    cited BT lives *within* the class's tree subtree (allowing the
    BT-2 vs BT-2-00 wrapper/value pattern to validate cleanly).
    """
    index: dict[str, str] = {}
    for bt_id, entry in terms.items():
        for occ in entry.get("occurrences", []):
            xpath = occ.get("xpath")
            if xpath:
                index.setdefault(bt_id, xpath)
                break
    return index


def _ids_at_xpath_index(terms: dict[str, Any]) -> dict[str, list[str]]:
    """``xpath -> [bt_id, ...]``. The xpath tree collapses multiple
    ids at the same xpath to one (e.g. ``BT-147-00`` allowance and
    ``BT-X-302-00`` charge live at the same
    ``AppliedTradeAllowanceCharge`` element — only one survives in
    the tree). Audit cross-checks should see both; build the reverse
    index from the flat sidecar where every occurrence is preserved.
    """
    index: dict[str, list[str]] = {}
    for bt_id, entry in terms.items():
        seen_xpaths: set[str] = set()
        for occ in entry.get("occurrences", []):
            xpath = occ.get("xpath")
            if xpath and xpath not in seen_xpaths:
                seen_xpaths.add(xpath)
                bucket = index.setdefault(xpath, [])
                if bt_id not in bucket:
                    bucket.append(bt_id)
    return index


def _xpath_of_position(path: tuple[str, ...]) -> str:
    """Walk a tree-segment tuple back to an xpath string."""
    return "".join(path)


def _cited_ids(docstring: str | None) -> list[str]:
    """Every BT-/BG- id called out in ``docstring``, in document order.

    Returns the full match (``BT-X-468`` not just the ``X-`` group).
    Duplicates collapse to first-seen.
    """
    if not docstring:
        return []
    seen: list[str] = []
    for match in BT_BG_RE.finditer(docstring):
        bt = match.group(0)
        if bt not in seen:
            seen.append(bt)
    return seen


def _audit_citations(
    docstring: str | None,
    canonical_ids: list[str],
    position_xpaths: list[str],
    where: str,
    label: str,
    terms: dict[str, Any],
    xpath_index: dict[str, str],
) -> list[Issue]:
    """Three checks against the BT/BG numbers in ``docstring``:

    1. *Existence* — every cited id must resolve in the flat
       ``business_terms.json`` sidecar; a typo or invented id fails
       the audit. A small set of EN 16931 base ids dropped by
       Factur-X (``BG-0`` / ``BG-33`` / ``BG-34``) is tolerated.
    2. *Primary correctness* — at least one cited id must either be
       a canonical id for the class / field's tree position **or**
       live at an xpath that is the position itself or a descendant
       of it. The descendant rule lets a wrapper field cite both the
       wrapper id (``BT-2-00``) and the inner value id (``BT-2``)
       without false-positive failures.
    3. *Uncited canonical ids* — every canonical id missing from the
       docstring is reported as an info note (the maintainer decides
       whether to add it; multi-position generic shapes legitimately
       cite only the most representative).

    ``label`` is ``"class"`` or ``"field"`` for the error message.
    """
    if not docstring:
        return []
    issues: list[Issue] = []
    cited = _cited_ids(docstring)
    for bt in cited:
        if bt in TOLERATED_MISSING_IDS:
            continue
        if bt not in terms:
            issues.append(
                Issue(
                    "error",
                    where,
                    f"{label} docstring cites {bt} which is not in the workbook sidecar",
                )
            )
    if canonical_ids and position_xpaths:
        canon_set = set(canonical_ids)

        def _is_in_subtree(bt_id: str) -> bool:
            cited_xpath = xpath_index.get(bt_id)
            if cited_xpath is None:
                return False
            for pos_xpath in position_xpaths:
                if cited_xpath == pos_xpath or cited_xpath.startswith(pos_xpath + "/"):
                    return True
            return False

        matched = [
            bt
            for bt in cited
            if bt not in TOLERATED_MISSING_IDS
            and (bt in canon_set or _is_in_subtree(bt))
        ]
        if not matched:
            issues.append(
                Issue(
                    "error",
                    where,
                    f"{label} docstring cites {cited!r} but none match the "
                    f"canonical id(s) for this XSD position (or a descendant)"
                    + _format_suggestion(canonical_ids, terms),
                )
            )
        uncited = [bt for bt in canonical_ids if bt not in set(cited)]
        for bt in uncited:
            issues.append(
                Issue(
                    "info",
                    where,
                    f"{label} docstring does not cite canonical id "
                    f"{_format_term(bt, terms)}",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class Issue:
    __slots__ = ("message", "severity", "where")

    def __init__(self, severity: str, where: str, message: str):
        self.severity: str = severity  # "error" | "info"
        self.where: str = where
        self.message: str = message


def _all_fields(
    cls: ClassInfo,
    classes_by_name: dict[str, ClassInfo],
    parents_by_name: dict[str, list[str]],
) -> list[FieldInfo]:
    """``cls.fields`` plus every field inherited from a parent
    ``Element`` subclass, walking up the chain.

    Subclasses that override a parent field re-declare it; first-seen
    wins so the subclass version is what ends up in the returned
    list. Used to compute the modelled-tag set for the
    missing-attribute report — a child of ``TradeAllowanceCharge``
    inherits its fields, the audit shouldn't claim those are missing.
    """
    out: list[FieldInfo] = list(cls.fields)
    seen_names: set[str] = {f.name for f in out}
    queue = list(parents_by_name.get(cls.name, []))
    while queue:
        parent_name = queue.pop(0)
        parent = classes_by_name.get(parent_name)
        if parent is None:
            continue
        for f in parent.fields:
            if f.name in seen_names:
                continue
            out.append(f)
            seen_names.add(f.name)
        queue.extend(parents_by_name.get(parent_name, []))
    return out


# Canonical profile ranking. A schema ``profile`` gate names the
# earliest profile at which an element / field appears; the workbook
# sidecar records the same as a per-node profile matrix. Declared gates
# use the ``Profile`` enum member names (``COMFORT``) while the sidecar
# uses the workbook sheet tag (``EN16931``) for that same rung — both
# fold onto one ordinal scale.
_PROFILE_RANK: dict[str, int] = {
    "MINIMUM": 0,
    "BASIC_WL": 1,
    "BASIC": 2,
    "COMFORT": 3,
    "EN16931": 3,
    "EXTENDED": 4,
}
_RANK_NAME: dict[int, str] = {
    0: "MINIMUM",
    1: "BASIC_WL",
    2: "BASIC",
    3: "COMFORT",
    4: "EXTENDED",
}

# Profile gates that intentionally sit *below* the workbook's semantic
# minimum, keyed by ``module:Class.field``. The schema's gate tracks XSD
# structural permissibility, the sidecar matrix tracks the EN 16931
# semantic appendix — and for these the two legitimately diverge. Each
# is documented at the field itself; they are allow-listed here the same
# way the citation audit allow-lists ``KNOWN_BG_ALIASES`` /
# ``KNOWN_RULE_EXCEPTIONS``.
KNOWN_PROFILE_EXCEPTIONS: frozenset[str] = frozenset(
    {
        # XSD permits the party address / tax registration at MINIMUM;
        # the EN BASIC_WL requirement is enforced by BR-10 validation.
        "party.py:BuyerTradeParty.address",
        "party.py:BuyerTradeParty.tax_registrations",
        # Payee sub-elements: the XSD admits them at the party's own
        # profile (BASIC_WL+, contact COMFORT+) even though the EN
        # appendix lists the BG-X-/BT-X- ids at EXTENDED. The vendored
        # per-profile XSDs (see tests/strategies.py) are the authority.
        "party.py:PayeeTradeParty.contact",
        "party.py:PayeeTradeParty.address",
        "party.py:PayeeTradeParty.electronic_address",
        "party.py:PayeeTradeParty.tax_registrations",
        # One XSD node shared by an EN allowance (COMFORT) and a Factur-X
        # charge extension; the sidecar collapses it to the EXTENDED
        # charge-side id BT-X-300.
        "line.py:AppliedTradeAllowanceCharge.calculation_percent",
        "line.py:AppliedTradeAllowanceCharge.basis_amount",
        # Factur-X CIUS extension dates the XSD admits earlier than the
        # appendix narrative; carthorse follows the XSD (see field docs).
        "references.py:DespatchAdviceReferencedDocument.issue_date_time",
        "references.py:ReceivingAdviceReferencedDocument.issue_date_time",
    }
)


def _profile_rank(name: str | None) -> int:
    """Declared / assumed profile gate → ordinal. ``None`` (no gate)
    assumes MINIMUM, matching the runtime fallback in
    ``Element._children_xml``.
    """
    if name is None:
        return 0
    return _PROFILE_RANK.get(name, 0)


def _sidecar_min_rank(profiles: list[str]) -> int | None:
    """Ordinal of the earliest profile a sidecar node is present on, or
    ``None`` when the node lists no recognised profile.
    """
    ranks = [_PROFILE_RANK[p] for p in profiles if p in _PROFILE_RANK]
    return min(ranks) if ranks else None


def _positions_min_rank(profile_lists: list[list[str]]) -> int | None:
    """Earliest profile (ordinal) across every XSD position a class /
    field resolves to — i.e. the most permissive profile the workbook
    admits the term on. ``None`` when no position carries a profile.

    Taking the minimum across positions is the lenient choice: a shape
    reused at several positions is judged against the easiest one, so a
    generic ``SchemeID`` gated at MINIMUM isn't faulted for also
    appearing at a higher-profile position.
    """
    mins = [r for ps in profile_lists if (r := _sidecar_min_rank(ps)) is not None]
    return min(mins) if mins else None


def _audit_profile(
    gate_rank: int,
    gate_display: str,
    profile_lists: list[list[str]],
    where: str,
    label: str,
) -> Issue | None:
    """Flag a ``profile`` gate that would render an element / field
    *below* the profile the workbook first admits it on.

    ``gate_rank`` is the effective render gate (the field's own
    ``profile`` metadata, the inner Element's class profile, or — for an
    ungated leaf field — the enclosing element's gate, matching
    ``Element._children_xml``). Rendering at or above the workbook
    minimum is correct; rendering below it emits a non-conformant
    element, which is the bug this catches. Over-strict gates (above the
    minimum) are left alone — the schema may legitimately defer an
    optional element to a higher profile.
    """
    workbook_min = _positions_min_rank(profile_lists)
    if workbook_min is None or gate_rank >= workbook_min:
        return None
    return Issue(
        "error",
        where,
        f"{label} profile {gate_display} renders below the workbook "
        f"minimum {_RANK_NAME[workbook_min]} — the term first appears there",
    )


def _audit_class(
    cls: ClassInfo,
    classes_by_name: dict[str, ClassInfo],
    parents_by_name: dict[str, list[str]],
    tree: dict[str, Any],
    terms: dict[str, Any],
    xpath_index: dict[str, str],
    ids_at_xpath: dict[str, list[str]],
) -> list[Issue]:
    issues: list[Issue] = []
    where = f"{cls.module}:{cls.name}"

    if cls.tag is None:
        issues.append(Issue("error", where, "missing tag ClassVar"))
        return issues

    ns = cls.ns or "ram"

    # Resolve the class to its tree position(s) up front — we re-use
    # the same lookup for both the class-level audit message and the
    # per-field child lookup below.
    positions = _positions_for(tree, ns, cls.tag)
    class_xpaths = [_xpath_of_position(path) for path, _node in positions]
    # Use the flat-sidecar reverse index so both ids at a shared
    # xpath (allowance + charge, wrapper + value) show up.
    class_ids: list[str] = []
    for xp in class_xpaths:
        for bt in ids_at_xpath.get(xp, []):
            if bt not in class_ids:
                class_ids.append(bt)

    # Class docstring + BT/BG citation.
    if not cls.docstring:
        issues.append(
            Issue(
                "error",
                where,
                f"missing class docstring{_format_suggestion(class_ids, terms)}",
            )
        )
    elif not BT_BG_RE.search(cls.docstring):
        issues.append(
            Issue(
                "error",
                where,
                "class docstring lacks a BT-/BG- citation"
                + _format_suggestion(class_ids, terms),
            )
        )
    issues.extend(
        _audit_citations(
            cls.docstring, class_ids, class_xpaths, where, "class", terms, xpath_index
        )
    )

    # Class profile gate vs. the workbook profile matrix.
    class_issue = _audit_profile(
        _profile_rank(cls.profile),
        cls.profile or "MINIMUM (assumed)",
        [node.get("profiles", []) for _path, node in positions],
        where,
        "class",
    )
    if class_issue is not None:
        issues.append(class_issue)

    # Modelled-tag set for the missing-attribute report — include
    # inherited fields so a subclass doesn't claim its parent's
    # fields are missing.
    modelled_tags: set[str] = set()
    for f in _all_fields(cls, classes_by_name, parents_by_name):
        if f.tag:
            modelled_tags.add(f"/{f.ns or 'ram'}:{f.tag}")
        elif f.inner_class and f.inner_class in classes_by_name:
            nested = classes_by_name[f.inner_class]
            if nested.tag:
                modelled_tags.add(f"/{f.ns or nested.ns or 'ram'}:{nested.tag}")

    # Field docstrings + BT/BG citations — declared-on-class only.
    for f in cls.fields:
        field_where = f"{where}.{f.name}"

        # Resolve the field's effective XML tag for the cross-check.
        effective_tag: str | None = None
        effective_ns: str | None = f.ns
        if f.tag:
            effective_tag = f.tag
        elif f.inner_class and f.inner_class in classes_by_name:
            nested = classes_by_name[f.inner_class]
            effective_tag = nested.tag
            if effective_ns is None:
                effective_ns = nested.ns
        if effective_ns is None:
            effective_ns = "ram"
        field_key: str | None = None
        if effective_tag is not None:
            field_key = f"/{effective_ns}:{effective_tag}"

        # Look the field up inside each parent-class tree position.
        field_ids: list[str] = []
        field_xpaths: list[str] = []
        field_nodes: list[dict[str, Any]] = []
        if field_key is not None:
            for path, node in positions:
                child = node.get("children", {}).get(field_key)
                if not child:
                    continue
                field_xpaths.append(_xpath_of_position((*path, field_key)))
                field_nodes.append(child)
            for xp in field_xpaths:
                for bt in ids_at_xpath.get(xp, []):
                    if bt not in field_ids:
                        field_ids.append(bt)

        # Field profile gate vs. the workbook. The field's *own* gate is
        # its ``profile`` metadata, else the inner Element's class profile
        # (mirroring ``Element._children_xml``), else nothing (MINIMUM).
        if f.profile is not None:
            own_gate, own_display = _profile_rank(f.profile), f.profile
        elif (
            f.inner_class in classes_by_name
            and classes_by_name[f.inner_class].profile is not None
        ):
            inner_profile = classes_by_name[f.inner_class].profile
            own_gate = _profile_rank(inner_profile)
            own_display = f"{inner_profile} (via {f.inner_class})"
        else:
            own_gate, own_display = 0, "MINIMUM"
        # A field can never render before its enclosing element does, so
        # the effective gate is the stricter of the field's own gate and
        # the enclosing class's gate. (The enclosing class's own gate is
        # validated by the class-level check above.)
        enclosing_rank = _profile_rank(cls.profile)
        if enclosing_rank > own_gate:
            field_gate = enclosing_rank
            field_gate_display = f"{cls.profile or 'MINIMUM'} (gated by {cls.name})"
        else:
            field_gate, field_gate_display = own_gate, own_display
        if field_where not in KNOWN_PROFILE_EXCEPTIONS:
            field_profile_issue = _audit_profile(
                field_gate,
                field_gate_display,
                [n.get("profiles", []) for n in field_nodes],
                field_where,
                "field",
            )
            if field_profile_issue is not None:
                issues.append(field_profile_issue)

        if not f.docstring:
            issues.append(
                Issue(
                    "error",
                    field_where,
                    f"missing field docstring{_format_suggestion(field_ids, terms)}",
                )
            )
            continue
        if not BT_BG_RE.search(f.docstring):
            issues.append(
                Issue(
                    "error",
                    field_where,
                    "field docstring lacks a BT-/BG- citation"
                    + _format_suggestion(field_ids, terms),
                )
            )
        issues.extend(
            _audit_citations(
                f.docstring,
                field_ids,
                field_xpaths,
                field_where,
                "field",
                terms,
                xpath_index,
            )
        )

    # Missing XSD children: take the union of children across every
    # tree position that matches ``/{ns}:{tag}`` (resolved once above).
    if positions:
        union_children: dict[str, dict[str, Any]] = {}
        for _path, node in positions:
            for child_key, child_node in node.get("children", {}).items():
                # Attribute children (``/@schemeID``) are modelled
                # elsewhere — they aren't independent ``Element``
                # subclasses, they're carried by the parent's field
                # metadata. Skip for the missing-attribute report.
                if child_key.startswith("/@"):
                    continue
                # First occurrence wins; merge profiles defensively.
                existing = union_children.get(child_key)
                if existing is None:
                    union_children[child_key] = dict(child_node)
                else:
                    for p in child_node.get("profiles", []):
                        if p not in existing.get("profiles", []):
                            existing["profiles"].append(p)
        missing = [k for k in union_children if k not in modelled_tags]
        for child_key in missing:
            info = union_children[child_key]
            id_ = info.get("id") or "?"
            name = info.get("name") or ""
            profiles = ",".join(info.get("profiles", []))
            issues.append(
                Issue(
                    "info",
                    where,
                    f"XSD child not modelled: {child_key} "
                    f"[{id_}] {name!r} (profiles: {profiles})",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Broad citation cross-check (formerly tools/check_bt_br_ids.py)
#
# Where the AST audit above only inspects schema docstrings and only
# knows about BT-/BG- terms, this pass sweeps every BT-/BG-/BR-
# citation across the whole source + docs surface and resolves it
# against the workbook sidecars. It is what catches a typo in a
# narrative ``docs/*.md`` passage or a hallucinated business-rule id
# in a validator docstring. Enabled with ``--check-citations``.
# ---------------------------------------------------------------------------

RULES_SIDECAR = ROOT / "tools/business_rules.json"

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

CITATION_BR_RE = re.compile(r"\bBR(?:-[A-Z0-9]+)+\b")


def _rule_known(rid: str, rules: dict[str, Any]) -> bool:
    """Does ``rid`` resolve to a business rule, tolerating the documented
    family / placeholder / zero-padding / schematron-artifact cases?

    * Direct hit, bare family name, or allow-listed exception → known.
    * Placeholder pattern ``BR-X-5`` → known if ``BR-{cat}-5`` exists
      for any VAT category.
    * Zero-padding mismatch ``BR-CO-3`` ↔ ``BR-CO-03`` → known if
      either padding exists.
    """
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


def _collect_citation_sources(root: Path) -> list[Path]:
    """Every file the broad cross-check scans: all carthorse ``*.py``,
    every ``docs/*.md``, plus the top-level ``README.md`` / ``AGENTS.md``.
    """
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


def _cross_check_citations(
    terms: dict[str, Any], root: Path = ROOT
) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """Resolve every BT-/BG-/BR- citation across the source + docs
    surface against the workbook sidecars.

    Returns ``(bad_bt, bad_br)`` — unresolved id → list of files it
    appears in. Citation conventions tolerated:

    * **EN 16931 base ids absent from the Factur-X xlsx** —
      ``BG-0`` / ``BG-33`` / ``BG-34`` (see ``TOLERATED_MISSING_IDS``).
    * **Family-name placeholders** like ``BR-CO`` / ``BR-FXEXT`` and
      the ``BR-X`` / ``BR-Y`` per-VAT-category placeholders.
    * **Zero-padding mismatch** (``BR-CO-3`` ↔ ``BR-CO-03``).
    * **Schematron-only / known artifacts** (``BR-FX-EN-04`` and the
      ``BR-FXEXT-BR-22..27`` double-prefix artifact).
    """
    rules = _load_sidecar(RULES_SIDECAR)
    bad_bt: dict[str, list[Path]] = {}
    bad_br: dict[str, list[Path]] = {}

    for path in _collect_citation_sources(root):
        text = path.read_text()
        for bt in set(BT_BG_RE.findall(text)):
            if bt in terms or bt in TOLERATED_MISSING_IDS:
                continue
            bad_bt.setdefault(bt, []).append(path)
        for br in set(CITATION_BR_RE.findall(text)):
            if br in PLACEHOLDERS:
                continue
            if _rule_known(br, rules):
                continue
            bad_br.setdefault(br, []).append(path)
    return bad_bt, bad_br


def _report_citations(
    bad_bt: dict[str, list[Path]], bad_br: dict[str, list[Path]], root: Path
) -> int:
    """Print the cross-check result. Returns 1 on any unresolved id."""
    if not bad_bt and not bad_br:
        print(  # noqa: T201
            "ok: every BT-/BG-/BR- citation resolves against the sidecars."
        )
        return 0
    if bad_bt:
        print("Unknown BT/BG citations:")  # noqa: T201
        for bt in sorted(bad_bt):
            files = ", ".join(sorted({str(p.relative_to(root)) for p in bad_bt[bt]}))
            print(f"  {bt:25s}  {files}")  # noqa: T201
        print()  # noqa: T201
    if bad_br:
        print("Unknown BR citations:")  # noqa: T201
        for br in sorted(bad_br):
            files = ", ".join(sorted({str(p.relative_to(root)) for p in bad_br[br]}))
            print(f"  {br:25s}  {files}")  # noqa: T201
        print()  # noqa: T201
    return 1


def _run(
    only_class: str | None, show_missing: bool, only_errors: bool, check_citations: bool
) -> int:
    tree = _load_sidecar(TREE_SIDECAR)
    terms = _load_sidecar(TERMS_SIDECAR)
    xpath_index = _xpath_index(terms)
    ids_at_xpath = _ids_at_xpath_index(terms)
    classes, parents_by_name = _load_schema()
    classes_by_name = {c.name: c for c in classes}

    all_issues: list[Issue] = []
    for cls in classes:
        if only_class and cls.name != only_class:
            continue
        all_issues.extend(
            _audit_class(
                cls,
                classes_by_name,
                parents_by_name,
                tree,
                terms,
                xpath_index,
                ids_at_xpath,
            )
        )

    errors = [i for i in all_issues if i.severity == "error"]
    info = [i for i in all_issues if i.severity == "info"]

    for i in errors:
        print(f"error  {i.where}: {i.message}")  # noqa: T201
    if not only_errors and (show_missing or only_class):
        for i in info:
            print(f"info   {i.where}: {i.message}")  # noqa: T201

    print(  # noqa: T201
        f"\naudited {len(classes)} Element classes: "
        f"{len(errors)} errors, {len(info)} missing-attribute notes"
    )
    status = 1 if errors else 0

    if check_citations:
        print("\nBT-/BG-/BR- citation cross-check (src, docs, README, AGENTS):")  # noqa: T201
        bad_bt, bad_br = _cross_check_citations(terms)
        if _report_citations(bad_bt, bad_br, ROOT):
            status = 1

    return status


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_schema_docs", description=__doc__.split("\n\n", maxsplit=1)[0]
    )
    parser.add_argument(
        "--class",
        dest="only_class",
        default=None,
        help="Restrict the audit (and informational missing-child report) "
        "to a single Element subclass by name.",
    )
    parser.add_argument(
        "--show-missing",
        action="store_true",
        help="Also print informational ``XSD child not modelled`` notes "
        "for every audited class. Otherwise these stay hidden so CI "
        "only flags hard errors.",
    )
    parser.add_argument(
        "--only-errors",
        action="store_true",
        help="Suppress the informational missing-child report even when "
        "``--class`` is given.",
    )
    parser.add_argument(
        "--check-citations",
        action="store_true",
        help="Additionally cross-check every BT-/BG-/BR- citation across "
        "src/, docs/, README.md and AGENTS.md against the workbook "
        "sidecars (the former check_bt_br_ids.py audit). Fails on any "
        "id that doesn't resolve.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return _run(
        only_class=args.only_class,
        show_missing=args.show_missing,
        only_errors=args.only_errors,
        check_citations=args.check_citations,
    )


if __name__ == "__main__":
    raise SystemExit(main())
