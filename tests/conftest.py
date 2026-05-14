"""Shared pytest fixtures.

The ``parser`` / ``parse_file`` fixtures from :mod:`tests._parsers` are
re-exported here so they're discovered automatically by every test in
the suite without each test having to import them explicitly.
"""

from tests._parsers import parse_file, parser

__all__ = ["parse_file", "parser"]
