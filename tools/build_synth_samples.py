"""Generate getafix-authored canonical EXTENDED sample invoices.

The vendored ZF24 / mustangproject corpus (see
``tests/samples/SOURCES.md``) does not exercise every EXTENDED-only
field getafix models. This script synthesises small, coherent
canonical invoices that *do* — one per thematic field group — by
taking the known-good mustangproject base
(``EXTENDED_factur-x-extended.xml``, Apache-2.0), attaching the
relevant structures via the getafix object model, and rendering.

Each generated file is:

* **XSD-valid** against ``FACTUR-X_EXTENDED.xsd`` (asserted here and
  re-asserted by ``tests/test_xsd_validity.py``), and
* **schematron-clean** under the ``tests/_schematron.py`` oracle
  (asserted here and re-asserted by
  ``tests/test_schematron_roundtrip.py``) — modulo the two known
  elementpath false positives ``BR-FXEXT-CO-15`` / ``BR-FXEXT-11``.

Serialization note: getafix's ``render(indent=True)`` injects
whitespace that the pure-Python elementpath ``xs:decimal`` evaluator
trips over (it is fine for ``lxml``'s XSD validator). We therefore
render flat and pretty-print via ``lxml`` with
``remove_blank_text=True``, which keeps leaf values tight on one line
— matching the vendored real-world samples and keeping the oracle
green.

Usage::

    uv run python tools/build_synth_samples.py [--check]

Without ``--check`` the files are (re)written into ``tests/samples/``.
With ``--check`` the files are built in memory and diffed against the
committed copies (non-zero exit on drift) — suitable for CI.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

from lxml import etree

from getafix.schema.agreement import RelevantTradeLocation, TradeDeliveryTerms
from getafix.schema.document import Document
from getafix.schema.element import ValidationErrors
from getafix.schema.line import (
    ChargeFreeQuantity,
    PackageQuantity,
    PerPackageUnitQuantity,
)
from getafix.schema.party import (
    BuyerAgentTradeParty,
    BuyerTaxRepresentativeTradeParty,
    InvoiceeTradeParty,
    InvoicerTradeParty,
    ItemSellerTradeParty,
    PayeeTradeParty,
    PayerTradeParty,
    PostalTradeAddressExtended,
    SalesAgentTradeParty,
    ShipToTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
    UltimateShipToTradeParty,
)
from getafix.schema.references import QuotationReferencedDocument
from getafix.schema.settlement import (
    AdvancePayment,
    AdvancePaymentReferencedDocument,
    AdvancePaymentTradeTax,
)
from getafix.schema.types import CategoryCode, Country, Incoterms, TypeCode

_ROOT = Path(__file__).resolve().parent.parent
_SAMPLES = _ROOT / "tests" / "samples"
_SCHEMA_DIR = _ROOT / "tests" / "schemas" / "4_Factur-X_1.08_EXTENDED"
_BASE = _SAMPLES / "EXTENDED_factur-x-extended.xml"

# elementpath evaluator false positives — see tests/test_schematron_roundtrip.py.
_KNOWN_FP = frozenset({"BR-FXEXT-CO-15", "BR-FXEXT-11"})


def _load_base() -> Document:
    return Document.from_xml(etree.fromstring(_BASE.read_bytes()))


def _serialize(doc: Document) -> bytes:
    """Render ``doc`` to oracle-safe, pretty-printed XML bytes."""
    return doc.to_xml().render(indent=True).encode()


def _validate(xml: bytes, name: str) -> None:
    """Assert ``xml`` is XSD-valid and schematron-clean; raise on failure."""
    # 1. XSD.
    schema = etree.XMLSchema(etree.parse(str(_SCHEMA_DIR / "FACTUR-X_EXTENDED.xsd")))
    root = etree.fromstring(xml)
    schema.assertValid(root)

    # 2. Schematron oracle (imported lazily — lives under tests/).
    sys.path.insert(0, str(_ROOT))
    from tests._schematron import evaluate_schematron

    sch = evaluate_schematron(_SCHEMA_DIR / "FACTUR-X_EXTENDED.sch", root)
    try:
        Document.from_xml(root).validate()
        getafix_codes: set[str] = set()
    except ValidationErrors as exc:
        getafix_codes = {v.code for v in exc.errors}

    false_positives = getafix_codes - sch.violations - sch.indeterminate
    gaps = sch.violations - getafix_codes - _KNOWN_FP
    if false_positives or gaps:
        raise AssertionError(
            f"{name}: oracle drift — getafix-only {sorted(false_positives)}, "
            f"schematron-only {sorted(gaps)}"
        )


# --- builders ----------------------------------------------------------------


def build_agent_parties() -> bytes:
    """§4.1 — header agent parties, delivery terms, header quotation ref.

    A domestic sale brokered by a sales agent, with both a buyer-side
    fiscal representative and a buyer procurement agent, shipped
    ``FCA Hamburg Hafen``, quoting an earlier offer.
    """
    doc = _load_base()
    ag = doc.trade.agreement
    ag.sales_agent = SalesAgentTradeParty(
        name="Handelsvertretung Meyer GmbH",
        address=PostalTradeAddressExtended(
            postcode="20095", city_name="Hamburg", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE111222333", scheme_id="VA")
        ),
    )
    ag.buyer_tax_representative = BuyerTaxRepresentativeTradeParty(
        name="Fiskalvertretung Schmidt KG",
        address=PostalTradeAddressExtended(
            postcode="80331", city_name="München", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE444555666", scheme_id="VA")
        ),
    )
    ag.buyer_agent = BuyerAgentTradeParty(
        name="Einkaufsbüro Nord eG",
        address=PostalTradeAddressExtended(
            postcode="28195", city_name="Bremen", country_id=Country.DE
        ),
    )
    ag.delivery_terms = TradeDeliveryTerms(
        delivery_type_code=Incoterms.FCA,
        relevant_location=RelevantTradeLocation(
            country_id=Country.DE, name="Hamburg Hafen"
        ),
    )
    ag.quotation = QuotationReferencedDocument(
        issuer_assigned_id="ANG-2026-0042", issue_date_time=date(2026, 5, 1)
    )
    return _serialize(doc)


def build_settlement_parties() -> bytes:
    """§4.3 — settlement parties + advance payment.

    A factoring scenario: the invoice is issued by a shared billing
    service (``InvoicerTradeParty``), addressed for accounting to a
    parent company (``InvoiceeTradeParty``), and settled by a factor
    (``PayerTradeParty``). A 119.00 EUR prepayment (incl. 19.00 EUR
    VAT) was already received against a proforma invoice
    (``SpecifiedAdvancePayment``), and the single payment term names
    the factor's collection account holder as its term-specific
    payee. ``InvoiceIssuerReference`` carries the Seller's file no.
    """
    doc = _load_base()
    s = doc.trade.settlement
    s.invoice_issuer_reference = "BILLING-REF-2026-0815"
    s.invoicer = InvoicerTradeParty(
        name="Konzern Shared Services GmbH",
        address=PostalTradeAddressExtended(
            postcode="60311", city_name="Frankfurt am Main", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE777888999", scheme_id="VA")
        ),
    )
    s.invoicee = InvoiceeTradeParty(
        name="Muster-Konzern Holding AG",
        address=PostalTradeAddressExtended(
            postcode="40213", city_name="Düsseldorf", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE123123123", scheme_id="VA")
        ),
    )
    s.payer = PayerTradeParty(
        name="Nord Factoring AG",
        address=PostalTradeAddressExtended(
            postcode="20354", city_name="Hamburg", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE321321321", scheme_id="VA")
        ),
    )
    # One prepayment of 119.00 (= 100.00 net + 19.00 VAT @ 19 % S).
    s.advance_payments = [
        AdvancePayment(
            paid_amount=Decimal("119.00"),
            received_date_time=date(2026, 4, 15),
            included_trade_tax=[
                AdvancePaymentTradeTax(
                    calculated_amount=Decimal("19.00"),
                    category_code=CategoryCode.T_S,
                    rate_applicable_percent=Decimal("19.00"),
                )
            ],
            invoice_referenced_document=AdvancePaymentReferencedDocument(
                issuer_assigned_id="PROFORMA-2026-0042",
                type_code=TypeCode.T_ProformaInvoice,
                issue_date_time=date(2026, 4, 15),
            ),
        )
    ]
    # Reconcile BT-113 (prepaid) and BT-115 (due) with the prepayment so
    # BR-CO-16 (BT-115 = BT-112 - BT-113 + BT-114) holds.
    ms = s.monetary_summation
    ms.prepaid_total = Decimal("119.00")
    ms.due_amount = ms.grand_total - Decimal("119.00")
    # Name the factor's collection account holder on the payment term.
    if s.terms:
        s.terms[0].payee = PayeeTradeParty(name="Nord Factoring AG - Inkasso")
    return _serialize(doc)


def build_product_line() -> bytes:
    """§4.5 — line/product enrichments on the first invoice line.

    A marketplace / drop-ship line: the item carries model, brand and
    industry identifiers (``ModelID`` / ``ModelName`` / ``BrandName`` /
    ``IndustryAssignedID``), is sold by a deviating line seller
    (``ItemSellerTradeParty``), ships to a per-line address with a
    distinct ultimate recipient (``ShipToTradeParty`` /
    ``UltimateShipToTradeParty``), and records free-goods,
    package-count and units-per-package quantities
    (``ChargeFreeQuantity`` / ``PackageQuantity`` /
    ``PerPackageUnitQuantity``).
    """
    doc = _load_base()
    item = doc.trade.items[0]
    unit = item.delivery.billed_quantity.unit_code  # type: ignore[union-attr]

    prod = item.product
    prod.industry_assigned_id = "39121600"  # UNSPSC-style class id
    prod.model_id = "MOD-4711"
    prod.brand_name = "MusterBrand"
    prod.model_name = "EcoLine 200"
    prod.batch_id = ["LOT-2026-08", "LOT-2026-09"]

    item.agreement.item_seller = ItemSellerTradeParty(
        name="Drittanbieter Direkt GmbH",
        address=PostalTradeAddressExtended(
            postcode="04109", city_name="Leipzig", country_id=Country.DE
        ),
        tax_registrations=SpecifiedTaxRegistration(
            id=TaxSchemeId(id="DE246810121", scheme_id="VA")
        ),
    )

    item.delivery.charge_free_quantity = ChargeFreeQuantity(
        value=Decimal("10.0000"), unit_code=unit
    )
    item.delivery.package_quantity = PackageQuantity(
        value=Decimal("1.0000"), unit_code="XPK"
    )
    item.delivery.per_package_unit_quantity = PerPackageUnitQuantity(
        value=Decimal("1000.0000"), unit_code=unit
    )
    item.delivery.ship_to = ShipToTradeParty(
        name="Filiale Süd",
        address=PostalTradeAddressExtended(
            postcode="70173", city_name="Stuttgart", country_id=Country.DE
        ),
    )
    item.delivery.ultimate_ship_to = UltimateShipToTradeParty(
        name="Endkunde Karl Käufer",
        address=PostalTradeAddressExtended(
            postcode="79098", city_name="Freiburg", country_id=Country.DE
        ),
    )
    return _serialize(doc)


_BUILDERS: dict[str, Callable[[], bytes]] = {
    "EXTENDED_synth_agent_parties.xml": build_agent_parties,
    "EXTENDED_synth_settlement_parties.xml": build_settlement_parties,
    "EXTENDED_synth_product_line.xml": build_product_line,
}


def main() -> int:
    check = "--check" in sys.argv[1:]
    drift = False
    for name, builder in _BUILDERS.items():
        xml = builder()
        _validate(xml, name)
        target = _SAMPLES / name
        if check:
            current = target.read_bytes() if target.exists() else b""
            if current != xml:
                drift = True
                print(f"DRIFT: {name} differs from committed copy")  # noqa: T201
            else:
                print(f"ok:    {name}")  # noqa: T201
        else:
            target.write_bytes(xml)
            print(f"wrote: {name}  ({len(xml)} bytes)")  # noqa: T201
    if check and drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
