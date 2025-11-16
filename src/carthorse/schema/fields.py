from dataclasses import dataclass
from datetime import date
from typing import override

from tagic.xml import XML

from .element import Element, Namespace, Profile


@dataclass(kw_only=True, slots=True)
class Field(Element):
    # have to override value

    def __class_getitem__(
        cls, params: tuple[Namespace, str] | tuple[Namespace, str, Profile]
    ) -> type[Element]:
        assert isinstance(params, tuple)
        if len(params) == 2:
            vars = {"tag": params[1], "namespace": params[0]}
        else:
            vars = {"tag": params[1], "namespace": params[0], "profile": params[2]}
        new_cls = type(cls.__name__, (cls,), vars)
        return dataclass(new_cls)

    @override
    def to_xml(self, profile: Profile) -> XML:
        assert hasattr(self, "value")
        return XML(self.get_tag())[self.value]  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]


@dataclass(kw_only=True, slots=True)
class Indicator(Field):
    value: bool

    @override
    def to_xml(self, profile: Profile) -> XML:
        return XML(self.get_tag())[XML("udt:Indicator")[str(self.value).lower()]]


@dataclass(kw_only=True, slots=True)
class String(Field):
    value: str


StringId = String[Namespace.ram, "ID"]


@dataclass(kw_only=True, slots=True)
class Date(Field):
    value: date

    @override
    def to_xml(self, profile: Profile) -> XML:
        return XML(self.get_tag())[
            XML("udt:DateTimeString", attrs={"format": "102"})[
                self.value.strftime("%Y%m%d")
            ]
        ]
