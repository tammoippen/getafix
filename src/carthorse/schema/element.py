import datetime
import json
import types
from abc import ABC
from collections.abc import Iterator
from dataclasses import Field, dataclass, fields
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
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code: str = code
        self.message: str = message


@dataclass(kw_only=True, slots=True)
class Element(ABC):
    namespace: ClassVar[Namespace]
    tag: ClassVar[str]
    profile: ClassVar[Profile] = Profile.MINIMUM

    def validate_internal(self, profile: Profile) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                # not required
                continue
            if not isinstance(value, list):
                value = [value]
            for v in value:
                if isinstance(v, Element):
                    v.validate_internal(profile)

    @classmethod
    def get_tag(cls) -> str:
        return f"{cls.namespace.name}:{cls.tag}"

    @classmethod
    def get_qualified_tag(cls) -> str:
        return cls.namespace.get_qualified_tag(cls.tag)

    def _children_xml(self, profile: Profile) -> list[XML]:
        children: list[XML] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                # not required
                continue

            p = field.metadata.get("profile")
            if p is None and isinstance(value, Element):
                p = value.__class__.profile
            if p is None:
                p = Profile.MINIMUM

            assert isinstance(p, Profile)
            # TODO: check in validate and only ignore here?
            if profile < p:
                raise ProfileMismatch(
                    f"{self.__class__.__name__}.{field.name}: {profile} < {p}"
                )
            match value:
                case str():
                    children += [_render_str(value, field)]
                case bool():
                    children += [_render_bool(value, field)]
                case datetime.date():
                    children += [_render_date(value, field)]
                case list():
                    children += [v.to_xml_internal(profile) for v in value]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                case _:
                    children += [value.to_xml_internal(profile)]

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
        fields_ = fields(cls)
        for el in elem:
            for field in fields_:
                curr_type = _get_non_none_type(field.type)
                if issubclass(curr_type, str):
                    params.update(_parse_str(el, field, curr_type))
                elif issubclass(curr_type, bool):
                    params.update(_parse_bool(el, field))
                elif issubclass(curr_type, datetime.date):
                    params.update(_parse_date(el, field))
                else:
                    origin = get_origin(curr_type)
                    is_list = False
                    if origin is list:
                        is_list = True
                        curr_type = get_args(curr_type)[0]

                    assert isinstance(curr_type, type), curr_type
                    assert issubclass(curr_type, Element)
                    if el.tag == curr_type.get_qualified_tag():
                        if is_list and field.name not in params:
                            params[field.name] = []
                        if isinstance(params.get(field.name), list):
                            params[field.name] += [curr_type.from_xml(el)]
                        else:
                            params[field.name] = curr_type.from_xml(el)
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
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)
    p = field.metadata.get("profile", Profile.MINIMUM)
    assert isinstance(p, Profile)

    return XML(f"{ns.name}:{tag}")[XML("udt:Indicator")[str(value).lower()]]


def _parse_bool(el: ETElement, field: Field[bool]) -> dict[str, bool]:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
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


def _render_str(value: str, field: Field[str]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    return XML(f"{ns.name}:{tag}")[value]


def _parse_str(el: ETElement, field: Field[str], curr_type: type) -> dict[str, Any]:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    if el.tag != ns.get_qualified_tag(tag):
        return {}
    if el.text is None:
        raise ValueError
    return {field.name: curr_type(el.text.strip())}


def _render_date(value: datetime.date, field: Field[datetime.date]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    return XML(f"{ns.name}:{tag}")[
        XML("udt:DateTimeString", attrs={"format": "102"})[value.strftime("%Y%m%d")]
    ]


def _parse_date(el: ETElement, field: Field[datetime.date]) -> dict[str, datetime.date]:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    if el.tag != ns.get_qualified_tag(tag):
        return {}
    if len(el) != 1:
        raise ValueError
    if el[0].tag != Namespace.udt.get_qualified_tag("DateTimeString"):
        raise ValueError
    if el[0].attrib.get("format") != "102":
        raise ValueError
    if el[0].text is None:
        raise ValueError
    return {field.name: datetime.datetime.strptime(el[0].text.strip(), "%Y%m%d").date()}
