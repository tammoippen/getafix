"""Tests for :mod:`getafix.report` — rich rendering of a parsed Document.

Drives the renderer with a doc built from :func:`tests._fixtures.make_vat_doc`
plus a couple of stripped-down cases. The Console is created with
``record=True`` so we can grep the rendered text rather than asserting
on terminal-control bytes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from rich.console import Console

from getafix.report import render_invoice, render_validation_errors
from getafix.report.line import net_price_cell
from getafix.report.types import format_bytes
from getafix.schema.accounting import LineTradeAllowanceCharge, MonetarySummation
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.document import Context, Document, GuidelineDocument, Header
from getafix.schema.element import ValidationError
from getafix.schema.line import (
    LineAdditionalReferencedDocument,
    LineBuyerOrderReferencedDocument,
    LineIncludedNote,
)
from getafix.schema.party import (
    URIID,
    BuyerTradeParty,
    EmailURI,
    GlobalID,
    ISO6523SchemeId,
    LegalOrganization,
    PhoneNumber,
    PostalTradeAddressExtended,
    SellerTradeParty,
    TradeContact,
    URIUniversalCommunication,
)
from getafix.schema.settlement import (
    BillingSpecifiedPeriod,
    PayeePartyCreditorFinancialAccount,
    PaymentMeans,
    ReceivableAccountingAccount,
    TradeSettlement,
)
from getafix.schema.trade import Trade
from getafix.schema.types import (
    Country,
    Currency,
    Profile,
    TypeCode,
    UNTDID2475TaxPointDateCode,
    UNTDID4461PaymentMeansCode,
)
from tests._fixtures import make_vat_doc


def _record() -> Console:
    """Console that captures everything for ``export_text`` assertions."""
    return Console(record=True, width=140, force_terminal=False, color_system=None)


def _minimum_doc() -> Document:
    """Bare MINIMUM document — no lines, no VAT breakdown, no payment."""
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
        header=Header(
            id="MIN-1",
            type_code=TypeCode.T_CommercialInvoice,
            issue_date=date(2025, 1, 2),
        ),
        trade=Trade(
            agreement=TradeAgreement(
                seller=SellerTradeParty(
                    name="Acme",
                    address=PostalTradeAddressExtended(country_id=Country.DE),
                ),
                buyer=BuyerTradeParty(
                    name="Beta",
                    address=PostalTradeAddressExtended(country_id=Country.DE),
                ),
            ),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code=Currency.EUR,
                monetary_summation=MonetarySummation(
                    tax_basis_total=Decimal("100"),
                    grand_total=Decimal("119"),
                    due_amount=Decimal("119"),
                ),
            ),
        ),
    )


def test_render_invoice_minimum_doc_emits_header_and_totals():
    console = _record()
    render_invoice(_minimum_doc(), console=console)
    text = console.export_text()
    # Header block
    assert "MIN-1" in text
    assert "2025-01-02" in text
    assert "MINIMUM" in text
    assert "CommercialInvoice" in text
    # Parties
    assert "Acme" in text
    assert "Beta" in text
    # Totals — the panel always renders the amount-due line.
    assert "Amount due" in text
    assert "119" in text
    assert "EUR" in text
    # No items / VAT / payment sections.
    assert "Line items" not in text
    assert "VAT breakdown" not in text
    assert "Payment" not in text


def test_render_invoice_full_doc_emits_lines_taxes_and_payment():
    doc = make_vat_doc()
    # Splice in contact + electronic address + payment means to exercise the
    # COMFORT contact branch and the payment panel.
    doc.trade.agreement.seller.contact = TradeContact(
        person_name="Jane Doe",
        email=EmailURI(address="jane@acme.test"),
        telephone=PhoneNumber(number="+49-30-12345"),
    )
    doc.trade.agreement.buyer.electronic_address = URIUniversalCommunication(
        uri_id=URIID(id="buyer@beta.test", scheme_id="EM")
    )
    doc.trade.settlement.payment_means = [
        PaymentMeans(
            type_code=UNTDID4461PaymentMeansCode.CODE_58,
            payee=PayeePartyCreditorFinancialAccount(iban_id="DE89370400440532013000"),
        )
    ]
    doc.trade.settlement.payment_reference = "INV-REF-1"
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    # Lines table
    assert "Line items" in text
    assert "W" in text  # product name from make_vat_doc
    assert "C62" in text  # unit code
    # VAT breakdown
    assert "VAT breakdown" in text
    # Seller VAT id from make_vat_doc defaults
    assert "VAT ID" in text
    assert "DE123456789" in text
    # Contact info
    assert "Jane Doe" in text
    assert "jane@acme.test" in text
    assert "+49-30-12345" in text
    # Electronic address with scheme hint
    assert "buyer@beta.test" in text
    assert "EM" in text
    # Payment panel
    assert "Payment" in text
    assert "58" in text
    assert "DE89370400440532013000" in text
    assert "INV-REF-1" in text


def test_render_validation_errors_empty_prints_success():
    console = _record()
    render_validation_errors([], console=console)
    assert "No validation errors" in console.export_text()


def test_render_validation_errors_prints_codes_and_messages():
    console = _record()
    render_validation_errors(
        [
            ValidationError("BR-16", "at least one line required"),
            ValidationError("BR-CO-15", "BT-112 mismatch"),
        ],
        console=console,
    )
    text = console.export_text()
    assert "Validation errors (2)" in text
    assert "BR-16" in text
    assert "at least one line required" in text
    assert "BR-CO-15" in text
    assert "BT-112 mismatch" in text


def test_render_invoice_extended_logistics_panel_shows_for_extended_doc() -> None:
    """The Logistics-service-charges panel (BG-X-42) appears when
    ``settlement.logistics_service_charges`` is populated."""
    from pathlib import Path

    from lxml import etree

    doc = Document.from_xml(
        etree.fromstring(
            Path("tests/samples/EXTENDED_factur-x-extended.xml").read_bytes()
        )
    )
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    assert "Logistics service charges (BG-X-42)" in text
    assert "Transportkosten" in text  # description of the sample charge
    assert "15.00" in text  # applied_amount
    assert "19.00% S" in text  # VAT cell


def test_render_invoice_indents_sub_invoice_line_children() -> None:
    """EXTENDED GROUP / DETAIL sub-invoice-line trees render with
    children indented two spaces under their parent, and the BT-X-8
    subtype is appended as a dim tag next to the line id."""
    from pathlib import Path

    from lxml import etree

    doc = Document.from_xml(
        etree.fromstring(
            Path(
                "tests/samples/EXTENDED_zf24_SubInvoiceLines_Hardware.xml"
            ).read_bytes()
        )
    )
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    # Subtype tags appear next to line ids.
    assert "(DETAIL)" in text
    assert "(GROUP)" in text
    # Children render with indentation (the regex catches "  0101"
    # — two leading spaces — but not "  01 " which would be the
    # parent at depth 0).
    assert "  0101" in text
    assert "  0102" in text
    # GROUP parent line is at depth 0 (no leading indent before "01").
    assert "01 (GROUP)" in text


def test_render_invoice_advance_payments_panel_shows_for_extended_doc() -> None:
    """The Advance-payments panel (BG-X-45) appears when
    ``settlement.advance_payments`` is populated. The
    ``EXTENDED_synth_settlement_parties.xml`` fixture carries a
    single 119.00 EUR prepayment (incl. 19.00 EUR VAT @ 19 % S)
    against the proforma invoice ``PROFORMA-2026-0042``."""
    from pathlib import Path

    from lxml import etree

    doc = Document.from_xml(
        etree.fromstring(
            Path("tests/samples/EXTENDED_synth_settlement_parties.xml").read_bytes()
        )
    )
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    assert "Advance payments (BG-X-45)" in text
    assert "2026-04-15" in text  # received_date_time
    assert "119.00" in text  # paid_amount
    assert "19.00 @ 19.00% S" in text  # IncludedTradeTax cell
    assert "PROFORMA-2026-0042" in text  # referenced prepayment invoice


def test_render_invoice_no_advance_payments_panel_for_basic_doc() -> None:
    """BASIC / COMFORT documents print no Advance-payments panel —
    the helper short-circuits on the empty / None list."""
    doc = make_vat_doc()
    console = _record()
    render_invoice(doc, console=console)
    assert "Advance payments" not in console.export_text()


def _innergem_doc() -> Document:
    """COMFORT sample carrying a Seller/Buyer id, a tax representative
    (BG-11) and a Payee with a global id (BT-60-0)."""
    from pathlib import Path

    from lxml import etree

    return Document.from_xml(
        etree.fromstring(
            Path("tests/samples/EN16931_zf24_Innergemeinschaftliche.xml").read_bytes()
        )
    )


def test_render_invoice_renders_seller_buyer_party_ids() -> None:
    """The Seller (BT-29) and Buyer (BT-46) identifiers render as their
    own rows with the BT id in the label."""
    console = _record()
    render_invoice(_innergem_doc(), console=console)
    text = console.export_text()
    assert "ID (BT-29):" in text
    assert "12345676" in text  # Seller id
    assert "ID (BT-46):" in text
    assert "75969813" in text  # Buyer id


def test_render_invoice_renders_tax_representative_panel() -> None:
    """The Seller tax representative (BG-11) renders as its own panel with
    name (BT-62), address (BG-12) and VAT id (BT-63)."""
    console = _record()
    render_invoice(_innergem_doc(), console=console)
    text = console.export_text()
    assert "Tax representative" in text
    assert "(BG-11)" in text
    assert "Friedrichstraße 165" in text  # tax-rep address line
    assert "DE987654321" in text  # tax-rep VAT id (BT-63)


def test_render_invoice_no_tax_representative_panel_when_absent() -> None:
    """Documents without a tax representative print no such panel."""
    console = _record()
    render_invoice(make_vat_doc(), console=console)
    assert "Tax representative" not in console.export_text()


def test_render_invoice_renders_payee_global_id() -> None:
    """The Payee global id (BT-60-0) renders with its scheme hint."""
    console = _record()
    render_invoice(_innergem_doc(), console=console)
    text = console.export_text()
    assert "Payee id (BT-60-0):" in text
    assert "432156789" in text
    assert "0060" in text  # ISO 6523 scheme of the payee global id


def test_render_invoice_renders_seller_legal_org_and_contact_detail() -> None:
    """Global id (BT-29-0), legal registration id (BT-30), additional
    legal info (BT-33) and the contact department (BT-41-0) all render."""
    doc = make_vat_doc()
    seller = doc.trade.agreement.seller
    seller.global_ids = [GlobalID(id="4012345000009", scheme_id="0088")]
    seller.legal_organization = LegalOrganization(
        id=ISO6523SchemeId(id="HRB12345", scheme_id="0198"), trade_name="Acme Trading"
    )
    seller.description = "Geschäftsführer: Max Muster"
    seller.contact = TradeContact(person_name="Jane Doe", department_name="Billing")
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    assert "Global ID (BT-29-0):" in text
    assert "4012345000009" in text
    assert "0088" in text  # scheme hint on the global id
    assert "Legal reg. (BT-30):" in text
    assert "HRB12345" in text
    assert "Trading as:" in text
    assert "Acme Trading" in text
    assert "Legal info (BT-33):" in text
    assert "Geschäftsführer: Max Muster" in text
    assert "Department (BT-41-0):" in text
    assert "Billing" in text


def _doc_from_sample(name: str) -> Document:
    from pathlib import Path

    from lxml import etree

    return Document.from_xml(
        etree.fromstring(Path(f"tests/samples/{name}").read_bytes())
    )


def test_render_invoice_orders_sub_lines_under_parent() -> None:
    """EXTENDED sub-invoice-lines render in tree order: each GROUP parent
    directly above its DETAIL children, even though the sample lists the
    children first in document order."""
    console = _record()
    render_invoice(
        _doc_from_sample("EXTENDED_zf24_SubInvoiceLines_Hardware.xml"), console=console
    )
    text = console.export_text()
    # Parent "01" appears before its children "0101"/"0102", which appear
    # before the next group "02".
    assert (
        text.index("01 (GROUP)")
        < text.index("0101")
        < text.index("0102")
        < text.index("02 (GROUP)")
    )


def test_render_invoice_renders_item_standard_id_and_gross_price() -> None:
    """Item standard id (BT-157) and the gross-price derivation (BT-148)
    render in the line — driven off a COMFORT sample with gross prices."""
    console = _record()
    render_invoice(_doc_from_sample("EN16931_Einfach.cii.xml"), console=console)
    text = console.export_text()
    assert "Std#: 4012345001235" in text  # BT-157 global id
    assert "gross 9.9000" in text  # BT-148 gross price under the net price


def test_render_invoice_renders_product_classification() -> None:
    """Item classification (BG-33) renders as ``Class: <code> (<scheme>)``."""
    console = _record()
    render_invoice(_doc_from_sample("EXTENDED_zf24_Herkunftsland.xml"), console=console)
    text = console.export_text()
    assert "Class:" in text
    assert "(HS)" in text  # ClassCode listID


def test_render_invoice_renders_line_detail_followups() -> None:
    """Line note (BT-127), invoicing period (BG-26), line allowance
    (BG-27) and line references (BT-132 / BT-128 / BT-133) render as dim
    follow-up lines in the Item cell."""
    doc = make_vat_doc()
    item = doc.trade.items[0]
    item.associated_document.note = LineIncludedNote(
        content="Fragile — handle with care"
    )
    item.settlement.billing_period = BillingSpecifiedPeriod(
        start=date(2025, 1, 1), end=date(2025, 1, 31)
    )
    item.settlement.allowance_charge = [
        LineTradeAllowanceCharge(
            indicator=False, actual_amount=Decimal("2.00"), reason="Mengenrabatt"
        )
    ]
    item.agreement.buyer_order_ref = LineBuyerOrderReferencedDocument(line_id="5")
    item.settlement.additional_references = [
        LineAdditionalReferencedDocument(issuer_assigned_id="OBJ-1")
    ]
    item.settlement.accounting_account = ReceivableAccountingAccount(id="ACCT-9")
    console = _record()
    render_invoice(doc, console=console)
    text = console.export_text()
    assert "Note: Fragile — handle with care" in text
    assert "Period: 2025-01-01 → 2025-01-31" in text
    assert "Allowance: Mengenrabatt 2.00" in text
    assert "Order line: 5" in text  # BT-132
    assert "Obj id: OBJ-1" in text  # BT-128
    assert "Acct: ACCT-9" in text  # BT-133


def test_net_price_cell_renders_multiple_price_allowances() -> None:
    """Both item price discounts (BT-147) on a gross price render under the
    net price, each with its reason (EXTENDED). Tested on the cell builder
    directly to avoid the line-items table wrapping the long derivation."""
    doc = _doc_from_sample("EXTENDED_zf24_Warenrechnung.xml")
    # Line 2 carries two price allowances: Artikelrabatt 1 / 2.
    cell = net_price_cell(doc.trade.items[1].agreement)
    assert "gross 1.5000" in cell
    assert "-0.0300 (Artikelrabatt 1)" in cell
    assert "-0.0200 (Artikelrabatt 2)" in cell


def test_render_invoice_renders_business_process_accounting_and_attachment() -> None:
    """Business process (BT-23), Buyer accounting reference (BT-19) and the
    BG-24 supporting-documents table (with a BT-125 attachment) all render."""
    console = _record()
    render_invoice(_doc_from_sample("EN16931_zf24_Elektron.xml"), console=console)
    text = console.export_text()
    assert "Process (BT-23):" in text
    assert "Baurechnung" in text  # BT-23 value
    assert "Booking ref (BT-19):" in text
    assert "420" in text  # BT-19 value
    assert "Supporting documents (BG-24)" in text
    assert "13130162" in text  # BT-122 reference id
    assert "Aufmass" in text  # BT-123 description
    assert "Aufmass.pdf (application/pdf, 35.6 KiB)" in text  # BT-125 attachment


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KiB"),
        (36480, "35.6 KiB"),  # the Aufmass.pdf attachment
        (1024 * 1024, "1.0 MiB"),
        (5 * 1024 * 1024 + 512 * 1024, "5.5 MiB"),
        (1024**3, "1.0 GiB"),
        (1024**4, "1.0 TiB"),
        (3 * 1024**5, "3.0 PiB"),
    ],
)
def test_format_bytes_picks_appropriate_unit(size: int, expected: str) -> None:
    """Byte counts render with a 1024-based IEC unit suffix."""
    assert format_bytes(size) == expected


def test_render_invoice_renders_payment_means_info() -> None:
    """Payment-means free text (BT-82) renders in the Payment panel."""
    console = _record()
    render_invoice(_doc_from_sample("EN16931_factur-x.xml"), console=console)
    text = console.export_text()
    assert "Means info (BT-82):" in text
    assert "Bank transfer" in text


def test_render_invoice_renders_vat_accounting_currency() -> None:
    """VAT accounting currency (BT-6) renders when it differs from BT-5."""
    console = _record()
    render_invoice(_doc_from_sample("EXTENDED_fremdwaehrung.xml"), console=console)
    text = console.export_text()
    assert "VAT acct currency (BT-6):" in text
    assert "EUR" in text  # BT-6 (the invoice currency BT-5 is GBP)


def test_render_invoice_tax_point_column_appears_only_when_set() -> None:
    """The BT-7 / BT-8 tax-point column is added to the VAT breakdown only
    when a row carries it, showing the date (BT-7) or the code (BT-8)."""
    # make_vat_doc defaults carry a BT-8 due-date code, so the column shows.
    coded = make_vat_doc()
    assert coded.trade.settlement.trade_taxes is not None
    coded.trade.settlement.trade_taxes[
        0
    ].due_date_code = UNTDID2475TaxPointDateCode.CODE_5
    console = _record()
    render_invoice(coded, console=console)
    text = console.export_text()
    assert "Tax point (BT-7/8)" in text
    assert "code 5" in text  # BT-8

    # With neither BT-7 nor BT-8 set, the column is dropped entirely.
    plain = make_vat_doc()
    assert plain.trade.settlement.trade_taxes is not None
    plain.trade.settlement.trade_taxes[0].due_date_code = None
    console = _record()
    render_invoice(plain, console=console)
    assert "Tax point (BT-7/8)" not in console.export_text()

    # A tax point date (BT-7) takes priority and renders in the column.
    dated = make_vat_doc()
    assert dated.trade.settlement.trade_taxes is not None
    dated.trade.settlement.trade_taxes[0].due_date_code = None
    dated.trade.settlement.trade_taxes[0].tax_point_date = date(2025, 3, 15)
    console = _record()
    render_invoice(dated, console=console)
    text = console.export_text()
    assert "Tax point (BT-7/8)" in text
    assert "2025-03-15" in text  # BT-7


def test_render_invoice_renders_ship_to_address_and_id() -> None:
    """The Delivery panel shows the ship-to location id (BT-71) and the
    full ship-to address (BG-15), not just the name."""
    console = _record()
    render_invoice(
        _doc_from_sample("EN16931_zf24_Innergemeinschaftliche.xml"), console=console
    )
    text = console.export_text()
    assert "Ship to (BG-13):" in text
    assert "Ship-to id (BT-71):" in text
    assert "75969815" in text  # BT-71 location id
    assert "Ship-to addr (BG-15):" in text
    assert "Eichenpromenade 37" in text  # ship-to address line
    assert "12347 Metallstadt" in text  # ship-to postcode + city


def test_render_invoice_renders_ship_to_global_id() -> None:
    """The ship-to global location id (BT-71-0) renders with its scheme."""
    console = _record()
    render_invoice(_doc_from_sample("EXTENDED_zf24_Herkunftsland.xml"), console=console)
    text = console.export_text()
    assert "Ship-to id (BT-71-0):" in text
    assert "GLN400000000S" in text
    assert "0088" in text  # scheme of the ship-to global id


# Every COMFORT-or-lower sample (MINIMUM / BASIC_WL / BASIC / EN16931),
# discovered at collection time, as a smoke-test corpus.
_COMFORT_SAMPLES = sorted(
    p.name
    for p in Path("tests/samples").glob("*.xml")
    if p.name.startswith(("MINIMUM", "BASIC", "EN16931"))
)


@pytest.mark.parametrize("sample", _COMFORT_SAMPLES)
def test_render_invoice_smoke_renders_every_comfort_sample(sample: str) -> None:
    """Every shipped COMFORT-or-lower invoice renders without raising and
    produces non-empty output — a broad guard that no populated field
    trips the renderer."""
    console = _record()
    render_invoice(_doc_from_sample(sample), console=console)
    assert console.export_text().strip()
