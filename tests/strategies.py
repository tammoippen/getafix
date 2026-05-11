"""Hypothesis strategies that emit Factur-X CII invoice XML.

The strategies are driven by the per-profile XSDs vendored under
``tests/schemas/`` (Factur-X 1.08 / ZUGFeRD 2.4). One composite strategy per
profile returns a ``bytes`` payload of UTF-8 XML that is structurally
schema-conformant for that profile:

* Every required element (``minOccurs >= 1``) is emitted.
* Element ordering matches the ``<xs:sequence>`` in the profile's
  ``…ReusableAggregateBusinessInformationEntity_100.xsd``.
* Cardinality respects ``maxOccurs``; ``unbounded`` is bounded to a small
  number for tractable shrinking.
* ``udt:IDType`` carries an optional ``schemeID`` attribute, ``udt:AmountType``
  an optional ``currencyID`` attribute, and ``udt:DateTimeType`` wraps the
  required ``udt:DateTimeString format="102"``.

The strategies are intentionally **independent of the carthorse model** — they
talk straight to the schema. The companion test
(``tests/test_hypothesis.py``) feeds the bytes into ``Document.from_xml`` and
then re-serialises via ``Document.to_xml`` to surface parser/serialiser gaps.
"""

from __future__ import annotations

import string
from datetime import date

import hypothesis.strategies as st
import lxml.etree as etree

from carthorse.schema.types import CategoryCode, Profile, TypeCode

# ---------------------------------------------------------------------------
# namespaces
# ---------------------------------------------------------------------------

_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}


def _q(prefix: str, local: str) -> str:
    return f"{{{_NS[prefix]}}}{local}"


def _sub(parent: etree._Element, prefix: str, local: str) -> etree._Element:
    return etree.SubElement(parent, _q(prefix, local))


# ---------------------------------------------------------------------------
# leaf strategies — text, numbers, codes
# ---------------------------------------------------------------------------

# Token text: no leading/trailing whitespace, no XML metachars; safe inside
# a TextType / IDType element body.
_token_alphabet = string.ascii_letters + string.digits + "._-/"
_token = st.text(alphabet=_token_alphabet, min_size=1, max_size=20)

# Free text content (TextType): we still avoid leading/trailing whitespace
# because the carthorse parser strips text on the way in — so text that
# starts or ends with whitespace would fail the round-trip leg of the test.
_text_alphabet = _token_alphabet + " "
_text = st.text(alphabet=_text_alphabet, min_size=1, max_size=40).filter(
    lambda s: bool(s.strip()) and s == s.strip()
)

# ISO 4217 alpha-3 currency code (shape only; the registry is not enforced).
_currency_code = st.text(alphabet=string.ascii_uppercase, min_size=3, max_size=3)
# ISO 3166-1 alpha-2 country code (shape only).
_country_code = st.text(alphabet=string.ascii_uppercase, min_size=2, max_size=2)

# UNTDID 1001 document type codes (subset that carthorse models).
_doc_type_codes = st.sampled_from([t.value for t in TypeCode])
# UNTDID 5305 VAT category codes.
_vat_categories = st.sampled_from([c.value for c in CategoryCode])
# UNTDID 4461 payment-means codes.
_payment_means_codes = st.sampled_from(
    ["10", "20", "30", "42", "48", "49", "57", "58", "59", "97"]
)
# UNTDID 2475 due-date type codes.
_due_date_codes = st.sampled_from(["5", "29", "72"])

# Decimals as strings, matching the schema lexical space for xs:decimal.
_amount = st.decimals(
    min_value="0", max_value="100000", places=2, allow_nan=False, allow_infinity=False
).map(str)
_percent = st.decimals(
    min_value="0", max_value="100", places=2, allow_nan=False, allow_infinity=False
).map(str)
_quantity = st.decimals(
    min_value="0", max_value="1000", places=2, allow_nan=False, allow_infinity=False
).map(str)

# Dates rendered in UNTDID 2379 format "102" (CCYYMMDD).
_dates = st.dates(min_value=date(2010, 1, 1), max_value=date(2030, 12, 31)).map(
    lambda d: d.strftime("%Y%m%d")
)


# ---------------------------------------------------------------------------
# leaf XML element builders (each consumes hypothesis values and a parent)
# ---------------------------------------------------------------------------


def _put_id(
    parent: etree._Element,
    prefix: str,
    local: str,
    value: str,
    scheme: str | None = None,
) -> None:
    """udt:IDType — text body + optional schemeID attribute."""
    el = _sub(parent, prefix, local)
    el.text = value
    if scheme is not None:
        el.set("schemeID", scheme)


def _put_text(parent: etree._Element, prefix: str, local: str, value: str) -> None:
    el = _sub(parent, prefix, local)
    el.text = value


def _put_code(parent: etree._Element, prefix: str, local: str, value: str) -> None:
    el = _sub(parent, prefix, local)
    el.text = value


def _put_amount(
    parent: etree._Element,
    prefix: str,
    local: str,
    value: str,
    currency: str | None = None,
) -> None:
    el = _sub(parent, prefix, local)
    el.text = value
    if currency is not None:
        el.set("currencyID", currency)


def _put_indicator(
    parent: etree._Element, prefix: str, local: str, value: bool
) -> None:
    el = _sub(parent, prefix, local)
    inner = _sub(el, "udt", "Indicator")
    inner.text = "true" if value else "false"


def _put_date_time(
    parent: etree._Element, prefix: str, local: str, formatted: str
) -> None:
    el = _sub(parent, prefix, local)
    inner = _sub(el, "udt", "DateTimeString")
    inner.text = formatted
    inner.set("format", "102")


def _put_formatted_date_time(
    parent: etree._Element, prefix: str, local: str, formatted: str
) -> None:
    """qdt:FormattedDateTimeType — wraps qdt:DateTimeString format='102'."""
    el = _sub(parent, prefix, local)
    inner = _sub(el, "qdt", "DateTimeString")
    inner.text = formatted
    inner.set("format", "102")


# ---------------------------------------------------------------------------
# composite element builders, parameterised by ``profile`` so we can re-use
# them across the per-profile entry points and add new fields by profile
# ---------------------------------------------------------------------------


def _put_address(draw, parent: etree._Element, profile: Profile) -> None:
    """ram:TradeAddressType. Element ordering per XSD; CountryID required."""
    addr = _sub(parent, "ram", "PostalTradeAddress")
    if profile != Profile.MINIMUM:
        # MINIMUM has only CountryID; richer profiles permit the optional set.
        if draw(st.booleans()):
            _put_code(addr, "ram", "PostcodeCode", draw(_token))
        if draw(st.booleans()):
            _put_text(addr, "ram", "LineOne", draw(_text))
        if draw(st.booleans()):
            _put_text(addr, "ram", "LineTwo", draw(_text))
        if draw(st.booleans()):
            _put_text(addr, "ram", "LineThree", draw(_text))
        if draw(st.booleans()):
            _put_text(addr, "ram", "CityName", draw(_text))
    _put_code(addr, "ram", "CountryID", draw(_country_code))
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_text(addr, "ram", "CountrySubDivisionName", draw(_text))


def _put_legal_org(draw, parent: etree._Element, profile: Profile) -> None:
    org = _sub(parent, "ram", "SpecifiedLegalOrganization")
    if draw(st.booleans()):
        _put_id(
            org, "ram", "ID", draw(_token), scheme=draw(st.one_of(st.none(), _token))
        )
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_text(org, "ram", "TradingBusinessName", draw(_text))


def _put_universal_communication(
    draw, parent: etree._Element, local: str, profile: Profile
) -> None:
    """ram:UniversalCommunicationType.

    Same XSD type for every parent element, but the *meaningful* child
    differs by parent: ``TelephoneUniversalCommunication`` carries
    ``CompleteNumber``; ``EmailURIUniversalCommunication`` and the
    party-level ``URIUniversalCommunication`` carry ``URIID``. The
    party-level one additionally requires a ``schemeID`` on the
    URIID (BR-62 / BR-63). The carthorse model declares the
    appropriate child as required for each role, so always emit it.
    """
    comm = _sub(parent, "ram", local)
    if local == "TelephoneUniversalCommunication":
        _put_text(comm, "ram", "CompleteNumber", draw(_text))
    elif local == "EmailURIUniversalCommunication":
        _put_id(comm, "ram", "URIID", draw(_token))
    else:
        # Party-level URIUniversalCommunication — schemeID required.
        _put_id(comm, "ram", "URIID", draw(_token), scheme=draw(_token))


def _put_trade_contact(draw, parent: etree._Element) -> None:
    """ram:TradeContactType — EN16931+ only."""
    c = _sub(parent, "ram", "DefinedTradeContact")
    if draw(st.booleans()):
        _put_text(c, "ram", "PersonName", draw(_text))
    if draw(st.booleans()):
        _put_text(c, "ram", "DepartmentName", draw(_text))
    if draw(st.booleans()):
        _put_universal_communication(
            draw, c, "TelephoneUniversalCommunication", Profile.COMFORT
        )
    if draw(st.booleans()):
        _put_universal_communication(
            draw, c, "EmailURIUniversalCommunication", Profile.COMFORT
        )


def _put_tax_registration(draw, parent: etree._Element) -> None:
    reg = _sub(parent, "ram", "SpecifiedTaxRegistration")
    _put_id(reg, "ram", "ID", draw(_token), scheme=draw(st.sampled_from(["VA", "FC"])))


def _put_trade_party(
    draw,
    parent: etree._Element,
    local: str,
    profile: Profile,
    *,
    name_required: bool = True,
) -> None:
    """ram:TradePartyType — fields per profile XSD."""
    party = _sub(parent, "ram", local)

    # ID / GlobalID — present from BASIC_WL on Seller/Buyer/Payee/ShipTo,
    # but the SellerTaxRepresentativeTradeParty (BG-11) only gets them
    # at EXTENDED.
    if local == "SellerTaxRepresentativeTradeParty":
        emit_ids = profile == Profile.EXTENDED
    else:
        emit_ids = profile != Profile.MINIMUM
    if emit_ids:
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_id(party, "ram", "ID", draw(_token))
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_id(party, "ram", "GlobalID", draw(_token), scheme=draw(_token))

    # Name: required at MINIMUM; optional everywhere else (per XSD), but
    # carthorse declares it required, so we always emit it.
    if name_required or draw(st.booleans()):
        _put_text(party, "ram", "Name", draw(_text))

    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_text(party, "ram", "Description", draw(_text))

    # legal_organization, contact, electronic_address, tax_registrations
    # — all "rich" sub-fields. SellerTaxRepresentativeTradeParty
    # (BG-11) and ShipToTradeParty (BG-13) only carry these at
    # EXTENDED; other roles allow them from BASIC_WL+.
    rich_only_at_extended = local in (
        "SellerTaxRepresentativeTradeParty",
        "ShipToTradeParty",
    )
    rich_allowed = (not rich_only_at_extended) or profile == Profile.EXTENDED

    if rich_allowed and draw(st.booleans()):
        _put_legal_org(draw, party, profile)

    if (
        rich_allowed
        and profile in (Profile.COMFORT, Profile.EXTENDED)
        and draw(st.booleans())
    ):
        _put_trade_contact(draw, party)

    # PostalTradeAddress: optional everywhere per XSD, but at MINIMUM
    # carthorse requires it on Seller/Buyer; we always emit on those.
    _put_address(draw, party, profile)

    if rich_allowed and profile != Profile.MINIMUM and draw(st.booleans()):
        _put_universal_communication(draw, party, "URIUniversalCommunication", profile)

    # SpecifiedTaxRegistration. At MINIMUM the appendix narrative
    # restricts these to the Seller (BG-4) only — the Buyer block is
    # Name + optional SpecifiedLegalOrganization. From BASIC_WL onwards
    # any party may carry up to two registrations. The Seller tax
    # representative party (BG-11) requires *at least one* (BR-56), so
    # we always emit one for that role. ShipToTradeParty (BG-13) only
    # carries them at EXTENDED.
    if local == "SellerTaxRepresentativeTradeParty":
        _put_tax_registration(draw, party)
    elif local == "ShipToTradeParty":
        if profile == Profile.EXTENDED:
            for _ in range(draw(st.integers(min_value=0, max_value=2))):
                _put_tax_registration(draw, party)
    elif local == "SellerTradeParty" or profile != Profile.MINIMUM:
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_tax_registration(draw, party)


def _put_referenced_document(
    draw, parent: etree._Element, local: str, profile: Profile, *, rich: bool = False
) -> None:
    """ram:ReferencedDocumentType.

    Shape varies: BASIC_WL/BASIC use the simple 2-element form (IssuerAssignedID
    + optional FormattedIssueDateTime). EN16931/EXTENDED expand to attachment +
    typing fields when ``rich`` is True (only used for AdditionalReferencedDocument).
    """
    ref = _sub(parent, "ram", local)
    if rich and profile in (Profile.COMFORT, Profile.EXTENDED):
        # The XSD makes IssuerAssignedID optional in the rich form, but
        # carthorse declares it required and every real-world BG-24
        # instance carries one. Always emit.
        _put_id(ref, "ram", "IssuerAssignedID", draw(_token))
        if draw(st.booleans()):
            _put_id(ref, "ram", "URIID", draw(_token))
        if draw(st.booleans()):
            _put_id(ref, "ram", "LineID", draw(_token))
        if draw(st.booleans()):
            _put_code(
                ref, "ram", "TypeCode", draw(st.sampled_from(["50", "130", "916"]))
            )
        if draw(st.booleans()):
            _put_text(ref, "ram", "Name", draw(_text))
    else:
        _put_id(ref, "ram", "IssuerAssignedID", draw(_token))
        # MINIMUM's ReferencedDocumentType has only IssuerAssignedID;
        # FormattedIssueDateTime appears from BASIC_WL onwards.
        if profile != Profile.MINIMUM and draw(st.booleans()):
            _put_formatted_date_time(ref, "ram", "FormattedIssueDateTime", draw(_dates))


def _put_trade_tax(draw, parent: etree._Element, local: str, profile: Profile) -> None:
    """ram:TradeTaxType — used both at header (BG-23) and inside allowance/charge."""
    tax = _sub(parent, "ram", local)
    if draw(st.booleans()):
        _put_amount(tax, "ram", "CalculatedAmount", draw(_amount))
    _put_code(tax, "ram", "TypeCode", "VAT")
    if draw(st.booleans()):
        _put_text(tax, "ram", "ExemptionReason", draw(_text))
    if draw(st.booleans()):
        _put_amount(tax, "ram", "BasisAmount", draw(_amount))
    _put_code(tax, "ram", "CategoryCode", draw(_vat_categories))
    if draw(st.booleans()):
        _put_code(tax, "ram", "ExemptionReasonCode", draw(_token))
    if draw(st.booleans()):
        _put_code(tax, "ram", "DueDateTypeCode", draw(_due_date_codes))
    if draw(st.booleans()):
        _put_code(tax, "ram", "RateApplicablePercent", draw(_percent))


def _put_allowance_charge(
    draw, parent: etree._Element, profile: Profile, *, header: bool
) -> None:
    """ram:TradeAllowanceChargeType — element naming is the same at header and line."""
    ac = _sub(
        parent,
        "ram",
        "SpecifiedTradeAllowanceCharge" if header else "AppliedTradeAllowanceCharge",
    )
    _put_indicator(ac, "ram", "ChargeIndicator", draw(st.booleans()))
    if draw(st.booleans()):
        _put_code(ac, "ram", "CalculationPercent", draw(_percent))
    if draw(st.booleans()):
        _put_amount(ac, "ram", "BasisAmount", draw(_amount))
    _put_amount(ac, "ram", "ActualAmount", draw(_amount))
    if draw(st.booleans()):
        _put_code(ac, "ram", "ReasonCode", draw(_token))
    if draw(st.booleans()):
        _put_text(ac, "ram", "Reason", draw(_text))
    # CategoryTradeTax: required at BASIC_WL, optional from BASIC onwards.
    if header and (profile == Profile.BASIC_WL or draw(st.booleans())):
        _put_trade_tax(draw, ac, "CategoryTradeTax", profile)


def _put_payment_means(draw, parent: etree._Element, profile: Profile) -> None:
    pm = _sub(parent, "ram", "SpecifiedTradeSettlementPaymentMeans")
    _put_code(pm, "ram", "TypeCode", draw(_payment_means_codes))
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_text(pm, "ram", "Information", draw(_text))
    if draw(st.booleans()):
        debt = _sub(pm, "ram", "PayerPartyDebtorFinancialAccount")
        _put_id(debt, "ram", "IBANID", draw(_token))
    if draw(st.booleans()):
        cred = _sub(pm, "ram", "PayeePartyCreditorFinancialAccount")
        if draw(st.booleans()):
            _put_id(cred, "ram", "IBANID", draw(_token))
        if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
            _put_text(cred, "ram", "AccountName", draw(_text))
        if draw(st.booleans()):
            _put_id(cred, "ram", "ProprietaryID", draw(_token))


def _put_specified_period(draw, parent: etree._Element, local: str) -> None:
    p = _sub(parent, "ram", local)
    if draw(st.booleans()):
        _put_date_time(p, "ram", "StartDateTime", draw(_dates))
    if draw(st.booleans()):
        _put_date_time(p, "ram", "EndDateTime", draw(_dates))


def _put_payment_terms(draw, parent: etree._Element) -> None:
    pt = _sub(parent, "ram", "SpecifiedTradePaymentTerms")
    if draw(st.booleans()):
        _put_text(pt, "ram", "Description", draw(_text))
    if draw(st.booleans()):
        _put_date_time(pt, "ram", "DueDateDateTime", draw(_dates))
    if draw(st.booleans()):
        _put_id(pt, "ram", "DirectDebitMandateID", draw(_token))


def _put_monetary_summation(draw, parent: etree._Element, profile: Profile) -> None:
    summ = _sub(parent, "ram", "SpecifiedTradeSettlementHeaderMonetarySummation")
    currency = draw(_currency_code)
    # MINIMUM does NOT have LineTotalAmount; every other profile requires it.
    if profile != Profile.MINIMUM:
        _put_amount(summ, "ram", "LineTotalAmount", draw(_amount))
        if draw(st.booleans()):
            _put_amount(summ, "ram", "ChargeTotalAmount", draw(_amount))
        if draw(st.booleans()):
            _put_amount(summ, "ram", "AllowanceTotalAmount", draw(_amount))
    _put_amount(summ, "ram", "TaxBasisTotalAmount", draw(_amount))
    if draw(st.booleans()):
        _put_amount(summ, "ram", "TaxTotalAmount", draw(_amount), currency=currency)
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_amount(summ, "ram", "RoundingAmount", draw(_amount))
    _put_amount(summ, "ram", "GrandTotalAmount", draw(_amount))
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_amount(summ, "ram", "TotalPrepaidAmount", draw(_amount))
    _put_amount(summ, "ram", "DuePayableAmount", draw(_amount))


# ---------------------------------------------------------------------------
# block builders
# ---------------------------------------------------------------------------


def _put_exchanged_doc_context(parent: etree._Element, profile: Profile) -> None:
    ctx = _sub(parent, "rsm", "ExchangedDocumentContext")
    guideline = _sub(ctx, "ram", "GuidelineSpecifiedDocumentContextParameter")
    _put_id(guideline, "ram", "ID", profile.value)


def _put_exchanged_document(draw, parent: etree._Element, profile: Profile) -> None:
    doc = _sub(parent, "rsm", "ExchangedDocument")
    _put_id(doc, "ram", "ID", draw(_token))
    _put_code(doc, "ram", "TypeCode", draw(_doc_type_codes))
    _put_date_time(doc, "ram", "IssueDateTime", draw(_dates))
    if profile != Profile.MINIMUM:
        # IncludedNote* — BASIC_WL+
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            note = _sub(doc, "ram", "IncludedNote")
            _put_text(note, "ram", "Content", draw(_text))
            if draw(st.booleans()):
                _put_code(note, "ram", "SubjectCode", draw(_token))


def _put_header_trade_agreement(draw, parent: etree._Element, profile: Profile) -> None:
    agr = _sub(parent, "ram", "ApplicableHeaderTradeAgreement")
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_text(agr, "ram", "BuyerReference", draw(_text))
    _put_trade_party(draw, agr, "SellerTradeParty", profile)
    _put_trade_party(draw, agr, "BuyerTradeParty", profile)
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_trade_party(draw, agr, "SellerTaxRepresentativeTradeParty", profile)
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_referenced_document(draw, agr, "SellerOrderReferencedDocument", profile)
    if draw(st.booleans()):
        _put_referenced_document(draw, agr, "BuyerOrderReferencedDocument", profile)
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_referenced_document(draw, agr, "ContractReferencedDocument", profile)
    if profile in (Profile.COMFORT, Profile.EXTENDED):
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_referenced_document(
                draw, agr, "AdditionalReferencedDocument", profile, rich=True
            )
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        proj = _sub(agr, "ram", "SpecifiedProcuringProject")
        _put_id(proj, "ram", "ID", draw(_token))
        _put_text(proj, "ram", "Name", draw(_text))


def _put_header_trade_delivery(draw, parent: etree._Element, profile: Profile) -> None:
    delv = _sub(parent, "ram", "ApplicableHeaderTradeDelivery")
    if profile != Profile.MINIMUM:
        if draw(st.booleans()):
            _put_trade_party(
                draw, delv, "ShipToTradeParty", profile, name_required=False
            )
        if draw(st.booleans()):
            ev = _sub(delv, "ram", "ActualDeliverySupplyChainEvent")
            _put_date_time(ev, "ram", "OccurrenceDateTime", draw(_dates))
        if draw(st.booleans()):
            _put_referenced_document(
                draw, delv, "DespatchAdviceReferencedDocument", profile
            )
        if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
            _put_referenced_document(
                draw, delv, "ReceivingAdviceReferencedDocument", profile
            )


def _put_header_trade_settlement(
    draw, parent: etree._Element, profile: Profile
) -> None:
    settle = _sub(parent, "ram", "ApplicableHeaderTradeSettlement")
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_id(settle, "ram", "CreditorReferenceID", draw(_token))
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_text(settle, "ram", "PaymentReference", draw(_text))
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_code(settle, "ram", "TaxCurrencyCode", draw(_currency_code))
    _put_code(settle, "ram", "InvoiceCurrencyCode", draw(_currency_code))
    if profile != Profile.MINIMUM and draw(st.booleans()):
        _put_trade_party(draw, settle, "PayeeTradeParty", profile, name_required=True)
    if profile != Profile.MINIMUM:
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_payment_means(draw, settle, profile)
        # ApplicableTradeTax+ at BASIC_WL+
        for _ in range(draw(st.integers(min_value=1, max_value=2))):
            _put_trade_tax(draw, settle, "ApplicableTradeTax", profile)
        if draw(st.booleans()):
            _put_specified_period(draw, settle, "BillingSpecifiedPeriod")
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_allowance_charge(draw, settle, profile, header=True)
        if draw(st.booleans()):
            _put_payment_terms(draw, settle)
    _put_monetary_summation(draw, settle, profile)
    if profile != Profile.MINIMUM:
        for _ in range(draw(st.integers(min_value=0, max_value=2))):
            _put_referenced_document(draw, settle, "InvoiceReferencedDocument", profile)
        if draw(st.booleans()):
            acct = _sub(settle, "ram", "ReceivableSpecifiedTradeAccountingAccount")
            _put_id(acct, "ram", "ID", draw(_token))


def _put_line_item(draw, parent: etree._Element, profile: Profile) -> None:
    """ram:SupplyChainTradeLineItemType — required from BASIC onwards."""
    item = _sub(parent, "ram", "IncludedSupplyChainTradeLineItem")
    # AssociatedDocumentLineDocument
    adld = _sub(item, "ram", "AssociatedDocumentLineDocument")
    _put_id(adld, "ram", "LineID", draw(_token))
    if draw(st.booleans()):
        note = _sub(adld, "ram", "IncludedNote")
        _put_text(note, "ram", "Content", draw(_text))
    # SpecifiedTradeProduct
    prod = _sub(item, "ram", "SpecifiedTradeProduct")
    if draw(st.booleans()):
        _put_id(prod, "ram", "GlobalID", draw(_token), scheme=draw(_token))
    if profile in (Profile.COMFORT, Profile.EXTENDED):
        if draw(st.booleans()):
            _put_id(prod, "ram", "SellerAssignedID", draw(_token))
        if draw(st.booleans()):
            _put_id(prod, "ram", "BuyerAssignedID", draw(_token))
    _put_text(prod, "ram", "Name", draw(_text))
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_text(prod, "ram", "Description", draw(_text))
    # SpecifiedLineTradeAgreement: NetPriceProductTradePrice required.
    lta = _sub(item, "ram", "SpecifiedLineTradeAgreement")
    net = _sub(lta, "ram", "NetPriceProductTradePrice")
    _put_amount(net, "ram", "ChargeAmount", draw(_amount))
    # SpecifiedLineTradeDelivery: BilledQuantity required.
    ltd = _sub(item, "ram", "SpecifiedLineTradeDelivery")
    bq = _sub(ltd, "ram", "BilledQuantity")
    bq.text = draw(_quantity)
    bq.set("unitCode", "C62")  # the qdt:QuantityType requires unitCode
    # SpecifiedLineTradeSettlement: ApplicableTradeTax + LineMonetarySummation required.
    lts = _sub(item, "ram", "SpecifiedLineTradeSettlement")
    _put_trade_tax(draw, lts, "ApplicableTradeTax", profile)
    if profile in (Profile.COMFORT, Profile.EXTENDED) and draw(st.booleans()):
        _put_specified_period(draw, lts, "BillingSpecifiedPeriod")
    lsumm = _sub(lts, "ram", "SpecifiedTradeSettlementLineMonetarySummation")
    _put_amount(lsumm, "ram", "LineTotalAmount", draw(_amount))


# ---------------------------------------------------------------------------
# top-level: one strategy per profile
# ---------------------------------------------------------------------------


def _serialise(root: etree._Element) -> bytes:
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    )


@st.composite
def _build(draw, profile: Profile) -> bytes:
    """Build a CII XML document for *profile* per the vendored XSDs."""
    root = etree.Element(_q("rsm", "CrossIndustryInvoice"), nsmap=_NS)
    _put_exchanged_doc_context(root, profile)
    _put_exchanged_document(draw, root, profile)
    txn = _sub(root, "rsm", "SupplyChainTradeTransaction")
    # BASIC and above: SupplyChainTradeLineItem precedes the header sections.
    if profile in (Profile.BASIC, Profile.COMFORT, Profile.EXTENDED):
        for _ in range(draw(st.integers(min_value=1, max_value=2))):
            _put_line_item(draw, txn, profile)
    _put_header_trade_agreement(draw, txn, profile)
    _put_header_trade_delivery(draw, txn, profile)
    _put_header_trade_settlement(draw, txn, profile)
    return _serialise(root)


def minimum_invoices() -> st.SearchStrategy[bytes]:
    return _build(Profile.MINIMUM)


def basic_wl_invoices() -> st.SearchStrategy[bytes]:
    return _build(Profile.BASIC_WL)


def basic_invoices() -> st.SearchStrategy[bytes]:
    return _build(Profile.BASIC)


def en16931_invoices() -> st.SearchStrategy[bytes]:
    """EN 16931 / Factur-X COMFORT profile."""
    return _build(Profile.COMFORT)


def extended_invoices() -> st.SearchStrategy[bytes]:
    return _build(Profile.EXTENDED)


def invoices_for(profile: Profile) -> st.SearchStrategy[bytes]:
    """Dispatch helper — handy for parametrised tests."""
    return _build(profile)
