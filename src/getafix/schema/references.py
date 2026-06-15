"""``ram:*ReferencedDocument`` wrappers — cross-references on the invoice.

This module owns every ``*ReferencedDocument`` element on the header,
plus the supporting-document family (BG-24) and its embedded binary
payload. These are the cross-references that point from an invoice
back to upstream documents (purchase order, contract, despatch
advice, …) or forward to downstream supporting material.

The line-level delivery-note reference twin lives on
``LineTradeDelivery.delivery_note`` (EXTENDED); the despatch / receiving
advice line twins are not yet modelled (see the README "Status and
known gaps").
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

    Order number of the Buyer's purchase order this invoice answers.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.EXTENDED},
    )
    """Purchase order date (BT-X-147-00); EXTENDED-only.

    When the purchase order cited in BT-13 was issued."""


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

    Order number the Seller assigned to the referenced sales order.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.EXTENDED},
    )
    """Sales order confirmation date (BT-X-146-00); EXTENDED-only.

    When the sales order cited in BT-14 was issued."""


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

    Identifies the contract the invoice settles against.

    Note: within a given trading relationship — and over a defined
    period of time — the identifier should be unambiguous.
    """


@dataclass(kw_only=True, slots=True)
class QuotationReferencedDocument(Element):
    """Header quotation reference (BG-X-61); EXTENDED-only.

    Reference to the quotation that this invoice as a whole responds
    to. Distinct from the per-line
    :class:`~getafix.schema.line.LineQuotationReferencedDocument`
    (BG-X-47).
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

    Order number placed by the final customer at the end of the
    purchase chain.
    """
    issue_date_time: date = field(metadata={"tag": "FormattedIssueDateTime"})
    """Ultimate customer order date (BT-X-151-00).

    The date when the ultimate customer order was issued.
    """


@dataclass(kw_only=True, slots=True)
class AttachmentBinaryObject(Element):
    """Attached document, binary payload (BT-125).

    A supporting document embedded as a binary object or sent along
    with the invoice. Used when the documentation needs to stay
    archived next to the invoice for later reference or audit.

    Note: rendered as a single ``BinaryObject`` element carrying the
    base64-encoded payload as text and the MIME code / filename as
    attributes — see :meth:`to_xml_internal`.
    """

    tag: ClassVar[str] = "AttachmentBinaryObject"
    profile: ClassVar[Profile] = Profile.COMFORT

    mime_code: MIME
    """Attached-document MIME code (BT-125-1)."""
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

    Extra documents that back up what the invoice claims — time
    sheets, usage reports, tender references and the like.

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

    The call for tender or lot concerned (BT-17), a Seller-chosen
    identifier for the object being invoiced (BT-18), or the
    supporting document's own identifier (BT-122).

    Note: which of the three terms this carries is selected via
    ``type_code`` (BT-17-0 / BT-18-0 / BT-122-0).
    """
    uriid: str | None = field(
        default=None, metadata={"tag": "URIID", "profile": Profile.COMFORT}
    )
    """External document location (BT-124).

    URL pointing at the external document; the scheme prefix
    (``http://``, ``ftp://``, …) states how the resource is reached.

    Note: an externally hosted document is not part of the invoice
    itself, and fetching it carries some risk — use only when the
    Buyer needs the extra material to support the invoice.
    """
    type_code: UNTDID1001TypeCode | None = field(
        default=None, metadata={"tag": "TypeCode", "profile": Profile.COMFORT}
    )
    """Reference type code (BT-17-0 / BT-18-0 / BT-122-0).

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

    Names and identifies the procurement project behind the invoice.
    """

    tag: ClassVar[str] = "SpecifiedProcuringProject"
    profile: ClassVar[Profile] = Profile.COMFORT

    id: str = field(metadata={"tag": "ID", "profile": Profile.COMFORT})
    """Project reference (BT-11).

    Identifier of the project behind the invoice.
    """
    name: str = field(metadata={"tag": "Name", "profile": Profile.COMFORT})
    """Project name (BT-11-0).

    Human-readable name of that same project.
    """


@dataclass(kw_only=True, slots=True)
class DespatchAdviceReferencedDocument(Element):
    """Despatch advice reference (BT-16-00).

    Points at the despatch advice that announced the shipment.
    """

    tag: ClassVar[str] = "DespatchAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Despatch advice reference (BT-16).

    Document number of that despatch advice.
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

    Points at the goods-receipt confirmation for the delivery.
    """

    tag: ClassVar[str] = "ReceivingAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Receiving advice reference (BT-15).

    Document number of that receiving advice.
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
    """Delivery note reference (BT-X-202-00). EXTENDED-only.

    Points at the delivery note that accompanied the goods.
    """

    tag: ClassVar[str] = "DeliveryNoteReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Delivery note reference (BT-X-202)."""
    line_id: str | None = field(default=None, metadata={"tag": "LineID"})
    """Delivery-note line position (BT-X-93).

    Set only on the per-line delivery note reference
    (:attr:`~getafix.schema.line.LineTradeDelivery.delivery_note`,
    BG-X-83); the header delivery note (BT-X-202-00) leaves it ``None``."""
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Delivery note date (BT-X-203-00)."""


@dataclass(kw_only=True, slots=True)
class InvoiceReferencedDocument(Element):
    """Preceding invoice reference (BG-3).

    Points back at one or more earlier invoices in the same billing
    chain.

    Note: used when correcting an earlier invoice, or when a final
    invoice refers back to earlier partial or prepayment invoices.
    """

    tag: ClassVar[str] = "InvoiceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Preceding invoice reference (BT-25).

    Invoice number of an earlier invoice the Seller already sent.
    """
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Preceding invoice issue date (BT-26).

    Note: must be supplied whenever the BT-25 reference alone would
    be ambiguous.
    """
