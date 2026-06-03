# carthorse

Build, parse and validate
[**ZUGFeRD 2.x / Factur-X**](https://www.ferd-net.de/standards/zugferd)
Cross-Industry-Invoice (CII) XML in Python. The dataclass model is
traceable to the EN 16931 business terms (`BT-…`) and groups
(`BG-…`), so every field on every class maps back to a line in the
spec.

> **Status: pre-1.0.** Solid for the fields that are modelled across
> MINIMUM / BASIC_WL / BASIC / COMFORT (EN 16931); selective EXTENDED
> coverage. PDF/A-3 conformance for the host PDF is **out of scope** —
> `carthorse` attaches the embedded `factur-x.xml` but does not
> upgrade the surrounding PDF to PDF/A-3.

## License and attribution

`carthorse` is distributed under the **Apache License 2.0** — see
[`LICENSE`](LICENSE).

This project is an application of the **ZUGFeRD / Factur-X**
publication issued by the *Forum elektronische Rechnung Deutschland*
(FeRD) at AWV e.V. The format incorporates **EN 16931**, reproduced
by FeRD with the permission of **CEN** and **DIN**. *ZUGFeRD* and
*Factur-X* are trademarks of FeRD / AWV e.V., used here only to
identify the standard this library implements.

The vendored test fixtures under
[`tests/schemas/`](tests/schemas/) and
[`tests/samples/`](tests/samples/) come from third parties and are
redistributed under the Apache License 2.0:

- **FeRD / AWV e.V.** — XML schemas, Schematron, and the `*_zf24_*`
  example invoices from the official ZUGFeRD 2.4 / Factur-X 1.08
  distribution.
- **[ZUGFeRD/mustangproject](https://github.com/ZUGFeRD/mustangproject)**
  — additional reference CII invoices from the Java implementation's
  test resources.
- **[ZUGFeRD/corpus](https://github.com/ZUGFeRD/corpus)** —
  community-curated `XML-Rechnung/CII/` reference invoices.

Original copyright remains with the respective upstream holders;
per-file provenance is tracked in
[`tests/samples/SOURCES.md`](tests/samples/SOURCES.md).

> **Important:** It is the user's responsibility to ensure that
> invoices generated or parsed with `carthorse` meet all legal and
> regulatory requirements applicable in their jurisdiction.
> `carthorse` does not guarantee compliance with any specific
> national or sector-specific e-invoicing mandate.

## Installation

Requires **Python 3.12+**. We recommend
[`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
pip install carthorse
```

The base install lets you build / serialise / validate documents with
the Python stdlib XML parser. The optional extras unlock more:

| Extra            | Pulls in                  | Enables |
|------------------|---------------------------|---------|
| `carthorse[lxml]` | `lxml`                    | Round-tripping XML produced by other tools (the stdlib parser is fine for most documents; `lxml` is faster and more tolerant of large / namespaced inputs). |
| `carthorse[pdf]`  | `pypdf`                   | Embedding / extracting `factur-x.xml` in a PDF (`carthorse.pdf.attach_xml` and `extract_xml`). |
| `carthorse[cli]`  | `lxml`, `rich`, `pypdf`   | The `carthorse` console script — pretty-print an invoice and run the BR-* validators against it. |

Install several at once:

```bash
pip install 'carthorse[lxml,pdf]'
```

## Quickstart — build an invoice

```python
from datetime import date
from decimal import Decimal

from carthorse.schema import (
    Context, Document, GuidelineDocument, Header, Profile, TypeCode,
)
from carthorse.schema.accounting import MonetarySummation, TaxTotal
from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.party import (
    BuyerTradeParty, PostalTradeAddressExtended, SellerTradeParty,
    SpecifiedTaxRegistration, TaxSchemeId,
)
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.trade import Trade
from carthorse.schema.types import Country, Currency

doc = Document(
    context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
    header=Header(
        id="INV-2025-0001",
        type_code=TypeCode.T_CommercialInvoice,  # 380
        issue_date=date(2025, 11, 16),
    ),
    trade=Trade(
        agreement=TradeAgreement(
            seller=SellerTradeParty(
                name="Acme GmbH",
                address=PostalTradeAddressExtended(country_id=Country.DE),
                tax_registrations=[
                    SpecifiedTaxRegistration(
                        id=TaxSchemeId(id="DE123456789", scheme_id="VA"),
                    ),
                ],
            ),
            buyer=BuyerTradeParty(
                name="Beta AG",
                address=PostalTradeAddressExtended(country_id=Country.DE),
            ),
        ),
        delivery=TradeDelivery(),
        settlement=TradeSettlement(
            currency_code=Currency.EUR,
            monetary_summation=MonetarySummation(
                tax_basis_total=Decimal("100.00"),
                tax_total=[TaxTotal(amount=Decimal("19.00"), currency_id=Currency.EUR)],
                grand_total=Decimal("119.00"),
                due_amount=Decimal("119.00"),
                currency="EUR",
            ),
        ),
    ),
)

xml = doc.to_xml().render(indent=True)   # str — ready to write to factur-x.xml
doc.validate()                           # raises ValidationErrors on BR-* failures
```

`doc.to_xml()` picks the right profile from `Context.guideline.id`.
Setting a field that requires a higher profile than the document
raises `ProfileMismatch` at render time.

## Quickstart — parse an invoice

From XML bytes or a file:

```python
import xml.etree.ElementTree as ET
from carthorse.schema import Document

tree = ET.parse("factur-x.xml")
doc = Document.from_xml(tree.getroot())

print(doc.header.id, doc.header.type_code, doc.header.issue_date)
print(doc.trade.settlement.monetary_summation.grand_total)

doc.validate()   # raises ValidationErrors with every violation
```

`lxml.etree` works the same way — pass the root element to
`Document.from_xml`.

From a Factur-X / ZUGFeRD PDF (`carthorse[pdf]` extra):

```python
import xml.etree.ElementTree as ET
from carthorse.pdf import extract_xml
from carthorse.schema import Document

payload = extract_xml(Path("invoice.pdf"))   # bytes or None
if payload is None:
    raise SystemExit("No factur-x.xml found in the PDF")
doc = Document.from_xml(ET.fromstring(payload))
```

To embed an XML into an existing PDF:

```python
from pathlib import Path
from carthorse.pdf import attach_xml

attach_xml(Path("invoice.pdf"), Path("factur-x.xml"))   # in-place
attach_xml(Path("invoice.pdf"), Path("factur-x.xml"),
           pdf_out=Path("invoice-with-xml.pdf"))
```

`attach_xml` produces a valid PDF with a generic embedded file; it
does **not** upgrade the host PDF to PDF/A-3, which is the formal
Factur-X compliance requirement. Pair with a dedicated PDF/A-3
converter for full conformance.

## Validation

```python
from carthorse.schema.element import ValidationErrors

try:
    doc.validate()
except ValidationErrors as exc:
    for err in exc.errors:
        print(f"{err.code}: {err.message}")
```

`Document.validate()` walks the document tree once and collects every
business-rule violation, raising a single `ValidationErrors`
aggregate. Each `ValidationError` carries the rule's code (e.g.
`BR-CO-15`) and a human-readable message.

The catalogue of enforced rules lives in
[`docs/VALIDATION.md`](docs/VALIDATION.md).

## Command-line tool

The `carthorse[cli]` extra ships a console script that pretty-prints
an invoice and runs the validators:

```bash
$ carthorse path/to/factur-x.xml
$ carthorse path/to/invoice.pdf            # reads the embedded XML
$ carthorse --no-validate path/to/file.xml # skip BR-* checks
```

Exit codes:

- `0` — parsed cleanly and passed every validator.
- `1` — parsed but at least one validation rule fired (or the
  document could not be parsed as a CII invoice, or no Factur-X XML
  was found in the supplied PDF).
- `2` — usage / IO / missing dependency error.

## Profiles

ZUGFeRD / Factur-X defines five conformance profiles, ordered by
completeness:

| Profile     | URN                                                                 | Carries line items |
|-------------|----------------------------------------------------------------------|--------------------|
| `MINIMUM`   | `urn:factur-x.eu:1p0:minimum`                                        | ✗ (header totals only) |
| `BASIC_WL`  | `urn:factur-x.eu:1p0:basicwl`                                        | ✗ (basic, without lines) |
| `BASIC`     | `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic`        | ✓ |
| `COMFORT`   | `urn:cen.eu:en16931:2017`  *(a.k.a. EN 16931)*                       | ✓ |
| `EXTENDED`  | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended`    | ✓ + sub-lines |

The profile is set on the document via
`Context(guideline=GuidelineDocument(id=Profile.X))`. Carthorse
enforces it at render time: setting a field that only exists at a
higher profile raises `ProfileMismatch`.

## Status and known gaps

Carthorse models every field that the MINIMUM, BASIC_WL, BASIC and
EN 16931 (COMFORT) profiles permit. EXTENDED coverage is broad —
sub-line hierarchy (`BT-X-7` / `BT-X-8` / `BT-X-304`), bundle
composition (`BG-X-1` `IncludedReferencedProduct`), per-instance
batch / serial details (`BG-X-84`), logistics service charges
(`BG-X-42`), advance payments (`BG-X-45` with `BG-X-46` /
`BG-X-85`), the EXTENDED-only deviating parties (sales agent,
buyer agent, buyer / item-level seller / tax representative,
invoicer, invoicee, payer, product end-user), the
penalty / discount payment-term schedules (`BG-X-43` / `BG-X-44`),
tax-currency exchange (`BG-X-41`), delivery terms (`BG-X-22`),
quotation / ultimate-customer-order references, and the
`PEPPOL`-flavoured rule overlay (`BR-FXEXT-*`) are all modelled.

The remaining EXTENDED gaps — mostly leaf attributes the carthorse
samples don't exercise — are enumerated in
[`docs/STRUCTURES.md §6`](docs/STRUCTURES.md). The headline ones:

* Line-level twins of header references on `LineTradeAgreement` /
  `LineTradeDelivery` / `LineTradeSettlement`: per-line
  delivery-terms / seller-order / contract / additional /
  ultimate-customer-order references; line-level
  ActualDeliverySupplyChainEvent and despatch / receiving /
  delivery-note references; line-level preceding-invoice reference.
* Leaf attributes on shared types: `TradeParty.role_code` /
  `description`, `TradeContact.type_code`, `ProductCharacteristic.type_code`
  / `value_measure`, `TradeProduct.id`, `TradeAllowanceCharge.sequence_numeric`
  / `basis_quantity`, `MonetarySummation.total_allowance_charge_amount`,
  `TradePrice.included_trade_tax`.

These are mechanical add-ons against the EXTENDED XSD; carthorse
will accept a PR (or wait for a sample that needs them).

- [`docs/STRUCTURES.md`](docs/STRUCTURES.md) — module → BG/BT field
  map with profile applicability and the EXTENDED coverage diff.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — every BR-* rule with
  enforcement status.

PDF/A-3 packaging is out of scope; use `factur-x` (PyPI),
[Mustangproject](https://github.com/ZUGFeRD/mustangproject) or a
dedicated converter for full Factur-X PDF conformance.

## Contributing

See [`AGENTS.md`](AGENTS.md) for the developer guide — module layout,
how the dataclass model works, how to add a new BT field or BR
validator, and the test / lint workflow.

## References

Specification and validators:

- [FeRD net — ZUGFeRD overview](https://www.ferd-net.de/standards/zugferd)
- [Rechnung Fans — XRechnung / EN 16931 portal](https://portal3.gefeg.com/invoice/tthome/index/617afdc4-623f-44e0-a05b-5b878840e508)
- [e-Rechnung Bund — official documents](https://e-rechnung-bund.de/mediathek/dokumente/)
- [Service BW e-Rechnung Validator](https://erechnungsvalidator.service-bw.de/)
- [Rechnung.fans validator](https://portal3.gefeg.com/invoice/validation)
- [Invoice Portal validator](https://validator.invoice-portal.de/index.php)
