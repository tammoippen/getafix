from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement
from carthorse.schema.types import MIME, Profile, UNTDID1001TypeCode


@dataclass(kw_only=True, slots=True)
class BuyerOrderReferencedDocument(Element):
    """Details about the referenced purchase order."""

    tag: ClassVar[str] = "BuyerOrderReferencedDocument"

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Purchase order reference / purchase order number (BT-13).

    An identifier of a referenced purchase order, issued by the Buyer.
    """


@dataclass(kw_only=True, slots=True)
class SellerOrderReferencedDocument(Element):
    """Details about the referenced sales order confirmation."""

    tag: ClassVar[str] = "SellerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.COMFORT}
    )
    """Sales order reference / sales order confirmation number (BT-14).

    An identifier of a referenced sales order, issued by the Seller.
    """


@dataclass(kw_only=True, slots=True)
class ContractReferencedDocument(Element):
    """Details about the referenced contract."""

    tag: ClassVar[str] = "ContractReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.BASIC_WL}
    )
    """Contract reference / contract number (BT-12).

    The identifier of a contract. The contract reference should be
    unique in the context of the specific trading relationship and for
    a defined period.
    """


@dataclass(kw_only=True, slots=True)
class UltimateCustomerOrderReferencedDocument(Element):
    tag: ClassVar[str] = "UltimateCustomerOrderReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    issue_date_time: date = field(metadata={"tag": "FormattedIssueDateTime"})


@dataclass(kw_only=True, slots=True)
class AttachmentBinaryObject(Element):
    """Attached document / binary data of the supporting document (BT-125).

    A supporting document attached as a binary object or sent along
    with the Invoice. A supporting document is used when documentation
    needs to be kept together with the Invoice for future reference or
    audit purposes.
    """

    tag: ClassVar[str] = "AttachmentBinaryObject"
    profile: ClassVar[Profile] = Profile.COMFORT

    mime_code: MIME
    """MIME code of the attached document (BT-125-1)."""
    filename: str
    """File name of the attached document (BT-125-2)."""
    object: str
    """Encoded attached document."""

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
        assert isinstance(mime_code, str)
        filename = elem.attrib["filename"]
        assert isinstance(filename, str)
        object = elem.text.strip()
        return cls(
            mime_code=MIME(mime_code.strip()), filename=filename.strip(), object=object
        )


@dataclass(kw_only=True, slots=True)
class AdditionalReferencedDocument(Element):
    """Additional supporting documents (BG-24).

    A group of business terms providing information about additional
    supporting documents substantiating the claims made in the
    Invoice. The additional supporting documents can be used for both
    referencing a document number that should be known to the
    recipient, an external document (referenced by a URL) or an
    embedded document (such as a time report in the form of a PDF).
    The option of linking to an external document is, for example,
    needed for very large attachments and/or sensitive information,
    e.g. for personal services, that has to be separated from the
    Invoice.
    """

    tag: ClassVar[str] = "AdditionalReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(
        metadata={"tag": "IssuerAssignedID", "profile": Profile.COMFORT}
    )
    """Supporting document identifier / document number (BT-17, BT-18, BT-122).

    The identifier of the tender or lot the Invoice relates to, or an
    identifier specified by the Seller for an object on which the
    Invoice is based, or an identifier of the supporting document.

    In some countries a reference to the tender that led to the
    contract must be given. Depending on the use case, this can be a
    subscription number, a telephone number, a meter reading, a
    vehicle, a person, etc.
    """
    uriid: str | None = field(
        default=None, metadata={"tag": "URIID", "profile": Profile.COMFORT}
    )
    """Location of the supporting document (BT-124).

    The URL (Uniform Resource Locator) under which the external
    document is available.

    A means of locating the resource, including its primary access
    method, e.g. http:// or ftp://. The location of the external
    document must be used when the Buyer needs additional information
    as evidence of the amounts invoiced. External documents are not
    part of the Invoice. Access to external documents may bear certain
    risks.
    """
    type_code: UNTDID1001TypeCode | None = field(
        default=None, metadata={"tag": "TypeCode", "profile": Profile.COMFORT}
    )
    """Type of the referenced document (BT-17-0, BT-18-0, BT-122-0).

    * Code 916 "Reference paper" is used to reference the identifier
      of the supporting document. (BT-122)
    * Code 50 "Price/sales catalogue response" is used to reference
      the tender or lot. (BT-17)
    * Code 130 "Invoicing data sheet" is used to reference an
      identifier specified by the Seller for an object. (BT-18)
    """
    name: str | None = field(
        default=None, metadata={"tag": "Name", "profile": Profile.COMFORT}
    )
    """Description of the supporting document (BT-123).

    A description of the document, such as a time sheet, usage or
    consumption report, etc.
    """
    attached_object: AttachmentBinaryObject | None = None


@dataclass(kw_only=True, slots=True)
class ProcuringProject(Element):
    """Project reference details."""

    tag: ClassVar[str] = "SpecifiedProcuringProject"
    profile: ClassVar[Profile] = Profile.COMFORT

    id: str = field(metadata={"tag": "ID", "profile": Profile.COMFORT})
    """Project reference (BT-11).

    The identifier of the project the Invoice refers to.
    """
    name: str = field(metadata={"tag": "Name", "profile": Profile.COMFORT})
    """Project name (BT-11-0).

    The name of the project the Invoice refers to.
    """


@dataclass(kw_only=True, slots=True)
class DespatchAdviceReferencedDocument(Element):
    """Details about the referenced despatch advice."""

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
    """Despatch advice date."""


@dataclass(kw_only=True, slots=True)
class ReceivingAdviceReferencedDocument(Element):
    """Details about the referenced receiving advice."""

    tag: ClassVar[str] = "ReceivingAdviceReferencedDocument"
    profile: ClassVar[Profile] = Profile.COMFORT

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Receiving advice reference / receiving advice number (BT-15).

    An identifier of a referenced receiving advice.
    """
    issue_date_time: date | None = field(
        default=None,
        metadata={"tag": "FormattedIssueDateTime", "profile": Profile.COMFORT},
    )
    """Receiving advice date."""


@dataclass(kw_only=True, slots=True)
class DeliveryNoteReferencedDocument(Element):
    """Details about the referenced delivery note."""

    tag: ClassVar[str] = "DeliveryNoteReferencedDocument"
    profile: ClassVar[Profile] = Profile.EXTENDED

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Delivery note number."""
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Delivery note date."""


@dataclass(kw_only=True, slots=True)
class InvoiceReferencedDocument(Element):
    """Reference to preceding Invoice(s) (BG-3).

    A group of business terms providing information about one or more
    preceding Invoices.

    To be used when:
    — a preceding Invoice is being corrected;
    — a final Invoice refers to preceding partial Invoices;
    — a final Invoice refers to preceding Invoices for prepayments.
    """

    tag: ClassVar[str] = "InvoiceReferencedDocument"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    issuer_assigned_id: str = field(metadata={"tag": "IssuerAssignedID"})
    """Preceding Invoice number (BT-25).

    The identification of an Invoice that was previously sent by the
    Seller.
    """
    issue_date_time: date | None = field(
        default=None, metadata={"tag": "FormattedIssueDateTime"}
    )
    """Preceding Invoice date."""
