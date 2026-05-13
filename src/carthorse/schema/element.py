import datetime
import json
import types
from abc import ABC
from collections.abc import Callable, Iterator
from dataclasses import Field, dataclass, fields
from decimal import Decimal
from typing import Any, ClassVar, Protocol, Self, get_args, get_origin

from tagic.xml import XML

from carthorse.schema.types import Namespace, Profile


class ETElement(Protocol):
    # works with lxml and xml
    tag: str
    text: str | None
    attrib: dict[str, str]

    def __iter__(self) -> "Iterator[ETElement]": ...
    def __len__(self) -> int: ...
    def __getitem__(self, item: int) -> "ETElement": ...


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

            p = f.metadata.get("profile")
            if p is None and isinstance(value, Element):
                p = value.__class__.profile
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
                    if (
                        has_currency_field
                        and f.metadata.get("amount")
                        and "currencyID" in el.attrib
                    ):
                        captured_currency = el.attrib["currencyID"]
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
