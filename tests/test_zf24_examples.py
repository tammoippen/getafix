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
        assert h.type_code == TypeCode.T_CommercialInvoice  # BT-3 = 380
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
        assert m.tax_total is not None
        assert len(m.tax_total) == 1
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
        assert minimum_buchungshilfe.header.type_code == TypeCode.T_AccountingNote

    def test_buyer_has_name_only(self, minimum_buchungshilfe: Document) -> None:
        buyer = minimum_buchungshilfe.trade.agreement.buyer
        assert buyer.name == "Kunden AG Mitte"
        assert buyer.address is None

    def test_seller_dual_tax_ids(self, minimum_buchungshilfe: Document) -> None:
        registrations = minimum_buchungshilfe.trade.agreement.seller.tax_registrations
        assert registrations is not None
        assert len(registrations) == 2

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

    Highlights: BG-1 IncludedNote x 3 (free-text), BT-72 actual delivery
    date, BG-23 ApplicableTradeTax (S, 7%), BG-22 with BT-106 LineTotal
    populated, payment terms with BT-9 due date."""

    def test_profile_is_basic_wl(self, basicwl_einfach: Document) -> None:
        assert basicwl_einfach.context.guideline.id == Profile.BASIC_WL

    def test_three_included_notes(self, basicwl_einfach: Document) -> None:
        # BG-1 IncludedNote repeats — 3 entries in this example.
        notes = basicwl_einfach.header.notes
        assert notes is not None
        assert len(notes) == 3
        assert "Taxifahrt" in (notes[0].content or "")

    def test_buyer_address_present_at_basic_wl(self, basicwl_einfach: Document) -> None:
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
        assert taxes is not None
        assert len(taxes) == 1
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
        assert basicwl_buchungshilfe.header.type_code == TypeCode.T_AccountingNote

    def test_notes_and_delivery_present(self, basicwl_buchungshilfe: Document) -> None:
        notes = basicwl_buchungshilfe.header.notes
        assert notes is not None
        assert len(notes) == 3
        event = basicwl_buchungshilfe.trade.delivery.event
        assert event is not None
        assert event.occurrence == date(2019, 10, 29)

    def test_validate_clean(self, basicwl_buchungshilfe: Document) -> None:
        basicwl_buchungshilfe.validate()

    def test_roundtrip(self, basicwl_buchungshilfe: Document) -> None:
        _roundtrip(basicwl_buchungshilfe)


# ---------------------------------------------------------------------------
# BASIC_zf24_Einfach — first line-item-bearing profile
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def basic_einfach() -> Document:
    return _load("BASIC_zf24_Einfach.xml")


class TestBasicEinfach:
    """ZF24 BASIC simple invoice: one line item with VAT 19% standard rate.

    Highlights: BG-25 line items first appear at BASIC. The example
    demonstrates ``AssociatedDocumentLineDocument`` (BT-126), product
    GlobalID with schemeID, BilledQuantity with unitCode (BT-129 +
    BT-130), line tax category, line monetary summation (BT-131)."""

    def test_profile_is_basic(self, basic_einfach: Document) -> None:
        assert basic_einfach.context.guideline.id == Profile.BASIC

    def test_single_line_item(self, basic_einfach: Document) -> None:
        # BR-16: at BASIC and above the Invoice must contain at least
        # one BG-25 line item. The Einfach example carries exactly one.
        assert len(basic_einfach.trade.items) == 1

    def test_line_carries_global_id_with_scheme(self, basic_einfach: Document) -> None:
        item = basic_einfach.trade.items[0]
        assert item.associated_document.line_id == "1"  # BT-126
        # BT-157 / BT-157-1: item global identifier with schemeID. The
        # ZF24 example uses GS1 GTIN-13 (schemeID="0160" per ISO 6523).
        product = item.product
        assert product.name.startswith("GTIN: 4012345001235")  # BT-153
        assert product.global_id is not None
        assert product.global_id.id == "4012345001235"
        assert product.global_id.scheme_id == "0160"

    def test_line_quantity_and_unit_code(self, basic_einfach: Document) -> None:
        # BT-129 BilledQuantity + BT-130 UnitCode (UN/ECE Rec 20). H87 = piece.
        delivery = basic_einfach.trade.items[0].delivery
        assert delivery.billed_quantity.value == Decimal("20.0000")
        assert delivery.billed_quantity.unit_code == "H87"

    def test_line_vat_category_standard(self, basic_einfach: Document) -> None:
        # Line VAT category (BG-30) — standard rate, 19%.
        tax = basic_einfach.trade.items[0].settlement.applicable_trade_tax
        assert tax.type_code == "VAT"
        assert tax.category_code == "S"
        assert tax.rate_applicable_percent == Decimal("19")

    def test_line_total(self, basic_einfach: Document) -> None:
        # BT-131: line net amount = 20 x 9.90 = 198.00.
        item = basic_einfach.trade.items[0]
        assert item.agreement.net_price.charge_amount == Decimal("9.90")  # BT-146
        assert item.settlement.monetary_summation.line_total == Decimal("198.00")

    def test_header_arithmetic(self, basic_einfach: Document) -> None:
        # BR-CO-10 / BR-CO-13: BT-106 = sum(BT-131); BT-109 = BT-106 - BT-107 + BT-108.
        m = basic_einfach.trade.settlement.monetary_summation
        assert m.line_total == Decimal("198.00")
        assert m.tax_basis_total == Decimal("198.00")
        assert m.grand_total == Decimal("235.62")
        assert m.due_amount == Decimal("235.62")

    def test_validate_clean(self, basic_einfach: Document) -> None:
        basic_einfach.validate()

    def test_roundtrip(self, basic_einfach: Document) -> None:
        _roundtrip(basic_einfach)


# ---------------------------------------------------------------------------
# BASIC_zf24_Taxifahrt — two line items, distinct unit codes (H87, KMT)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def basic_taxifahrt() -> Document:
    return _load("BASIC_zf24_Taxifahrt.xml")


class TestBasicTaxifahrt:
    """ZF24 BASIC taxi-fare invoice: two lines with distinct unit codes.

    Highlights: a flat-fare line (unitCode H87 = piece) and a per-kilometer
    line (unitCode KMT = kilometre) — exercises the BT-130 UnitCode
    namespace breadth. Reduced-rate 7% VAT throughout."""

    def test_profile_is_basic(self, basic_taxifahrt: Document) -> None:
        assert basic_taxifahrt.context.guideline.id == Profile.BASIC

    def test_two_line_items(self, basic_taxifahrt: Document) -> None:
        assert len(basic_taxifahrt.trade.items) == 2

    def test_first_line_is_flat_fare(self, basic_taxifahrt: Document) -> None:
        item = basic_taxifahrt.trade.items[0]
        assert item.associated_document.line_id == "1"
        assert item.product.name == "Grundpreis (Pauschale)"
        assert item.delivery.billed_quantity.unit_code == "H87"
        assert item.delivery.billed_quantity.value == Decimal("1")
        assert item.agreement.net_price.charge_amount == Decimal("3.90")
        assert item.settlement.monetary_summation.line_total == Decimal("3.90")

    def test_second_line_is_per_km(self, basic_taxifahrt: Document) -> None:
        item = basic_taxifahrt.trade.items[1]
        assert item.associated_document.line_id == "2"
        # UN/ECE Rec 20 code "KMT" = kilometre. Decimal-precision quantity.
        assert item.delivery.billed_quantity.unit_code == "KMT"
        assert item.delivery.billed_quantity.value == Decimal("6.50")
        assert item.agreement.net_price.charge_amount == Decimal("2.00")
        # 6.50 km x 2.00 EUR/km = 13.00, but the example renders as "13".
        assert item.settlement.monetary_summation.line_total == Decimal("13")

    def test_both_lines_share_reduced_rate(self, basic_taxifahrt: Document) -> None:
        for item in basic_taxifahrt.trade.items:
            tax = item.settlement.applicable_trade_tax
            assert tax.category_code == "S"
            assert tax.rate_applicable_percent == Decimal("7")

    def test_validate_clean(self, basic_taxifahrt: Document) -> None:
        basic_taxifahrt.validate()

    def test_roundtrip(self, basic_taxifahrt: Document) -> None:
        _roundtrip(basic_taxifahrt)


# ---------------------------------------------------------------------------
# BASIC_zf24_Rechnungskorrektur — TypeCode=384 (credit note / correction)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def basic_rechnungskorrektur() -> Document:
    return _load("BASIC_zf24_Rechnungskorrektur.xml")


class TestBasicRechnungskorrektur:
    """ZF24 BASIC credit note / correction invoice (UNTDID 1001 = 384).

    Highlights: ``TypeCode=384`` flags the document as a corrected
    invoice, six BG-1 IncludedNotes give a rich free-text context, two
    line items demonstrate multi-line BG-25 rendering at BASIC."""

    def test_profile_is_basic(self, basic_rechnungskorrektur: Document) -> None:
        assert basic_rechnungskorrektur.context.guideline.id == Profile.BASIC

    def test_type_code_is_correction(self, basic_rechnungskorrektur: Document) -> None:
        # UNTDID 1001 code 384 = "Corrected invoice"; matches our enum.
        assert basic_rechnungskorrektur.header.type_code == TypeCode.T_CorrectedInvoice

    def test_six_included_notes(self, basic_rechnungskorrektur: Document) -> None:
        notes = basic_rechnungskorrektur.header.notes
        assert notes is not None
        assert len(notes) == 6

    def test_two_line_items(self, basic_rechnungskorrektur: Document) -> None:
        assert len(basic_rechnungskorrektur.trade.items) == 2

    def test_each_line_carries_required_basic_fields(
        self, basic_rechnungskorrektur: Document
    ) -> None:
        for idx, item in enumerate(basic_rechnungskorrektur.trade.items, start=1):
            # BR-22 / BR-23 / BR-24 / BR-25 / BR-26 / BR-CO-4 — all
            # required line-level BTs must be populated.
            assert item.associated_document.line_id == str(idx)
            assert item.product.name  # BT-153
            assert item.delivery.billed_quantity.unit_code  # BT-130
            assert item.delivery.billed_quantity.value is not None  # BT-129
            assert item.agreement.net_price.charge_amount is not None  # BT-146
            assert item.settlement.applicable_trade_tax.category_code  # BT-151
            assert item.settlement.monetary_summation.line_total is not None  # BT-131

    def test_validate_clean(self, basic_rechnungskorrektur: Document) -> None:
        basic_rechnungskorrektur.validate()

    def test_roundtrip(self, basic_rechnungskorrektur: Document) -> None:
        _roundtrip(basic_rechnungskorrektur)


# ===========================================================================
# COMFORT (EN 16931) examples
# ===========================================================================
# COMFORT lifts most of the EN 16931 enrichments over BASIC: contact info
# (BG-6 / BG-9), electronic addresses (BT-34 / BT-49), full reference
# documents (BG-24, BT-12-00, BT-13-00, BT-14, BT-15-00), product
# ``Description`` / ``SellerAssignedID`` / ``BuyerAssignedID``, line-level
# ``TaxPointDate`` (BT-7), and the seven non-S VAT categories.


# ---------------------------------------------------------------------------
# EN16931_zf24_Rabatte — document-level allowance and charge (BG-20 / BG-21)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_rabatte() -> Document:
    return _load("EN16931_zf24_Rabatte.xml")


class TestEN16931Rabatte:
    """COMFORT invoice exercising document-level allowances + charges and a
    multi-rate VAT breakdown.

    Highlights: two BG-23 rows (S/7% and S/19%), three BG-20/BG-21 entries
    (two allowances + one charge), per-line tax category, BR-CO-11/-12/-13
    arithmetic over real numbers."""

    def test_profile_is_comfort(self, en16931_rabatte: Document) -> None:
        assert en16931_rabatte.context.guideline.id == Profile.COMFORT

    def test_multi_rate_breakdown(self, en16931_rabatte: Document) -> None:
        taxes = en16931_rabatte.trade.settlement.trade_taxes or []
        # BG-23 x 2: standard rate at 7% and 19% on the same invoice.
        rates = {t.rate_applicable_percent: t.basis_amount for t in taxes}
        assert rates == {
            Decimal("7.00"): Decimal("129.37"),
            Decimal("19.00"): Decimal("64.40"),
        }
        for t in taxes:
            assert t.category_code == "S"

    def test_two_allowances_and_one_charge(self, en16931_rabatte: Document) -> None:
        # BG-20 ChargeIndicator=false → allowance, BG-21 ChargeIndicator=true → charge.
        acs = en16931_rabatte.trade.settlement.allowance_charge or []
        allowances = [a for a in acs if not a.indicator]
        charges = [a for a in acs if a.indicator]
        assert len(allowances) == 2
        assert len(charges) == 1
        # BR-33 / BR-38: reason text required when reason_code is absent.
        for ac in acs:
            assert ac.reason is not None  # BT-97 / BT-104
            assert ac.category_trade_tax is not None  # BT-95-00 / BT-102-00

    def test_validate_clean(self, en16931_rabatte: Document) -> None:
        en16931_rabatte.validate()

    def test_roundtrip(self, en16931_rabatte: Document) -> None:
        _roundtrip(en16931_rabatte)


# ---------------------------------------------------------------------------
# EN16931_zf24_Innergemeinschaftliche — VAT category K (intra-community)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_innergemeinschaftliche() -> Document:
    return _load("EN16931_zf24_Innergemeinschaftliche.xml")


class TestEN16931Innergemeinschaftliche:
    """COMFORT intra-community-supply invoice (UNTDID 5305 = K).

    Highlights: category K triggers ``BR-IC-2`` (Seller VAT + Buyer VAT
    required), ``BR-IC-11`` (actual delivery date BT-72 or invoicing
    period BG-14) and ``BR-IC-12`` (deliver-to country BT-80). The
    example carries Seller VAT in GB (Brexit-aware) and Buyer VAT in
    DE; rate is 0% with an exemption reason."""

    def test_profile_is_comfort(self, en16931_innergemeinschaftliche: Document) -> None:
        assert en16931_innergemeinschaftliche.context.guideline.id == Profile.COMFORT

    def test_seller_and_buyer_vat_ids(
        self, en16931_innergemeinschaftliche: Document
    ) -> None:
        seller = en16931_innergemeinschaftliche.trade.agreement.seller
        buyer = en16931_innergemeinschaftliche.trade.agreement.buyer
        assert any(
            tr.id.scheme_id == "VA" and tr.id.id.startswith("GB")
            for tr in (seller.tax_registrations or [])
        )
        assert any(
            tr.id.scheme_id == "VA" and tr.id.id.startswith("DE")
            for tr in (buyer.tax_registrations or [])
        )

    def test_vat_category_k_zero_rate_with_reason(
        self, en16931_innergemeinschaftliche: Document
    ) -> None:
        taxes = en16931_innergemeinschaftliche.trade.settlement.trade_taxes or []
        assert len(taxes) == 1
        t = taxes[0]
        assert t.category_code == "K"
        assert t.rate_applicable_percent == Decimal("0")
        assert t.exemption_reason is not None  # BT-120

    def test_delivery_evidence_present(
        self, en16931_innergemeinschaftliche: Document
    ) -> None:
        # BR-IC-11: BT-72 (actual delivery date) OR BG-14 (period) required.
        delivery = en16931_innergemeinschaftliche.trade.delivery
        billing_period = en16931_innergemeinschaftliche.trade.settlement.billing_period
        has_date = delivery.event is not None and delivery.event.occurrence is not None
        has_period = billing_period is not None and (
            billing_period.start is not None or billing_period.end is not None
        )
        assert has_date or has_period

    def test_validate_clean(self, en16931_innergemeinschaftliche: Document) -> None:
        en16931_innergemeinschaftliche.validate()

    def test_roundtrip(self, en16931_innergemeinschaftliche: Document) -> None:
        _roundtrip(en16931_innergemeinschaftliche)


# ---------------------------------------------------------------------------
# EN16931_zf24_Auslandslieferung — VAT category E (Exempt from VAT)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_auslandslieferung() -> Document:
    return _load("EN16931_zf24_Auslandslieferung.xml")


class TestEN16931Auslandslieferung:
    """COMFORT VAT-exempt export invoice (UNTDID 5305 = E).

    Highlights: category E (`steuerfreie Ausfuhrlieferung`) at 0%, exemption
    reason text required, Seller carries both BT-32 (FC) and BT-31 (VA)
    so BR-E-2 (Seller VAT or local tax) is satisfied via either path.
    Buyer-side contact info, electronic address, and DefinedTradeContact
    on the Seller are all populated — typical EN 16931 surface."""

    def test_profile_is_comfort(self, en16931_auslandslieferung: Document) -> None:
        assert en16931_auslandslieferung.context.guideline.id == Profile.COMFORT

    def test_seller_contact_and_electronic_address(
        self, en16931_auslandslieferung: Document
    ) -> None:
        seller = en16931_auslandslieferung.trade.agreement.seller
        # BG-6 DefinedTradeContact — COMFORT enrichment.
        assert seller.contact is not None
        assert seller.contact.person_name == "Max Verkäufer"  # BT-41
        assert seller.contact.email is not None
        assert seller.contact.email.address == "mv@firma.de"  # BT-43
        # BT-34 electronic address with ISO 6523 schemeID (0088 = EAN/GS1).
        assert seller.electronic_address is not None
        assert seller.electronic_address.uri_id.scheme_id == "0088"

    def test_vat_category_e_with_exemption_reason(
        self, en16931_auslandslieferung: Document
    ) -> None:
        taxes = en16931_auslandslieferung.trade.settlement.trade_taxes or []
        assert len(taxes) == 1
        t = taxes[0]
        assert t.category_code == "E"
        assert t.rate_applicable_percent == Decimal("0.00")
        # BR-E-10: exemption reason required.
        assert t.exemption_reason
        assert "Ausfuhrlieferung" in t.exemption_reason

    def test_validate_clean(self, en16931_auslandslieferung: Document) -> None:
        en16931_auslandslieferung.validate()

    def test_roundtrip(self, en16931_auslandslieferung: Document) -> None:
        _roundtrip(en16931_auslandslieferung)


# ---------------------------------------------------------------------------
# EN16931_zf24_Kleinunternehmer — small business without VAT id (category E)
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_kleinunternehmer() -> Document:
    return _load("EN16931_zf24_Kleinunternehmer.xml")


class TestEN16931Kleinunternehmer:
    """COMFORT small-business invoice — no VAT identifier on the Seller.

    Highlights: §19 UStG small businesses do not issue VAT — the Seller
    has only BT-32 (local tax id, schemeID="FC") and no BT-31; category
    E still requires *some* Seller tax identifier, satisfied here by
    BT-32. Exemption reason text is mandatory. Demonstrates BR-CO-26
    (Seller identifiable via BT-32) and BR-E-2 satisfied by local id."""

    def test_profile_is_comfort(self, en16931_kleinunternehmer: Document) -> None:
        assert en16931_kleinunternehmer.context.guideline.id == Profile.COMFORT

    def test_seller_has_only_local_tax_id(
        self, en16931_kleinunternehmer: Document
    ) -> None:
        seller = en16931_kleinunternehmer.trade.agreement.seller
        regs = seller.tax_registrations or []
        scheme_ids = {r.id.scheme_id for r in regs}
        # Critical: BT-32 (FC) present, BT-31 (VA) absent.
        assert "FC" in scheme_ids
        assert "VA" not in scheme_ids

    def test_vat_category_e_with_kleinunternehmer_reason(
        self, en16931_kleinunternehmer: Document
    ) -> None:
        taxes = en16931_kleinunternehmer.trade.settlement.trade_taxes or []
        assert len(taxes) == 1
        t = taxes[0]
        assert t.category_code == "E"
        assert t.rate_applicable_percent == Decimal("0.00")
        # §19 UStG exemption-reason text mentions "Kleinunternehmer".
        assert t.exemption_reason
        assert "Kleinu" in t.exemption_reason

    def test_validate_clean(self, en16931_kleinunternehmer: Document) -> None:
        # BR-CO-26 satisfied because BT-32 is present even though BT-31
        # is not; BR-E-2 satisfied by Seller's BT-32 (FC).
        en16931_kleinunternehmer.validate()

    def test_roundtrip(self, en16931_kleinunternehmer: Document) -> None:
        _roundtrip(en16931_kleinunternehmer)


# ---------------------------------------------------------------------------
# EN16931_zf24_ElektronischeAdresse — BT-34 electronic address with schemeID
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_elektronische_adresse() -> Document:
    return _load("EN16931_zf24_ElektronischeAdresse.xml")


class TestEN16931ElektronischeAdresse:
    """COMFORT invoice highlighting BT-34 ``URIUniversalCommunication`` with
    a SchemeID-tagged GLN.

    Highlights: Seller carries electronic address ``1234567890128``
    with ``schemeID="0088"`` (GS1 GLN) — covers BR-62 narrative."""

    def test_profile_is_comfort(self, en16931_elektronische_adresse: Document) -> None:
        assert en16931_elektronische_adresse.context.guideline.id == Profile.COMFORT

    def test_seller_has_gln_electronic_address(
        self, en16931_elektronische_adresse: Document
    ) -> None:
        seller = en16931_elektronische_adresse.trade.agreement.seller
        addr = seller.electronic_address
        assert addr is not None
        # BR-62 narrative: BT-34-1 schemeID is required on URIID. The
        # example uses ISO 6523 "0088" (GS1 GLN).
        assert addr.uri_id.scheme_id == "0088"
        assert addr.uri_id.id == "1234567890128"

    def test_validate_clean(self, en16931_elektronische_adresse: Document) -> None:
        en16931_elektronische_adresse.validate()

    def test_roundtrip(self, en16931_elektronische_adresse: Document) -> None:
        _roundtrip(en16931_elektronische_adresse)


# ---------------------------------------------------------------------------
# EN16931_zf24_OEPNV — exercises the empty-element parse fix
# ---------------------------------------------------------------------------


@pt.fixture(scope="module")
def en16931_oepnv() -> Document:
    return _load("EN16931_zf24_OEPNV.xml")


class TestEN16931OePNV:
    """COMFORT public-transport invoice — exercises empty / self-closing
    XML elements (``<ram:LineTwo/>``, ``<ram:BICID/>``).

    The Factur-X 1.08 specification's informational rule
    PEPPOL-EN16931-R008 warns against empty elements, but real-world
    ZUGFeRD samples ship them anyway. The parser treats an empty
    element as absent for the corresponding optional field."""

    def test_profile_is_comfort(self, en16931_oepnv: Document) -> None:
        assert en16931_oepnv.context.guideline.id == Profile.COMFORT

    def test_empty_line_two_treated_as_absent(self, en16931_oepnv: Document) -> None:
        # The buyer's PostalTradeAddress contains <ram:LineTwo/> with no
        # text. The parser should set line_two to None (not crash) so the
        # round-trip simply drops the empty element on re-render.
        buyer_addr = en16931_oepnv.trade.agreement.buyer.address
        assert buyer_addr is not None
        assert buyer_addr.line_two is None

    def test_validate_clean(self, en16931_oepnv: Document) -> None:
        en16931_oepnv.validate()

    def test_roundtrip(self, en16931_oepnv: Document) -> None:
        _roundtrip(en16931_oepnv)
