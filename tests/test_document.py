from datetime import date

from carthorse.schema.document import (
    CompleteDateTime,
    Content,
    Context,
    CopyIndicator,
    Document,
    EffectivePeriod,
    Header,
    IssueDateTime,
    LanguageId,
    NameStr,
    Note,
    TestIndicator,
    TypeCodeEnum,
)
from carthorse.schema.element import Profile
from src.carthorse.schema.document import TypeCode
from src.carthorse.schema.fields import StringId


def test_sample():
    doc = Document(
        context=Context(),
        header=Header(
            id=StringId(value="1234"),
            type_code=TypeCode(value=TypeCodeEnum.T_Handelsrechnung),
            issue_date_time=IssueDateTime(value=date(2025, 11, 16)),
        ),
    )

    assert (
        doc.to_xml(Profile.BASIC).render(indent=True)
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:DocumentContextParameterType>
      <ram:ID>
        urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic
      </ram:ID>
    </ram:DocumentContextParameterType>
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


def test_sample_indicator():
    doc = Document(
        context=Context(test_indicator=TestIndicator(value=True)),
        header=Header(
            id=StringId(value="1234"),
            type_code=TypeCode(value=TypeCodeEnum.T_Handelsrechnung),
            issue_date_time=IssueDateTime(value=date(2025, 11, 16)),
            name=NameStr(value="Fooo"),
            copyright_indicator=CopyIndicator(value=False),
            language_id=LanguageId(value="de"),
            notes=[
                Note(content=Content(value="XXX")),
                Note(content=Content(value="YYY")),
            ],
            effective_period=EffectivePeriod(
                complete=CompleteDateTime(value=date(2025, 11, 16))
            ),
        ),
    )

    assert (
        doc.to_xml(Profile.EXTENDED).render(indent=True)
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:TestIndicator>
      <udt:Indicator>
        true
      </udt:Indicator>
    </ram:TestIndicator>
    <ram:DocumentContextParameterType>
      <ram:ID>
        urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended
      </ram:ID>
    </ram:DocumentContextParameterType>
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
