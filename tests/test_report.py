"""Tests for :mod:`getafix.report` — rich rendering of a parsed Document.

Drives the renderer with a doc built from :func:`tests._fixtures.make_vat_doc`
plus a couple of stripped-down cases. The Console is created with
``record=True`` so we can grep the rendered text rather than asserting
on terminal-control bytes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rich.console import Console

from getafix.report import render_invoice, render_validation_errors
from getafix.schema import (
    Context,
    Document,
    GuidelineDocument,
    Header,
    Profile,
    TypeCode,
)
from getafix.schema.accounting import MonetarySummation
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.element import ValidationError
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
    PayeePartyCreditorFinancialAccount,
    PaymentMeans,
    TradeSettlement,
)
from getafix.schema.trade import Trade
from getafix.schema.types import Country, Currency, UNTDID4461PaymentMeansCode
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
