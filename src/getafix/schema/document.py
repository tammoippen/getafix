"""Root ``Document`` and its header (BG-0 / BG-2 / BT-1-00).

Top-level shape of a Cross-Industry Invoice:

* :class:`Document` — the ``rsm:CrossIndustryInvoice`` root carrying
  :attr:`~Document.context` (BG-2), :attr:`~Document.header`
  (BT-1-00) and :attr:`~Document.trade` (BG-25-00). Public entry
  points are :meth:`~Document.to_xml` and :meth:`~Document.validate`.
* :class:`Context` (BG-2) — process-control block; carries the
  optional :class:`BusinessDocument` (BT-23-00) and the required
  :class:`GuidelineDocument` (BT-24-00).
* :class:`Header` (BT-1-00) — document-wide properties: invoice
  number (BT-1), type code (BT-3), issue date (BT-2), invoice notes
  (BG-1), plus EXTENDED-only ``Name`` / ``CopyIndicator`` /
  ``LanguageID`` / ``EffectiveSpecifiedPeriod``.
* :class:`IncludedNote` (BG-1) — invoice note repeated 0..* on the
  header.
* :class:`EffectivePeriod` (BT-X-6-000) — contractual due date when
  it differs from the payment due date (e.g. SEPA direct debit).

No business rules are enforced in this module. ``BR-1`` (specification
identifier required), ``BR-2`` (invoice number required), ``BR-3``
(issue date required) and ``BR-4`` (type code required) are implicit
through the required dataclass fields on :class:`Header` and
:class:`GuidelineDocument`.

The :meth:`Document.validate` method is the public entry point that
collects every :class:`ValidationError` recursively in one pass and
raises a single :class:`ValidationErrors`; child validators append to
the list and never raise.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, override

from tagic.xml import XML

from getafix.schema.element import Element
from getafix.schema.trade import Trade
from getafix.schema.types import Namespace, Profile, TypeCode


@dataclass(kw_only=True, slots=True)
class BusinessDocument(Element):
    """Business process context (BT-23-00).

    Wrapper around BT-23. Optional ``0..1`` at every profile from
    MINIMUM through EXTENDED.

    Note: the EXTENDED technical-appendix PDF lists a ``Diverging
    cardinality: 1..1`` annotation against this element. The
    authoritative artefacts disagree — the XSD ``minOccurs="0"``,
    the EXTENDED schematron (``FX-SCH-A-000024``,
    ``count(ram:BusinessProcessSpecifiedDocumentContextParameter)<=1``)
    and the workbook ``EXT PROFILES Cardinality`` column all stay at
    ``0..1``. getafix follows the schematron because that is what
    invoices are actually validated against.
    """

    tag: ClassVar[str] = "BusinessProcessSpecifiedDocumentContextParameter"

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Business process type (BT-23).

    Identifies the business process context in which the transaction
    appears, to enable the Buyer to process the invoice in an
    appropriate way.

    Note: to be specified by the Buyer. Used to define the purpose of
    the settlement (invoice of an agent, contract partner,
    subcontractor, settlement document for a construction contract,
    etc.).

    Examples: production material, other material, freight invoice.
    """


@dataclass(kw_only=True, slots=True)
class GuidelineDocument(Element):
    """Specification identifier wrapper (BT-24-00).

    Names the EN 16931 / Factur-X / ZUGFeRD profile this document
    conforms to. Required at every profile.
    """

    tag: ClassVar[str] = "GuidelineSpecifiedDocumentContextParameter"

    id: Profile = field(metadata={"tag": "ID"})
    """Specification identifier (BT-24).

    An identification of the specification containing the total set
    of rules regarding semantic content, cardinalities and business
    rules to which the data contained in the instance document
    conforms.

    Note: conformant invoices specify ``urn:cen.eu:en16931:2017``.
    Invoices compliant with a user specification may identify that
    user specification here. No identification scheme is to be used.
    """


@dataclass(kw_only=True, slots=True)
class Context(Element):
    """Exchange document context (BG-2).

    A group of business terms providing information on the business
    process and rules applicable to the invoice document.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocumentContext"

    test_indicator: bool | None = field(
        default=None, metadata={"tag": "TestIndicator", "profile": Profile.EXTENDED}
    )
    """Test indicator (BT-X-1).

    Marks the document as a "test invoice" — useful when introducing
    a new system. EXTENDED-only.
    """

    business: BusinessDocument | None = None
    """Business process context (BT-23-00); EXTENDED-mandatory."""
    guideline: GuidelineDocument
    """Specification identifier (BT-24-00); required at every profile."""


@dataclass(kw_only=True, slots=True)
class IncludedNote(Element):
    """Invoice note (BG-1).

    A group of business terms providing textual notes that are
    relevant to the invoice as a whole, together with an indication
    of the subject of the note.
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    content_code: str | None = field(
        default=None, metadata={"tag": "ContentCode", "profile": Profile.EXTENDED}
    )
    """Content code (BT-X-5).

    A code classifying the content of the invoice note. EXTENDED-only.

    Code list: UNTDID 4451 — must carry the same meaning as
    ``subject_code`` (BT-21).
    """
    content: str | None = field(
        default=None, metadata={"tag": "Content", "profile": Profile.BASIC_WL}
    )
    """Invoice note text (BT-22).

    A textual note that gives unstructured information that is
    relevant to the invoice as a whole, such as the reason for a
    correction or an assignment note when the invoice has been
    factored.
    """
    subject_code: str | None = field(
        default=None, metadata={"tag": "SubjectCode", "profile": Profile.BASIC_WL}
    )
    """Invoice note subject code (BT-21).

    The subject of the textual note in BT-22.

    Code list: UNTDID 4451.
    """


@dataclass(kw_only=True, slots=True)
class EffectivePeriod(Element):
    """Contractual due date of the invoice (BT-X-6-000).

    Indicates the due date of the invoice when it differs from the
    payment due date (typical case: SEPA direct debits). EXTENDED-only.
    """

    tag: ClassVar[str] = "EffectiveSpecifiedPeriod"
    profile: ClassVar[Profile] = Profile.EXTENDED

    complete: date = field(
        metadata={"tag": "CompleteDateTime", "profile": Profile.EXTENDED}
    )
    """Contractual due date (BT-X-6-00)."""


@dataclass(kw_only=True, slots=True)
class Header(Element):
    """Exchange document header (BT-1-00).

    Document-wide properties of the invoice: identifier, type, issue
    date, free-text notes, plus the EXTENDED-only ``Name``,
    ``CopyIndicator``, ``LanguageID`` and contractual ``EffectivePeriod``.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "ExchangedDocument"

    id: str = field(metadata={"tag": "ID"})
    """Invoice number (BT-1).

    A unique identification of the invoice.

    Note: the sequential number required in Article 226(2) of
    Directive 2006/112/EC to uniquely identify the invoice within
    the business context, time frame, operating systems and records
    of the Seller. It may be based on one or more series of numbers
    which may include alphanumeric characters. No identification
    scheme is to be used.
    """

    name: str | None = field(
        default=None, metadata={"tag": "Name", "profile": Profile.EXTENDED}
    )
    """Document name (BT-X-2).

    Free-text label for the document — e.g. ``INVOICE``, ``CREDIT
    NOTE``, ``DEBIT NOTE``, ``PROFORMA INVOICE``.

    Note: the Factur-X 1.08 XSD emits ``Name`` on
    ``ExchangedDocumentType`` only at EXTENDED; MINIMUM, BASIC_WL,
    BASIC and EN 16931 drop the field. Placed between ``ID`` and
    ``TypeCode`` to match the EXTENDED XSD ``<xs:sequence>``.
    """

    type_code: TypeCode = field(metadata={"tag": "TypeCode"})
    """Invoice type code (BT-3).

    A code specifying the functional type of the invoice.

    Code list: UNTDID 1001 — commercial invoices and credit notes are
    defined according to the entries in UNTDID 1001; other entries
    may be used where applicable.

    Note: at BASIC_WL and MINIMUM only code ``751`` "Invoice
    information for accounting purposes" may be used — that profile
    does NOT carry an actual invoice but only the accounting
    summary.
    """

    issue_date: date = field(metadata={"tag": "IssueDateTime"})
    """Invoice issue date (BT-2).

    The date when the invoice was issued.
    """

    copyright_indicator: bool | None = field(
        default=None, metadata={"tag": "CopyIndicator", "profile": Profile.EXTENDED}
    )
    """Copy indicator (BT-X-3).

    Marks the document as a copy of another invoice document.
    EXTENDED-only.
    """
    language_id: str | None = field(
        default=None, metadata={"tag": "LanguageID", "profile": Profile.EXTENDED}
    )
    """Invoice language code (BT-X-4).

    Indicates the language used in the invoice document.
    EXTENDED-only.

    Code list: ISO 639-2.

    Example: ``de``.
    """
    notes: list[IncludedNote] | None = None
    """Invoice notes (BG-1, 0..*); BASIC_WL+."""
    effective_period: EffectivePeriod | None = None
    """Contractual due date period (BT-X-6-000); EXTENDED-only."""


@dataclass(kw_only=True, slots=True)
class Document(Element):
    """Cross-Industry Invoice — root document (BG-0).

    The content of the ZUGFeRD XML invoice must, independently of the
    document image, represent a complete, self-contained invoice. It
    should reflect the same business content as the document image.
    """

    namespace: ClassVar[Namespace] = Namespace.rsm
    tag: ClassVar[str] = "CrossIndustryInvoice"

    context: Context
    """Exchange document context (BG-2)."""
    header: Header
    """Exchange document header (BT-1-00)."""
    trade: Trade
    """Supply chain trade transaction (BG-25-00)."""

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
        from getafix.schema.element import ValidationErrors

        profile = self.context.guideline.id
        errors = self.validate_internal(profile)
        if errors:
            raise ValidationErrors(errors)
