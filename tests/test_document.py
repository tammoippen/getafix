import xml.etree.ElementTree as other_etree
from datetime import date
from decimal import Decimal

import lxml.etree as etree
import pytest as pt

from carthorse.schema import (
    Context,
    Document,
    EffectivePeriod,
    GuidelineDocument,
    Header,
    IncludedNote,
    Profile,
    TypeCode,
)
from carthorse.schema.accounting import ApplicableTradeTax, MonetarySummation, TaxTotal
from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import ValidationError
from carthorse.schema.line import (
    DocumentLineDocument,
    LineMonetarySummation,
    LineTradeAgreement,
    LineTradeDelivery,
    LineTradeSettlement,
    NetTradePrice,
    Quantity,
    TradeProduct,
)
from carthorse.schema.party import (
    URIID,
    BuyerTradeParty,
    EmailURI,
    FaxNumber,
    GlobalID,
    ISO6523SchemeId,
    LegalOrganization,
    PhoneNumber,
    PostalTradeAddress,
    PostalTradeAddressExtended,
    ProductEndUserTradeParty,
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemeId,
    TradeContact,
    URIUniversalCommunication,
)
from carthorse.schema.references import (
    AdditionalReferencedDocument,
    AttachmentBinaryObject,
    BuyerOrderReferencedDocument,
    ContractReferencedDocument,
    ProcuringProject,
    SellerOrderReferencedDocument,
    UltimateCustomerOrderReferencedDocument,
)
from carthorse.schema.settlement import PaymentTerms, TradeSettlement
from carthorse.schema.trade import Trade, TradeLineItem
from carthorse.schema.types import MIME, CategoryCode, UNTDID1001TypeCode


@pt.fixture
def minimum_doc() -> Document:
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.MINIMUM)),
        header=Header(
            id="1234",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date=date(2025, 11, 16),
        ),
        trade=Trade(
            agreement=TradeAgreement(
                seller=SellerTradeParty(
                    name="Foo", address=PostalTradeAddressExtended(country_id="DE")
                ),
                buyer=BuyerTradeParty(
                    name="Bar", address=PostalTradeAddressExtended(country_id="DE")
                ),
            ),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code="EUR",
                monetary_summation=MonetarySummation(
                    # MINIMUM does not have BT-106 (LineTotalAmount).
                    tax_basis_total=Decimal("123.45"),
                    tax_total=[TaxTotal(amount=Decimal("23.46"), currency_id="EUR")],
                    grand_total=Decimal("146.91"),
                    due_amount=Decimal("146.91"),
                ),
            ),
        ),
    )


@pt.fixture
def full_doc() -> Document:
    address1 = PostalTradeAddressExtended(
        country_id="DE",
        postcode="12345",
        line_one="Teststr 1",
        line_two="Second floor",
        line_three="third door",
        city_name="Musterstadt",
        country_subdivision="NRW",
    )
    address2 = PostalTradeAddress(
        country_id="DE",
        postcode="12345",
        line_one="Teststr 1",
        line_two="Second floor",
        line_three="third door",
        city_name="Musterstadt",
    )
    contact = TradeContact(
        person_name="Person",
        department_name="department",
        telephone=PhoneNumber(number="+49 (0) 12345"),
        fax=FaxNumber(number="+49 (0) 54321"),
        email=EmailURI(address="name@domain.de"),
    )
    return Document(
        context=Context(
            test_indicator=True, guideline=GuidelineDocument(id=Profile.EXTENDED)
        ),
        header=Header(
            id="1234",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date=date(2025, 11, 16),
            name="Fooo",
            copyright_indicator=False,
            language_id="de",
            notes=[IncludedNote(content="XXX"), IncludedNote(content="YYY")],
            effective_period=EffectivePeriod(complete=date(2025, 11, 16)),
        ),
        trade=Trade(
            agreement=TradeAgreement(
                buyer_reference="some-reference",
                seller=SellerTradeParty(
                    name="Foo",
                    address=address1,
                    id="1234",
                    global_ids=[GlobalID(id="0234", scheme_id="4321")],
                    description="Some description",
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemeId(id="8765", scheme_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http:example.com", scheme_id="baz")
                    ),
                    tax_registrations=[
                        SpecifiedTaxRegistration(
                            id=TaxSchemeId(id="4321/5432/21", scheme_id="FC")
                        ),
                        SpecifiedTaxRegistration(
                            id=TaxSchemeId(id="DE1234567", scheme_id="VA")
                        ),
                    ],
                ),
                buyer=BuyerTradeParty(
                    name="Bar",
                    address=address1,
                    id="5678",
                    global_ids=[GlobalID(id="5678", scheme_id="6780")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemeId(id="98765", scheme_id="0021"),
                        trade_name="Some other trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http://example.com", scheme_id="baz")
                    ),
                    tax_registrations=[
                        SpecifiedTaxRegistration(
                            id=TaxSchemeId(id="DE76543210", scheme_id="VA")
                        )
                    ],
                ),
                seller_tax_representative_party=SellerTaxRepresentativeTradeParty(
                    name="Foo",
                    address=address1,
                    id="1234",
                    global_ids=[GlobalID(id="0234", scheme_id="4321")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemeId(id="8765", scheme_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http:example.com", scheme_id="baz")
                    ),
                    tax_registrations=SpecifiedTaxRegistration(
                        id=TaxSchemeId(id="DE1234567", scheme_id="VA")
                    ),
                ),
                end_user=ProductEndUserTradeParty(
                    name="End User",
                    id="End1234",
                    global_ids=[GlobalID(id="foo", scheme_id="0012")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemeId(id="8765", scheme_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    address=address1,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="ftp://example.com", scheme_id="ftp")
                    ),
                    tax_registrations=SpecifiedTaxRegistration(
                        id=TaxSchemeId(id="1234/5678/90", scheme_id="FC")
                    ),
                ),
                seller_order=SellerOrderReferencedDocument(issuer_assigned_id="1234"),
                buyer_order=BuyerOrderReferencedDocument(issuer_assigned_id="5678"),
                contract=ContractReferencedDocument(issuer_assigned_id="2468"),
                additional_references=[
                    AdditionalReferencedDocument(
                        issuer_assigned_id="369",
                        uriid="http://example.com",
                        type_code=UNTDID1001TypeCode.Rechnungsdatenblatt,
                        name="XXX",
                        attached_object=AttachmentBinaryObject(
                            mime_code=MIME.pdf,
                            filename="example.pdf",
                            object="some-binary-data",
                        ),
                    ),
                    AdditionalReferencedDocument(
                        issuer_assigned_id="370",
                        uriid="http://example.com",
                        type_code=UNTDID1001TypeCode.Rechnungsdatenblatt,
                        name="XXX",
                        attached_object=AttachmentBinaryObject(
                            mime_code=MIME.pdf,
                            filename="example.pdf",
                            object="some-binary-data",
                        ),
                    ),
                ],
                procuring_project=ProcuringProject(id="FooBar", name="Baz"),
                customer_order=UltimateCustomerOrderReferencedDocument(
                    issuer_assigned_id="some-id", issue_date_time=date(2025, 11, 17)
                ),
            ),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(
                currency_code="EUR",
                monetary_summation=MonetarySummation(
                    line_total=Decimal("123.45"),
                    tax_basis_total=Decimal("123.45"),
                    tax_total=[TaxTotal(amount=Decimal("23.46"), currency_id="EUR")],
                    grand_total=Decimal("146.91"),
                    due_amount=Decimal("146.91"),
                ),
                trade_taxes=[
                    ApplicableTradeTax(
                        calculated_amount=Decimal("23.46"),
                        basis_amount=Decimal("123.45"),
                        category_code=CategoryCode.T_S,
                        due_date_code="5",
                        rate_applicable_percent=Decimal("19"),
                    )
                ],
                terms=PaymentTerms(due=date(2025, 12, 16)),
            ),
            items=[
                TradeLineItem(
                    associated_document=DocumentLineDocument(line_id="1"),
                    product=TradeProduct(name="Widget"),
                    agreement=LineTradeAgreement(
                        net_price=NetTradePrice(charge_amount=Decimal("100.00"))
                    ),
                    delivery=LineTradeDelivery(
                        billed_quantity=Quantity(value=Decimal("1"), unit_code="C62")
                    ),
                    settlement=LineTradeSettlement(
                        applicable_trade_tax=ApplicableTradeTax(
                            category_code=CategoryCode.T_S,
                            due_date_code="5",
                            rate_applicable_percent=Decimal("19"),
                        ),
                        monetary_summation=LineMonetarySummation(
                            line_total=Decimal("123.45")
                        ),
                    ),
                )
            ],
        ),
    )


def test_simple(minimum_doc):
    xml = minimum_doc.to_xml().render(indent=True)
    assert (
        xml
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>
        urn:factur-x.eu:1p0:minimum
      </ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>
      1234
    </ram:ID>
    <ram:TypeCode>
      380
    </ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">
        20251116
      </udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>
          Foo
        </ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>
          Bar
        </ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery />
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>
        EUR
      </ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>
          123.45
        </ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">
          23.46
        </ram:TaxTotalAmount>
        <ram:GrandTotalAmount>
          146.91
        </ram:GrandTotalAmount>
        <ram:DuePayableAmount>
          146.91
        </ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""
    )

    assert Document.from_xml(etree.fromstring(xml.encode())) == minimum_doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == minimum_doc  # noqa: S314  # pyright: ignore[reportArgumentType]


def test_full(full_doc):
    xml = full_doc.to_xml().render(indent=True)
    assert (
        xml
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:TestIndicator>
      <udt:Indicator>
        true
      </udt:Indicator>
    </ram:TestIndicator>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>
        urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended
      </ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>
      1234
    </ram:ID>
    <ram:TypeCode>
      380
    </ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">
        20251116
      </udt:DateTimeString>
    </ram:IssueDateTime>
    <ram:Name>
      Fooo
    </ram:Name>
    <ram:CopyIndicator>
      <udt:Indicator>
        false
      </udt:Indicator>
    </ram:CopyIndicator>
    <ram:LanguageID>
      de
    </ram:LanguageID>
    <ram:IncludedNote>
      <ram:Content>
        XXX
      </ram:Content>
    </ram:IncludedNote>
    <ram:IncludedNote>
      <ram:Content>
        YYY
      </ram:Content>
    </ram:IncludedNote>
    <ram:EffectiveSpecifiedPeriod>
      <ram:CompleteDateTime>
        <udt:DateTimeString format="102">
          20251116
        </udt:DateTimeString>
      </ram:CompleteDateTime>
    </ram:EffectiveSpecifiedPeriod>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>
          Foo
        </ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
          <ram:PostcodeCode>
            12345
          </ram:PostcodeCode>
          <ram:LineOne>
            Teststr 1
          </ram:LineOne>
          <ram:LineTwo>
            Second floor
          </ram:LineTwo>
          <ram:LineThree>
            third door
          </ram:LineThree>
          <ram:CityName>
            Musterstadt
          </ram:CityName>
          <ram:CountrySubDivisionName>
            NRW
          </ram:CountrySubDivisionName>
        </ram:PostalTradeAddress>
        <ram:ID>
          1234
        </ram:ID>
        <ram:GlobalID schemeID="4321">
          0234
        </ram:GlobalID>
        <ram:Description>
          Some description
        </ram:Description>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemeID="0021">
            8765
          </ram:ID>
          <ram:TradingBusinessName>
            Some trade name
          </ram:TradingBusinessName>
          <ram:PostalTradeAddress>
            <ram:CountryID>
              DE
            </ram:CountryID>
            <ram:PostcodeCode>
              12345
            </ram:PostcodeCode>
            <ram:LineOne>
              Teststr 1
            </ram:LineOne>
            <ram:LineTwo>
              Second floor
            </ram:LineTwo>
            <ram:LineThree>
              third door
            </ram:LineThree>
            <ram:CityName>
              Musterstadt
            </ram:CityName>
          </ram:PostalTradeAddress>
        </ram:SpecifiedLegalOrganization>
        <ram:DefinedTradeContact>
          <ram:PersonName>
            Person
          </ram:PersonName>
          <ram:DepartmentName>
            department
          </ram:DepartmentName>
          <ram:TelephoneUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 12345
            </ram:CompleteNumber>
          </ram:TelephoneUniversalCommunication>
          <ram:FaxUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 54321
            </ram:CompleteNumber>
          </ram:FaxUniversalCommunication>
          <ram:EmailURIUniversalCommunication>
            <ram:URIID>
              name@domain.de
            </ram:URIID>
          </ram:EmailURIUniversalCommunication>
        </ram:DefinedTradeContact>
        <ram:URIUniversalCommunication>
          <ram:URIID schemeID="baz">
            http:example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="FC">
            4321/5432/21
          </ram:ID>
        </ram:SpecifiedTaxRegistration>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">
            DE1234567
          </ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>
          Bar
        </ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
          <ram:PostcodeCode>
            12345
          </ram:PostcodeCode>
          <ram:LineOne>
            Teststr 1
          </ram:LineOne>
          <ram:LineTwo>
            Second floor
          </ram:LineTwo>
          <ram:LineThree>
            third door
          </ram:LineThree>
          <ram:CityName>
            Musterstadt
          </ram:CityName>
          <ram:CountrySubDivisionName>
            NRW
          </ram:CountrySubDivisionName>
        </ram:PostalTradeAddress>
        <ram:ID>
          5678
        </ram:ID>
        <ram:GlobalID schemeID="6780">
          5678
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemeID="0021">
            98765
          </ram:ID>
          <ram:TradingBusinessName>
            Some other trade name
          </ram:TradingBusinessName>
          <ram:PostalTradeAddress>
            <ram:CountryID>
              DE
            </ram:CountryID>
            <ram:PostcodeCode>
              12345
            </ram:PostcodeCode>
            <ram:LineOne>
              Teststr 1
            </ram:LineOne>
            <ram:LineTwo>
              Second floor
            </ram:LineTwo>
            <ram:LineThree>
              third door
            </ram:LineThree>
            <ram:CityName>
              Musterstadt
            </ram:CityName>
          </ram:PostalTradeAddress>
        </ram:SpecifiedLegalOrganization>
        <ram:DefinedTradeContact>
          <ram:PersonName>
            Person
          </ram:PersonName>
          <ram:DepartmentName>
            department
          </ram:DepartmentName>
          <ram:TelephoneUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 12345
            </ram:CompleteNumber>
          </ram:TelephoneUniversalCommunication>
          <ram:FaxUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 54321
            </ram:CompleteNumber>
          </ram:FaxUniversalCommunication>
          <ram:EmailURIUniversalCommunication>
            <ram:URIID>
              name@domain.de
            </ram:URIID>
          </ram:EmailURIUniversalCommunication>
        </ram:DefinedTradeContact>
        <ram:URIUniversalCommunication>
          <ram:URIID schemeID="baz">
            http://example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">
            DE76543210
          </ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:BuyerTradeParty>
      <ram:BuyerReference>
        some-reference
      </ram:BuyerReference>
      <ram:SellerTaxRepresentativeTradeParty>
        <ram:Name>
          Foo
        </ram:Name>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
          <ram:PostcodeCode>
            12345
          </ram:PostcodeCode>
          <ram:LineOne>
            Teststr 1
          </ram:LineOne>
          <ram:LineTwo>
            Second floor
          </ram:LineTwo>
          <ram:LineThree>
            third door
          </ram:LineThree>
          <ram:CityName>
            Musterstadt
          </ram:CityName>
          <ram:CountrySubDivisionName>
            NRW
          </ram:CountrySubDivisionName>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">
            DE1234567
          </ram:ID>
        </ram:SpecifiedTaxRegistration>
        <ram:ID>
          1234
        </ram:ID>
        <ram:GlobalID schemeID="4321">
          0234
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemeID="0021">
            8765
          </ram:ID>
          <ram:TradingBusinessName>
            Some trade name
          </ram:TradingBusinessName>
          <ram:PostalTradeAddress>
            <ram:CountryID>
              DE
            </ram:CountryID>
            <ram:PostcodeCode>
              12345
            </ram:PostcodeCode>
            <ram:LineOne>
              Teststr 1
            </ram:LineOne>
            <ram:LineTwo>
              Second floor
            </ram:LineTwo>
            <ram:LineThree>
              third door
            </ram:LineThree>
            <ram:CityName>
              Musterstadt
            </ram:CityName>
          </ram:PostalTradeAddress>
        </ram:SpecifiedLegalOrganization>
        <ram:DefinedTradeContact>
          <ram:PersonName>
            Person
          </ram:PersonName>
          <ram:DepartmentName>
            department
          </ram:DepartmentName>
          <ram:TelephoneUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 12345
            </ram:CompleteNumber>
          </ram:TelephoneUniversalCommunication>
          <ram:FaxUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 54321
            </ram:CompleteNumber>
          </ram:FaxUniversalCommunication>
          <ram:EmailURIUniversalCommunication>
            <ram:URIID>
              name@domain.de
            </ram:URIID>
          </ram:EmailURIUniversalCommunication>
        </ram:DefinedTradeContact>
        <ram:URIUniversalCommunication>
          <ram:URIID schemeID="baz">
            http:example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
      </ram:SellerTaxRepresentativeTradeParty>
      <ram:ProductEndUserTradeParty>
        <ram:Name>
          End User
        </ram:Name>
        <ram:ID>
          End1234
        </ram:ID>
        <ram:GlobalID schemeID="0012">
          foo
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemeID="0021">
            8765
          </ram:ID>
          <ram:TradingBusinessName>
            Some trade name
          </ram:TradingBusinessName>
          <ram:PostalTradeAddress>
            <ram:CountryID>
              DE
            </ram:CountryID>
            <ram:PostcodeCode>
              12345
            </ram:PostcodeCode>
            <ram:LineOne>
              Teststr 1
            </ram:LineOne>
            <ram:LineTwo>
              Second floor
            </ram:LineTwo>
            <ram:LineThree>
              third door
            </ram:LineThree>
            <ram:CityName>
              Musterstadt
            </ram:CityName>
          </ram:PostalTradeAddress>
        </ram:SpecifiedLegalOrganization>
        <ram:DefinedTradeContact>
          <ram:PersonName>
            Person
          </ram:PersonName>
          <ram:DepartmentName>
            department
          </ram:DepartmentName>
          <ram:TelephoneUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 12345
            </ram:CompleteNumber>
          </ram:TelephoneUniversalCommunication>
          <ram:FaxUniversalCommunication>
            <ram:CompleteNumber>
              +49 (0) 54321
            </ram:CompleteNumber>
          </ram:FaxUniversalCommunication>
          <ram:EmailURIUniversalCommunication>
            <ram:URIID>
              name@domain.de
            </ram:URIID>
          </ram:EmailURIUniversalCommunication>
        </ram:DefinedTradeContact>
        <ram:PostalTradeAddress>
          <ram:CountryID>
            DE
          </ram:CountryID>
          <ram:PostcodeCode>
            12345
          </ram:PostcodeCode>
          <ram:LineOne>
            Teststr 1
          </ram:LineOne>
          <ram:LineTwo>
            Second floor
          </ram:LineTwo>
          <ram:LineThree>
            third door
          </ram:LineThree>
          <ram:CityName>
            Musterstadt
          </ram:CityName>
          <ram:CountrySubDivisionName>
            NRW
          </ram:CountrySubDivisionName>
        </ram:PostalTradeAddress>
        <ram:URIUniversalCommunication>
          <ram:URIID schemeID="ftp">
            ftp://example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="FC">
            1234/5678/90
          </ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:ProductEndUserTradeParty>
      <ram:SellerOrderReferencedDocument>
        <ram:IssuerAssignedID>
          1234
        </ram:IssuerAssignedID>
      </ram:SellerOrderReferencedDocument>
      <ram:BuyerOrderReferencedDocument>
        <ram:IssuerAssignedID>
          5678
        </ram:IssuerAssignedID>
      </ram:BuyerOrderReferencedDocument>
      <ram:ContractReferencedDocument>
        <ram:IssuerAssignedID>
          2468
        </ram:IssuerAssignedID>
      </ram:ContractReferencedDocument>
      <ram:AdditionalReferencedDocument>
        <ram:IssuerAssignedID>
          369
        </ram:IssuerAssignedID>
        <ram:URIID>
          http://example.com
        </ram:URIID>
        <ram:TypeCode>
          130
        </ram:TypeCode>
        <ram:Name>
          XXX
        </ram:Name>
        <ram:AttachmentBinaryObject mimeCode="application/pdf" filename="example.pdf">
          some-binary-data
        </ram:AttachmentBinaryObject>
      </ram:AdditionalReferencedDocument>
      <ram:AdditionalReferencedDocument>
        <ram:IssuerAssignedID>
          370
        </ram:IssuerAssignedID>
        <ram:URIID>
          http://example.com
        </ram:URIID>
        <ram:TypeCode>
          130
        </ram:TypeCode>
        <ram:Name>
          XXX
        </ram:Name>
        <ram:AttachmentBinaryObject mimeCode="application/pdf" filename="example.pdf">
          some-binary-data
        </ram:AttachmentBinaryObject>
      </ram:AdditionalReferencedDocument>
      <ram:SpecifiedProcuringProject>
        <ram:ID>
          FooBar
        </ram:ID>
        <ram:Name>
          Baz
        </ram:Name>
      </ram:SpecifiedProcuringProject>
      <ram:UltimateCustomerOrderReferencedDocument>
        <ram:IssuerAssignedID>
          some-id
        </ram:IssuerAssignedID>
        <ram:FormattedIssueDateTime>
          <qdt:DateTimeString format="102">
            20251117
          </qdt:DateTimeString>
        </ram:FormattedIssueDateTime>
      </ram:UltimateCustomerOrderReferencedDocument>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery />
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>
        EUR
      </ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>
          123.45
        </ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount>
          123.45
        </ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">
          23.46
        </ram:TaxTotalAmount>
        <ram:GrandTotalAmount>
          146.91
        </ram:GrandTotalAmount>
        <ram:DuePayableAmount>
          146.91
        </ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
      <ram:ApplicableTradeTax>
        <ram:CalculatedAmount>
          23.46
        </ram:CalculatedAmount>
        <ram:TypeCode>
          VAT
        </ram:TypeCode>
        <ram:BasisAmount>
          123.45
        </ram:BasisAmount>
        <ram:CategoryCode>
          S
        </ram:CategoryCode>
        <ram:DueDateTypeCode>
          5
        </ram:DueDateTypeCode>
        <ram:RateApplicablePercent>
          19
        </ram:RateApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradePaymentTerms>
        <ram:DueDateDateTime>
          <udt:DateTimeString format="102">
            20251216
          </udt:DateTimeString>
        </ram:DueDateDateTime>
      </ram:SpecifiedTradePaymentTerms>
    </ram:ApplicableHeaderTradeSettlement>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument>
        <ram:LineID>
          1
        </ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedTradeProduct>
        <ram:Name>
          Widget
        </ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice>
          <ram:ChargeAmount>
            100.00
          </ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <ram:BilledQuantity unitCode="C62">
          1
        </ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>
            VAT
          </ram:TypeCode>
          <ram:CategoryCode>
            S
          </ram:CategoryCode>
          <ram:DueDateTypeCode>
            5
          </ram:DueDateTypeCode>
          <ram:RateApplicablePercent>
            19
          </ram:RateApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>
            123.45
          </ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""
    )
    assert Document.from_xml(etree.fromstring(xml.encode())) == full_doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == full_doc  # noqa: S314    # pyright: ignore[reportArgumentType]


def test_br_16_error(full_doc: Document):
    full_doc.trade.items.clear()

    with pt.raises(ValidationError) as e:
        full_doc.validate()

    assert e.value.code == "BR-16"

    full_doc.context.guideline.id = Profile.MINIMUM
    full_doc.validate()
    full_doc.context.guideline.id = Profile.BASIC_WL
    full_doc.validate()


_NS_DECL = (
    'xmlns:ram="urn:un:unece:uncefact:data:standard:'
    'ReusableAggregateBusinessInformationEntity:100" '
    'xmlns:udt="urn:un:unece:uncefact:data:standard:'
    'UnqualifiedDataType:100"'
)


def _wrap_subtree(rendered: str, root_tag: str) -> bytes:
    """Inject the ram/udt namespace bindings on the root element so a
    sub-tree rendered via ``Element.to_xml_internal`` parses standalone."""
    return rendered.replace(
        f"<ram:{root_tag}>", f"<ram:{root_tag} {_NS_DECL}>", 1
    ).encode()


def test_exemption_reason_code_uses_distinct_tag():
    """BT-121 (ExemptionReasonCode) must round-trip independently of BT-120
    (ExemptionReason). Bug sweep #3."""
    tax = ApplicableTradeTax(
        calculated_amount=Decimal("0.00"),
        basis_amount=Decimal("0.00"),
        category_code=CategoryCode.T_E,
        due_date_code="5",
        exemption_reason="exempt-text",
        exemption_reason_code="VATEX-EU-79-C",
    )
    xml = tax.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    assert "<ram:ExemptionReason>" in xml
    assert "<ram:ExemptionReasonCode>" in xml
    parsed = ApplicableTradeTax.from_xml(  # pyright: ignore[reportArgumentType]
        etree.fromstring(_wrap_subtree(xml, "ApplicableTradeTax"))
    )
    assert parsed == tax


def test_trade_allowance_charge_basis_amount_uses_correct_tag():
    """BT-93 (BasisAmount) must render under <ram:BasisAmount>, not
    <ram:CalculationPercent>. Bug sweep #4."""
    from carthorse.schema.accounting import CategoryTradeTax, TradeAllowanceCharge

    ac = TradeAllowanceCharge(
        indicator=False,
        actual_amount=Decimal("5.00"),
        category_trade_tax=CategoryTradeTax(
            category_code=CategoryCode.T_S, rate_applicable_percent=Decimal("19")
        ),
        calculation_percent=Decimal("5"),
        basis_amount=Decimal("100.00"),
        reason="x",
    )
    xml = ac.to_xml_internal(Profile.COMFORT).render(indent=True)
    assert "<ram:BasisAmount>" in xml
    assert "<ram:CalculationPercent>" in xml
    parsed = TradeAllowanceCharge.from_xml(  # pyright: ignore[reportArgumentType]
        etree.fromstring(_wrap_subtree(xml, "SpecifiedTradeAllowanceCharge"))
    )
    assert parsed == ac


def test_monetary_summation_two_tax_totals():
    """BG-22 may carry both BT-110 (invoice currency) and BT-111 (VAT
    accounting currency) as ``TaxTotalAmount`` siblings. Bug sweep #6."""
    summation = MonetarySummation(
        line_total=Decimal("100.00"),
        tax_basis_total=Decimal("100.00"),
        tax_total=[
            TaxTotal(amount=Decimal("19.00"), currency_id="EUR"),
            TaxTotal(amount=Decimal("20.45"), currency_id="USD"),
        ],
        grand_total=Decimal("119.00"),
        due_amount=Decimal("119.00"),
    )
    xml = summation.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    # Both currency-tagged amounts must appear in the wire output.
    assert xml.count("<ram:TaxTotalAmount") == 2
    assert 'currencyID="EUR"' in xml
    assert 'currencyID="USD"' in xml
    parsed = MonetarySummation.from_xml(  # pyright: ignore[reportArgumentType]
        etree.fromstring(
            _wrap_subtree(xml, "SpecifiedTradeSettlementHeaderMonetarySummation")
        )
    )
    assert parsed == summation


def test_amount_currency_id_round_trips():
    """``currencyID`` attributes on udt:AmountType elements survive a
    parse → render round-trip even though carthorse does not expose
    them as dataclass fields. Bug sweep #7."""
    src = (
        "<ram:SpecifiedTradeSettlementHeaderMonetarySummation "
        'xmlns:ram="urn:un:unece:uncefact:data:standard:'
        'ReusableAggregateBusinessInformationEntity:100" '
        'xmlns:udt="urn:un:unece:uncefact:data:standard:'
        'UnqualifiedDataType:100">\n'
        '  <ram:LineTotalAmount currencyID="EUR">100.00</ram:LineTotalAmount>\n'
        '  <ram:TaxBasisTotalAmount currencyID="EUR">100.00</ram:TaxBasisTotalAmount>\n'
        '  <ram:TaxTotalAmount currencyID="EUR">19.00</ram:TaxTotalAmount>\n'
        '  <ram:GrandTotalAmount currencyID="EUR">119.00</ram:GrandTotalAmount>\n'
        '  <ram:DuePayableAmount currencyID="EUR">119.00</ram:DuePayableAmount>\n'
        "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
    )
    parsed = MonetarySummation.from_xml(etree.fromstring(src.encode()))  # pyright: ignore[reportArgumentType]
    out = parsed.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    # Every amount element keeps its currencyID="EUR" attribute.
    assert out.count('currencyID="EUR"') == 5


def test_billing_specified_period_round_trips():
    """BG-14 BillingSpecifiedPeriod with start + end round-trips."""
    from carthorse.schema.settlement import BillingSpecifiedPeriod

    period = BillingSpecifiedPeriod(start=date(2025, 1, 1), end=date(2025, 1, 31))
    xml = period.to_xml_internal(Profile.BASIC_WL).render(indent=True)
    assert "<ram:BillingSpecifiedPeriod>" in xml
    assert "<ram:StartDateTime>" in xml
    assert "<ram:EndDateTime>" in xml
    parsed = BillingSpecifiedPeriod.from_xml(  # pyright: ignore[reportArgumentType]
        etree.fromstring(_wrap_subtree(xml, "BillingSpecifiedPeriod"))
    )
    assert parsed == period


def test_billing_specified_period_br_co_19_at_least_one_endpoint():
    """BG-14 with neither start nor end set raises BR-CO-19."""
    from carthorse.schema.settlement import BillingSpecifiedPeriod

    period = BillingSpecifiedPeriod()
    with pt.raises(ValidationError) as e:
        period.validate_internal(Profile.BASIC_WL)
    assert e.value.code == "BR-CO-19"


def test_billing_specified_period_br_29_end_after_start():
    """BG-14 with end < start raises BR-29."""
    from carthorse.schema.settlement import BillingSpecifiedPeriod

    period = BillingSpecifiedPeriod(start=date(2025, 2, 1), end=date(2025, 1, 1))
    with pt.raises(ValidationError) as e:
        period.validate_internal(Profile.BASIC_WL)
    assert e.value.code == "BR-29"


def test_tax_currency_code_requires_matching_tax_total():
    """If BT-6 (TaxCurrencyCode) is set, MonetarySummation must carry a
    TaxTotal whose currency_id == BT-6 (BR-53)."""
    from carthorse.schema.settlement import TradeSettlement

    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id="EUR")],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        tax_currency_code="USD",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=PaymentTerms(due=date(2025, 12, 16)),
    )
    with pt.raises(ValidationError) as e:
        settlement.validate_internal(Profile.BASIC_WL)
    assert e.value.code == "BR-53"

    # With matching second TaxTotal it passes.
    settlement.monetary_summation.tax_total = [
        TaxTotal(amount=Decimal("19"), currency_id="EUR"),
        TaxTotal(amount=Decimal("20.45"), currency_id="USD"),
    ]
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_9_vat_id_country_prefix():
    """BR-CO-9: VAT identifiers must start with an ISO 3166-1 alpha-2
    country prefix (with EL allowed for Greece)."""
    bad = TaxSchemeId(id="1234567890", scheme_id="VA")
    with pt.raises(ValidationError) as e:
        bad.validate_internal(Profile.MINIMUM)
    assert e.value.code == "BR-CO-9"

    # Local tax identifiers (FC) are exempt — their codes are national.
    TaxSchemeId(id="201/113/40209", scheme_id="FC").validate_internal(Profile.MINIMUM)

    # German VAT prefix is fine.
    TaxSchemeId(id="DE123456789", scheme_id="VA").validate_internal(Profile.MINIMUM)
    # Greek 'EL' prefix is fine.
    TaxSchemeId(id="EL123456789", scheme_id="VA").validate_internal(Profile.MINIMUM)


def test_br_co_25_payment_terms_required_when_due():
    """BR-CO-25: positive DuePayableAmount requires terms.due or
    terms.description to be set."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id="EUR")],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )

    # No terms → BR-CO-25.
    settlement = TradeSettlement(currency_code="EUR", monetary_summation=summation)
    with pt.raises(ValidationError) as e:
        settlement.validate_internal(Profile.MINIMUM)
    assert e.value.code == "BR-CO-25"

    # terms.due present → ok.
    settlement.terms = PaymentTerms(due=date(2025, 12, 16))
    settlement.validate_internal(Profile.MINIMUM)

    # terms.description present, no due → ok.
    settlement.terms = PaymentTerms(description="Net 30 days")
    settlement.validate_internal(Profile.MINIMUM)

    # due_amount = 0 → no requirement. Also adjust grand_total to keep
    # BR-CO-16 (BT-115 == BT-112 - BT-113) satisfied.
    summation.due_amount = Decimal("0")
    summation.grand_total = Decimal("0")
    summation.tax_basis_total = Decimal("0")
    summation.tax_total = None
    settlement.terms = None
    settlement.validate_internal(Profile.MINIMUM)


def test_br_co_26_seller_must_be_identifiable():
    """BR-CO-26: at least one of BT-29 (Seller.id),
    BT-30 (Seller.legal_organization.id) or BT-31
    (Seller.tax_registrations[VAT]) must be present."""
    addr = PostalTradeAddressExtended(country_id="DE")

    # No identifier — fails.
    seller = SellerTradeParty(name="Acme", address=addr)
    with pt.raises(ValidationError) as e:
        seller.validate_internal(Profile.MINIMUM)
    assert e.value.code == "BR-CO-26"

    # BT-29 set — ok.
    seller.id = "S-1234"
    seller.validate_internal(Profile.MINIMUM)

    # BT-30 set (no BT-29) — ok.
    seller.id = None
    seller.legal_organization = LegalOrganization(
        id=ISO6523SchemeId(id="0123456789", scheme_id="0021")
    )
    seller.validate_internal(Profile.MINIMUM)

    # BT-31 set (no BT-29, no BT-30) — ok.
    seller.legal_organization = None
    seller.tax_registrations = [
        SpecifiedTaxRegistration(id=TaxSchemeId(id="DE123456789", scheme_id="VA"))
    ]
    seller.validate_internal(Profile.MINIMUM)

    # Only FC tax registration (no VA) doesn't satisfy BR-CO-26.
    seller.tax_registrations = [
        SpecifiedTaxRegistration(id=TaxSchemeId(id="201/113/40209", scheme_id="FC"))
    ]
    with pt.raises(ValidationError) as e:
        seller.validate_internal(Profile.MINIMUM)
    assert e.value.code == "BR-CO-26"


def test_br_co_3_tax_point_date_and_due_date_code_mutually_exclusive():
    """BR-CO-3: BT-7 (TaxPointDate) and BT-8 (DueDateTypeCode) are
    mutually exclusive on a single ApplicableTradeTax."""
    tax = ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        tax_point_date=date(2025, 1, 15),
        due_date_code="5",  # also setting BT-8 → conflict
        rate_applicable_percent=Decimal("19"),
    )
    with pt.raises(ValidationError) as e:
        tax.validate_internal(Profile.COMFORT)
    assert e.value.code == "BR-CO-3"

    # Either alone is fine.
    ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        tax_point_date=date(2025, 1, 15),
        rate_applicable_percent=Decimal("19"),
    ).validate_internal(Profile.COMFORT)
    ApplicableTradeTax(
        category_code=CategoryCode.T_S,
        due_date_code="5",
        rate_applicable_percent=Decimal("19"),
    ).validate_internal(Profile.COMFORT)


def test_br_co_15_grand_total_equals_tax_basis_plus_tax_total():
    """BR-CO-15: GrandTotalAmount (BT-112) = TaxBasisTotalAmount (BT-109)
    + TaxTotalAmount in invoice currency (BT-110)."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id="EUR")],
        grand_total=Decimal("999"),  # WRONG — should be 119
        due_amount=Decimal("999"),
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=PaymentTerms(due=date(2025, 2, 1)),
    )
    with pt.raises(ValidationError) as e:
        settlement.validate_internal(Profile.BASIC_WL)
    assert e.value.code == "BR-CO-15"

    # Fix the math → passes.
    summation.grand_total = Decimal("119")
    summation.due_amount = Decimal("119")
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_15_with_no_tax_total_treats_bt_110_as_zero():
    """When BT-110 is absent (e.g. a tax-exempt invoice), BR-CO-15
    reduces to BT-112 == BT-109."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=None,
        grand_total=Decimal("100"),
        due_amount=Decimal("100"),
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                category_code=CategoryCode.T_E,
                due_date_code="5",
                rate_applicable_percent=Decimal("0"),
                exemption_reason="Exempt",
            )
        ],
        terms=PaymentTerms(due=date(2025, 2, 1)),
    )
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_15_uses_only_invoice_currency_tax_total():
    """The BT-111 row (currency != BT-5) is not part of BR-CO-15."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[
            TaxTotal(amount=Decimal("19"), currency_id="EUR"),  # BT-110
            TaxTotal(amount=Decimal("20"), currency_id="USD"),  # BT-111
        ],
        grand_total=Decimal("119"),  # 100 + 19 only
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        tax_currency_code="USD",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=PaymentTerms(due=date(2025, 2, 1)),
    )
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_16_due_amount_equals_grand_total_minus_prepaid():
    """BR-CO-16: DuePayableAmount (BT-115) = GrandTotal (BT-112)
    - PrepaidTotal (BT-113) + RoundingAmount (BT-114). BT-114 isn't
    yet modelled in carthorse; treat it as 0."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id="EUR")],
        grand_total=Decimal("119"),
        prepaid_total=Decimal("19"),
        due_amount=Decimal("999"),  # WRONG — expected 100
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=PaymentTerms(due=date(2025, 2, 1)),
    )
    with pt.raises(ValidationError) as e:
        settlement.validate_internal(Profile.BASIC_WL)
    assert e.value.code == "BR-CO-16"

    summation.due_amount = Decimal("100")
    settlement.validate_internal(Profile.BASIC_WL)


def test_br_co_16_no_prepaid_total_means_due_equals_grand():
    """When BT-113 is absent (default 0), BR-CO-16 reduces to
    BT-115 == BT-112."""
    summation = MonetarySummation(
        line_total=Decimal("100"),
        tax_basis_total=Decimal("100"),
        tax_total=[TaxTotal(amount=Decimal("19"), currency_id="EUR")],
        grand_total=Decimal("119"),
        due_amount=Decimal("119"),
    )
    settlement = TradeSettlement(
        currency_code="EUR",
        monetary_summation=summation,
        trade_taxes=[
            ApplicableTradeTax(
                calculated_amount=Decimal("19"),
                basis_amount=Decimal("100"),
                category_code=CategoryCode.T_S,
                due_date_code="5",
                rate_applicable_percent=Decimal("19"),
            )
        ],
        terms=PaymentTerms(due=date(2025, 2, 1)),
    )
    settlement.validate_internal(Profile.BASIC_WL)
