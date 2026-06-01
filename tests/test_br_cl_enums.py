"""BR-CL-* — code-list membership enforcement via vendored StrEnums.

Carthorse enforces every BR-CL-* rule by re-typing the affected
schema fields to a vendored ``StrEnum``. The :py:class:`StrEnum`
constructor rejects any value outside the enum, so construction- and
parse-time both raise on out-of-list inputs — that's the
spec-required behaviour. See ``docs/VALIDATION.md §6`` for the
field-to-enum registry.

This file pins the smoke-level constraint: every vendored enum
should accept the canonical example values from the EN 16931 code
lists, and reject obvious nonsense.
"""

from __future__ import annotations

import pytest as pt

from carthorse.schema.types import (
    Country,
    Currency,
    EASCode,
    UNTDID2475TaxPointDateCode,
    UNTDID4461PaymentMeansCode,
    UNTDID5189AllowanceReasonCode,
    VATEXCode,
)


class TestCurrency:
    def test_well_known_values(self) -> None:
        assert Currency.EUR == "EUR"
        assert Currency.USD == "USD"
        assert Currency.GBP == "GBP"

    def test_rejects_unknown(self) -> None:
        with pt.raises(ValueError):
            Currency("XYZ")  # not a real ISO 4217 code

    def test_accepts_via_constructor(self) -> None:
        # Existing ISO 4217 codes can be constructed from the wire
        # string — that's what the parser does on ``from_xml``.
        assert Currency("EUR") is Currency.EUR


class TestCountry:
    def test_well_known_values(self) -> None:
        assert Country.DE == "DE"
        assert Country.FR == "FR"
        assert Country.US == "US"

    def test_rejects_unknown(self) -> None:
        with pt.raises(ValueError):
            Country("XX")  # not an ISO 3166-1 alpha-2 code


class TestUNTDID4461:
    def test_canonical_payment_codes(self) -> None:
        # ``58`` is the most common European code (SEPA credit transfer).
        assert UNTDID4461PaymentMeansCode.CODE_58 == "58"
        assert UNTDID4461PaymentMeansCode.CODE_30 == "30"

    def test_rejects_unknown(self) -> None:
        with pt.raises(ValueError):
            UNTDID4461PaymentMeansCode("999")


class TestUNTDID2475:
    def test_known_values(self) -> None:
        # Code ``5`` is "Date of invoice", the default.
        assert UNTDID2475TaxPointDateCode.CODE_5 == "5"

    def test_rejects_unknown(self) -> None:
        with pt.raises(ValueError):
            UNTDID2475TaxPointDateCode("99")


class TestEAS:
    def test_known_scheme(self) -> None:
        # ``0002`` is the SIRENE registry (FR).
        assert EASCode.CODE_0002 == "0002"

    def test_rejects_unknown(self) -> None:
        with pt.raises(ValueError):
            EASCode("9999")


class TestVATEX:
    def test_known_exemption(self) -> None:
        # Some VATEX-EU-* codes are widely used; just verify membership
        # for any well-known one we can find in the generated enum.
        members = [m.value for m in VATEXCode]
        assert any(m.startswith("VATEX-EU") for m in members)


class TestUNTDID5189:
    def test_some_member_exists(self) -> None:
        # 19 members — we don't pin specific ones, just verify the
        # enum was generated with the right shape.
        assert len(list(UNTDID5189AllowanceReasonCode)) >= 10
