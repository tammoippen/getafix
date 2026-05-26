import datetime
import json
import types
import xml.etree.ElementTree as _stdlib_etree
from abc import ABC
from collections.abc import Callable
from dataclasses import Field, dataclass, fields
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, get_args, get_origin

from tagic.xml import XML

from carthorse.schema.types import Namespace, Profile

if TYPE_CHECKING:
    # lxml is an optional runtime dependency; the ``ETElement`` alias unions
    # the stdlib ``Element`` with lxml's ``_Element`` so :meth:`Element.from_xml`
    # accepts either parser's output. The TYPE_CHECKING guard keeps lxml off
    # the import path at runtime — pyright still sees the lxml branch.
    from lxml.etree import _Element as _LxmlElement

    type ETElement = _stdlib_etree.Element | _LxmlElement
else:
    # Runtime alias — both parsers expose the same duck-typed shape
    # (tag/text/attrib/__iter__/__len__/__getitem__), so the runtime form
    # carries only the always-importable stdlib type.
    type ETElement = _stdlib_etree.Element


class ProfileMismatch(ValueError): ...


class ValidationError(ValueError):
    """A single business-rule violation.

    ``code`` is the rule identifier (``BR-CO-15`` etc.) and ``message``
    a human-readable explanation. Subclassing ``ValueError`` keeps
    backwards-compat with code that catches ``ValueError`` broadly, but
    the public ``Document.validate`` entry point raises the plural
    :class:`ValidationErrors` instead so callers can see every
    violation in one pass.
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code: str = code
        self.message: str = message


class ValidationErrors(ValueError):
    """Aggregate exception holding every ValidationError from a single
    ``Document.validate`` pass.

    ``errors`` is the list, in document order. Callers can check for a
    specific rule with::

        assert any(e.code == "BR-CO-15" for e in exc.errors)
    """

    def __init__(self, errors: list[ValidationError]):
        joined = "; ".join(f"{e.code}: {e.message}" for e in errors)
        super().__init__(joined)
        self.errors: list[ValidationError] = errors


@dataclass(kw_only=True, slots=True)
class Element(ABC):
    tag: ClassVar[str]
    namespace: ClassVar[Namespace] = Namespace.ram
    profile: ClassVar[Profile] = Profile.MINIMUM

    _validators: ClassVar[
        tuple[Callable[[Any, Profile], list["ValidationError"]], ...]
    ] = ()
    """Business-rule validators that apply to *this* element.

    Subclasses override this with a tuple of free-standing functions
    from :mod:`carthorse.rules` (one per ``BR-*`` rule). Each function
    is invoked with ``(self, profile)`` and returns a
    ``list[ValidationError]`` (empty on success). See
    ``docs/VALIDATOR_REFACTOR.md`` for the architecture.
    """

    def __post_init__(self) -> None:
        # Type-shape check at construction time: every dataclass-declared
        # field must hold a value compatible with its annotation before
        # any ``BR-*`` validator or XML renderer touches the data. Catches
        # parser bugs (``from_xml`` builds an ``Any``-typed dict and splats
        # it into ``cls(**params)``) and hand-built fixtures that drift
        # from the model. Business rules — which presuppose the shape is
        # correct — stay in ``validate_internal``.
        for f in fields(self):
            value = getattr(self, f.name)
            expected = _get_non_none_type(f.type)
            assert not isinstance(expected, str), (
                f"{type(self).__name__}.{f.name}: annotation {f.type!r} is a "
                "string-form forward reference; resolve via get_type_hints "
                "or drop the future-annotations import on the module."
            )
            if value is None:
                if _allows_none(f.type):
                    continue
                raise TypeError(f"{type(self).__name__}.{f.name}: required, got None.")
            _check_field(type(self).__name__, f.name, value, expected)

    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        """Collect every business-rule violation under this Element.

        First runs ``self._validators`` against this element, then
        recurses into every child :class:`Element` reachable through
        dataclass fields. The Document root raises
        :class:`ValidationErrors` if the final list is non-empty.
        """
        errors: list[ValidationError] = [
            e for v in self._validators for e in v(self, profile)
        ]
        for f in fields(self):
            if f.name == "currency":
                continue
            value = getattr(self, f.name)
            if value is None:
                continue
            if not isinstance(value, list):
                value = [value]
            for v in value:
                if isinstance(v, Element):
                    errors.extend(v.validate_internal(profile))
        return errors

    @classmethod
    def get_tag(cls) -> str:
        return f"{cls.namespace.name}:{cls.tag}"

    @classmethod
    def get_qualified_tag(cls) -> str:
        return cls.namespace.get_qualified_tag(cls.tag)

    def _field_profile(self, name: str) -> Profile | None:
        """Hook for context-dependent per-field profile gates.

        Returns ``None`` by default so the per-field ``metadata['profile']``
        is consulted unchanged. Override on subclasses that need the
        gate to depend on instance state — see
        :class:`~carthorse.schema.accounting.TradeAllowanceCharge`,
        whose ``calculation_percent`` (BT-94 / BT-101 / BT-138 / BT-142)
        and ``basis_amount`` (BT-93 / BT-100 / BT-137 / BT-141) ship at
        BASIC_WL when the allowance/charge is on the document header
        and at COMFORT when it is on an invoice line.
        """
        return None

    def _children_xml(self, profile: Profile) -> list[XML]:
        children: list[XML] = []
        # Per-Element "currency" field provides the ``currencyID``
        # attribute for every Decimal field marked ``"amount": True`` in
        # metadata. Elements without amount fields don't declare it.
        currency: str | None = getattr(self, "currency", None)
        for f in fields(self):
            if f.name == "currency":
                # Internal: not rendered as its own element; it shows up
                # as the ``currencyID`` attribute on amount fields.
                continue
            value = getattr(self, f.name)
            if value is None:
                # not required
                continue

            p = self._field_profile(f.name)
            if p is None:
                p = f.metadata.get("profile")
            if p is None:
                # For list-of-Element fields, the framework consults the
                # item's class profile so a 0..* group declared at e.g.
                # COMFORT is gated like a single 0..1 Element field would
                # be. Empty lists fall through to MINIMUM.
                sample = value[0] if isinstance(value, list) and value else value
                if isinstance(sample, Element):
                    p = sample.__class__.profile
            if p is None:
                p = Profile.MINIMUM

            assert isinstance(p, Profile)
            # TODO: check in validate and only ignore here?
            if profile < p:
                raise ProfileMismatch(
                    f"{self.__class__.__name__}.{f.name}: {profile} < {p}"
                )
            if not isinstance(value, list):
                value = [value]
            extra_attrs: dict[str, str] | None = None
            if f.metadata.get("amount") and currency:
                extra_attrs = {"currencyID": currency}
            for v in value:
                match v:
                    case str():
                        children += [_render_str(v, f, extra_attrs)]
                    case Decimal():
                        children += [_render_str(str(v), f, extra_attrs)]
                    case bool():
                        children += [_render_bool(v, f)]
                    case datetime.date():
                        children += [_render_date(v, f)]
                    case Element():
                        children += [v.to_xml_internal(profile)]
                    case _:
                        raise TypeError(f"Unknown type {v=}.")

        return children

    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(self.get_tag(), children=self._children_xml(profile))

    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        """Parse the document from a lxml / xml Element.

        Typing those modules is difficult, but for what we do here,
        they are interchangeable. Hence, we use duck-typing. Sorry for you having to
        ignore possible warnings.

        FIXME: Better typing for ETElement
        """
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")

        params: dict[str, Any] = {}
        has_currency_field = any(f.name == "currency" for f in fields(cls))
        captured_currency: str | None = None
        for el in elem:
            for f in fields(cls):
                if f.name == "currency":
                    continue
                curr_type = _get_non_none_type(f.type)
                origin = get_origin(curr_type)
                is_list = False
                if origin is list:
                    is_list = True
                    curr_type = get_args(curr_type)[0]
                # ``Literal[...]`` is not a class — dispatch on the type of
                # its first literal value. ``__post_init__`` then enforces
                # membership.
                if get_origin(curr_type) is Literal:
                    curr_type = type(get_args(curr_type)[0])

                if issubclass(curr_type, str):
                    res = _parse_str(el, f, curr_type)
                    if res is None:
                        continue
                    if is_list:
                        before = params.get(f.name, [])
                        res = [*before, res]
                    params[f.name] = res
                elif issubclass(curr_type, Decimal):
                    res = _parse_str(el, f, str)
                    if res is None:
                        continue
                    params[f.name] = Decimal(res)
                    if has_currency_field and f.metadata.get("amount"):
                        currency_attr = el.attrib.get("currencyID")
                        if currency_attr is not None:
                            captured_currency = currency_attr
                elif issubclass(curr_type, bool):
                    assert not is_list
                    params.update(_parse_bool(el, f))
                elif issubclass(curr_type, datetime.date):
                    assert not is_list
                    params.update(_parse_date(el, f))
                else:
                    assert isinstance(curr_type, type), curr_type
                    assert issubclass(curr_type, Element)
                    if el.tag == curr_type.get_qualified_tag():
                        if is_list and f.name not in params:
                            params[f.name] = []
                        if isinstance(params.get(f.name), list):
                            params[f.name] += [curr_type.from_xml(el)]
                        else:
                            params[f.name] = curr_type.from_xml(el)
        if has_currency_field and captured_currency is not None:
            params.setdefault("currency", captured_currency)
        return cls(**params)


def _get_non_none_type(field_type: Any) -> Any:
    if get_origin(field_type) is types.UnionType:
        ts = [arg for arg in get_args(field_type) if arg is not type(None)]
        assert len(ts) == 1, ts
        return ts[0]
    return field_type


def _allows_none(field_type: Any) -> bool:
    return get_origin(field_type) is types.UnionType and type(None) in get_args(
        field_type
    )


def _check_field(cls_name: str, name: str, value: Any, expected: Any) -> None:
    origin = get_origin(expected)
    if origin is list:
        if not isinstance(value, list):
            raise TypeError(
                f"{cls_name}.{name}: expected list, got {type(value).__name__}."
            )
        (item_t,) = get_args(expected)
        assert not isinstance(item_t, str), (
            f"{cls_name}.{name}: list item annotation {item_t!r} is a "
            "string-form forward reference; resolve via get_type_hints "
            "or drop the future-annotations import on the module."
        )
        for i, item in enumerate(value):
            _check_scalar(cls_name, f"{name}[{i}]", item, item_t)
        return
    _check_scalar(cls_name, name, value, expected)


def _check_scalar(cls_name: str, name: str, value: Any, expected: Any) -> None:
    # ``Literal[...]`` — value must be one of the declared literals. The
    # underlying runtime type is also checked so e.g. ``Literal["130"]``
    # still rejects an int.
    if get_origin(expected) is Literal:
        allowed = get_args(expected)
        if value not in allowed:
            quoted = ", ".join(repr(a) for a in allowed)
            raise TypeError(
                f"{cls_name}.{name}: expected one of {{{quoted}}}, got {value!r}."
            )
        return
    if not isinstance(expected, type):
        return
    # ``bool`` is a subclass of ``int`` — be strict so a stray ``0``/``1``
    # doesn't sneak into an indicator field.
    if expected is bool:
        if type(value) is not bool:
            raise TypeError(
                f"{cls_name}.{name}: expected bool, got {type(value).__name__}."
            )
        return
    if not isinstance(value, expected):
        raise TypeError(
            f"{cls_name}.{name}: expected {expected.__name__}, "
            f"got {type(value).__name__}."
        )


def _render_bool(value: bool, field: Field[bool]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)
    p = field.metadata.get("profile", Profile.MINIMUM)
    assert isinstance(p, Profile)

    return XML(f"{ns.name}:{tag}")[XML("udt:Indicator")[str(value).lower()]]


def _parse_bool(el: ETElement, field: Field[bool]) -> dict[str, bool]:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)

    if el.tag != ns.get_qualified_tag(tag):
        return {}
    if len(el) != 1:
        raise ValueError
    if el[0].tag != Namespace.udt.get_qualified_tag("Indicator"):
        raise ValueError
    if el[0].text is None:
        raise ValueError
    return {field.name: json.loads(el[0].text)}


def _render_str(
    value: str, field: Field[str], extra_attrs: dict[str, str] | None = None
) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)

    attrs: dict[str, str | bool] = dict(extra_attrs) if extra_attrs else {}
    return XML(f"{ns.name}:{tag}", attrs=attrs)[value]


def _parse_str[T: str](
    el: ETElement, field: Field[str], curr_type: type[T]
) -> T | None:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)

    if el.tag != ns.get_qualified_tag(tag):
        return None
    if el.text is None:
        # Self-closing or whitespace-only element (e.g. ``<ram:LineTwo/>``)
        # — treat as absent rather than crashing on parse. The
        # PEPPOL-EN16931-R008 informational rule warns against empty
        # elements, but real-world ZUGFeRD samples ship them anyway.
        return None
    return curr_type(el.text.strip())


def _date_inner_namespace(tag: str) -> Namespace:
    """Inner ``DateTimeString`` namespace for a date field's wrapper tag.

    The CII XSD uses two date wrapper types: ``udt:DateTimeType`` (which
    nests ``udt:DateTimeString``) for plain dates like BT-2 IssueDateTime,
    BT-72 OccurrenceDateTime, BT-9 DueDateDateTime, BT-73/74 Start/EndDateTime,
    BT-X-6 CompleteDateTime — and ``qdt:FormattedDateTimeType`` (which
    nests ``qdt:DateTimeString``) for the formatted issue dates of
    referenced documents (BT-26 etc.).
    """
    return Namespace.qdt if tag == "FormattedIssueDateTime" else Namespace.udt


def _render_date(value: datetime.date, field: Field[datetime.date]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)
    inner_ns = _date_inner_namespace(tag)

    return XML(f"{ns.name}:{tag}")[
        XML(f"{inner_ns.name}:DateTimeString", attrs={"format": "102"})[
            value.strftime("%Y%m%d")
        ]
    ]


def _parse_date(el: ETElement, field: Field[datetime.date]) -> dict[str, datetime.date]:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata.get("ns", Namespace.ram)
    assert isinstance(ns, Namespace)
    inner_ns = _date_inner_namespace(tag)

    if el.tag != ns.get_qualified_tag(tag):
        return {}
    if len(el) != 1:
        raise ValueError
    if el[0].tag != inner_ns.get_qualified_tag("DateTimeString"):
        raise ValueError
    if el[0].attrib.get("format") != "102":
        raise ValueError
    if el[0].text is None:
        raise ValueError
    return {field.name: datetime.datetime.strptime(el[0].text.strip(), "%Y%m%d").date()}
