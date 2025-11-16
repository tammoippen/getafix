import xml.etree.ElementTree as other_etree
from datetime import date

import lxml.etree as etree

from carthorse.schema._defs import Profile, TypeCode
from carthorse.schema.document import (
    Context,
    Document,
    EffectivePeriod,
    GuidelineDocumentContextParameter,
    Header,
    Note,
)


def test_simple():
    doc = Document(
        context=Context(
            guideline_parameter=GuidelineDocumentContextParameter(id=Profile.BASIC)
        ),
        header=Header(
            id="1234",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date_time=date(2025, 11, 16),
        ),
    )

    xml = doc.to_xml(Profile.BASIC).render(indent=True)
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
</rsm:CrossIndustryInvoiceType>
"""
    )

    assert Document.from_xml(etree.fromstring(xml.encode())) == doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == doc  # noqa: S314  # pyright: ignore[reportArgumentType]


def test_full():
    doc = Document(
        context=Context(
            test_indicator=True,
            guideline_parameter=GuidelineDocumentContextParameter(id=Profile.EXTENDED),
        ),
        header=Header(
            id="1234",
            type_code=TypeCode.T_Handelsrechnung,
            issue_date_time=date(2025, 11, 16),
            name="Fooo",
            copyright_indicator=False,
            language_id="de",
            notes=[
                Note(content="XXX"),
                Note(content="YYY"),
            ],
            effective_period=EffectivePeriod(complete=date(2025, 11, 16)),
        ),
    )

    xml = doc.to_xml(Profile.EXTENDED).render(indent=True)
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
</rsm:CrossIndustryInvoiceType>
"""
    )
    assert Document.from_xml(etree.fromstring(xml.encode())) == doc  # pyright: ignore[reportArgumentType]
    assert Document.from_xml(other_etree.fromstring(xml.encode())) == doc  # noqa: S314    # pyright: ignore[reportArgumentType]
