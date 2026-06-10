"""``ram:*ReferencedDocument`` wrappers — cross-references on the invoice.

This module owns every ``*ReferencedDocument`` element on the header,
plus the supporting-document family (BG-24) and its embedded binary
payload. These are the cross-references that point from an invoice
back to upstream documents (purchase order, contract, despatch
advice, …) or forward to downstream supporting material.

Header references by profile:

* MINIMUM: ``BuyerOrderReferencedDocument`` (BT-13-00).
* BASIC_WL: ``ContractReferencedDocument`` (BT-12-00),
  ``DespatchAdviceReferencedDocument`` (BT-16-00),
  ``InvoiceReferencedDocument`` (BG-3).
* COMFORT: ``SellerOrderReferencedDocument`` (BT-14-00),
  ``ReceivingAdviceReferencedDocument`` (BT-15-00),
  ``AdditionalReferencedDocument`` (BG-24) carrying
  ``AttachmentBinaryObject`` (BT-125), ``SpecifiedProcuringProject``
  (BT-11-00).
* EXTENDED: ``DeliveryNoteReferencedDocument`` (BT-X-202-00),
  ``UltimateCustomerOrderReferencedDocument`` (BG-X-23).

No business rules are enforced in this module. ``BR-52`` (every BG-24
entry must carry BT-122) is implicit through ``AdditionalReferencedDocument.issuer_assigned_id``
being a required field.

Line-level twins of the despatch advice, receiving advice and
delivery note references live on ``LineTradeDelivery`` (EXTENDED) and
are tracked in ``docs/STRUCTURES.md §5.1``.
:class:`~getafix.schema.line.LineBuyerOrderReferencedDocument` (BT-132-00)
and :class:`~getafix.schema.line.LineAdditionalReferencedDocument`
(BT-128-00) cover the COMFORT line-level references.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, Self, override

from tagic.xml import XML

from getafix.schema.element import Element, ETElement
from getafix.schema.types import MIME, Profile, UNTDID1001TypeCode


@dataclass(kw_only=True, slots=True)
class BuyerOrderReferencedDocument(Element):
    """Purchase order reference (BT-13-00).

    Detailed information about the referenced purchase order.
    """

    tag: ClassVar[str] = "BuyerOrderReferencedDocument"

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Purchase order reference (BT-13).

    An identifier of a referenced purchase order, issued by the Buyer.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.EXTENDED},
    )
    """Purchase order issue date (BT-13-00 ``FormattedIssueDateTime``);
    EXTENDED-only — the issue date of the referenced purchase order."""


@dataclass(kw_only=True, slots=True)
class SellerOrderReferencedDocument(Element):
    """Sales order reference (BT-14-00).

    Detailed information about the referenced sales order confirmation.
    """

    tag: ClassVar[str] = "SellerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.COMFORT}
    )
    """Sales order reference (BT-14).

    An identifier of a referenced sales order, issued by the Seller.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.EXTENDED},
    )
    """Sales order issue date (BT-14-00 ``FormattedIssueDateTime``);
    EXTENDED-only — the issue date of the referenced sales order."""


@dataclass(kw_only=True, slots=True)
class ContractReferencedDocument(Element):
    """Contract reference (BT-12-00).

    Detailed information about the referenced contract.
    """

    tag: ClassVar[str] = "ContractReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.BASIC_WL}
    )
    """Contract reference (BT-12).

    The identification of a contract.

    Note: the contract identifier should be unique in the context of
    the specific trading relationship and for a defined time period.
    """


@dataclass(kw_only=True, slots=True)
class QuotationReferencedDocument(Element):
    """Header quotation reference (BG-X-61); EXTENDED-only.

    Reference to the quotation that this invoice as a whole responds
    to. Distinct from the per-line
    :class:`~getafix.schema.line.LineQuotationReferencedDocument`
    (BG-X-47). XSD position: between ``BuyerOrderReferencedDocument``
    and ``ContractReferencedDocument``.
    """

    tag: ClassVar[str] = "QuotationReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Quotation document identifier (BT-X-403)."""
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Quotation issue date (BT-X-404, wrapped in BT-X-404-00)."""


@dataclass(kw_only=True, slots=True)
class UltimateCustomerOrderReferencedDocument(Element):
    """Ultimate customer order reference (BG-X-23).

    Detailed information about the final customer order at the end of
    a chain of intermediated purchases. EXTENDED-only.
    """

    tag: ClassVar[str] = "UltimateCustomerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Ultimate customer order number (BT-X-150).

    The Ultimate Customer Order number of the final customer.
    """
    issue_date_time: date = field(metadata={"tag": "FormattedIssueDateTime"})
    """Ultimate customer order date (BT-X-151-00).

    The date when the ultimate customer order was issued.
    """


@dataclass(kw_only=True, slots=True)
class AttachmentBinaryObject(Element):
    """Attached document, binary payload (BT-125).

    A supporting document attached as a binary object or sent together
    with the invoice. Used when documentation has to be stored with
    the invoice for future reference or audit purposes.

    Note: rendered as a single ``BinaryObject`` element carrying the
    base64-encoded payload as text and the MIME code / filename as
    attributes — see :meth:`to_xml_internal`.
    """

    tag: ClassVar[str] = "AttachmentBinaryObject"
    profile: ClassVar[Profile] = Profile.COMFORT

    mime_code: MIME
    """Attached-document MIME code (BT-125-1).

    Code list: allowed values are ``application/pdf``, ``image/png``,
    ``image/jpeg``, ``text/csv``,
    ``application/vnd.openxmlformats-officedocument.spreadsheetml.sheet``,
    ``application/vnd.oasis.opendocument.spreadsheet``.
    """
    filename: str
    """Attached-document file name (BT-125-2)."""
    object: str
    """Base64-encoded payload of the attached document (BT-125)."""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        return XML(
            self.get_tag(),
            attrs={"mimeCode": self.mime_code, "filename": self.filename},
        )[self.object]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if "mimeCode" not in elem.attrib:
            raise ValueError
        if "filename" not in elem.attrib:
            raise ValueError
        if elem.text is None:
            raise ValueError
        mime_code = elem.attrib["mimeCode"]
        filename = elem.attrib["filename"]
        assert isinstance(mime_code, str)
        assert isinstance(filename, str)
        return cls(
            mime_code=MIME(mime_code.strip()),
            filename=filename.strip(),
            object=elem.text.strip(),
        )


@dataclass(kw_only=True, slots=True)
class AdditionalReferencedDocument(Element):
    """Additional supporting documents (BG-24).

    A group of business terms providing information about additional
    supporting documents substantiating the claims made in the
    invoice.

    Note: the same element multiplexes three EN 16931 business terms
    distinguished by ``TypeCode`` (BT-17-0 / BT-18-0 / BT-122-0): a
    tender or lot reference (BT-17), an invoiced-object identifier
    (BT-18), or a generic supporting-document reference (BT-122).
    Each occurrence can either point to an external resource (BT-124,
    URL) or carry the document inline as an
    :class:`AttachmentBinaryObject` (BT-125).
    """

    tag: ClassVar[str] = "AdditionalReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.COMFORT}
    )
    """Supporting-document identifier (BT-17 / BT-18 / BT-122).

    The identifier of the tender or lot the invoice relates to
    (BT-17), an identifier specified by the Seller for an object on
    which the invoice is based (BT-18), or an identifier of the
    supporting document itself (BT-122).

    Note: which of the three terms this carries is selected via
    ``type_code`` (BT-17-0 / BT-18-0 / BT-122-0).
    """
    uriid: str | None = field(
        default=None, metadata={"tag": "URIID", "profile": Profile.COMFORT}
    )
    """External document location (BT-124).

    The URL that identifies where the external document is located —
    a means of locating the resource including its primary access
    mechanism (e.g. ``http://`` or ``ftp://``).

    Note: external documents do not form part of the invoice. Access
    to external documents may bear certain risks; use only when the
    Buyer requires additional information to support the invoice.
    """
    type_code: UNTDID1001TypeCode | None = field(
        default=None, metadata={"tag": "TypeCode", "profile": Profile.COMFORT}
    )
    """Reference type code (BT-17-0 / BT-18-0 / BT-122-0).

    Selects which EN 16931 term ``issuer_assigned_id`` carries:

    * ``50`` "Price/sales catalogue response" — tender or lot
      reference (BT-17-0).
    * ``130`` "Invoicing data sheet" — invoiced-object identifier
      (BT-18-0).
    * ``916`` "Reference paper" — supporting-document reference
      (BT-122-0).

    Code list: UNTDID 1001 (Document name code).
    """
    name: str | None = field(
        default=None, metadata={"tag": "Name", "profile": Profile.COMFORT}
    )
    """Supporting-document description (BT-123).

    A free-text description of the supporting document, e.g. "time
    sheet", "usage report".
    """
    attached_object: AttachmentBinaryObject | None = None
    """Embedded supporting document (BT-125); COMFORT+."""


@dataclass(kw_only=True, slots=True)
class ProcuringProject(Element):
    """Project reference (BT-11-00).

    Detailed information about the project the invoice refers to.
    """

    tag: ClassVar[str] = "SpecifiedProcuringProject"
    profile: ClassVar[Profile] = Profile.COMFORT

    id: str = field(metadata={"tag": "ID", "profile": Profile.COMFORT})
    """Project reference (BT-11).

    The identification of the project the invoice refers to.
    """
    name: str = field(metadata={"tag": "Name", "profile": Profile.COMFORT})
    """Project name (BT-11-0).

    The name of the project the invoice refers to.
    """


@dataclass(kw_only=True, slots=True)
class DespatchAdviceReferencedDocument(Element):
    """Despatch advice reference (BT-16-00).

    Detailed information on the corresponding despatch advice.
    """

    tag: ClassVar[str] = "DespatchAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Despatch advice reference (BT-16).

    An identifier of a referenced despatch advice.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.BASIC_WL},
    )
    """Despatch advice date (BT-X-200-00).

    Note: a Factur-X CIUS extension; the XSD permits it from BASIC_WL
    upwards even though the appendix narrative restricts it to
    EXTENDED. Getafix follows the XSD here.
    """


@dataclass(kw_only=True, slots=True)
class ReceivingAdviceReferencedDocument(Element):
    """Receiving advice reference (BT-15-00).

    Detailed information about the associated goods receipt.
    """

    tag: ClassVar[str] = "ReceivingAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Receiving advice reference (BT-15).

    An identifier of a referenced receiving advice.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.COMFORT},
    )
    """Goods receipt date (BT-X-201-00).

    Note: a Factur-X CIUS extension; gated at COMFORT in getafix to
    match the XSD even though the appendix narrative restricts it to
    EXTENDED.
    """


@dataclass(kw_only=True, slots=True)
class DeliveryNoteReferencedDocument(Element):
    """Delivery note reference (BT-X-202-00).

    Detailed information about the corresponding delivery note.
    EXTENDED-only.
    """

    tag: ClassVar[str] = "DeliveryNoteReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Delivery note reference (BT-X-202)."""
    line_id: str | None = field(default=None, metadata={"tag": "LineID"})
    """Referenced delivery-note line position (BT-X-202-00 ``LineID``).

    Set only on the per-line delivery note reference
    (:attr:`~getafix.schema.line.LineTradeDelivery.delivery_note`); the
    header delivery note leaves it ``None``."""
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Delivery note date (BT-X-203-00)."""


@dataclass(kw_only=True, slots=True)
class InvoiceReferencedDocument(Element):
    """Preceding invoice reference (BG-3).

    A group of business terms providing information on one or more
    preceding invoices.

    Note: to be used when a preceding invoice is corrected, when a
    final invoice refers to preceding partial invoices, or when a
    final invoice refers to preceding prepayment invoices.
    """

    tag: ClassVar[str] = "InvoiceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Preceding invoice reference (BT-25).

    The identification of an invoice that was previously sent by the
    Seller.
    """
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Preceding invoice issue date (BT-26).

    Note: required when the preceding-invoice identifier is not
    unique.
    """
