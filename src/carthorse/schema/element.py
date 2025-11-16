import enum
from abc import ABC
from dataclasses import Field, dataclass, fields
from datetime import date
from typing import ClassVar, override

from tagic.xml import XML


class ProfileMismatch(ValueError): ...


@enum.unique
class Profile(enum.StrEnum):
    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    COMFORT = "urn:cen.eu:en16931:2017"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

    @override
    def __lt__(self, value: str, /) -> bool:
        p = Profile(value)
        ps = list(Profile)
        return ps.index(self) < ps.index(p)


@enum.unique
class Namespace(enum.StrEnum):
    rsm = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    qdt = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
    ram = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xs = "http://www.w3.org/2001/XMLSchema"
    xsi = "http://www.w3.org/2001/XMLSchema-instance"
    udt = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"


@dataclass(kw_only=True, slots=True)
class Element(ABC):
    namespace: ClassVar[Namespace]
    tag: ClassVar[str]
    profile: ClassVar[Profile] = Profile.MINIMUM

    def get_tag(self) -> str:
        return f"{self.namespace.name}:{self.tag}"

    def _children_xml(self, profile: Profile) -> list[XML]:
        children: list[XML] = []
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                # not required
                continue

            p = field.metadata.get("profile", Profile.MINIMUM)
            assert isinstance(p, Profile)
            if profile < p:
                raise ProfileMismatch(
                    f"{self.__class__.__name__}.{field.name}: {profile} < {p}"
                )
            match value:
                case str():
                    children += [_render_str(value, field)]
                case bool():
                    children += [_render_bool(value, field)]
                case date():
                    children += [_render_date(value, field)]
                case list():
                    children += [v.to_xml(profile) for v in value]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                case _:
                    children += [value.to_xml(profile)]

        return children

    def to_xml(self, profile: Profile) -> XML:
        return XML(self.get_tag(), children=self._children_xml(profile))


def _render_bool(value: bool, field: Field[bool]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)
    p = field.metadata.get("profile", Profile.MINIMUM)
    assert isinstance(p, Profile)

    return XML(f"{ns.name}:{tag}")[XML("udt:Indicator")[str(value).lower()]]


def _render_str(value: str, field: Field[str]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    return XML(f"{ns.name}:{tag}")[value]


def _render_date(value: date, field: Field[date]) -> XML:
    tag = field.metadata["tag"]
    assert isinstance(tag, str)
    ns = field.metadata["ns"]
    assert isinstance(ns, Namespace)

    return XML(f"{ns.name}:{tag}")[
        XML("udt:DateTimeString", attrs={"format": "102"})[value.strftime("%Y%m%d")]
    ]
