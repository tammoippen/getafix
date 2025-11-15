from carthorse.schema.document import Context, Document, TestIndicator
from carthorse.schema.element import Profile


def test_sample():
    doc = Document(context=Context())

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
</rsm:CrossIndustryInvoiceType>
"""
    )


def test_sample_indicator():
    doc = Document(context=Context(test_indicator=TestIndicator()))

    assert (
        doc.to_xml(Profile.BASIC).render(indent=True)
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
        urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic
      </ram:ID>
    </ram:DocumentContextParameterType>
  </rsm:ExchangedDocumentContext>
</rsm:CrossIndustryInvoiceType>
"""
    )
