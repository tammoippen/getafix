"""AST-audit every ``Element`` subclass in ``src/carthorse/schema``.

Catches three classes of regression that hand-review keeps missing:

1. **Missing docstrings** — every ``Element`` subclass and every
   dataclass field on one must carry a docstring.
2. **Missing BT-/BG- citation** — every such docstring must reference
   the term it models (e.g. ``BT-31``, ``BG-X-49``). The companion
   ``tools/check_bt_br_ids.py`` then validates each citation resolves
   against the workbook sidecar.
3. **Missing XSD-allowed children** — for each class, look the class's
   ``namespace`` + ``tag`` up in the xpath tree
   (``tools/business_terms_tree.json``). Any direct child node that
   isn't backed by a declared field is reported, with its BT/BG id
   and per-profile coverage. The tool intentionally doesn't fail on
   missing children — the maintainer decides whether to model them
   (EXTENDED-only attributes are valid omissions until needed) — but
   the report makes the gap visible.

The first two checks fail the audit; the third is informational.

Run:
    uv run python tools/check_schema_docs.py
    uv run python tools/check_schema_docs.py --show-missing
    uv run python tools/check_schema_docs.py --class PayeeTradeParty

CI:
    Wired into ``make ids-check`` after the existing BT/BR-citation
    audit.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "src/carthorse/schema"
TREE_SIDECAR = ROOT / "tools/business_terms_tree.json"
TERMS_SIDECAR = ROOT / "tools/business_terms.json"

# Files we skip entirely — the reflective core, primitives, and the
# enum / type vendoring module hold no Element subclasses worth
# auditing for BT/BG coverage.
SKIP_FILES: frozenset[str] = frozenset(
    {"__init__.py", "_numeric.py", "element.py", "types.py"}
)

BT_BG_RE = re.compile(r"\bB[GT]-(X-)?\d+(-\d+)?(-\d+)?\b")


# ---------------------------------------------------------------------------
# AST extraction
# ---------------------------------------------------------------------------


class FieldInfo:
    __slots__ = ("docstring", "inner_class", "name", "ns", "profile", "tag", "type_str")

    def __init__(
        self,
        name: str,
        type_str: str,
        inner_class: str | None,
        tag: str | None,
        ns: str | None,
        profile: str | None,
        docstring: str | None,
    ):
        self.name: str = name
        self.type_str: str = type_str
        self.inner_class: str | None = inner_class
        self.tag: str | None = tag
        self.ns: str | None = ns
        self.profile: str | None = profile
        self.docstring: str | None = docstring


class ClassInfo:
    __slots__ = ("docstring", "fields", "module", "name", "ns", "profile", "tag")

    def __init__(
        self,
        name: str,
        module: str,
        tag: str | None,
        ns: str | None,
        profile: str | None,
        docstring: str | None,
        fields: list[FieldInfo],
    ):
        self.name: str = name
        self.module: str = module
        self.tag: str | None = tag
        self.ns: str | None = ns
        self.profile: str | None = profile
        self.docstring: str | None = docstring
        self.fields: list[FieldInfo] = fields


def _base_names(node: ast.ClassDef) -> list[str]:
    return [b.id for b in node.bases if isinstance(b, ast.Name)]


def _element_subclass_names(modules: list[ast.Module]) -> set[str]:
    """Names of every ``Element`` subclass across the given parsed
    modules — including transitive subclasses
    (``ISO6523SchemeId(SchemeID(Element))`` and
    ``GlobalID(ISO6523SchemeId)``).

    Computed as a fixed-point: seed with ``"Element"``, then keep
    adding classes whose first textual base is already in the set.
    """
    subclasses: set[str] = {"Element"}
    all_classes: list[tuple[str, list[str]]] = [
        (node.name, _base_names(node))
        for module in modules
        for node in module.body
        if isinstance(node, ast.ClassDef)
    ]
    changed = True
    while changed:
        changed = False
        for name, bases in all_classes:
            if name in subclasses:
                continue
            if any(b in subclasses for b in bases):
                subclasses.add(name)
                changed = True
    return subclasses


def _str_constant(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _attr_terminal(node: ast.AST | None) -> str | None:
    """``Profile.EXTENDED`` → ``"EXTENDED"``; ``Namespace.ram`` → ``"ram"``.

    Used to read enum-typed ClassVar / metadata values out of the AST
    without importing the project.
    """
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _type_annotation_text(node: ast.AST) -> str:
    return ast.unparse(node)


def _inner_class_name(node: ast.AST) -> str | None:
    """Pull the (likely Element) class name out of a type annotation.

    Strips ``| None`` and ``list[...]`` wrappers, returns the bare
    ``Name`` if any survives. Returns ``None`` for builtins, unions
    of multiple classes, or anything more exotic.
    """
    # Strip ``X | None`` / ``None | X``
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _inner_class_name(node.left)
        right = _inner_class_name(node.right)
        # ``None`` becomes ``NoneType`` here — discard it.
        candidates = [c for c in (left, right) if c and c != "None"]
        if len(candidates) == 1:
            return candidates[0]
        return None
    # ``list[X]`` / ``Sequence[X]`` …
    if isinstance(node, ast.Subscript):
        # ``Subscript.slice`` is the inner type expr in 3.9+.
        return _inner_class_name(node.slice)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    return None


def _extract_metadata(call: ast.Call) -> tuple[str | None, str | None, str | None]:
    """Pull ``metadata={"tag": ..., "ns": ..., "profile": ...}`` from a
    ``field(...)`` call. Returns ``(tag, ns, profile)``.

    Misses the keys silently when the literal dict isn't there — the
    caller treats ``None`` as "no metadata supplied".
    """
    tag: str | None = None
    ns: str | None = None
    profile: str | None = None
    for kw in call.keywords:
        if kw.arg != "metadata" or not isinstance(kw.value, ast.Dict):
            continue
        for key_node, value_node in zip(kw.value.keys, kw.value.values, strict=False):
            key = _str_constant(key_node)
            if key == "tag":
                tag = _str_constant(value_node)
            elif key == "ns":
                ns = _attr_terminal(value_node)
            elif key == "profile":
                profile = _attr_terminal(value_node)
    return tag, ns, profile


def _next_docstring(stmts: list[ast.stmt], index: int) -> str | None:
    """A field's docstring is the bare string expression immediately
    after its ``AnnAssign``."""
    if index + 1 >= len(stmts):
        return None
    nxt = stmts[index + 1]
    if isinstance(nxt, ast.Expr):
        return _str_constant(nxt.value)
    return None


def _parse_modules() -> list[tuple[Path, ast.Module]]:
    out: list[tuple[Path, ast.Module]] = []
    for path in sorted(SCHEMA_DIR.glob("*.py")):
        if path.name in SKIP_FILES:
            continue
        out.append((path, ast.parse(path.read_text(), filename=str(path))))
    return out


def _walk_modules(
    parsed: list[tuple[Path, ast.Module]], subclasses: set[str]
) -> list[ClassInfo]:
    classes: list[ClassInfo] = []
    for path, module in parsed:
        for node in module.body:
            if not isinstance(node, ast.ClassDef) or node.name not in subclasses:
                continue
            classes.append(_extract_class(node, path.name))
    # Resolve inherited ClassVars (``tag`` / ``namespace`` / ``profile``)
    # for transitive subclasses such as ``GlobalID(ISO6523SchemeId)``
    # that don't re-declare them.
    by_name = {c.name: c for c in classes}
    # Build a parent map indexed by class name from the AST bases.
    parents: dict[str, list[str]] = {}
    for _path, module in parsed:
        for node in module.body:
            if not isinstance(node, ast.ClassDef) or node.name not in subclasses:
                continue
            parents[node.name] = _base_names(node)
    for cls in classes:
        if cls.tag is not None and cls.ns is not None and cls.profile is not None:
            continue
        for parent_name in parents.get(cls.name, []):
            parent = by_name.get(parent_name)
            if parent is None:
                continue
            if cls.tag is None and parent.tag is not None:
                cls.tag = parent.tag
            if cls.ns is None and parent.ns is not None:
                cls.ns = parent.ns
            if cls.profile is None and parent.profile is not None:
                cls.profile = parent.profile
    return classes


def _extract_class(node: ast.ClassDef, module_name: str) -> ClassInfo:
    tag: str | None = None
    ns: str | None = None
    profile: str | None = None
    fields: list[FieldInfo] = []

    body = node.body
    docstring = ast.get_docstring(node)

    for i, stmt in enumerate(body):
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        name = stmt.target.id
        annotation_text = _type_annotation_text(stmt.annotation)

        # ClassVar values: ``tag: ClassVar[str] = "Foo"``,
        # ``namespace: ClassVar[Namespace] = Namespace.ram``,
        # ``profile: ClassVar[Profile] = Profile.EXTENDED``.
        if annotation_text.startswith("ClassVar"):
            if name == "tag":
                tag = _str_constant(stmt.value)
            elif name == "namespace":
                ns = _attr_terminal(stmt.value)
            elif name == "profile":
                profile = _attr_terminal(stmt.value)
            continue

        # Skip private bookkeeping fields and the internal ``currency``
        # context-carrier (an out-of-band parameter the framework uses
        # to thread the document currency through amount fields — it's
        # not rendered as its own XML element, see
        # ``Element._children_xml``).
        if name.startswith("_") or name == "currency":
            continue

        field_tag: str | None = None
        field_ns: str | None = None
        field_profile: str | None = None
        if (
            isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "field"
        ):
            field_tag, field_ns, field_profile = _extract_metadata(stmt.value)

        inner_class = _inner_class_name(stmt.annotation)
        # ``str`` / ``int`` / ``Decimal`` / ``datetime`` etc. aren't
        # Element subclasses — keep ``inner_class`` only when it could
        # be one (capitalised, not a builtin).
        BUILTINS = frozenset(
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
        if inner_class in BUILTINS:
            inner_class = None

        fields.append(
            FieldInfo(
                name=name,
                type_str=annotation_text,
                inner_class=inner_class,
                tag=field_tag,
                ns=field_ns,
                profile=field_profile,
                docstring=_next_docstring(body, i),
            )
        )

    return ClassInfo(
        name=node.name,
        module=module_name,
        tag=tag,
        ns=ns,
        profile=profile,
        docstring=docstring,
        fields=fields,
    )


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


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class Issue:
    __slots__ = ("message", "severity", "where")

    def __init__(self, severity: str, where: str, message: str):
        self.severity: str = severity  # "error" | "info"
        self.where: str = where
        self.message: str = message


def _audit_class(
    cls: ClassInfo,
    classes_by_name: dict[str, ClassInfo],
    tree: dict[str, Any],
    terms: dict[str, Any],
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
    class_ids = _collect_ids(node for _path, node in positions)

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

    # Field docstrings + BT/BG citations.
    field_tags: set[str] = set()
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
            field_tags.add(field_key)

        # Look the field up inside each parent-class tree position.
        field_ids: list[tuple[str, str]] = []
        if field_key is not None:
            field_ids = _collect_ids(
                node.get("children", {}).get(field_key, {})
                for _path, node in positions
                if node.get("children", {}).get(field_key)
            )

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

    # Missing XSD children: take the union of children across every
    # tree position that matches ``/{ns}:{tag}``.
    positions = _positions_for(tree, ns, cls.tag)
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
        missing = [k for k in union_children if k not in field_tags]
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


def _run(only_class: str | None, show_missing: bool, only_errors: bool) -> int:
    tree = _load_sidecar(TREE_SIDECAR)
    terms = _load_sidecar(TERMS_SIDECAR)
    parsed = _parse_modules()
    subclasses = _element_subclass_names([m for _path, m in parsed])
    classes = _walk_modules(parsed, subclasses)

    classes_by_name = {c.name: c for c in classes}

    all_issues: list[Issue] = []
    for cls in classes:
        if only_class and cls.name != only_class:
            continue
        all_issues.extend(_audit_class(cls, classes_by_name, tree, terms))

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
    return 1 if errors else 0


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return _run(
        only_class=args.only_class,
        show_missing=args.show_missing,
        only_errors=args.only_errors,
    )


if __name__ == "__main__":
    raise SystemExit(main())
