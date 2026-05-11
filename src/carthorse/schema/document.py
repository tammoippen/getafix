from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, override

from tagic.xml import XML

from carthorse.schema.element import Element
from carthorse.schema.trade import Trade
from carthorse.schema.types import Namespace, Profile, TypeCode


@dataclass(kw_only=True, slots=True)
class BusinessDocument(Element):
    """Business process information group."""

    tag: ClassVar[str] = "DocumentContextParameterType"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Business process type.

    Identifies the business process context in which the transaction
    appears, to enable the Buyer to process the Invoice in an
    appropriate way.

    Application: This information allows the purpose of the settlement
    (Invoice of an agent, contract partner, subcontractor, settlement
    document for a construction contract, etc.) to be defined.

    Examples: production material, other material, freight invoice

    EN 16931-ID: BT-23
    """


@dataclass(kw_only=True, slots=True)
class GuidelineDocument(Element):
    """Specification identifier group."""

    tag: ClassVar[str] = "GuidelineSpecifiedDocumentContextParameter"

    id: Profile = field(metadata={"tag": "ID"})
    """Specification identifier.

    An identification of the specification containing the total set of
    rules regarding semantic content, cardinalities and business rules
    to which the data contained in the instance document conforms.

    Note: This identifies compliance or conformance of the instance to
    this document. Invoices that are compliant state:
    urn:cen.eu:en16931:2017. Invoices that comply with a user
    specification may state that user specification here. No
    identification scheme is to be used.

    EN 16931-ID: BT-24
    """


@dataclass(kw_only=True, slots=True)
class Context(Element):
    """Process control.

    A group of business terms providing information on the business
    process and rules applicable to the Invoice document.

    EN 16931-ID: BG-2
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocumentContext"

    test_indicator: bool | None = field(
        default=None, metadata={"tag": "TestIndicator", "profile": Profile.EXTENDED}
    )
    """Test indicator.

    The test indicator may be used when introducing a new system, to
    mark the Invoice as a "test invoice".
    """

    guideline: GuidelineDocument
    business: BusinessDocument | None = None


@dataclass(kw_only=True, slots=True)
class IncludedNote(Element):
    """Invoice note (free text).

    A group of business terms providing textual notes that are
    relevant for the Invoice, together with an indication of the
    subject of the note.

    EN 16931-ID: BG-1
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    content_code: str | None = field(
        default=None, metadata={"tag": "ContentCode", "profile": Profile.EXTENDED}
    )
    content: str | None = field(
        default=None, metadata={"tag": "Content", "profile": Profile.BASIC_WL}
    )
    subject_code: str | None = field(
        default=None, metadata={"tag": "SubjectCode", "profile": Profile.BASIC_WL}
    )


@dataclass(kw_only=True, slots=True)
class EffectivePeriod(Element):
    """Contractual due date of the Invoice.

    Only required if the contractual due date differs from the payment
    due date (for example with SEPA direct debits).
    """

    tag: ClassVar[str] = "EffectiveSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.EXTENDED

    complete: date = field(
        metadata={"tag": "CompleteDateTime", "profile": Profile.EXTENDED}
    )


@dataclass(kw_only=True, slots=True)
class Header(Element):
    """Document-wide header properties."""

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocument"

    id: str = field(metadata={"tag": "ID"})
    """Invoice number.

    A unique identification of the Invoice.

    Note: The sequential number required in Article 226(2) of
    Directive 2006/112/EC, to uniquely identify the Invoice within the
    business context, time frame, operating systems and records of the
    Seller. It may be based on one or more series of numbers which may
    include alphanumeric characters. No identification scheme is to be
    used.

    EN 16931-ID: BT-1
    """

    type_code: TypeCode = field(metadata={"tag": "TypeCode"})
    """Invoice type code / document type code.

    Commercial Invoices and credit notes are defined according to the
    entries in UNTDID 1001. Other entries from UNTDID 1001 with
    specific invoices or credit notes may be used where applicable.

    For the BASIC WL and MINIMUM profiles only the following code may
    be used:
    751 : Invoice information for accounting purposes — NOT an Invoice

    EN 16931-ID: BT-3
    """

    issue_date: date = field(metadata={"tag": "IssueDateTime"})
    """Invoice issue date.

    The date on which the Invoice was issued.

    EN 16931-ID: BT-2
    """

    name: str | None = field(
        default=None, metadata={"tag": "Name", "profile": Profile.EXTENDED}
    )
    """Document type (free text).

    INVOICE, CREDIT NOTE, DEBIT NOTE, PROFORMA INVOICE

    The Factur-X 1.08 XSD only emits ``Name`` on
    ``ExchangedDocumentType`` in the EXTENDED profile; the BASIC,
    BASIC_WL, EN 16931 and MINIMUM profiles drop the field. Gated
    accordingly.
    """

    copyright_indicator: bool | None = field(
        default=None, metadata={"tag": "CopyIndicator", "profile": Profile.EXTENDED}
    )
    language_id: str | None = field(
        default=None, metadata={"tag": "LanguageID", "profile": Profile.EXTENDED}
    )
    """Language indicator.

    Example: de
    """
    notes: list[IncludedNote] | None = None
    effective_period: EffectivePeriod | None = None


@dataclass(kw_only=True, slots=True)
class Document(Element):
    """Invoice.

    The content of the ZUGFeRD XML invoice must, independently of the
    document image, represent a complete, self-contained Invoice. It
    should reflect the same business content as the document image.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoice"

    context: Context
    header: Header
    trade: Trade

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        if profile != self.context.guideline.id:
            raise ValueError(
                f"{profile=} has to be the same as set profile: {self.context.guideline.id}"
            )
        return XML(
            self.get_tag(),
            attrs={f"xmlns:{ns.name}": ns.value for ns in Namespace},
            is_root=True,
            children=self._children_xml(profile),
        )

    def to_xml(self) -> XML:
        profile = self.context.guideline.id
        return self.to_xml_internal(profile)

    def validate(self) -> None:
        """Validate every business rule recursively.

        Collects every :class:`ValidationError` from this document and
        raises a single :class:`ValidationErrors` if any was found.
        Callers can inspect ``exc.errors`` to see every violation in
        one pass, rather than fixing one error only to discover the
        next on the following run.
        """
        from carthorse.schema.element import ValidationErrors

        profile = self.context.guideline.id
        errors = self.validate_internal(profile)
        if errors:
            raise ValidationErrors(errors)
