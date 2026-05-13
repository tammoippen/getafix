"""Trade parties — Seller, Buyer, Payee, Ship-to and friends.

Every ``ram:*TradeParty`` element on the invoice lives here. The XML
shape is the same across roles (``ram:TradePartyType`` in the XSD);
the dataclasses specialise on which fields are required vs optional
per profile and on which BT IDs they map to in EN 16931.

Roles modelled:

* :class:`SellerTradeParty` (BG-4) and :class:`BuyerTradeParty`
  (BG-7) — header.
* :class:`SellerTaxRepresentativeTradeParty` (BG-11) — header,
  BASIC_WL+.
* :class:`PayeeTradeParty` (BG-10) — settlement, BASIC_WL+.
* :class:`ShipToTradeParty` (BG-13) — delivery, BASIC_WL+.
* :class:`UltimateShipToTradeParty` (BG-X-27) and
  :class:`ShipFromTradeParty` (BG-X-30) — delivery, EXTENDED.
* :class:`ProductEndUserTradeParty` (BG-X-18) — agreement, EXTENDED.

The shared sub-elements are factored at the top of the file:

* :class:`SchemeID` family — :class:`SchemeID` (base),
  :class:`ISO6523SchemeId`, :class:`GlobalID`, :class:`URIID`,
  :class:`TaxSchemeId`. All wrap a value plus optional / required
  ``schemeID`` attribute.
* :class:`PostalTradeAddress` (BG-5 / BG-8 / BG-12 / BG-15 — and
  :class:`PostalTradeAddressExtended` with ``CountrySubDivisionName``).
* :class:`LegalOrganization` (BT-30-00 Seller / BT-47-00 Buyer).
* :class:`TradeContact` (BG-6 Seller / BG-9 Buyer) with
  :class:`PhoneNumber`, :class:`FaxNumber` and :class:`EmailURI`.
* :class:`URIUniversalCommunication` (BT-34-00 Seller / BT-49-00 Buyer).
* :class:`SpecifiedTaxRegistration` (BT-31-00 / BT-32-00 / BT-48-00 /
  BT-63-00).

Address fields use parallel BT numbering across roles — e.g.
``line_one`` is BT-35 on Seller, BT-50 on Buyer, BT-64 on the tax
representative, BT-75 on ship-to. The class docstring lists the
Seller-side BT; consult the appendix for buyer / tax-rep / ship-to
counterparts.

Validation rules enforced here:

* ✓ ``BR-10`` — :meth:`BuyerTradeParty.validate_internal` requires
  ``address`` (BG-8) from BASIC_WL upwards; MINIMUM may omit it per
  the XSD.
* ✓ ``BR-CO-9`` — :meth:`TaxSchemeId.validate_internal` requires
  VAT identifiers (``schemeID == "VA"``) to carry an ISO 3166-1
  alpha-2 country prefix (Greece may use ``EL``). Local tax
  identifiers (``FC``, BT-32) are exempt.
* ✓ ``BR-CO-26`` — :meth:`SellerTradeParty.validate_internal`
  requires at least one of BT-29 (Seller identifier), BT-30 (legal
  registration identifier) or BT-31 (VAT identifier).
* ✓ ``BT-31-0 / BT-32-0`` — :meth:`TaxSchemeId.validate_internal`
  restricts ``schemeID`` to ``VA`` or ``FC``.
* ◯ ``BR-6`` / ``BR-7`` (Seller / Buyer name) and ``BR-8`` / ``BR-9``
  (Seller postal address / country) are implicit through required
  dataclass fields.
* ◯ ``BR-18`` / ``BR-19`` / ``BR-20`` / ``BR-56`` (tax representative
  needs name / address / country / VAT id) — implicit through
  required fields on :class:`SellerTaxRepresentativeTradeParty`.

Validation rules not yet enforced (see ``docs/VALIDATION.md``):

* ``BR-62`` / ``BR-63`` — Seller / Buyer electronic address require a
  ``schemeID`` attribute. The :class:`URIID` element accepts an
  optional ``scheme_id`` today; the presence rule is not checked.

All ``SchemeID`` / ``SchemeId`` / ``scheme_id`` names follow the XSD
``schemeID`` attribute spelling (no ``a`` after ``schem``).
"""

from dataclasses import dataclass, field
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class SchemeID(Element):
    """``udt:IDType`` — value with an optional ``schemeID`` attribute.

    Base class for every identifier element that carries the
    ``schemeID`` XSD attribute. The XSD makes the attribute optional;
    the appendix narrative flags whether it is required for each
    specific BT. Subclasses such as :class:`TaxSchemeId` enforce
    stricter constraints in :meth:`validate_internal`.
    """

    tag: ClassVar[str] = "ID"

    id: str
    """The identifier value."""
    scheme_id: str | None = None
    """Identification scheme code (``schemeID`` attribute)."""

    @override
    def to_xml_internal(self, profile: Profile) -> XML:
        attrs: dict[str, str | bool] = {}
        if self.scheme_id is not None:
            attrs["schemeID"] = self.scheme_id
        return XML(self.get_tag(), attrs=attrs)[self.id]

    @override
    @classmethod
    def from_xml(cls, elem: ETElement) -> Self:
        if elem.tag != cls.get_qualified_tag():
            raise ValueError(f"Have {elem.tag=}. Expect {cls.get_qualified_tag()=}")
        if elem.text is None:
            raise ValueError
        return cls(id=elem.text.strip(), scheme_id=elem.attrib.get("schemeID"))


@dataclass(kw_only=True, slots=True)
class ISO6523SchemeId(SchemeID):
    """Identifier whose ``schemeID`` is drawn from ISO/IEC 6523.

    Used for ``GlobalID`` and legal-organisation identifiers. When a
    ``scheme_id`` is set, it must come from the ISO/IEC 6523
    Maintenance Agency code list.

    Code list: ISO/IEC 6523. Frequently-used codes:

    * ``0021`` — SWIFT
    * ``0060`` — DUNS
    * ``0088`` — EAN / GLN
    * ``0177`` — ODETTE

    https://test-docs.peppol.eu/poacc/billing/3.0/2024-q4-release/codelist/ICD/
    """


@dataclass(kw_only=True, slots=True)
class GlobalID(ISO6523SchemeId):
    """Party global identifier (BT-29-0 Seller / BT-46-0 Buyer).

    Identifier uniquely assigned to a party by a global registration
    organisation (GLN, DUNS, BIC, ODETTE, ...). The ``scheme_id``
    attribute (BT-29-1 / BT-46-1) names the registration scheme; see
    :class:`ISO6523SchemeId` for the code list.
    """

    tag: ClassVar[str] = "GlobalID"
    profile: ClassVar[Profile] = Profile.BASIC_WL


@dataclass(kw_only=True, slots=True)
class URIID(SchemeID):
    """Electronic-address identifier (BT-34 Seller / BT-49 Buyer).

    Wraps the URI-based electronic address (e.g. an email or a PEPPOL
    participant id). The ``scheme_id`` attribute names the address
    scheme — required per ``BR-62`` / ``BR-63`` (not yet enforced).
    """

    tag: ClassVar[str] = "URIID"
    profile: ClassVar[Profile] = Profile.BASIC_WL


@dataclass(kw_only=True, slots=True)
class PostalTradeAddress(Element):
    """Postal address (BG-5 Seller / BG-8 Buyer / BG-12 TaxRep / BG-15 ShipTo).

    A group of business terms providing information about a party's
    postal address. Sufficient components must be filled in to comply
    with legal requirements.

    Note: BT IDs are role-dependent — address line 1 is BT-35
    (Seller), BT-50 (Buyer), BT-64 (TaxRep), BT-75 (ShipTo); the
    same pattern applies to the other endpoints. Field-level
    docstrings cite the Seller-side BT; see the appendix for buyer /
    tax-rep / ship-to counterparts.
    """

    tag: ClassVar[str] = "PostalTradeAddress"

    postcode: str | None = field(
        default=None, metadata={"tag": "PostcodeCode", "profile": Profile.BASIC_WL}
    )
    """Post code (BT-38 Seller / BT-53 Buyer / BT-67 TaxRep / BT-78 ShipTo).

    The identifier for an addressable group of properties according
    to the relevant postal service.
    """
    line_one: str | None = field(
        default=None, metadata={"tag": "LineOne", "profile": Profile.BASIC_WL}
    )
    """Address line 1 (BT-35 Seller / BT-50 Buyer / BT-64 TaxRep / BT-75 ShipTo).

    The main address line — street or PO box.

    Note: for major-customer addresses the field must be set to "-".

    Example: ``Lieferantenstraße 20``.
    """
    line_two: str | None = field(
        default=None, metadata={"tag": "LineTwo", "profile": Profile.BASIC_WL}
    )
    """Address line 2 (BT-36 Seller / BT-51 Buyer / BT-65 TaxRep / BT-76 ShipTo).

    An additional address line giving further detail.

    Example: ``Gebäude 3``.
    """
    line_three: str | None = field(
        default=None, metadata={"tag": "LineThree", "profile": Profile.BASIC_WL}
    )
    """Address line 3 (BT-162 Seller / BT-163 Buyer / BT-164 TaxRep / BT-165 ShipTo).

    An additional address line giving further detail.

    Example: ``Tür B``.
    """
    city_name: str | None = field(
        default=None, metadata={"tag": "CityName", "profile": Profile.BASIC_WL}
    )
    """City (BT-37 Seller / BT-52 Buyer / BT-66 TaxRep / BT-77 ShipTo).

    The common name of the city, town or village where the address
    is located.

    Example: ``München``.
    """
    country_id: str = field(metadata={"tag": "CountryID"})
    """Country code (BT-40 Seller / BT-55 Buyer / BT-69 TaxRep / BT-80 ShipTo).

    A code that identifies the country.

    Code list: ISO 3166-1, alpha-2 representation only.

    Example: ``DE``.
    """


@dataclass(kw_only=True, slots=True)
class PostalTradeAddressExtended(PostalTradeAddress):
    """Postal address with subdivision (final field of the XSD ``<xs:sequence>``).

    Adds ``CountrySubDivisionName`` (BT-39 Seller / BT-54 Buyer /
    BT-68 TaxRep / BT-79 ShipTo) — the only field permitted on
    party-level addresses but not on legal-organisation addresses.
    """

    country_subdivision: str | None = field(
        default=None,
        metadata={"tag": "CountrySubDivisionName", "profile": Profile.BASIC_WL},
    )
    """Country subdivision (BT-39 Seller / BT-54 Buyer / BT-68 TaxRep / BT-79 ShipTo).

    The subdivision of a country — state, region or province.

    Example: ``NRW``.
    """


@dataclass(kw_only=True, slots=True)
class PhoneNumber(Element):
    """Contact telephone number (BT-42 Seller / BT-57 Buyer)."""

    tag: ClassVar[str] = "TelephoneUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Telephone number (BT-42 Seller / BT-57 Buyer).

    A phone number for the contact point.

    Example: ``+49 (123) 56789-0``.
    """


@dataclass(kw_only=True, slots=True)
class FaxNumber(Element):
    """Contact fax number.

    Note: not part of the EN 16931 semantic model; carried as an
    EXTENDED-only XSD extension on ``DefinedTradeContact``.
    """

    tag: ClassVar[str] = "FaxUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Fax number for the contact point.

    Example: ``+49 (123) 456789-999``.
    """


@dataclass(kw_only=True, slots=True)
class EmailURI(Element):
    """Contact email address (BT-43 Seller / BT-58 Buyer)."""

    tag: ClassVar[str] = "EmailURIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    address: str | None = field(
        default=None, metadata={"tag": "URIID", "profile": Profile.COMFORT}
    )
    """Email address (BT-43 Seller / BT-58 Buyer).

    An e-mail address for the contact point.

    Example: ``karin.mustermann@seller.tld``.
    """


@dataclass(kw_only=True, slots=True)
class TradeContact(Element):
    """Defined trade contact (BG-6 Seller / BG-9 Buyer).

    A group of business terms providing contact information for the
    party. May be given on Seller or Buyer when ordering, or
    exchanged as master data beforehand.

    Note: contact information should not be used for internal
    routing of received invoices — use ``BuyerReference`` (BT-10)
    for that.
    """

    tag: ClassVar[str] = "DefinedTradeContact"
    profile: ClassVar[Profile] = Profile.COMFORT

    person_name: str | None = field(
        default=None, metadata={"tag": "PersonName", "profile": Profile.COMFORT}
    )
    """Contact point name (BT-41 Seller / BT-56 Buyer).

    A contact point for a legal entity or person — typically the
    name of the contact person.
    """
    department_name: str | None = field(
        default=None, metadata={"tag": "DepartmentName", "profile": Profile.COMFORT}
    )
    """Contact department name (BT-41-0 Seller / BT-56-0 Buyer).

    Name of the department or office for the contact point.
    """
    telephone: PhoneNumber | None = None
    """Telephone number (BT-42 Seller / BT-57 Buyer)."""
    fax: FaxNumber | None = None
    """Fax number (EXTENDED-only)."""
    email: EmailURI | None = None
    """Email address (BT-43 Seller / BT-58 Buyer)."""


@dataclass(kw_only=True, slots=True)
class LegalOrganization(Element):
    """Legal organisation (BT-30-00 Seller / BT-47-00 Buyer).

    Wraps the legal-registration identifier (BT-30 / BT-47) plus the
    trading name (BT-28 / BT-45) and — at EXTENDED only — a separate
    business address.
    """

    tag: ClassVar[str] = "SpecifiedLegalOrganization"

    id: ISO6523SchemeId | None = None
    """Legal registration identifier (BT-30 Seller / BT-47 Buyer).

    An identifier issued by an official registrar that identifies
    the party as a legal entity or person. The ``scheme_id``
    attribute (BT-30-1 / BT-47-1) names the registration scheme.
    """
    trade_name: str | None = field(
        default=None,
        metadata={"tag": "TradingBusinessName", "profile": Profile.BASIC_WL},
    )
    """Trading name (BT-28 Seller / BT-45 Buyer).

    A name by which the party is known, when different from its
    formal name (BT-27 / BT-44). Also known as the business name.
    """
    trade_address: PostalTradeAddress | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Legal-organisation business address (BG-X-14); EXTENDED-only."""


@dataclass(kw_only=True, slots=True)
class URIUniversalCommunication(Element):
    """Electronic address (BT-34-00 Seller / BT-49-00 Buyer).

    Wrapper around the URI-based electronic address used to deliver
    business documents.
    """

    tag: ClassVar[str] = "URIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    uri_id: URIID
    """Electronic-address URI (BT-34 Seller / BT-49 Buyer).

    On Seller: the electronic address to which the application-level
    response to the invoice may be sent. On Buyer: the electronic
    address to which the invoice is delivered.
    """


@dataclass(kw_only=True, slots=True)
class TaxSchemeId(ISO6523SchemeId):
    """VAT / local tax identifier (BT-31, BT-32, BT-48, BT-63).

    Allowed ``scheme_id`` codes:

    * ``VA`` — VAT identification number (BT-31 Seller / BT-48 Buyer
      / BT-63 TaxRep).
    * ``FC`` — local tax identifier / Steuernummer (BT-32 Seller).

    Note: rendered as ``<ram:ID schemeID="VA|FC">…</ram:ID>`` inside
    :class:`SpecifiedTaxRegistration`. The element name is plain
    ``ID`` (inherited from :class:`SchemeID`); earlier versions of
    this module incorrectly emitted ``<ram:GlobalID>``.

    ``validate_internal`` enforces:

    * ``BT-31-0 / BT-32-0`` — ``scheme_id`` must be ``VA`` or ``FC``.
    * ``BR-CO-9`` — VAT identifiers (``scheme_id == "VA"``) must
      start with an ISO 3166-1 alpha-2 country prefix; Greece may
      use ``EL``. Local tax identifiers are exempt.
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if self.scheme_id not in ("VA", "FC"):
            errors.append(
                ValidationError(
                    "BT-31-0/BT-32-0",
                    "schemeID on a SpecifiedTaxRegistration must be 'VA' "
                    f"(VAT identifier) or 'FC' (local tax id); got "
                    f"{self.scheme_id!r}.",
                )
            )
        # BR-CO-9: VAT identifiers must carry an ISO 3166-1 alpha-2
        # country prefix (Greece may use 'EL'). Local tax identifiers
        # (FC, BT-32) are exempt — they're national codes without the
        # country prefix convention.
        if self.scheme_id == "VA":
            prefix = self.id[:2]
            if len(self.id) < 3 or not prefix.isalpha() or prefix != prefix.upper():
                errors.append(
                    ValidationError(
                        "BR-CO-9",
                        "The Seller VAT identifier (BT-31), the Seller tax "
                        "representative VAT identifier (BT-63) and the Buyer "
                        "VAT identifier (BT-48) must each carry a prefix "
                        "according to ISO 3166-1 alpha-2 by which the "
                        "country of issue may be identified. Greece may use "
                        "the prefix 'EL'.",
                    )
                )
        errors.extend(super(TaxSchemeId, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class SpecifiedTaxRegistration(Element):
    """Tax registration (BT-31-00 / BT-32-00 / BT-48-00 / BT-63-00).

    Wraps a single :class:`TaxSchemeId`. A party may carry up to two
    sibling registrations — one VAT identifier (``schemeID="VA"``)
    and one local tax identifier (``schemeID="FC"``) — modelled as a
    list on the surrounding party dataclass.
    """

    tag: ClassVar[str] = "SpecifiedTaxRegistration"

    id: TaxSchemeId
    """Tax identifier value with ``VA`` / ``FC`` scheme."""


@dataclass(kw_only=True, slots=True)
class SellerTradeParty(Element):
    """Seller (BG-4).

    A group of business terms providing information about the
    Seller — the supplier of the goods or services.
    """

    tag: ClassVar[str] = "SellerTradeParty"

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.BASIC_WL}
    )
    """Seller identifier (BT-29).

    An identification of the Seller, frequently a supplier number
    assigned by the Buyer.

    Note: several Seller identifiers may be assigned; they may be
    differentiated by using different schemes. If no scheme is
    given, the identifier must be known to both parties — typically
    a previously exchanged Seller identifier assigned by the Buyer.
    Where a Global ID is available, prefer ``global_ids`` over this
    field.
    """
    global_ids: list[GlobalID] | None = None
    """Seller global identifier (BT-29-0): GLN, DUNS, BIC, ODETTE, ...

    The identification scheme of the Seller identifier — an
    identifier uniquely assigned to a Seller by a global
    registration organisation.
    """
    name: str = field(metadata={"tag": "Name"})
    """Seller name (BT-27).

    The full formal name by which the Seller is registered in the
    national registry of legal entities or as a taxable person, or
    otherwise trades as a person or persons.
    """
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Seller additional legal information (BT-33); COMFORT+.

    Additional legal information relevant for the Seller, such as
    share capital.
    """
    legal_organization: LegalOrganization | None = None
    """Seller legal organisation (BT-30-00)."""
    contact: TradeContact | None = None
    """Seller contact (BG-6); COMFORT+."""
    address: PostalTradeAddressExtended
    """Seller postal address (BG-5); required at every profile."""
    electronic_address: URIUniversalCommunication | None = None
    """Seller electronic address (BT-34-00); BASIC_WL+."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Seller tax registrations (BT-31-00 VAT / BT-32-00 local).

    The XSD permits up to two sibling registrations — one VAT
    identifier (``schemeID="VA"``, BT-31) and one local tax
    identifier (``schemeID="FC"``, BT-32).
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # BR-CO-26: Seller automatic identification — at least one of
        # BT-29 (Seller identifier), BT-30 (Seller legal registration
        # identifier) or BT-31 (Seller VAT identifier) must be present.
        has_id = self.id is not None
        has_legal = (
            self.legal_organization is not None
            and self.legal_organization.id is not None
        )
        has_vat = bool(self.tax_registrations) and any(
            tr.id.scheme_id == "VA" for tr in self.tax_registrations
        )
        if not (has_id or has_legal or has_vat):
            errors.append(
                ValidationError(
                    "BR-CO-26",
                    "In order for the buyer to automatically identify a "
                    "supplier, the Seller identifier (BT-29), the Seller "
                    "legal registration identifier (BT-30) and/or the "
                    "Seller VAT identifier (BT-31) shall be present.",
                )
            )
        errors.extend(super(SellerTradeParty, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class BuyerTradeParty(Element):
    """Buyer (BG-7).

    A group of business terms providing information about the
    Buyer — the recipient of the goods or services.
    """

    tag: ClassVar[str] = "BuyerTradeParty"

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.BASIC_WL}
    )
    """Buyer identifier (BT-46).

    An identifier of the Buyer — frequently a customer number
    assigned by the Seller.

    Note: if no scheme is given, the identifier must be known to
    both parties, e.g. a previously exchanged Buyer identifier
    assigned by the Seller.
    """
    global_ids: list[GlobalID] | None = None
    """Buyer global identifier (BT-46-0): GLN, DUNS, BIC, ODETTE, ...

    The identification scheme of the Buyer identifier — an
    identifier uniquely assigned to a Buyer by a global registration
    organisation.
    """
    name: str = field(metadata={"tag": "Name"})
    """Buyer name (BT-44).

    The full name of the Buyer.
    """
    legal_organization: LegalOrganization | None = None
    """Buyer legal organisation (BT-47-00)."""
    contact: TradeContact | None = None
    """Buyer contact (BG-9); COMFORT+."""
    address: PostalTradeAddressExtended | None = None
    """Buyer postal address (BG-8); required from BASIC_WL.

    Note: the MINIMUM XSD makes ``PostalTradeAddress`` optional on
    every party, and the MINIMUM appendix does NOT list BG-8 as
    required. ``BR-10`` enforces presence from BASIC_WL upwards in
    :meth:`validate_internal`.
    """
    electronic_address: URIUniversalCommunication | None = None
    """Buyer electronic address (BT-49-00); BASIC_WL+."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Buyer tax registrations (BT-48-00 VAT / BT-48-00 local).

    The XSD permits up to two sibling registrations — typically a
    VAT identifier (``schemeID="VA"``, BT-48) and optionally a local
    tax identifier (``schemeID="FC"``).
    """

    @override
    def validate_internal(self, profile: Profile) -> list[ValidationError]:
        errors: list[ValidationError] = []
        # BR-10: An Invoice shall contain the Buyer postal address (BG-8).
        # The MINIMUM XSD lets the element be omitted; EN 16931 / BASIC_WL
        # and above require it.
        if profile > Profile.MINIMUM and self.address is None:
            errors.append(
                ValidationError(
                    "BR-10", "An Invoice shall contain the Buyer postal address (BG-8)."
                )
            )
        errors.extend(super(BuyerTradeParty, self).validate_internal(profile))
        return errors


@dataclass(kw_only=True, slots=True)
class SellerTaxRepresentativeTradeParty(Element):
    """Seller tax representative party (BG-11).

    A group of business terms providing information about the
    Seller's tax representative. Required when the Seller is
    represented by a tax representative responsible for paying the
    VAT due.
    """

    tag: ClassVar[str] = "SellerTaxRepresentativeTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.EXTENDED}
    )
    """Tax representative identifier; EXTENDED-only."""
    global_ids: list[GlobalID] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative global identifier; EXTENDED-only."""
    name: str = field(metadata={"tag": "Name"})
    """Tax representative name (BT-62).

    The full name of the Seller's tax representative party.
    """
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative legal organisation; EXTENDED-only."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative contact; EXTENDED-only."""
    address: PostalTradeAddressExtended
    """Tax representative postal address (BG-12); required at every
    profile that carries BG-11.

    Note: sufficient components must be filled in to comply with
    legal requirements.
    """
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative electronic address; EXTENDED-only."""
    tax_registrations: SpecifiedTaxRegistration
    """Tax representative VAT identifier (BT-63-00); required.

    Note: VAT identifier with ISO 3166-1 alpha-2 country prefix
    (``BR-CO-9``).
    """


@dataclass(kw_only=True, slots=True)
class ProductEndUserTradeParty(Element):
    """Product end user party (BG-X-18); EXTENDED-only.

    The party acting as the end user for the products in this header
    trade agreement.
    """

    tag: ClassVar[str] = "ProductEndUserTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """End-user identifier."""
    global_ids: list[GlobalID] | None = None
    """End-user global identifier."""
    name: str = field(metadata={"tag": "Name"})
    """End-user name."""
    legal_organization: LegalOrganization | None = None
    """End-user legal organisation."""
    contact: TradeContact | None = None
    """End-user contact details."""
    address: PostalTradeAddressExtended | None = None
    """End-user postal address."""
    electronic_address: URIUniversalCommunication | None = None
    """End-user electronic address."""
    tax_registrations: SpecifiedTaxRegistration | None = field(
        default=None, metadata={"profile": Profile.BASIC_WL}
    )
    """End-user tax registration (VAT identifier or local tax id)."""


@dataclass(kw_only=True, slots=True)
class ShipToTradeParty(Element):
    """Deliver-to / ship-to party (BG-13); BASIC_WL+.

    A group of business terms providing information about where and
    when the goods and services invoiced are delivered.
    """

    tag: ClassVar[str] = "ShipToTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Deliver-to location identifier (BT-71).

    An identifier of the location to which the goods are delivered
    or where the services are provided.

    Note: if no scheme is given, it should be known to Buyer and
    Seller, e.g. a previously exchanged identifier assigned by the
    Buyer or Seller.
    """
    global_id: GlobalID | None = None
    """Deliver-to location global identifier (BT-71-0)."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Deliver-to party name (BT-70).

    The name of the party to which the goods are delivered or for
    which the services are provided. Required when the deliver-to
    party is not identical to the Buyer.
    """
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Deliver-to legal organisation; EXTENDED-only."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.COMFORT}
    )
    """Deliver-to contact details; COMFORT+."""
    address: PostalTradeAddressExtended | None = None
    """Deliver-to address (BG-15).

    The address to which goods invoiced are delivered or at which
    services invoiced are provided.

    Note: in the case of pickup, the deliver-to address is the
    pickup address. Sufficient components must be filled in to
    comply with legal requirements.
    """
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Deliver-to electronic address; EXTENDED-only."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Deliver-to tax registrations; EXTENDED-only."""


@dataclass(kw_only=True, slots=True)
class ShipFromTradeParty(Element):
    """Ship-from party (BG-X-30); EXTENDED-only.

    Identification of the party that goods are shipped from. The
    ship-from identifier is a unique, bilaterally agreed identifier
    of the sender.
    """

    tag: ClassVar[str] = "ShipFromTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ship-from party identifier."""
    global_id: GlobalID | None = None
    """Ship-from party global identifier."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ship-from party name."""
    legal_organization: LegalOrganization | None = None
    """Ship-from legal organisation."""
    contact: TradeContact | None = None
    """Ship-from contact details."""
    address: PostalTradeAddressExtended | None = None
    """Ship-from postal address."""
    electronic_address: URIUniversalCommunication | None = None
    """Ship-from electronic address."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ship-from tax registrations."""


@dataclass(kw_only=True, slots=True)
class UltimateShipToTradeParty(Element):
    """Ultimate ship-to party (BG-X-27); EXTENDED-only.

    Identification of the final recipient when it differs from the
    deliver-to party. The ultimate ship-to identifier is a unique,
    bilaterally agreed identifier of the final recipient.
    """

    tag: ClassVar[str] = "UltimateShipToTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ultimate ship-to party identifier."""
    global_ids: list[GlobalID] | None = None
    """Ultimate ship-to party global identifier."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ultimate ship-to party name."""
    legal_organization: LegalOrganization | None = None
    """Ultimate ship-to legal organisation."""
    contact: TradeContact | None = None
    """Ultimate ship-to contact details."""
    address: PostalTradeAddressExtended | None = None
    """Ultimate ship-to postal address."""
    electronic_address: URIUniversalCommunication | None = None
    """Ultimate ship-to electronic address."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ultimate ship-to tax registrations."""


@dataclass(kw_only=True, slots=True)
class PayeeTradeParty(Element):
    """Payee (BG-10); BASIC_WL+.

    A group of business terms providing information about the
    Payee — the role that receives the payment.

    Note: the Payee role may be filled by a party other than the
    Seller (e.g. a factoring service).
    """

    tag: ClassVar[str] = "PayeeTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Payee identifier (BT-60).

    An identifier for the Payee.

    Note: if no scheme is given, the identifier should be known to
    Buyer and Seller — typically a previously exchanged identifier
    assigned by the Buyer or Seller.
    """
    global_id: GlobalID | None = None
    """Payee global identifier."""
    name: str = field(metadata={"tag": "Name"})
    """Payee name (BT-59).

    The name of the Payee. Required when the Payee is not identical
    to the Seller; may be the same as the Seller name.
    """
    legal_organization: LegalOrganization | None = None
    """Payee legal organisation."""

    # contact: TradeContact | None = None
    # """Payee contact details."""
    # address: PostalTradeAddressExtended | None = None
    # """Payee address details."""
    # electronic_address: URIUniversalCommunication | None = None
    # """Electronic address details."""
    # tax_registrations: list[SpecifiedTaxRegistration] | None = None
    # """Payee tax registration details.
    #
    # Tax number, VAT identifier.
    # """
