import enum
from abc import ABC
from dataclasses import dataclass, fields
from typing import ClassVar

from tagic.xml import XML


@enum.unique
class Profile(enum.StrEnum):
    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    COMFORT = "urn:cen.eu:en16931:2017"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"


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

    def _children_xml(self) -> list[XML]:
        children: list[XML] = []
        for field in fields(self):
            value = getattr(self, field.name)  # pyright: ignore[reportAny]
            if value is None:
                # not required
                continue
            assert isinstance(value, Element)
            children += [value.to_xml()]
        return children

    def to_xml(self) -> XML:
        return XML(self.get_tag(), children=self._children_xml())
