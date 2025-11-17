import xml.etree.ElementTree as other_etree
from datetime import date

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
    SellerTaxRepresentativeTradeParty,
    SellerTradeParty,
    SpecifiedTaxRegistration,
    TaxSchemaId,
    TradeContact,
    URIUniversalCommunication,
)
from carthorse.schema.trade import (
    Trade,
    TradeDelivery,
    TradeLineItem,
    TradeSettlement,
)


@pt.fixture
def basic_simple() -> Document:
    return Document(
        context=Context(guideline=GuidelineDocument(id=Profile.BASIC)),
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
            settlement=TradeSettlement(),
            items=[TradeLineItem()],
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
            test_indicator=True,
            guideline=GuidelineDocument(id=Profile.EXTENDED),
        ),
        header=Header(
            id="1234",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date=date(2025, 11, 16),
            name="Fooo",
            copyright_indicator=False,
            language_id="de",
            notes=[
                IncludedNote(content="XXX"),
                IncludedNote(content="YYY"),
            ],
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
            ),
            delivery=TradeDelivery(),
            settlement=TradeSettlement(),
            items=[TradeLineItem()],
        ),
    )


def test_simple(basic_simple):
    xml = basic_simple.to_xml().render(indent=True)
    assert (
        xml
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>
        urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic
      </ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:CrossIndustryInvoiceType>
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
  </rsm:CrossIndustryInvoiceType>
  <ram:SupplyChainTradeTransaction>
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
    <ram:ApplicableHeaderTradeSettlement />
    <ram:IncludedSupplyChainTradeLineItem />
  </ram:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoiceType>
"""
    )

    assert Document.from_xml(etree.fromstring(xml.encode())) == basic_simple  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == basic_simple  # noqa: S314  # pyright: ignore[reportArgumentType]


def test_full(full_doc):
    xml = full_doc.to_xml().render(indent=True)
    assert (
        xml
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
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
  <rsm:CrossIndustryInvoiceType>
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
  </rsm:CrossIndustryInvoiceType>
  <ram:SupplyChainTradeTransaction>
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
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery />
    <ram:ApplicableHeaderTradeSettlement />
    <ram:IncludedSupplyChainTradeLineItem />
  </ram:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoiceType>
"""
    )
    assert Document.from_xml(etree.fromstring(xml.encode())) == full_doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == full_doc  # noqa: S314    # pyright: ignore[reportArgumentType]


def test_br_16_error(basic_simple: Document):
    basic_simple.trade.items.clear()

    with pt.raises(ValidationError) as e:
        basic_simple.validate()

    assert e.value.code == "BR-16"

    basic_simple.context.guideline.id = Profile.MINIMUM
    basic_simple.validate()
    basic_simple.context.guideline.id = Profile.BASIC_WL
    basic_simple.validate()
