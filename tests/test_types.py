"""Regression tests for ``getafix.schema.types``."""

from __future__ import annotations

import pytest as pt

from getafix.schema.types import Profile

_ORDERED = [
    Profile.MINIMUM,
    Profile.BASIC_WL,
    Profile.BASIC,
    Profile.COMFORT,
    Profile.EXTENDED,
]


class TestProfileOrdering:
    """All four order comparators follow declaration order, not str.__lt__."""

    def test_strict_less_than(self) -> None:
        for i, lhs in enumerate(_ORDERED):
            for j, rhs in enumerate(_ORDERED):
                assert (lhs < rhs) is (i < j), (lhs, rhs)

    def test_less_than_or_equal(self) -> None:
        for i, lhs in enumerate(_ORDERED):
            for j, rhs in enumerate(_ORDERED):
                assert (lhs <= rhs) is (i <= j), (lhs, rhs)

    def test_strict_greater_than(self) -> None:
        for i, lhs in enumerate(_ORDERED):
            for j, rhs in enumerate(_ORDERED):
                assert (lhs > rhs) is (i > j), (lhs, rhs)

    def test_greater_than_or_equal(self) -> None:
        for i, lhs in enumerate(_ORDERED):
            for j, rhs in enumerate(_ORDERED):
                assert (lhs >= rhs) is (i >= j), (lhs, rhs)

    @pt.mark.parametrize(
        ("lhs", "rhs"),
        [
            # The lex-compare fallback used to flip these; pin them as
            # explicit regressions so a future StrEnum override tweak
            # cannot regress silently.
            (Profile.BASIC_WL, Profile.MINIMUM),
            (Profile.BASIC, Profile.BASIC_WL),
            (Profile.COMFORT, Profile.BASIC),
            (Profile.EXTENDED, Profile.COMFORT),
        ],
    )
    def test_higher_profile_is_greater(self, lhs: Profile, rhs: Profile) -> None:
        assert lhs > rhs
        assert lhs >= rhs
        assert not (lhs < rhs)
        assert not (lhs <= rhs)

    def test_equal_to_self(self) -> None:
        for p in _ORDERED:
            assert p <= p
            assert p >= p
            assert not (p < p)
            assert not (p > p)

    def test_compare_against_str_value(self) -> None:
        # The override accepts either a Profile or its str URN.
        assert Profile.MINIMUM < Profile.BASIC_WL.value
        assert Profile.EXTENDED > Profile.MINIMUM.value
