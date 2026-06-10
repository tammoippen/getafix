"""Tests for the high-level factories in :mod:`getafix.build`.

Each profile constructor must produce a document that (a) passes
``Document.validate()`` out of the box, (b) renders, and (c) is valid
against the profile XSD (when lxml is available). The piece-wise
factories (:func:`line_item`, :func:`vat_breakdown`,
:func:`monetary_summation`) are checked against the BR-CO-* arithmetic
they claim to satisfy, plus their error paths.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest as pt

from getafix.build import (
    basic_wl_invoice,
    buyer_party,
    invoice,
    line_item,
    minimum_invoice,
    monetary_summation,
    seller_party,
    vat_breakdown,
)
from getafix.schema import Document, Profile
from getafix.schema.accounting import (
    ApplicableTradeTax,
    CategoryTradeTax,
    HeaderTradeAllowanceCharge,
)
from getafix.schema.settlement import PaymentTerms
from getafix.schema.types import CategoryCode, Country, Currency, VATEXCode

SCHEMAS_DIR = Path(__file__).parent / "schemas"

_PROFILE_TO_XSD: dict[Profile, Path] = {
    Profile.MINIMUM: SCHEMAS_DIR / "0_Factur-X_1.08_MINIMUM" / "FACTUR-X_MINIMUM.xsd",
    Profile.BASIC_WL: SCHEMAS_DIR / "1_Factur-X_1.08_BASICWL" / "FACTUR-X_BASIC-WL.xsd",
    Profile.BASIC: SCHEMAS_DIR / "2_Factur-X_1.08_BASIC" / "FACTUR-X_BASIC.xsd",
    Profile.COMFORT: SCHEMAS_DIR / "3_Factur-X_1.08_EN16931" / "FACTUR-X_EN16931.xsd",
    Profile.EXTENDED: SCHEMAS_DIR
    / "4_Factur-X_1.08_EXTENDED"
    / "FACTUR-X_EXTENDED.xsd",
}

_SCHEMA_CACHE: dict[Profile, object] = {}


def _assert_xsd_valid(doc: Document) -> None:
    """Validate the rendered document against its profile XSD."""
    etree = pt.importorskip("lxml.etree", reason="XSD validation requires lxml")
    profile = doc.context.guideline.id
    schema = _SCHEMA_CACHE.get(profile)
    if schema is None:
        schema = etree.XMLSchema(etree.parse(str(_PROFILE_TO_XSD[profile])))
        _SCHEMA_CACHE[profile] = schema
    parsed = etree.fromstring(doc.to_xml().render(indent=True).encode())
    schema.assertValid(parsed)


def _seller():
    return seller_party(
        "Acme GmbH",
        country=Country.DE,
        vat_id="DE123456789",
        postcode="80331",
        city="München",
        line_one="Musterstraße 1",
    )


def _buyer():
    return buyer_party(
        "Beta AG",
        country=Country.DE,
        vat_id="DE987654321",
        postcode="50667",
        city="Köln",
        line_one="Domplatz 2",
    )


# ---------------------------------------------------------------------------
# party helpers
# ---------------------------------------------------------------------------


def test_seller_party_wires_registrations_and_address() -> None:
    seller = seller_party(
        "Acme GmbH",
        country=Country.DE,
        vat_id="DE123456789",
        tax_id="201/113/40209",
        city="München",
    )
    assert seller.name == "Acme GmbH"
    assert seller.address.country_id == Country.DE
    assert seller.address.city_name == "München"
    regs = seller.tax_registrations
    assert regs is not None
    assert [(r.id.id, r.id.scheme_id) for r in regs] == [
        ("DE123456789", "VA"),
        ("201/113/40209", "FC"),
    ]


def test_buyer_party_without_ids_has_no_registrations() -> None:
    buyer = buyer_party("Beta AG", country=Country.FR)
    assert buyer.tax_registrations is None
    assert buyer.address is not None
    assert buyer.address.country_id == Country.FR


# ---------------------------------------------------------------------------
# line_item
# ---------------------------------------------------------------------------


def test_line_item_computes_line_total() -> None:
    item = line_item("1", "Widget", net_price="100.00", quantity=3, vat_rate=19)
    assert item.settlement.monetary_summation.line_total == Decimal("300.00")
    assert item.delivery.billed_quantity is not None
    assert item.delivery.billed_quantity.value == Decimal("3")
    assert item.delivery.billed_quantity.unit_code == "C62"
    tt = item.settlement.applicable_trade_tax
    assert tt is not None
    assert tt.category_code == CategoryCode.T_S
    assert tt.rate_applicable_percent == Decimal("19")


def test_line_item_rounds_half_away_from_zero() -> None:
    item = line_item("1", "W", net_price="13.455", quantity=1, vat_rate=19)
    assert item.settlement.monetary_summation.line_total == Decimal("13.46")


def test_line_item_basis_quantity_scales_the_total() -> None:
    # 7.90 per 100 pieces, 250 pieces billed -> 19.75
    item = line_item(
        "1",
        "Screw",
        net_price="7.90",
        quantity=250,
        unit_code="H87",
        basis_quantity=100,
        vat_rate=19,
    )
    assert item.settlement.monetary_summation.line_total == Decimal("19.75")
    net = item.agreement.net_price
    assert net is not None
    assert net.basis_quantity is not None
    assert net.basis_quantity.value == Decimal("100")
    assert net.basis_quantity.unit_code == "H87"


def test_line_item_gross_price_derives_discount() -> None:
    item = line_item(
        "1", "W", net_price="90.00", gross_price="100.00", quantity=1, vat_rate=19
    )
    gross = item.agreement.gross_price
    assert gross is not None
    assert gross.charge_amount == Decimal("100.00")
    assert gross.applied_allowance_charge is not None
    (allowance,) = gross.applied_allowance_charge
    assert allowance.indicator is False
    assert allowance.actual_amount == Decimal("10.00")


def test_line_item_gross_equal_net_has_no_discount() -> None:
    item = line_item(
        "1", "W", net_price="90.00", gross_price="90.00", quantity=1, vat_rate=19
    )
    gross = item.agreement.gross_price
    assert gross is not None
    assert gross.applied_allowance_charge is None


def test_line_item_gross_below_net_raises() -> None:
    with pt.raises(ValueError, match="gross_price"):
        line_item("1", "W", net_price="90", gross_price="80", vat_rate=19)


def test_line_item_zero_rate_categories_default_to_zero() -> None:
    for category in (
        CategoryCode.T_Z,
        CategoryCode.T_E,
        CategoryCode.T_AE,
        CategoryCode.T_G,
        CategoryCode.T_K,
    ):
        item = line_item("1", "W", net_price="10", vat_category=category)
        tt = item.settlement.applicable_trade_tax
        assert tt is not None
        assert tt.rate_applicable_percent == Decimal("0")


def test_line_item_category_o_carries_no_rate() -> None:
    item = line_item("1", "W", net_price="10", vat_category=CategoryCode.T_O)
    tt = item.settlement.applicable_trade_tax
    assert tt is not None
    assert tt.rate_applicable_percent is None


def test_line_item_category_o_with_rate_raises() -> None:
    with pt.raises(ValueError, match="'O'"):
        line_item("1", "W", net_price="10", vat_category=CategoryCode.T_O, vat_rate=0)


def test_line_item_standard_rate_requires_explicit_rate() -> None:
    with pt.raises(ValueError, match="vat_rate is required"):
        line_item("1", "W", net_price="10")


def test_line_item_rejects_float() -> None:
    with pt.raises(TypeError, match="float"):
        line_item("1", "W", net_price=10.0, vat_rate=19)


def test_line_item_note_and_description() -> None:
    item = line_item(
        "1", "W", net_price="10", vat_rate=19, description="blue", note="fragile"
    )
    assert item.product.description == "blue"
    assert item.associated_document.note is not None
    assert item.associated_document.note.content == "fragile"


# ---------------------------------------------------------------------------
# vat_breakdown
# ---------------------------------------------------------------------------


def test_vat_breakdown_groups_by_category_and_rate() -> None:
    items = [
        line_item("1", "A", net_price="100.00", quantity=3, vat_rate=19),
        line_item("2", "B", net_price="9.90", quantity=2, vat_rate=7),
        line_item("3", "C", net_price="50.00", vat_rate=19),
    ]
    rows = vat_breakdown(items, currency=Currency.EUR)
    by_key = {(r.category_code, r.rate_applicable_percent): r for r in rows}
    s19 = by_key[(CategoryCode.T_S, Decimal("19"))]
    s7 = by_key[(CategoryCode.T_S, Decimal("7"))]
    assert s19.basis_amount == Decimal("350.00")
    assert s19.calculated_amount == Decimal("66.50")
    assert s7.basis_amount == Decimal("19.80")
    assert s7.calculated_amount == Decimal("1.39")  # 1.386 rounds up
    assert s19.currency == "EUR"


def test_vat_breakdown_nets_allowances_and_charges() -> None:
    items = [line_item("1", "A", net_price="100.00", vat_rate=19)]
    acs = [
        HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            reason="discount",
            category_trade_tax=CategoryTradeTax(
                category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
            ),
        ),
        HeaderTradeAllowanceCharge(
            indicator=True,
            actual_amount=Decimal("3.00"),
            reason="shipping",
            category_trade_tax=CategoryTradeTax(
                category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
            ),
        ),
    ]
    (row,) = vat_breakdown(items, acs)
    assert row.basis_amount == Decimal("98.00")
    assert row.calculated_amount == Decimal("18.62")


def test_vat_breakdown_defaults_canonical_exemption_codes() -> None:
    items = [
        line_item("1", "A", net_price="10", vat_category=CategoryCode.T_AE),
        line_item("2", "B", net_price="10", vat_category=CategoryCode.T_K),
        line_item("3", "C", net_price="10", vat_category=CategoryCode.T_G),
        line_item("4", "D", net_price="10", vat_category=CategoryCode.T_O),
    ]
    rows = {r.category_code: r for r in vat_breakdown(items)}
    assert rows[CategoryCode.T_AE].exemption_reason_code == VATEXCode.VATEX_EU_AE
    assert rows[CategoryCode.T_K].exemption_reason_code == VATEXCode.VATEX_EU_IC
    assert rows[CategoryCode.T_G].exemption_reason_code == VATEXCode.VATEX_EU_G
    assert rows[CategoryCode.T_O].exemption_reason_code == VATEXCode.VATEX_EU_O
    assert rows[CategoryCode.T_O].calculated_amount == Decimal("0.00")


def test_vat_breakdown_category_e_requires_explicit_reason() -> None:
    items = [line_item("1", "A", net_price="10", vat_category=CategoryCode.T_E)]
    with pt.raises(ValueError, match="'E'"):
        vat_breakdown(items)
    (row,) = vat_breakdown(
        items, exemption_reasons={CategoryCode.T_E: "Exempt under §4 UStG"}
    )
    assert row.exemption_reason == "Exempt under §4 UStG"
    assert row.exemption_reason_code is None


def test_vat_breakdown_allowance_without_category_raises() -> None:
    items = [line_item("1", "A", net_price="10", vat_rate=19)]
    acs = [
        HeaderTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("1.00"), reason="x"
        )
    ]
    with pt.raises(ValueError, match="BT-95-00"):
        vat_breakdown(items, acs)


def test_vat_breakdown_line_without_vat_or_total_raises() -> None:
    item = line_item("1", "A", net_price="10", vat_rate=19)
    item.settlement.applicable_trade_tax = None
    with pt.raises(ValueError, match="BG-30"):
        vat_breakdown([item])
    item = line_item("1", "A", net_price="10", vat_rate=19)
    item.settlement.monetary_summation.line_total = None
    with pt.raises(ValueError, match="BT-131"):
        vat_breakdown([item])


# ---------------------------------------------------------------------------
# monetary_summation
# ---------------------------------------------------------------------------


def test_monetary_summation_identities() -> None:
    taxes = [
        ApplicableTradeTax(
            calculated_amount=Decimal("18.62"),
            basis_amount=Decimal("98.00"),
            category_code=CategoryCode.T_S,
            rate_applicable_percent=Decimal("19"),
        )
    ]
    acs = [
        HeaderTradeAllowanceCharge(
            indicator=False,
            actual_amount=Decimal("5.00"),
            category_trade_tax=CategoryTradeTax(
                category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
            ),
        ),
        HeaderTradeAllowanceCharge(
            indicator=True,
            actual_amount=Decimal("3.00"),
            category_trade_tax=CategoryTradeTax(
                category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
            ),
        ),
    ]
    ms = monetary_summation(
        currency=Currency.EUR,
        line_total="100.00",
        trade_taxes=taxes,
        allowance_charges=acs,
        prepaid_total="10.00",
    )
    assert ms.allowance_total == Decimal("5.00")
    assert ms.charge_total == Decimal("3.00")
    assert ms.tax_basis_total == Decimal("98.00")  # BR-CO-13
    assert ms.tax_total is not None
    assert ms.tax_total[0].amount == Decimal("18.62")  # BR-CO-14
    assert ms.grand_total == Decimal("116.62")  # BR-CO-15
    assert ms.due_amount == Decimal("106.62")  # BR-CO-16
    assert ms.currency == "EUR"


def test_monetary_summation_without_line_total_sums_bases() -> None:
    taxes = [
        ApplicableTradeTax(
            calculated_amount=Decimal("19.00"),
            basis_amount=Decimal("100.00"),
            category_code=CategoryCode.T_S,
            rate_applicable_percent=Decimal("19"),
        ),
        ApplicableTradeTax(
            calculated_amount=Decimal("0.00"),
            basis_amount=Decimal("50.00"),
            category_code=CategoryCode.T_Z,
            rate_applicable_percent=Decimal("0"),
        ),
    ]
    ms = monetary_summation(currency=Currency.EUR, trade_taxes=taxes)
    assert ms.line_total is None
    assert ms.tax_basis_total == Decimal("150.00")
    assert ms.grand_total == Decimal("169.00")
    assert ms.due_amount == Decimal("169.00")


# ---------------------------------------------------------------------------
# minimum_invoice
# ---------------------------------------------------------------------------


def test_minimum_invoice_with_vat_rate() -> None:
    doc = minimum_invoice(
        "INV-1",
        date(2025, 1, 1),
        seller=seller_party("Acme GmbH", country=Country.DE, vat_id="DE123456789"),
        buyer=buyer_party("Beta AG", country=Country.DE),
        tax_basis_total="100.00",
        vat_rate=19,
    )
    assert doc.context.guideline.id == Profile.MINIMUM
    ms = doc.trade.settlement.monetary_summation
    assert ms.tax_basis_total == Decimal("100.00")
    assert ms.tax_total is not None
    assert ms.tax_total[0].amount == Decimal("19.00")
    assert ms.grand_total == Decimal("119.00")
    assert ms.due_amount == Decimal("119.00")
    doc.validate()
    _assert_xsd_valid(doc)


def test_minimum_invoice_with_explicit_tax_amount() -> None:
    doc = minimum_invoice(
        "INV-1",
        date(2025, 1, 1),
        seller=seller_party("Acme GmbH", country=Country.DE, vat_id="DE123456789"),
        buyer=buyer_party("Beta AG", country=Country.DE),
        tax_basis_total="100.00",
        tax_amount="19.00",
        buyer_reference="04011000-12345-03",
    )
    assert doc.trade.agreement.buyer_reference == "04011000-12345-03"
    assert doc.trade.settlement.monetary_summation.grand_total == Decimal("119.00")
    doc.validate()


def test_minimum_invoice_without_tax() -> None:
    doc = minimum_invoice(
        "INV-1",
        date(2025, 1, 1),
        seller=seller_party("Acme GmbH", country=Country.DE, vat_id="DE123456789"),
        buyer=buyer_party("Beta AG", country=Country.DE),
        tax_basis_total="100.00",
    )
    ms = doc.trade.settlement.monetary_summation
    assert ms.tax_total is None
    assert ms.grand_total == Decimal("100.00")
    doc.validate()
    _assert_xsd_valid(doc)


def test_minimum_invoice_tax_amount_and_rate_conflict() -> None:
    with pt.raises(ValueError, match="either tax_amount or vat_rate"):
        minimum_invoice(
            "INV-1",
            date(2025, 1, 1),
            seller=seller_party("S", country=Country.DE, vat_id="DE123456789"),
            buyer=buyer_party("B", country=Country.DE),
            tax_basis_total="100.00",
            tax_amount="19.00",
            vat_rate=19,
        )


# ---------------------------------------------------------------------------
# basic_wl_invoice
# ---------------------------------------------------------------------------


def test_basic_wl_invoice_completes_rows_and_totals() -> None:
    doc = basic_wl_invoice(
        "INV-2",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        trade_taxes=[
            ApplicableTradeTax(
                basis_amount=Decimal("100.00"),
                category_code=CategoryCode.T_S,
                rate_applicable_percent=Decimal("19"),
            ),
            ApplicableTradeTax(
                basis_amount=Decimal("50.00"),
                category_code=CategoryCode.T_AE,
                rate_applicable_percent=Decimal("0"),
            ),
        ],
        due_date=date(2025, 2, 1),
        delivery_date=date(2024, 12, 24),
        notes=["Thank you for your order."],
    )
    assert doc.context.guideline.id == Profile.BASIC_WL
    taxes = doc.trade.settlement.trade_taxes
    assert taxes is not None
    s_row = next(t for t in taxes if t.category_code == CategoryCode.T_S)
    ae_row = next(t for t in taxes if t.category_code == CategoryCode.T_AE)
    assert s_row.calculated_amount == Decimal("19.00")
    assert ae_row.calculated_amount == Decimal("0.00")
    assert ae_row.exemption_reason_code == VATEXCode.VATEX_EU_AE
    ms = doc.trade.settlement.monetary_summation
    assert ms.line_total == Decimal("150.00")
    assert ms.tax_basis_total == Decimal("150.00")
    assert ms.grand_total == Decimal("169.00")
    assert doc.trade.delivery.event is not None
    assert doc.trade.delivery.event.occurrence == date(2024, 12, 24)
    assert doc.header.notes is not None
    assert doc.header.notes[0].content == "Thank you for your order."
    doc.validate()
    _assert_xsd_valid(doc)


def test_basic_wl_invoice_with_allowance_charge_derives_line_total() -> None:
    # BT-116 already nets in the allowance/charge; BT-106 is recovered
    # via the inverse of BR-CO-13.
    doc = basic_wl_invoice(
        "INV-3",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        trade_taxes=[
            ApplicableTradeTax(
                basis_amount=Decimal("98.00"),
                category_code=CategoryCode.T_S,
                rate_applicable_percent=Decimal("19"),
            )
        ],
        allowance_charges=[
            HeaderTradeAllowanceCharge(
                indicator=False,
                actual_amount=Decimal("5.00"),
                reason="discount",
                category_trade_tax=CategoryTradeTax(
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19"),
                ),
            ),
            HeaderTradeAllowanceCharge(
                indicator=True,
                actual_amount=Decimal("3.00"),
                reason="shipping",
                category_trade_tax=CategoryTradeTax(
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19"),
                ),
            ),
        ],
        terms=PaymentTerms(description="Net 30 days"),
        prepaid_total="10.00",
    )
    ms = doc.trade.settlement.monetary_summation
    assert ms.line_total == Decimal("100.00")
    assert ms.tax_basis_total == Decimal("98.00")
    assert ms.grand_total == Decimal("116.62")
    assert ms.due_amount == Decimal("106.62")
    acs = doc.trade.settlement.allowance_charge
    assert acs is not None
    assert all(ac.currency == "EUR" for ac in acs)
    doc.validate()
    _assert_xsd_valid(doc)


def test_basic_wl_invoice_row_without_basis_raises() -> None:
    with pt.raises(ValueError, match="BT-116"):
        basic_wl_invoice(
            "INV-4",
            date(2025, 1, 1),
            seller=_seller(),
            buyer=_buyer(),
            trade_taxes=[
                ApplicableTradeTax(
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19"),
                )
            ],
            due_date=date(2025, 2, 1),
        )


def test_terms_and_due_date_conflict() -> None:
    with pt.raises(ValueError, match="either terms or due_date"):
        basic_wl_invoice(
            "INV-5",
            date(2025, 1, 1),
            seller=_seller(),
            buyer=_buyer(),
            trade_taxes=[
                ApplicableTradeTax(
                    basis_amount=Decimal("1.00"),
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19"),
                )
            ],
            due_date=date(2025, 2, 1),
            terms=PaymentTerms(due=date(2025, 2, 1)),
        )


# ---------------------------------------------------------------------------
# invoice (BASIC+)
# ---------------------------------------------------------------------------


def test_invoice_comfort_default_end_to_end() -> None:
    doc = invoice(
        "INV-6",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        items=[
            line_item("1", "Widget", net_price="100.00", quantity=3, vat_rate=19),
            line_item("2", "Gadget", net_price="9.90", quantity=2, vat_rate=7),
        ],
        due_date=date(2025, 2, 1),
    )
    assert doc.context.guideline.id == Profile.COMFORT
    ms = doc.trade.settlement.monetary_summation
    assert ms.line_total == Decimal("319.80")
    assert ms.tax_basis_total == Decimal("319.80")
    assert ms.tax_total is not None
    assert ms.tax_total[0].amount == Decimal("58.39")  # 57.00 + 1.39
    assert ms.grand_total == Decimal("378.19")
    assert ms.due_amount == Decimal("378.19")
    doc.validate()
    _assert_xsd_valid(doc)


def test_invoice_basic_profile_with_allowance_charge() -> None:
    doc = invoice(
        "INV-7",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        items=[line_item("1", "Widget", net_price="100.00", vat_rate=19)],
        profile=Profile.BASIC,
        allowance_charges=[
            HeaderTradeAllowanceCharge(
                indicator=False,
                actual_amount=Decimal("5.00"),
                reason="discount",
                category_trade_tax=CategoryTradeTax(
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19"),
                ),
            )
        ],
        due_date=date(2025, 2, 1),
        delivery_date=date(2024, 12, 24),
    )
    ms = doc.trade.settlement.monetary_summation
    assert ms.line_total == Decimal("100.00")
    assert ms.allowance_total == Decimal("5.00")
    assert ms.tax_basis_total == Decimal("95.00")
    assert ms.grand_total == Decimal("113.05")
    doc.validate()
    _assert_xsd_valid(doc)


def test_invoice_extended_profile_renders() -> None:
    doc = invoice(
        "INV-8",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        items=[line_item("1", "Widget", net_price="100.00", vat_rate=19)],
        profile=Profile.EXTENDED,
        due_date=date(2025, 2, 1),
    )
    doc.validate()
    _assert_xsd_valid(doc)


def test_invoice_reverse_charge_defaults_exemption_code() -> None:
    doc = invoice(
        "INV-9",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        items=[
            line_item(
                "1", "Consulting", net_price="500.00", vat_category=CategoryCode.T_AE
            )
        ],
        due_date=date(2025, 2, 1),
    )
    taxes = doc.trade.settlement.trade_taxes
    assert taxes is not None
    assert taxes[0].exemption_reason_code == VATEXCode.VATEX_EU_AE
    assert doc.trade.settlement.monetary_summation.grand_total == Decimal("500.00")
    doc.validate()
    _assert_xsd_valid(doc)


def test_invoice_prepaid_and_rounding() -> None:
    doc = invoice(
        "INV-10",
        date(2025, 1, 1),
        seller=_seller(),
        buyer=_buyer(),
        items=[line_item("1", "Widget", net_price="100.00", vat_rate=19)],
        prepaid_total="19.00",
        rounding_amount="0.05",
        due_date=date(2025, 2, 1),
    )
    ms = doc.trade.settlement.monetary_summation
    assert ms.due_amount == Decimal("100.05")  # 119.00 - 19.00 + 0.05
    doc.validate()
    _assert_xsd_valid(doc)


def test_invoice_rejects_profiles_without_line_items() -> None:
    with pt.raises(ValueError, match="minimum_invoice"):
        invoice(
            "INV-11",
            date(2025, 1, 1),
            seller=_seller(),
            buyer=_buyer(),
            items=[line_item("1", "W", net_price="1", vat_rate=19)],
            profile=Profile.MINIMUM,
        )


def test_invoice_rejects_empty_items() -> None:
    with pt.raises(ValueError, match="BR-16"):
        invoice("INV-12", date(2025, 1, 1), seller=_seller(), buyer=_buyer(), items=[])
