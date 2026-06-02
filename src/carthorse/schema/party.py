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
* ✓ ``BR-62`` / ``BR-63`` — :meth:`SellerTradeParty.validate_internal`
  and :meth:`BuyerTradeParty.validate_internal` require a
  ``schemeID`` on the electronic-address ``URIID`` when present.

All ``SchemeID`` / ``SchemeId`` / ``scheme_id`` names follow the XSD
``schemeID`` attribute spelling.
"""

from dataclasses import dataclass, field
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.rules import Validator
from carthorse.rules.party import (
    br_10,
    br_62,
    br_63,
    br_co_9,
    br_co_26,
    bt_31_0_scheme_id,
)
from carthorse.schema.element import Element, ETElement
from carthorse.schema.types import Country, Profile


@dataclass(kw_only=True, slots=True)
class SchemeID(Element):
    """``udt:IDType`` — value with an optional ``schemeID`` attribute.

    Generic shape reused by every identifier element that carries
    the XSD ``schemeID`` attribute (BT-29 Seller, BT-46 Buyer, BT-60
    Payee, BT-71 Ship-to, etc.). The XSD makes the attribute
    optional; the appendix narrative flags whether it is required
    for each specific BT. Subclasses such as :class:`TaxSchemeId`
    enforce stricter constraints in :meth:`validate_internal`.
    """

    tag: ClassVar[str] = "ID"

    id: str
    """The identifier value (carrying BT depends on context — e.g.
    BT-29 Seller / BT-46 Buyer / BT-60 Payee identifier value)."""
    scheme_id: str | None = None
    """Identification scheme code — XSD ``schemeID`` attribute
    (carrying BT is the parent BT's ``-1`` suffix — e.g. BT-29-1
    Seller / BT-46-1 Buyer identifier scheme)."""

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

    Used for ``GlobalID`` (BT-29-0 Seller / BT-46-0 Buyer) and the
    legal-organisation identifier (BT-30 / BT-47) — the carrying BT
    depends on the parent party. When ``scheme_id`` is set, it must
    come from the ISO/IEC 6523 Maintenance Agency code list.

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
    scheme — required per ``BR-62`` (Seller) and ``BR-63`` (Buyer),
    enforced in :mod:`carthorse.rules.party`.
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
    country_id: Country = field(metadata={"tag": "CountryID"})
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
    """Contact fax number (BT-X-107-00 Seller / BT-X-115-00 Buyer / …).

    Not part of the EN 16931 semantic model; carried as an
    EXTENDED-only XSD extension on every ``DefinedTradeContact``.
    The carrying BT depends on the parent party (BT-X-107-00 Seller,
    BT-X-115-00 Buyer, BT-X-134-00 SellerTaxRep, BT-X-189-00 ShipTo,
    BT-X-247-00 Invoicee, etc.).
    """

    tag: ClassVar[str] = "FaxUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Fax number value (BT-X-107 Seller / BT-X-115 Buyer / etc. —
    BT depends on the parent party, see class docstring).

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
    """Fax number (BT-X-107-00 Seller / BT-X-115-00 Buyer / etc.);
    EXTENDED-only XSD extension, no EN 16931 semantic equivalent."""
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
    ``ID`` (inherited from :class:`SchemeID`).

    ``validate_internal`` enforces:

    * ``BT-31-0 / BT-32-0`` — ``scheme_id`` must be ``VA`` or ``FC``.
    * ``BR-CO-9`` — VAT identifiers (``scheme_id == "VA"``) must
      start with an ISO 3166-1 alpha-2 country prefix; Greece may
      use ``EL``. Local tax identifiers are exempt.
    """

    _validators: ClassVar[tuple[Validator["TaxSchemeId"], ...]] = (
        bt_31_0_scheme_id,
        br_co_9,
    )


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
    """Tax identifier value (BT-31 / BT-32 / BT-48 / BT-63) with
    ``VA`` (VAT) or ``FC`` (local tax / Steuernummer) ``schemeID``."""


@dataclass(kw_only=True, slots=True)
class SellerTradeParty(Element):
    """Seller (BG-4).

    A group of business terms providing information about the
    Seller — the supplier of the goods or services.
    """

    tag: ClassVar[str] = "SellerTradeParty"

    _validators: ClassVar[tuple[Validator["SellerTradeParty"], ...]] = (br_co_26, br_62)

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


@dataclass(kw_only=True, slots=True)
class BuyerTradeParty(Element):
    """Buyer (BG-7).

    A group of business terms providing information about the
    Buyer — the recipient of the goods or services.
    """

    tag: ClassVar[str] = "BuyerTradeParty"

    _validators: ClassVar[tuple[Validator["BuyerTradeParty"], ...]] = (br_10, br_63)

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
    """Buyer tax registrations (BT-48-00).

    The XSD permits up to two sibling registrations. EN 16931 only
    names BT-48 — the Buyer VAT identifier (``schemeID="VA"``); a
    local tax identifier (``schemeID="FC"``) is allowed by the XSD
    but has no dedicated BT id.
    """


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
    """Tax representative identifier (BT-X-116); EXTENDED-only."""
    global_ids: list[GlobalID] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative global identifier (BT-X-117); EXTENDED-only."""
    name: str = field(metadata={"tag": "Name"})
    """Tax representative name (BT-62).

    The full name of the Seller's tax representative party.
    """
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative legal organisation (BG-X-16); EXTENDED-only."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative contact (BG-X-17); EXTENDED-only."""
    address: PostalTradeAddressExtended
    """Tax representative postal address (BG-12); required at every
    profile that carries BG-11.

    Note: sufficient components must be filled in to comply with
    legal requirements.
    """
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative electronic address (BT-X-125-00); EXTENDED-only."""
    tax_registrations: SpecifiedTaxRegistration
    """Tax representative VAT identifier (BT-63-00); required.

    Note: VAT identifier with ISO 3166-1 alpha-2 country prefix
    (``BR-CO-9``).
    """


@dataclass(kw_only=True, slots=True)
class SalesAgentTradeParty(Element):
    """Sales agent party (BG-X-49); EXTENDED-only.

    A commercial intermediary (broker / agent) acting on the
    Seller's behalf between Seller and Buyer. Same generic
    ``TradePartyType`` shape as :class:`ProductEndUserTradeParty`;
    every field except ``name`` is optional.
    """

    tag: ClassVar[str] = "SalesAgentTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Sales agent identifier (BT-X-337)."""
    global_ids: list[GlobalID] | None = None
    """Sales agent global identifier(s) (BT-X-338)."""
    name: str = field(metadata={"tag": "Name"})
    """Sales agent name (BT-X-335)."""
    legal_organization: LegalOrganization | None = None
    """Sales agent legal organisation (BG-X-50)."""
    contact: TradeContact | None = None
    """Sales agent contact details (BG-X-51)."""
    address: PostalTradeAddressExtended | None = None
    """Sales agent postal address (BG-X-52)."""
    electronic_address: URIUniversalCommunication | None = None
    """Sales agent electronic address (BT-X-341-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Sales agent tax registration (BT-X-340-00; VAT id only —
    ``BR-FXEXT-03``)."""


@dataclass(kw_only=True, slots=True)
class BuyerTaxRepresentativeTradeParty(Element):
    """Buyer tax representative party (BG-X-54); EXTENDED-only.

    Buyer-side counterpart of :class:`SellerTaxRepresentativeTradeParty`
    (BG-11) — the party responsible for the Buyer's VAT obligations
    when the Buyer is represented by a fiscal representative.
    """

    tag: ClassVar[str] = "BuyerTaxRepresentativeTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Buyer tax representative identifier (BT-X-364)."""
    global_ids: list[GlobalID] | None = None
    """Buyer tax representative global identifier(s) (BT-X-365)."""
    name: str = field(metadata={"tag": "Name"})
    """Buyer tax representative name (BT-X-362)."""
    legal_organization: LegalOrganization | None = None
    """Buyer tax representative legal organisation (BG-X-58)."""
    contact: TradeContact | None = None
    """Buyer tax representative contact details (BG-X-55)."""
    address: PostalTradeAddressExtended | None = None
    """Buyer tax representative postal address (BG-X-56)."""
    electronic_address: URIUniversalCommunication | None = None
    """Buyer tax representative electronic address (BT-X-368-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Buyer tax representative VAT identifier (BT-X-367-00)."""


@dataclass(kw_only=True, slots=True)
class BuyerAgentTradeParty(Element):
    """Buyer agent party (BG-X-62); EXTENDED-only.

    The Buyer's procurement agent — a party acting on the Buyer's
    behalf in the purchasing transaction. Same generic
    ``TradePartyType`` shape; only ``name`` is required.
    """

    tag: ClassVar[str] = "BuyerAgentTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Buyer agent identifier (BT-X-408)."""
    global_ids: list[GlobalID] | None = None
    """Buyer agent global identifier(s) (BT-X-409)."""
    name: str = field(metadata={"tag": "Name"})
    """Buyer agent name (BT-X-406)."""
    legal_organization: LegalOrganization | None = None
    """Buyer agent legal organisation (BG-X-63)."""
    contact: TradeContact | None = None
    """Buyer agent contact details (BG-X-64)."""
    address: PostalTradeAddressExtended | None = None
    """Buyer agent postal address (BG-X-65)."""
    electronic_address: URIUniversalCommunication | None = None
    """Buyer agent electronic address (BT-X-412-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Buyer agent tax registration (BT-X-411-00)."""


@dataclass(kw_only=True, slots=True)
class ProductEndUserTradeParty(Element):
    """Product end user party (BG-X-18); EXTENDED-only.

    The party acting as the end user for the products in this header
    trade agreement.
    """

    tag: ClassVar[str] = "ProductEndUserTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """End-user identifier (BT-X-126)."""
    global_ids: list[GlobalID] | None = None
    """End-user global identifier (BT-X-127)."""
    name: str = field(metadata={"tag": "Name"})
    """End-user name (BT-X-128)."""
    legal_organization: LegalOrganization | None = None
    """End-user legal organisation (BG-X-19)."""
    contact: TradeContact | None = None
    """End-user contact details (BG-X-20)."""
    address: PostalTradeAddressExtended | None = None
    """End-user postal address (BG-X-21)."""
    electronic_address: URIUniversalCommunication | None = None
    """End-user electronic address (BT-X-143-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = field(
        default=None, metadata={"profile": Profile.BASIC_WL}
    )
    """End-user tax registration (BT-X-144-00) — VAT identifier or
    local tax id."""


@dataclass(kw_only=True, slots=True)
class ShipToTradeParty(Element):
    """Deliver-to / ship-to party (BG-13); BASIC_WL+.

    A group of business terms providing information about where and
    when the goods and services invoiced are delivered.
    """

    tag: ClassVar[str] = "ShipToTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

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
    """Deliver-to legal organisation (BG-X-25); EXTENDED-only."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.COMFORT}
    )
    """Deliver-to contact details (BG-X-26); COMFORT+."""
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
    """Deliver-to electronic address (BT-X-160-00); EXTENDED-only."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Deliver-to tax registrations (BT-X-161-00); EXTENDED-only."""


@dataclass(kw_only=True, slots=True)
class ShipFromTradeParty(Element):
    """Ship-from party (BG-X-30); EXTENDED-only.

    Identification of the party that goods are shipped from. The
    ship-from identifier is a unique, bilaterally agreed identifier
    of the sender.
    """

    tag: ClassVar[str] = "ShipFromTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ship-from party identifier (BT-X-181)."""
    global_id: GlobalID | None = None
    """Ship-from party global identifier (BT-X-182)."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ship-from party name (BT-X-183)."""
    legal_organization: LegalOrganization | None = None
    """Ship-from legal organisation (BT-X-184-00)."""
    contact: TradeContact | None = None
    """Ship-from contact details (BG-X-31)."""
    address: PostalTradeAddressExtended | None = None
    """Ship-from postal address (BG-X-32)."""
    electronic_address: URIUniversalCommunication | None = None
    """Ship-from electronic address (BT-X-198-00)."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ship-from tax registrations (BT-X-199-00)."""


@dataclass(kw_only=True, slots=True)
class UltimateShipToTradeParty(Element):
    """Ultimate ship-to party (BG-X-27); EXTENDED-only.

    Identification of the final recipient when it differs from the
    deliver-to party. The ultimate ship-to identifier is a unique,
    bilaterally agreed identifier of the final recipient.
    """

    tag: ClassVar[str] = "UltimateShipToTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ultimate ship-to party identifier (BT-X-162)."""
    global_ids: list[GlobalID] | None = None
    """Ultimate ship-to party global identifier (BT-X-163)."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ultimate ship-to party name (BT-X-164)."""
    legal_organization: LegalOrganization | None = None
    """Ultimate ship-to legal organisation (BT-X-165-00)."""
    contact: TradeContact | None = None
    """Ultimate ship-to contact details (BG-X-28)."""
    address: PostalTradeAddressExtended | None = None
    """Ultimate ship-to postal address (BG-X-29)."""
    electronic_address: URIUniversalCommunication | None = None
    """Ultimate ship-to electronic address (BT-X-179-00)."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ultimate ship-to tax registrations (BT-X-180-00)."""


@dataclass(kw_only=True, slots=True)
class ItemSellerTradeParty(Element):
    """Line-level deviating seller (BG-X-90); EXTENDED-only.

    The seller-of-record for an individual invoice line, when it
    differs from the header Seller — e.g. a marketplace / drop-ship
    arrangement where each line is fulfilled by a different vendor.
    Generic ``TradePartyType`` shape; only ``name`` is required.
    """

    tag: ClassVar[str] = "ItemSellerTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Item seller identifier (BT-X-567)."""
    global_ids: list[GlobalID] | None = None
    """Item seller global identifier(s) (BT-X-568)."""
    name: str = field(metadata={"tag": "Name"})
    """Item seller name (BT-X-569)."""
    legal_organization: LegalOrganization | None = None
    """Item seller legal organisation (BT-X-572-00)."""
    contact: TradeContact | None = None
    """Item seller contact details (BG-X-91)."""
    address: PostalTradeAddressExtended | None = None
    """Item seller postal address (BG-X-92)."""
    electronic_address: URIUniversalCommunication | None = None
    """Item seller electronic address (BT-X-586-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Item seller tax registration (BT-X-587-00 / BT-X-588-00;
    VAT id only — ``BR-FXEXT-03``)."""


@dataclass(kw_only=True, slots=True)
class InvoicerTradeParty(Element):
    """Invoicer party (BG-X-33); EXTENDED-only.

    The party that issued the invoice, when different from the
    Seller (e.g. a shared service centre or an outsourced billing
    provider). Generic ``TradePartyType`` shape — only ``name`` is
    required.
    """

    tag: ClassVar[str] = "InvoicerTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Invoicer identifier (BT-X-205)."""
    global_ids: list[GlobalID] | None = None
    """Invoicer global identifier(s) (BT-X-206)."""
    name: str = field(metadata={"tag": "Name"})
    """Invoicer name (BT-X-207)."""
    legal_organization: LegalOrganization | None = None
    """Invoicer legal organisation (BT-X-208-00)."""
    contact: TradeContact | None = None
    """Invoicer contact details (BG-X-34)."""
    address: PostalTradeAddressExtended | None = None
    """Invoicer postal address (BG-X-35)."""
    electronic_address: URIUniversalCommunication | None = None
    """Invoicer electronic address (BT-X-222-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Invoicer tax registration (BT-X-223-00)."""


@dataclass(kw_only=True, slots=True)
class InvoiceeTradeParty(Element):
    """Invoicee party (BG-X-36); EXTENDED-only.

    The party the invoice is addressed to for accounting purposes,
    when different from the Buyer (e.g. a parent company or a
    payer-pays-on-behalf-of arrangement). Generic ``TradePartyType``
    shape.
    """

    tag: ClassVar[str] = "InvoiceeTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Invoicee identifier (BT-X-224)."""
    global_ids: list[GlobalID] | None = None
    """Invoicee global identifier(s) (BT-X-225)."""
    name: str = field(metadata={"tag": "Name"})
    """Invoicee name (BT-X-226)."""
    legal_organization: LegalOrganization | None = None
    """Invoicee legal organisation (BT-X-227-00)."""
    contact: TradeContact | None = None
    """Invoicee contact details (BG-X-37)."""
    address: PostalTradeAddressExtended | None = None
    """Invoicee postal address (BG-X-38)."""
    electronic_address: URIUniversalCommunication | None = None
    """Invoicee electronic address (BT-X-241-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Invoicee tax registration (BT-X-242-00)."""


@dataclass(kw_only=True, slots=True)
class PayerTradeParty(Element):
    """Payer party (BG-X-73); EXTENDED-only.

    The party that actually settles the invoice when it is neither
    the Buyer nor the Payee — e.g. a factor or a paying agent.
    Generic ``TradePartyType`` shape.
    """

    tag: ClassVar[str] = "PayerTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Payer identifier (BT-X-478)."""
    global_ids: list[GlobalID] | None = None
    """Payer global identifier(s) (BT-X-479)."""
    name: str = field(metadata={"tag": "Name"})
    """Payer name (BT-X-476)."""
    legal_organization: LegalOrganization | None = None
    """Payer legal organisation (BT-X-480-00)."""
    contact: TradeContact | None = None
    """Payer contact details (BG-X-74)."""
    address: PostalTradeAddressExtended | None = None
    """Payer postal address (BG-X-75)."""
    electronic_address: URIUniversalCommunication | None = None
    """Payer electronic address (BT-X-482-00)."""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Payer tax registration (BT-X-481-00)."""


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
    """Payee global identifier (BT-60-0; ``schemeID`` per ISO/IEC 6523)."""
    name: str = field(metadata={"tag": "Name"})
    """Payee name (BT-59).

    The name of the Payee. Required when the Payee is not identical
    to the Seller; may be the same as the Seller name.
    """
    legal_organization: LegalOrganization | None = None
    """Payee legal organisation (BT-61-00) — carries the legal
    registration identifier (BT-61) and its ``schemeID`` (BT-61-1)."""
    contact: TradeContact | None = None
    """Payee contact details. (BG-X-39)"""
    address: PostalTradeAddressExtended | None = None
    """Payee postal address. (BG-X-40)"""
    electronic_address: URIUniversalCommunication | None = None
    """Payee electronic address. (BT-X-256)"""
    tax_registrations: SpecifiedTaxRegistration | None = None
    """Payee tax registrations. (BT-X-257)"""
