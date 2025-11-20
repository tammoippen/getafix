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
from carthorse.schema.agreement import TradeAgreement
from carthorse.schema.delivery import TradeDelivery
from carthorse.schema.element import ValidationError
from carthorse.schema.party import (
    URIID,
    BuyerTradeParty,
    EmailURI,
    FaxNumber,
    GlobalID,
    ISO6523SchemaId,
    LegalOrganization,
    PhoneNumber,
    PostalTradeAddress,
    PostalTradeAddressExtended,
    ProductEndUserTradeParty,
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemaId,
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
from carthorse.schema.settlement import MonetarySummation, TaxTotal, TradeSettlement
from carthorse.schema.trade import Trade, TradeLineItem
from carthorse.schema.types import MIME, UNTDID1001TypeCode


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
                    line_total=Decimal("123.45"),
                    tax_basis_total=Decimal("123.45"),
                    tax_total=TaxTotal(amount=Decimal("23.46"), currency_id="EUR"),
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
                    global_ids=[GlobalID(id="0234", schema_id="4321")],
                    description="Some description",
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemaId(id="8765", schema_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http:example.com", schema_id="baz")
                    ),
                    tax_registrations=[
                        SpecifiedTaxRegistration(
                            id=TaxSchemaId(id="4321/5432/21", schema_id="FC")
                        ),
                        SpecifiedTaxRegistration(
                            id=TaxSchemaId(id="DE1234567", schema_id="VA")
                        ),
                    ],
                ),
                buyer=BuyerTradeParty(
                    name="Bar",
                    address=address1,
                    id="5678",
                    global_ids=[GlobalID(id="5678", schema_id="6780")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemaId(id="98765", schema_id="0021"),
                        trade_name="Some other trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http://example.com", schema_id="baz")
                    ),
                    tax_registrations=SpecifiedTaxRegistration(
                        id=TaxSchemaId(id="DE76543210", schema_id="VA")
                    ),
                ),
                seller_tax_representative_party=SellerTaxRepresentativeTradeParty(
                    name="Foo",
                    address=address1,
                    id="1234",
                    global_ids=[GlobalID(id="0234", schema_id="4321")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemaId(id="8765", schema_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="http:example.com", schema_id="baz")
                    ),
                    tax_registrations=SpecifiedTaxRegistration(
                        id=TaxSchemaId(id="DE1234567", schema_id="VA")
                    ),
                ),
                end_user=ProductEndUserTradeParty(
                    name="End User",
                    id="End1234",
                    global_ids=[GlobalID(id="foo", schema_id="0012")],
                    legal_organization=LegalOrganization(
                        id=ISO6523SchemaId(id="8765", schema_id="0021"),
                        trade_name="Some trade name",
                        trade_address=address2,
                    ),
                    contact=contact,
                    address=address1,
                    electronic_address=URIUniversalCommunication(
                        uri_id=URIID(id="ftp://example.com", schema_id="ftp")
                    ),
                    tax_registrations=SpecifiedTaxRegistration(
                        id=TaxSchemaId(id="1234/5678/90", schema_id="FC")
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
                    tax_total=TaxTotal(amount=Decimal("23.46"), currency_id="EUR"),
                    grand_total=Decimal("146.91"),
                    due_amount=Decimal("146.91"),
                ),
            ),
            items=[TradeLineItem()],
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
        <ram:GlobalID schemaID="4321">
          0234
        </ram:GlobalID>
        <ram:Description>
          Some description
        </ram:Description>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemaID="0021">
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
          <ram:URIID schemaID="baz">
            http:example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:GlobalID schemaID="FC">
            4321/5432/21
          </ram:GlobalID>
        </ram:SpecifiedTaxRegistration>
        <ram:SpecifiedTaxRegistration>
          <ram:GlobalID schemaID="VA">
            DE1234567
          </ram:GlobalID>
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
        <ram:GlobalID schemaID="6780">
          5678
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemaID="0021">
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
          <ram:URIID schemaID="baz">
            http://example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:GlobalID schemaID="VA">
            DE76543210
          </ram:GlobalID>
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
          <ram:GlobalID schemaID="VA">
            DE1234567
          </ram:GlobalID>
        </ram:SpecifiedTaxRegistration>
        <ram:ID>
          1234
        </ram:ID>
        <ram:GlobalID schemaID="4321">
          0234
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemaID="0021">
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
          <ram:URIID schemaID="baz">
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
        <ram:GlobalID schemaID="0012">
          foo
        </ram:GlobalID>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemaID="0021">
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
          <ram:URIID schemaID="ftp">
            ftp://example.com
          </ram:URIID>
        </ram:URIUniversalCommunication>
        <ram:SpecifiedTaxRegistration>
          <ram:GlobalID schemaID="FC">
            1234/5678/90
          </ram:GlobalID>
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
          <udt:DateTimeString format="102">
            20251117
          </udt:DateTimeString>
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
    </ram:ApplicableHeaderTradeSettlement>
    <ram:IncludedSupplyChainTradeLineItem />
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""
    )
    assert Document.from_xml(etree.fromstring(xml.encode())) == full_doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == full_doc  # noqa: S314    # pyright: ignore[reportArgumentType]


def test_br_16_error(minimum_doc: Document):
    minimum_doc.context.guideline.id = Profile.BASIC
    minimum_doc.trade.items.clear()

    with pt.raises(ValidationError) as e:
        minimum_doc.validate()

    assert e.value.code == "BR-16"

    minimum_doc.context.guideline.id = Profile.MINIMUM
    minimum_doc.validate()
    minimum_doc.context.guideline.id = Profile.BASIC_WL
    minimum_doc.validate()
