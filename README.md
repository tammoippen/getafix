# getafix

[![CI](https://github.com/tammoippen/getafix/actions/workflows/CI.yml/badge.svg)](https://github.com/tammoippen/getafix/actions/workflows/CI.yml)
[![PyPi version](https://img.shields.io/pypi/v/getafix.svg)](https://pypi.python.org/pypi/getafix)
[![Downloads](https://pepy.tech/badge/getafix/month)](https://pepy.tech/project/getafix)
[![PyPi license](https://img.shields.io/pypi/l/getafix.svg)](https://pypi.python.org/pypi/getafix)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Build, parse and validate
[**ZUGFeRD 2.x / Factur-X**](https://www.ferd-net.de/standards/zugferd)
Cross-Industry-Invoice (CII) XML in Python. The dataclass model is
traceable to the EN 16931 business terms (`BT-…`) and groups
(`BG-…`), so every field on every class maps back to a line in the
spec.

## Why "getafix"?

Getafix is the village druid in _Asterix_ — the one who brews the
magic potion from an exact recipe, drop by drop, so it comes out
right every time. That is what this library does for **Factur-X**:
it follows the EN 16931 recipe term by term (`BT-…`/`BG-…`) and
mixes a valid invoice. The Gaulish `-ix` ending even echoes the
`-X` in Factur-**X**, and since Factur-X is the French half of the
standard, a French druid felt right. As a bonus, the name reads as
"get a fix" — _get a valid Factur-X_.

> **Status: pre-1.0.** Solid for the fields that are modelled across
> MINIMUM / BASIC_WL / BASIC / COMFORT (EN 16931); selective EXTENDED
> coverage. PDF/A-3 conformance for the host PDF is **out of scope** —
> `getafix` attaches the embedded `factur-x.xml` but does not
> upgrade the surrounding PDF to PDF/A-3.

## License and attribution

`getafix` is distributed under the **Apache License 2.0** — see
[`LICENSE`](LICENSE).

This project is an application of the **ZUGFeRD / Factur-X**
publication issued by the _Forum elektronische Rechnung Deutschland_
(FeRD) at AWV e.V. The format incorporates **EN 16931**, reproduced
by FeRD with the permission of **CEN** and **DIN**. _ZUGFeRD_ and
_Factur-X_ are trademarks of FeRD / AWV e.V., used here only to
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
> invoices generated or parsed with `getafix` meet all legal and
> regulatory requirements applicable in their jurisdiction.
> `getafix` does not guarantee compliance with any specific
> national or sector-specific e-invoicing mandate.

## Installation

Requires **Python 3.12+**. We recommend
[`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
pip install getafix
```

The base install lets you build / serialise / validate documents with
the Python stdlib XML parser. The optional extras unlock more:

| Extra           | Pulls in                | Enables                                                                                                                                                     |
| --------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `getafix[lxml]` | `lxml`                  | Round-tripping XML produced by other tools (the stdlib parser is fine for most documents; `lxml` is faster and more tolerant of large / namespaced inputs). |
| `getafix[pdf]`  | `pypdf`                 | Embedding / extracting `factur-x.xml` in a PDF (`getafix.pdf.attach_xml` and `extract_xml`).                                                                |
| `getafix[cli]`  | `lxml`, `rich`, `pypdf` | The `getafix` console script — pretty-print an invoice and run the BR-\* validators against it.                                                             |

Install several at once:

```bash
pip install 'getafix[lxml,pdf]'
```

## Quickstart — build an invoice

```python
from datetime import date
from decimal import Decimal

from getafix.schema.document import (
    Context, Document, GuidelineDocument, Header
)
from getafix.schema.accounting import MonetarySummation, TaxTotal
from getafix.schema.agreement import TradeAgreement
from getafix.schema.delivery import TradeDelivery
from getafix.schema.party import (
    BuyerTradeParty, PostalTradeAddressExtended, SellerTradeParty,
    SpecifiedTaxRegistration, TaxSchemeId,
)
from getafix.schema.settlement import TradeSettlement
from getafix.schema.trade import Trade
from getafix.schema.types import Country, Currency, Profile, TypeCode

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
from getafix.schema.document import Document

tree = ET.parse("factur-x.xml")
doc = Document.from_xml(tree.getroot())

print(doc.header.id, doc.header.type_code, doc.header.issue_date)
print(doc.trade.settlement.monetary_summation.grand_total)

doc.validate()   # raises ValidationErrors with every violation
```

`lxml.etree` works the same way — pass the root element to
`Document.from_xml`.

From a Factur-X / ZUGFeRD PDF (`getafix[pdf]` extra):

```python
import xml.etree.ElementTree as ET
from getafix.pdf import extract_xml
from getafix.schema.document import Document

payload = extract_xml(Path("invoice.pdf"))   # bytes or None
if payload is None:
    raise SystemExit("No factur-x.xml found in the PDF")
doc = Document.from_xml(ET.fromstring(payload))
```

To embed an XML into an existing PDF:

```python
from pathlib import Path
from getafix.pdf import attach_xml

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
from getafix.schema.element import ValidationErrors

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

Every rule getafix enforces lives in `getafix.rules` — one module per
schema topic (`accounting`, `line`, `party`, `settlement`, `trade`,
`extended`), each wired onto the relevant element's `_validators`.

## Command-line tool

The `getafix[cli]` extra ships a console script that pretty-prints
an invoice and runs the validators:

```bash
> getafix path/to/factur-x.xml
> getafix path/to/invoice.pdf            # reads the embedded XML
> getafix --no-validate path/to/file.xml # skip BR-* checks
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

| Profile    | URN                                                               | Carries line items       |
| ---------- | ----------------------------------------------------------------- | ------------------------ |
| `MINIMUM`  | `urn:factur-x.eu:1p0:minimum`                                     | ✗ (header totals only).  |
| `BASIC_WL` | `urn:factur-x.eu:1p0:basicwl`                                     | ✗ (basic, without lines) |
| `BASIC`    | `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic`     | ✓                        |
| `COMFORT`  | `urn:cen.eu:en16931:2017` _(a.k.a. EN 16931)_                     | ✓                        |
| `EXTENDED` | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended` | ✓ + sub-lines            |

The profile is set on the document via
`Context(guideline=GuidelineDocument(id=Profile.X))`. Getafix
enforces it at render time: setting a field that only exists at a
higher profile raises `ProfileMismatch`.

## Status and known gaps

Getafix models every field that the MINIMUM, BASIC_WL, BASIC and
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

Every shipped sample re-renders **1:1** with its source XML
(`tests/test_roundtrip_fidelity.py`) — getafix never silently drops a
field it claims to model.

The remaining EXTENDED gaps are optional leaf attributes and line-level
twins the shipped samples don't exercise. Each is a mechanical add-on
against the EXTENDED XSD (declare a `field()` gated `Profile.EXTENDED`,
in XSD-sequence order); getafix will accept a PR, or pick one up when a
sample needs it:

- **Party extras** — `RoleCode` (`BT-X-483`…`BT-X-575`) on every trade
  party; additional legal info (`Description`) on the Buyer (`BT-X-334`)
  and the line-level item seller (`BT-X-571`); contact `TypeCode`
  (`BT-X-315`…`BT-X-575`) on every `DefinedTradeContact` (BG-6 / BG-9).
- **Line-level twins of header references** — on `LineTradeAgreement`:
  delivery terms (`BG-X-87`), contract (`BG-X-2`), seller order
  (`BG-X-81`), ultimate-customer order (`BG-X-5`); on
  `LineTradeDelivery`: the actual delivery event / date (`BT-X-85-000`),
  despatch (`BG-X-13`) and receiving (`BG-X-82`) advice; on
  `LineTradeSettlement`: the preceding-invoice reference (`BG-X-48`);
  line-note codes (`BT-X-9` / `BT-X-10`).
  _(The line-level delivery-note `BG-X-83` and additional-document
  `BG-X-3` twins **are** modelled.)_
- **Line monetary totals** — `AllowanceTotalAmount` / `ChargeTotalAmount`
  / `TaxTotalAmount` / `GrandTotalAmount` (`BT-X-327`…`BT-X-330`); the
  line total and total-allowance-charge are modelled.
- **Referenced-document leaves** — `FormattedIssueDateTime` on the header
  additional / contract references (`BT-X-33-00` / `BT-X-148-00` /
  `BT-X-149-00`); preceding-invoice `TypeCode` (`BT-X-555`); accounting
  reference `TypeCode` (`BT-X-99` / `BT-X-290`).
- **Other shared leaves** — item characteristic `TypeCode` / `ValueMeasure`
  (`BT-X-11` / `BT-X-12`), invoicing-period `Description` (`BT-X-264`),
  allowance/charge `SequenceNumeric` / `BasisQuantity` (`BT-X-265` /
  `BT-X-266`), per-line product local `ID` (`BT-X-305`), net-price
  `IncludedTradeTax` (`BG-X-4`, B2C VAT in the unit price).

PDF/A-3 packaging is out of scope; use `factur-x` (PyPI),
[Mustangproject](https://github.com/ZUGFeRD/mustangproject) or a
dedicated converter for full Factur-X PDF conformance.

## Contributing

See [`AGENTS.md`](AGENTS.md) for the developer guide — module layout,
how the dataclass model works, how to add a new BT field or BR
validator, and the test / lint workflow.

## References

Specification and validators:

- [FeRD net — ZUGFeRD standard](https://www.ferd-net.de/standards/zugferd)
- [Rechnung Fans — XRechnung / EN 16931 portal](https://portal3.gefeg.com/invoice/tthome/index/617afdc4-623f-44e0-a05b-5b878840e508)
- [Service BW e-Rechnung Validator](https://erechnungsvalidator.service-bw.de/)
- [Rechnung.fans validator](https://portal3.gefeg.com/invoice/validation)
- [Invoice Portal validator](https://validator.invoice-portal.de/index.php)
