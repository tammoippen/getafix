from dataclasses import dataclass
from typing import Literal, override

from tagic.xml import XML

from .element import Element, Namespace, Profile


@dataclass()
class Indicator(Element):
    value: Literal[True] = True

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
    def to_xml(self) -> XML:
        return XML(self.get_tag())[XML("udt:Indicator")["true"]]
