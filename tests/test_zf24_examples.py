"""Dedicated tests for the ZF24 official example invoices vendored under
``tests/samples/`` (prefix ``MINIMUM_zf24_*`` / ``BASICWL_zf24_*``).

Each example in the ZUGFeRD 2.4 / Factur-X 1.08 distribution illustrates a
specific subset of business terms — e.g. ``MINIMUM_Rechnung`` shows the
absolute bare-minimum invoice shape, ``BASIC-WL_Einfach`` demonstrates
BG-14 / BG-22 / BG-23 working together, ``Buchungshilfe`` variants exercise
``TypeCode=751`` (accounting voucher, **not** an Invoice).

These tests parse each example end-to-end through ``Document.from_xml``,
re-render through ``to_xml``, then assert the BT-* / BG-* values the
example was crafted to highlight are present. They double as regression
tests for the MINIMUM / BASIC_WL surface: any future refactor that drops
a field or mis-gates a profile will break here loudly.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import lxml.etree as etree
import pytest as pt

from carthorse.schema import Document, Profile
from carthorse.schema.types import TypeCode

SAMPLES_DIR = Path(__file__).parent / "samples"


def _load(name: str) -> Document:
    tree = etree.parse(str(SAMPLES_DIR / name))
    return Document.from_xml(tree.getroot())


def _roundtrip(doc: Document) -> Document:
    """Render to XML and parse back — equality must hold."""
    rendered = doc.to_xml().render(indent=True)
    reparsed = Document.from_xml(etree.fromstring(rendered.encode()))
    assert reparsed == doc, "round-trip produced a different Document"
    return reparsed


# ---------------------------------------------------------------------------
# MINIMUM_zf24_Rechnung — type=380 (Handelsrechnung)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def minimum_rechnung() -> Document:
    return _load("MINIMUM_zf24_Rechnung.xml")


class TestMinimumRechnung:
    """ZF24 MINIMUM example for a commercial Invoice (UNTDID 1001 = 380).

    Highlights from the spec example: only the few BTs MINIMUM requires.
    Seller name + country, Seller VAT id (BT-31) **and** local tax id
    (BT-32), Buyer name only (BG-8 omitted — legal at MINIMUM), invoice
    currency (BT-5), and the four required monetary totals (BT-109,
    BT-110, BT-112, BT-115)."""

    def test_profile_is_minimum(self, minimum_rechnung: Document) -> None:
        assert minimum_rechnung.context.guideline.id == Profile.MINIMUM

    def test_header(self, minimum_rechnung: Document) -> None:
        h = minimum_rechnung.header
        assert h.id == "471102"  # BT-1
        assert h.type_code == TypeCode.T_Handelsrechnung  # BT-3 = 380
        assert h.issue_date == date(2020, 3, 5)  # BT-2

    def test_seller_minimal_address_country_only(
        self, minimum_rechnung: Document
    ) -> None:
        seller = minimum_rechnung.trade.agreement.seller
        assert seller.name == "Lieferant GmbH"  # BT-27
        assert seller.address is not None  # BG-5 (required at MINIMUM)
        assert seller.address.country_id == "DE"  # BT-40
        # MINIMUM permits the address to carry nothing but BT-40.
        assert seller.address.line_one is None
        assert seller.address.city_name is None
        assert seller.address.postcode is None

    def test_seller_carries_both_vat_and_local_tax(
        self, minimum_rechnung: Document
    ) -> None:
        registrations = minimum_rechnung.trade.agreement.seller.tax_registrations
        assert registrations is not None
        scheme_to_id = {r.id.scheme_id: r.id.id for r in registrations}
        # BT-32 (local tax id, schemeID=FC) and BT-31 (VAT id, schemeID=VA)
        # MUST be supported simultaneously per the MINIMUM XSD
        # (SpecifiedTaxRegistration maxOccurs="2").
        assert scheme_to_id["FC"] == "201/113/40209"
        assert scheme_to_id["VA"] == "DE123456789"

    def test_buyer_has_name_only(self, minimum_rechnung: Document) -> None:
        # The ZF24 example deliberately omits BG-8 to demonstrate that
        # BR-10 (Buyer postal address) does NOT apply at MINIMUM.
        buyer = minimum_rechnung.trade.agreement.buyer
        assert buyer.name == "Kunden AG Frankreich"
        assert buyer.address is None

    def test_settlement_is_currency_and_totals_only(
        self, minimum_rechnung: Document
    ) -> None:
        s = minimum_rechnung.trade.settlement
        assert s.currency_code == "EUR"  # BT-5
        m = s.monetary_summation
        assert m.tax_basis_total == Decimal("198.00")  # BT-109
        assert m.tax_total is not None and len(m.tax_total) == 1
        assert m.tax_total[0].amount == Decimal("37.62")  # BT-110
        assert m.tax_total[0].currency_id == "EUR"
        assert m.grand_total == Decimal("235.62")  # BT-112
        assert m.due_amount == Decimal("235.62")  # BT-115
        # MINIMUM does NOT carry BT-106; no payment terms, no
        # ApplicableTradeTax (BG-23), no PaymentMeans (BG-16), …
        assert m.line_total is None
        assert s.terms is None
        assert not s.trade_taxes  # absent at MINIMUM
        assert s.payment_means is None

    def test_validate_clean(self, minimum_rechnung: Document) -> None:
        minimum_rechnung.validate()

    def test_roundtrip(self, minimum_rechnung: Document) -> None:
        _roundtrip(minimum_rechnung)


# ---------------------------------------------------------------------------
# MINIMUM_zf24_Buchungshilfe — type=751 (NOT an invoice, accounting voucher)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def minimum_buchungshilfe() -> Document:
    return _load("MINIMUM_zf24_Buchungshilfe.xml")


class TestMinimumBuchungshilfe:
    """ZF24 MINIMUM example for a booking-aid voucher (UNTDID 1001 = 751).

    Highlights: same MINIMUM shape but ``TypeCode=751`` flags the document
    as **not** an invoice but accounting information."""

    def test_profile_is_minimum(self, minimum_buchungshilfe: Document) -> None:
        assert minimum_buchungshilfe.context.guideline.id == Profile.MINIMUM

    def test_type_code_is_751(self, minimum_buchungshilfe: Document) -> None:
        # UNTDID 1001 code 751 = "Invoice information for accounting
        # purposes" — explicitly NOT an Invoice. Permitted at MINIMUM
        # and BASIC_WL per the appendix narrative.
        assert minimum_buchungshilfe.header.type_code == TypeCode.T_751

    def test_buyer_has_name_only(self, minimum_buchungshilfe: Document) -> None:
        buyer = minimum_buchungshilfe.trade.agreement.buyer
        assert buyer.name == "Kunden AG Mitte"
        assert buyer.address is None

    def test_seller_dual_tax_ids(self, minimum_buchungshilfe: Document) -> None:
        registrations = minimum_buchungshilfe.trade.agreement.seller.tax_registrations
        assert registrations is not None and len(registrations) == 2

    def test_validate_clean(self, minimum_buchungshilfe: Document) -> None:
        minimum_buchungshilfe.validate()

    def test_roundtrip(self, minimum_buchungshilfe: Document) -> None:
        _roundtrip(minimum_buchungshilfe)


# ---------------------------------------------------------------------------
# BASICWL_zf24_Einfach — BR-12, BR-CO-18, BG-23, payment terms with due date
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def basicwl_einfach() -> Document:
    return _load("BASICWL_zf24_Einfach.xml")


class TestBasicWlEinfach:
    """ZF24 BASIC_WL example for a simple invoice (taxi fare).

    Highlights: BG-1 IncludedNote × 3 (free-text), BT-72 actual delivery
    date, BG-23 ApplicableTradeTax (S, 7%), BG-22 with BT-106 LineTotal
    populated, payment terms with BT-9 due date."""

    def test_profile_is_basic_wl(self, basicwl_einfach: Document) -> None:
        assert basicwl_einfach.context.guideline.id == Profile.BASIC_WL

    def test_three_included_notes(self, basicwl_einfach: Document) -> None:
        # BG-1 IncludedNote repeats — 3 entries in this example.
        notes = basicwl_einfach.header.notes
        assert notes is not None and len(notes) == 3
        assert "Taxifahrt" in (notes[0].content or "")

    def test_buyer_address_present_at_basic_wl(
        self, basicwl_einfach: Document
    ) -> None:
        # BR-10 enforced from BASIC_WL up — BG-8 must be present.
        buyer = basicwl_einfach.trade.agreement.buyer
        assert buyer.address is not None
        assert buyer.address.country_id == "DE"  # BT-55

    def test_actual_delivery_date(self, basicwl_einfach: Document) -> None:
        # BT-72 actual delivery date, inside BG-13-00 ActualDeliverySupplyChainEvent.
        event = basicwl_einfach.trade.delivery.event
        assert event is not None
        assert event.occurrence == date(2019, 10, 29)

    def test_bg23_vat_breakdown(self, basicwl_einfach: Document) -> None:
        # BG-23 (ApplicableTradeTax) — one row, category S, rate 7%.
        taxes = basicwl_einfach.trade.settlement.trade_taxes
        assert taxes is not None and len(taxes) == 1
        t = taxes[0]
        assert t.type_code == "VAT"  # BT-118-0
        assert t.category_code == "S"  # BT-118
        assert t.rate_applicable_percent == Decimal("7")  # BT-119
        assert t.basis_amount == Decimal("16.90")  # BT-116
        assert t.calculated_amount == Decimal("1.18")  # BT-117

    def test_payment_terms_due_date(self, basicwl_einfach: Document) -> None:
        terms = basicwl_einfach.trade.settlement.terms
        assert terms is not None
        assert terms.due == date(2019, 11, 29)  # BT-9

    def test_monetary_summation_full(self, basicwl_einfach: Document) -> None:
        m = basicwl_einfach.trade.settlement.monetary_summation
        # BT-106 BasicWL-required, BR-12.
        assert m.line_total == Decimal("16.90")
        assert m.charge_total == Decimal("0.00")  # BT-108
        assert m.allowance_total == Decimal("0.00")  # BT-107
        assert m.tax_basis_total == Decimal("16.90")  # BT-109
        assert m.tax_total is not None
        assert m.tax_total[0].amount == Decimal("1.18")  # BT-110
        assert m.grand_total == Decimal("18.08")  # BT-112
        assert m.due_amount == Decimal("18.08")  # BT-115

    def test_validate_clean(self, basicwl_einfach: Document) -> None:
        basicwl_einfach.validate()

    def test_roundtrip(self, basicwl_einfach: Document) -> None:
        _roundtrip(basicwl_einfach)


# ---------------------------------------------------------------------------
# BASICWL_zf24_Buchungshilfe — same shape as Einfach but TypeCode=751
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def basicwl_buchungshilfe() -> Document:
    return _load("BASICWL_zf24_Buchungshilfe.xml")


class TestBasicWlBuchungshilfe:
    """ZF24 BASIC_WL voucher (UNTDID 1001 = 751).

    Same field set as BASIC-WL_Einfach but the document is flagged as
    accounting information (TypeCode=751)."""

    def test_profile_is_basic_wl(self, basicwl_buchungshilfe: Document) -> None:
        assert basicwl_buchungshilfe.context.guideline.id == Profile.BASIC_WL

    def test_type_code_is_751(self, basicwl_buchungshilfe: Document) -> None:
        assert basicwl_buchungshilfe.header.type_code == TypeCode.T_751

    def test_notes_and_delivery_present(
        self, basicwl_buchungshilfe: Document
    ) -> None:
        notes = basicwl_buchungshilfe.header.notes
        assert notes is not None and len(notes) == 3
        event = basicwl_buchungshilfe.trade.delivery.event
        assert event is not None and event.occurrence == date(2019, 10, 29)

    def test_validate_clean(self, basicwl_buchungshilfe: Document) -> None:
        basicwl_buchungshilfe.validate()

    def test_roundtrip(self, basicwl_buchungshilfe: Document) -> None:
        _roundtrip(basicwl_buchungshilfe)
