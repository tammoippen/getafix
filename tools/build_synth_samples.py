"""Generate carthorse-authored canonical EXTENDED sample invoices.

The vendored ZF24 / mustangproject corpus (see
``tests/samples/SOURCES.md``) does not exercise every EXTENDED-only
field carthorse models. This script synthesises small, coherent
canonical invoices that *do* — one per thematic field group — by
taking the known-good mustangproject base
(``EXTENDED_factur-x-extended.xml``, Apache-2.0), attaching the
relevant structures via the carthorse object model, and rendering.

Each generated file is:

* **XSD-valid** against ``FACTUR-X_EXTENDED.xsd`` (asserted here and
  re-asserted by ``tests/test_xsd_validity.py``), and
* **schematron-clean** under the ``tests/_schematron.py`` oracle
  (asserted here and re-asserted by
  ``tests/test_schematron_roundtrip.py``) — modulo the two known
  elementpath false positives ``BR-FXEXT-CO-15`` / ``BR-FXEXT-11``.

Serialization note: carthorse's ``render(indent=True)`` injects
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

from carthorse.schema import Document
from carthorse.schema.agreement import RelevantTradeLocation, TradeDeliveryTerms
from carthorse.schema.element import ValidationErrors
from carthorse.schema.party import (
    BuyerAgentTradeParty,
    BuyerTaxRepresentativeTradeParty,
    PostalTradeAddressExtended,
    SalesAgentTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
)
from carthorse.schema.references import QuotationReferencedDocument
from carthorse.schema.types import Country

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
    flat = doc.to_xml().render(indent=False).encode()
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.fromstring(flat, parser)
    return etree.tostring(
        tree, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )


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
        carthorse_codes: set[str] = set()
    except ValidationErrors as exc:
        carthorse_codes = {v.code for v in exc.errors}

    false_positives = carthorse_codes - sch.violations - sch.indeterminate
    gaps = sch.violations - carthorse_codes - _KNOWN_FP
    if false_positives or gaps:
        raise AssertionError(
            f"{name}: oracle drift — carthorse-only {sorted(false_positives)}, "
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
        delivery_type_code="FCA",
        relevant_location=RelevantTradeLocation(
            country_id=Country.DE, name="Hamburg Hafen"
        ),
    )
    ag.quotation = QuotationReferencedDocument(
        issuer_assigned_id="ANG-2026-0042", issue_date_time=date(2026, 5, 1)
    )
    return _serialize(doc)


_BUILDERS: dict[str, Callable[[], bytes]] = {
    "EXTENDED_synth_agent_parties.xml": build_agent_parties
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


# ``Decimal`` is imported for builders added in later commits (advance
# payments, line monetary extras); keep the import stable.
_ = Decimal

if __name__ == "__main__":
    raise SystemExit(main())
