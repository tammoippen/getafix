"""Currency-related rules: BT-5 / BT-6 / BR-53 / BR-CO-9, currency-id
round-trip and the two-tax-totals BG-22 shape."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from getafix.schema.accounting import ApplicableTradeTax, MonetarySummation, TaxTotal
from getafix.schema.party import TaxSchemeId
from getafix.schema.settlement import PaymentTerms, TradeSettlement
from getafix.schema.types import (
    CategoryCode,
    Currency,
    Profile,
    UNTDID2475TaxPointDateCode,
)
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


def test_monetary_summation_two_tax_totals(parser: ParseFromBytes):
    """BG-22 may carry both BT-110 (invoice currency) and BT-111 (VAT
    accounting currency) as ``TaxTotalAmount`` siblings. Bug sweep #6."""
    summation = MonetarySummation(
        line_total=Decimal("100.00"),
        tax_basis_total=Decimal("100.00"),
        tax_total=[
            TaxTotal(amount=Decimal("19.00"), currency_id=Currency.EUR),
            TaxTotal(amount=Decimal("20.45"), currency_id=Currency.USD),
        ],
        grand_total=Decimal("119.00"),
        due_amount=Decimal("119.00"),
    )
    xml = summation.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    # Both currency-tagged amounts must appear in the wire output.
    assert xml.count("<ram:TaxTotalAmount") == 2
    assert 'currencyID="EUR"' in xml
    assert 'currencyID="USD"' in xml
    parsed = MonetarySummation.from_xml(
        parser(wrap_subtree(xml, "SpecifiedTradeSettlementHeaderMonetarySummation"))
    )
    assert parsed == summation


def test_amount_currency_id_dropped_except_tax_total(parser: ParseFromBytes):
    """The Factur-X Schematron forbids ``currencyID`` on every monetary
    amount except ``TaxTotalAmount`` (BT-110 / BT-111). getafix renders it
    only there: the attribute is read but dropped on parse for the plain
    amounts, and never re-emitted on render. Bug sweep #7."""
    src = (
        "<ram:SpecifiedTradeSettlementHeaderMonetarySummation "
        'xmlns:ram="urn:un:unece:uncefact:data:standard:'
        'ReusableAggregateBusinessInformationEntity:100" '
        'xmlns:udt="urn:un:unece:uncefact:data:standard:'
        'UnqualifiedDataType:100">\n'
        '  <ram:LineTotalAmount currencyID="EUR">100.00</ram:LineTotalAmount>\n'
        '  <ram:TaxBasisTotalAmount currencyID="EUR">100.00</ram:TaxBasisTotalAmount>\n'
        '  <ram:TaxTotalAmount currencyID="EUR">19.00</ram:TaxTotalAmount>\n'
        '  <ram:GrandTotalAmount currencyID="EUR">119.00</ram:GrandTotalAmount>\n'
        '  <ram:DuePayableAmount currencyID="EUR">119.00</ram:DuePayableAmount>\n'
        "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
    )
    parsed = MonetarySummation.from_xml(parser(src.encode()))
    out = parsed.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    # Only TaxTotalAmount keeps its currencyID (via TaxTotal.currency_id);
    # the four plain amounts render bare.
    assert out.count('currencyID="EUR"') == 1
    assert '<ram:TaxTotalAmount currencyID="EUR">' in out
    assert "<ram:LineTotalAmount>100.00</ram:LineTotalAmount>" in out


def test_tax_currency_code_requires_matching_tax_total():
    """If BT-6 (TaxCurrencyCode) is set, MonetarySummation must carry a
    TaxTotal whose currency_id == BT-6 (BR-53)."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR)],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code=Currency.EUR,
        tax_currency_code=Currency.USD,
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code=UNTDID2475TaxPointDateCode.CODE_5,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=[PaymentTerms(due=date(2025, 12, 16))],
    )
    errors = settlement.validate_internal(Profile.BASIC_WL)
    assert any(v.code == "BR-53" for v in errors)

    # With matching second TaxTotal it passes.
    settlement.monetary_summation.tax_total = [
        TaxTotal(amount=Decimal("19"), currency_id=Currency.EUR),
        TaxTotal(amount=Decimal("20.45"), currency_id=Currency.USD),
    ]
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_9_vat_id_country_prefix():
    """BR-CO-9: VAT identifiers must start with an ISO 3166-1 alpha-2
    country prefix (with EL allowed for Greece)."""
    bad = TaxSchemeId(id="1234567890", scheme_id="VA")
    errors = bad.validate_internal(Profile.MINIMUM)
    assert any(v.code == "BR-CO-9" for v in errors)

    # Local tax identifiers (FC) are exempt — their codes are national.
    TaxSchemeId(id="201/113/40209", scheme_id="FC").validate_internal(Profile.MINIMUM)

    # German VAT prefix is fine.
    TaxSchemeId(id="DE123456789", scheme_id="VA").validate_internal(Profile.MINIMUM)
    # Greek 'EL' prefix is fine.
    TaxSchemeId(id="EL123456789", scheme_id="VA").validate_internal(Profile.MINIMUM)
