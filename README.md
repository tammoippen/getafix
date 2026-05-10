# carthorse

Build and parse [**ZUGFeRD 2.x / Factur-X**](https://www.ferd-net.de/standards/zugferd)
Cross-Industry-Invoice (CII) XML in Python, modelled directly on the EN 16931
business terms (BT-/BG-codes) so that the dataclasses stay traceable to the spec.

> **Status: early WIP.** The XML serialiser ("create") is solid for the fields
> that are modelled; the parser ("parse") works for documents this library
> itself emits but trips over real-world samples (see *Known gaps* below).
> There is **no PDF/A-3 packaging** yet — carthorse handles the embedded XML
> only, not the surrounding Factur-X PDF container.

## Quickstart

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
)
from carthorse.schema.settlement import TradeSettlement
from carthorse.schema.trade import Trade

doc = Document(
    context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
    header=Header(
        id="INV-2025-0001",
        type_code=TypeCode.T_Handelsrechnung,  # 380 = commercial invoice
        issue_date=date(2025, 11, 16),
    ),
    trade=Trade(
        agreement=TradeAgreement(
            seller=SellerTradeParty(
                name="Acme GmbH",
                address=PostalTradeAddressExtended(country_id="DE"),
            ),
            buyer=BuyerTradeParty(
                name="Beta AG",
                address=PostalTradeAddressExtended(country_id="DE"),
            ),
        ),
        delivery=TradeDelivery(),
        settlement=TradeSettlement(
            currency_code="EUR",
            monetary_summation=MonetarySummation(
                line_total=Decimal("100.00"),
                tax_basis_total=Decimal("100.00"),
                tax_total=TaxTotal(amount=Decimal("19.00"), currency_id="EUR"),
                grand_total=Decimal("119.00"),
                due_amount=Decimal("119.00"),
            ),
        ),
    ),
)

xml = doc.to_xml().render(indent=True)        # serialise
doc.validate()                                # raises ValidationError on BR-* failures

# Round-trip back into a Document
import lxml.etree as etree
parsed = Document.from_xml(etree.fromstring(xml.encode()))
assert parsed == doc
```

## Requirements

- Python **3.12+** (uses PEP 695 generics, `override`, `StrEnum`, etc.)
- [`uv`](https://docs.astral.sh/uv/) for env / dependency management

Runtime deps (locked in `uv.lock`): `lxml`, `tagic` (tiny XML builder), `beartype`.

## Development

```bash
uv sync                 # create .venv and install dev deps

make tests              # pytest + 90% coverage gate (fails below)
make check              # ruff format check + ruff lint + basedpyright
make fmt                # auto-format and auto-fix lint
```

CI runs `make check` then `make tests` on Linux/macOS/Windows (see
`.github/workflows/CI.yml`). Tagging `v*` triggers `Publish.yml` to push to PyPI.

## How the model is structured

Everything inherits from `carthorse.schema.element.Element`, a `@dataclass`
mixin that knows three things:

- **`tag` / `namespace`** (`ClassVar`s) — the qualified XML tag the element
  emits (`ram:`, `rsm:`, `udt:` …). See `carthorse.schema.types.Namespace`.
- **`profile`** — the minimum [Factur-X profile](#profiles) at which the
  element is allowed. Trying to render at a lower profile raises
  `ProfileMismatch`.
- A pair of methods, `to_xml_internal(profile)` and `from_xml(elem)`, that
  walk the dataclass fields. Each field's `metadata` carries `tag`, optional
  `ns`, and optional `profile` overrides.

### Module map

| Module | What lives there |
|---|---|
| `schema/types.py` | Enums: `Profile`, `Namespace`, `TypeCode` (UNTDID 1001), `CategoryCode` (UNTDID 5305 / VAT), `MIME`. |
| `schema/element.py` | `Element` base class; XML render/parse plumbing for `str`, `Decimal`, `bool`, `date`, child `Element`. Defines `ProfileMismatch` and `ValidationError`. |
| `schema/document.py` | Top-level `Document` (CII root) and its three children: `Context` (BG-2), `Header` (BG-1) and `Trade`. |
| `schema/trade.py` | `Trade` aggregate (`agreement` + `delivery` + `settlement` + `items`) and `TradeLineItem` (BG-25, currently a stub). |
| `schema/agreement.py` | `TradeAgreement` (BG-4/BG-7/BG-11/BG-24 …) — seller, buyer, tax representative, references. |
| `schema/delivery.py` | `TradeDelivery` (BG-13/BG-14) — ship-to/from, delivery date, despatch & receiving advice. |
| `schema/settlement.py` | `TradeSettlement` (BG-16/BG-22/BG-23) — currency, payment means, taxes, totals, terms. |
| `schema/accounting.py` | `MonetarySummation` (BG-22), `ApplicableTradeTax` (BG-23), `TradeAllowanceCharge` (BG-20/21), `TaxTotal`. |
| `schema/party.py` | `SellerTradeParty`, `BuyerTradeParty`, `SellerTaxRepresentativeTradeParty`, ship-to/from/end-user, addresses, contacts, IBAN-style identifiers. |
| `schema/references.py` | All `*ReferencedDocument` types (buyer order, contract, despatch advice, delivery note, prior invoice, …) plus `AdditionalReferencedDocument` with attachments. |

When extending the schema, look for `# TODO` comments — they mark fields and
business rules that have been read in the spec but not yet implemented.

### Profiles

`Profile` is `StrEnum` with comparison overridden to be ordinal (`MINIMUM <
BASIC_WL < BASIC < COMFORT < EXTENDED`). The URN values are the actual
Factur-X profile identifiers that go into
`<ram:GuidelineSpecifiedDocumentContextParameter><ram:ID>…</ram:ID></ram:GuidelineSpecifiedDocumentContextParameter>`.

| Constant | Profile URN |
|---|---|
| `MINIMUM` | `urn:factur-x.eu:1p0:minimum` |
| `BASIC_WL` | `urn:factur-x.eu:1p0:basicwl` |
| `BASIC` | `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic` |
| `COMFORT` | `urn:cen.eu:en16931:2017` (a.k.a. EN 16931) |
| `EXTENDED` | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended` |

`Document.to_xml()` picks the profile from the document's own context. Each
field in the model can declare a `profile` in its `metadata`; rendering at a
lower profile while a stricter field is set raises `ProfileMismatch`.

## Testing

```bash
uv run pytest                       # everything
uv run pytest tests/test_samples.py # just the sample-corpus tests
```

`tests/test_document.py` covers builder / serialiser / round-trip on a
hand-constructed `minimum_doc` and `full_doc` plus the BR-16 validator.

`tests/test_samples.py` runs the parser against real-world Factur-X / ZUGFeRD
XML files in `tests/samples/`. Three checks per sample:

1. Well-formed CII XML — must pass.
2. Declared profile matches filename prefix and is a known `Profile` — must pass.
3. Full `Document.from_xml(...)` round-trip — currently `xfail(strict=False)`.
   When parser gaps close these flip to **XPASS**; remove the `xfail` on the
   ones that pass to lock the contract in.

Sample provenance, license (Apache 2.0) and download URLs are in
[`tests/samples/SOURCES.md`](tests/samples/SOURCES.md). Sources are
[ZUGFeRD/mustangproject](https://github.com/ZUGFeRD/mustangproject) and
[ZUGFeRD/corpus](https://github.com/ZUGFeRD/corpus).

## Reference docs

Per-profile reference material lives under `docs/`:

- [`docs/STRUCTURES.md`](docs/STRUCTURES.md) — module → BG/BT field map,
  profile applicability, and wire conventions.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — every EN 16931 / Factur-X
  business rule (`BR-1..65`, `BR-CO-3..26`, the per-VAT-category
  families, and the EXTENDED `BR-FXEXT-*` overlay) with implementation
  status.
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) — gap
  list and ordered roadmap for the missing structures and validators.

## Known gaps

Roughly in order of how often they come up when feeding real samples in:

- **`schemeID` vs `schemaID`** — real ZUGFeRD CII attributes are spelled
  `schemeID` (no `a`). `carthorse.schema.party.SchemaID` hardcodes
  `schemaID` in both render and parse, so any party identifier from upstream
  fails to parse.
- **`SpecifiedTaxRegistration` uses `<ram:ID>` in the wild**, not
  `<ram:GlobalID>` as currently modelled.
- **`MonetarySummation.line_total` is required**, but the **MINIMUM** profile
  legitimately omits `LineTotalAmount`. The dataclass needs a profile-aware
  `default=None` or per-profile splits.
- **`currencyID` attribute on monetary amounts** (`TaxBasisTotalAmount`,
  `GrandTotalAmount`, `DuePayableAmount`, …) is dropped by the parser —
  `Decimal` fields are read as plain strings, the attribute is discarded.
  Round-tripping a real sample loses this attribute.
- **`TradeLineItem` is a stub.** Real BG-25 has product, agreement,
  delivery, settlement sub-trees that are not yet modelled — see TODOs in
  `schema/__init__.py` and `schema/trade.py`.
- **Missing fields tracked in `schema/__init__.py`**: party fields,
  agreement fields, reference fields.
- **No PDF/A-3 packaging.** carthorse only handles the embedded
  `factur-x.xml`; embedding it into a PDF/A-3 invoice (or extracting it from
  one) is out of scope today. See `factur-x` (PyPI) or Mustang for that piece.
- **Validation is partial.** Existing checks: BR-16, BR-50, BR-CO-18,
  BR-CO-21/22, currency code, UNTDID 4461 form, VAT/FC schema id. The bulk
  of the BR-CO computational rules (BR-CO-10..17) are listed as TODOs in
  `schema/accounting.py` but not yet enforced.
## ZUGFeRD references

Specification:
- [FeRD net — ZUGFeRD overview](https://www.ferd-net.de/standards/zugferd)
- [Rechnung Fans — XRechnung / EN 16931 portal](https://portal3.gefeg.com/invoice/tthome/index/617afdc4-623f-44e0-a05b-5b878840e508)
- [e-Rechnung Bund — official documents](https://e-rechnung-bund.de/mediathek/dokumente/)
- [Feldvorgaben xRechnung (es2000)](https://manual.es2000.de/esoffice/1300/content/esoffice/faq/xrechnung_feldvorgaben.htm?TocPath=FAQ%7C_____26)

Online validators (paste an XML or upload a Factur-X PDF):
- [Service BW e-Rechnung Validator](https://erechnungsvalidator.service-bw.de/)
- [Rechnung.fans validator](https://portal3.gefeg.com/invoice/validation)
- [Invoice Portal validator](https://validator.invoice-portal.de/index.php)
