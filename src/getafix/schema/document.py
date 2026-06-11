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

    Names the business-process setting the transaction belongs to so
    the Buyer can route the invoice through the matching workflow.

    Note: the value is prescribed by the Buyer and conveys what the
    settlement is for — an agent's invoice, a contract partner, a
    subcontractor, a settlement document under a construction
    contract, and so on.

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

    Points at the specification — the complete rule set covering
    semantics, cardinalities and business rules — that the instance
    document claims conformance with.

    Note: EN 16931-conformant invoices carry
    ``urn:cen.eu:en16931:2017``; an invoice following a CIUS or user
    specification names that specification's URN here instead. The
    value is given bare, without an identification scheme.
    """


@dataclass(kw_only=True, slots=True)
class Context(Element):
    """Exchange document context (BG-2).

    Process-control block: states which business process the invoice
    takes part in and which rule set (specification) governs it.
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

    Free-text note block on the invoice header: the note text itself
    plus optional codes stating what the note is about.
    """

    tag: ClassVar[str] = "IncludedNote"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    content_code: str | None = field(
        default=None, metadata={"tag": "ContentCode", "profile": Profile.EXTENDED}
    )
    """Content code (BT-X-5).

    Coded classification of what the note says. EXTENDED-only.

    Code list: [UNTDID 4451](https://service.unece.org/trade/untdid/d16b/tred/tred4451.htm)
    — must carry the same meaning as ``subject_code`` (BT-21).
    """
    content: str | None = field(
        default=None, metadata={"tag": "Content", "profile": Profile.BASIC_WL}
    )
    """Invoice note text (BT-22).

    Unstructured free text carrying information that concerns the
    invoice as a whole — e.g. why a correction was issued, or an
    assignment note when the invoice has been factored.
    """
    subject_code: str | None = field(
        default=None, metadata={"tag": "SubjectCode", "profile": Profile.BASIC_WL}
    )
    """Invoice note subject code (BT-21).

    States what the note text (BT-22) is about.

    Code list: [UNTDID 4451](https://service.unece.org/trade/untdid/d16b/tred/tred4451.htm).
    """


@dataclass(kw_only=True, slots=True)
class EffectivePeriod(Element):
    """Contractual due date of the invoice (BT-X-6-000).

    Marks when the invoice contractually falls due, where that
    differs from the payment due date (typical case: SEPA direct
    debits). EXTENDED-only.
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

    Uniquely identifies the invoice.

    Note: this is the sequential number that Article 226(2) of
    Directive 2006/112/EC demands so an invoice can be told apart
    unambiguously across the Seller's records, operating systems,
    business context and time frame. One or more number series — which
    may mix in alphanumeric characters — can feed it; the value
    carries no identification scheme.
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

    Coded document function — what kind of invoice this is.

    Code list: UNTDID 1001 — commercial invoices and credit notes
    take their definitions from the UNTDID 1001 entries; further
    entries may be used where they apply.

    Note: at BASIC_WL and MINIMUM only code ``751`` "Invoice
    information for accounting purposes" may be used — that profile
    does NOT carry an actual invoice but only the accounting
    summary.
    """

    issue_date: date = field(metadata={"tag": "IssueDateTime"})
    """Invoice issue date (BT-2).

    Calendar date on which the Seller issued the invoice.
    """

    copyright_indicator: bool | None = field(
        default=None, metadata={"tag": "CopyIndicator", "profile": Profile.EXTENDED}
    )
    """Copy indicator (BT-X-3).

    Flags this document as a duplicate of an invoice issued earlier.
    EXTENDED-only.
    """
    language_id: str | None = field(
        default=None, metadata={"tag": "LanguageID", "profile": Profile.EXTENDED}
    )
    """Invoice language code (BT-X-4).

    Language the invoice document is written in.
    EXTENDED-only.

    Code list: [ISO 639-2](https://www.loc.gov/standards/iso639-2/php/code_list.php).

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
