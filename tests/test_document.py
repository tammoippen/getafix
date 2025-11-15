from carthorse.schema.document import Context, Document, TestIndicator


def test_sample():
    doc = Document(context=Context())

    assert (
        doc.to_xml().render(indent=True)
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext />
</rsm:CrossIndustryInvoiceType>
"""
    )


def test_sample_indicator():
    doc = Document(context=Context(test_indicator=TestIndicator()))

    assert (
        doc.to_xml().render(indent=True)
        == """\
<?xml version='1.0' encoding='UTF-8' ?>
<rsm:CrossIndustryInvoiceType xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:TestIndicator>
      <udt:Indicator>
        true
      </udt:Indicator>
    </ram:TestIndicator>
  </rsm:ExchangedDocumentContext>
</rsm:CrossIndustryInvoiceType>
"""
    )
