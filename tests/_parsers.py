"""Per-parser helpers so the round-trip tests cover both lxml and the
stdlib ``xml.etree.ElementTree``.

lxml is an optional runtime dependency; tests parametrised on ``parser``
or ``parse_file`` skip the lxml leg automatically when lxml is not
importable. Both parsers produce objects that satisfy the
``getafix.schema.element.ETElement`` alias (stdlib ``Element`` |
lxml ``_Element``), so the same call sites accept either output.
"""

from __future__ import annotations

import importlib.util
import xml.etree.ElementTree as _stdlib_etree
from collections.abc import Callable
from pathlib import Path

import pytest as pt

from getafix.schema.element import ETElement

# Bytes-or-str → element callable. Tests use this signature so they don't
# care which library backs the parser.
ParseFromBytes = Callable[[bytes], ETElement]
ParseFromFile = Callable[[Path], ETElement]


def _stdlib_parse(data: bytes) -> ETElement:
    return _stdlib_etree.fromstring(data)


def _stdlib_parse_file(path: Path) -> ETElement:
    return _stdlib_etree.parse(str(path)).getroot()


def _lxml_parse(data: bytes) -> ETElement:
    from lxml import etree

    return etree.fromstring(data)


def _lxml_parse_file(path: Path) -> ETElement:
    from lxml import etree

    return etree.parse(str(path)).getroot()


HAS_LXML: bool = importlib.util.find_spec("lxml") is not None

_lxml_skip = pt.mark.skipif(not HAS_LXML, reason="lxml not installed")

PARSER_PARAMS = [
    pt.param("stdlib", id="stdlib"),
    pt.param("lxml", id="lxml", marks=_lxml_skip),
]


def _parse_for(name: str) -> ParseFromBytes:
    return _lxml_parse if name == "lxml" else _stdlib_parse


def _parse_file_for(name: str) -> ParseFromFile:
    return _lxml_parse_file if name == "lxml" else _stdlib_parse_file


@pt.fixture(params=PARSER_PARAMS)
def parser(request: pt.FixtureRequest) -> ParseFromBytes:
    """Parametrised XML parser — yields once per available backend."""
    return _parse_for(request.param)


@pt.fixture(params=PARSER_PARAMS)
def parse_file(request: pt.FixtureRequest) -> ParseFromFile:
    """Parametrised XML file parser — yields once per available backend."""
    return _parse_file_for(request.param)
