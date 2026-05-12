"""Trade parties — Seller, Buyer, and friends.

This module owns every ``ram:*TradeParty`` element. The shape is the
same across roles (``ram:TradePartyType`` in the XSD); the dataclasses
specialise on which fields are required vs optional per profile and
on which BT-IDs they map to.

Roles modelled:

* ``SellerTradeParty`` (BG-4) and ``BuyerTradeParty`` (BG-7) — header.
* ``SellerTaxRepresentativeTradeParty`` (BG-11) — header, BASIC_WL+.
* ``PayeeTradeParty`` (BG-10) — settlement, BASIC_WL+.
* ``ShipToTradeParty`` (BG-13), ``ShipFromTradeParty`` (BG-X-30),
  ``UltimateShipToTradeParty`` (BG-X-27) — delivery.
* ``ProductEndUserTradeParty`` (BG-X-18) — agreement, EXTENDED.

Sub-elements (``PostalTradeAddress``, ``LegalOrganization``,
``TradeContact``, ``URIUniversalCommunication``, ``GlobalID``,
``ISO6523SchemeId``, ``TaxSchemeId``, ``SpecifiedTaxRegistration``)
are factored at the top of the file because they're reused across
party roles.

Validation rules covered (or missing) in this module:

* △ ``BR-CO-9`` — ``TaxSchemeId.validate_internal`` checks the
  ``schemeID ∈ {VA, FC}`` constraint, but does NOT yet check that the
  VAT identifier value starts with an ISO 3166-1 alpha-2 country
  prefix (Greece may use ``EL``). See
  ``docs/IMPLEMENTATION_PLAN.md §3``.
* — ``BR-CO-26`` (Seller automatic identification: BT-29 OR BT-30 OR
  BT-31). Not enforced.
* — ``BR-18 / BR-19 / BR-20 / BR-56`` (tax representative requires
  name / address / country / VAT ID): all implicit through required
  fields on :class:`SellerTaxRepresentativeTradeParty`.
* — ``BR-62 / BR-63`` (electronic address requires ``schemeID``):
  required by the schema, not yet enforced at the dataclass level.

All ``SchemeID`` / ``SchemeId`` / ``scheme_id`` names follow the XSD's
``schemeID`` attribute spelling (no ``a`` after ``schem``).
"""

from dataclasses import dataclass, field
from typing import ClassVar, Self, override

from tagic.xml import XML

from carthorse.schema.element import Element, ETElement, ValidationError
from carthorse.schema.types import Profile


@dataclass(kw_only=True, slots=True)
class SchemeID(Element):
    """``udt:IDType`` value with an optional ``schemeID`` attribute.

    The XSD makes ``schemeID`` optional; the appendix narrative for
    individual BTs (BT-30, BT-47, BT-46-1, …) flags whether the
    attribute is required *for that BT*. This base class is permissive
    — subclasses such as :class:`TaxSchemeId` enforce stricter
    constraints in ``validate_internal``.
    """

    tag: ClassVar[str] = "ID"

    id: str
    scheme_id: str | None = None
    """Optional identification scheme code (``schemeID`` attribute)."""

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
    """ISO 6523 SchemeId.

    Note: If the identification scheme is used, it shall be chosen
    from the entries of the list published by the ISO/IEC 6523
    Maintenance Agency.

    Application: In particular, the following codes may be used:
        0021 : SWIFT
        0088 : EAN
        0060 : DUNS
        0177 : ODETTE

    Code list: ISO 6523
    https://test-docs.peppol.eu/poacc/billing/3.0/2024-q4-release/codelist/ICD/
    """


@dataclass(kw_only=True, slots=True)
class GlobalID(ISO6523SchemeId):
    """GlobalID

    SchemeID:
    EN 16931-ID: BT-29-1 (Seller), BT-46-1 (Buyer)
    """

    tag: ClassVar[str] = "GlobalID"
    profile: ClassVar[Profile] = Profile.BASIC_WL


@dataclass(kw_only=True, slots=True)
class URIID(SchemeID):
    """GlobalID

    SchemeID:
    EN 16931-ID: BT-34 (Seller), BT-49 (Buyer)
    """

    tag: ClassVar[str] = "URIID"
    profile: ClassVar[Profile] = Profile.BASIC_WL


@dataclass(kw_only=True, slots=True)
class PostalTradeAddress(Element):
    """``ram:TradeAddressType`` — postal address group (BG-5 / BG-8 / …).

    Field order follows the Factur-X XSD ``<xs:sequence>``:
    ``PostcodeCode``, ``LineOne``, ``LineTwo``, ``LineThree``,
    ``CityName``, ``CountryID``, [``CountrySubDivisionName``]. The
    XSD makes every line element ``minOccurs="0"`` and ``CountryID``
    required; carthorse therefore keeps ``country_id`` required while
    every other field is optional. :class:`PostalTradeAddressExtended`
    appends ``country_subdivision`` (the final field in the sequence).
    """

    tag: ClassVar[str] = "PostalTradeAddress"

    postcode: str | None = field(
        default=None, metadata={"tag": "PostcodeCode", "profile": Profile.BASIC_WL}
    )
    """Postal code."""
    line_one: str | None = field(
        default=None, metadata={"tag": "LineOne", "profile": Profile.BASIC_WL}
    )
    """Address line 1.

    Note: The street or PO box. For major customer addresses this
    field must be set to "-".

    Example: Lieferantenstraße 20
    """
    line_two: str | None = field(
        default=None, metadata={"tag": "LineTwo", "profile": Profile.BASIC_WL}
    )
    """Address line 2.

    Example: Gebäude 3
    """
    line_three: str | None = field(
        default=None, metadata={"tag": "LineThree", "profile": Profile.BASIC_WL}
    )
    """Address line 3.

    Example: Tür B
    """
    city_name: str | None = field(
        default=None, metadata={"tag": "CityName", "profile": Profile.BASIC_WL}
    )
    """City.
    Example: München
    """
    country_id: str = field(metadata={"tag": "CountryID"})
    """Country code.

    Code list: ISO 3166-1, only the alpha-2 representation may be used.

    Example: DE
    """


@dataclass(kw_only=True, slots=True)
class PostalTradeAddressExtended(PostalTradeAddress):
    country_subdivision: str | None = field(
        default=None,
        metadata={"tag": "CountrySubDivisionName", "profile": Profile.BASIC_WL},
    )
    """Country subdivision (state / region).

    Example: NRW

    EN 16931-ID: BT-68 (SellerTaxRepresentativeTradeParty)
    """


@dataclass(kw_only=True, slots=True)
class PhoneNumber(Element):
    tag: ClassVar[str] = "TelephoneUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Telephone number of the contact.

    Example: +49 (123) 56789-0

    EN 16931-ID: BT-42 (Seller), BT-57 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class FaxNumber(Element):
    tag: ClassVar[str] = "FaxUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    number: str = field(metadata={"tag": "CompleteNumber", "profile": Profile.COMFORT})
    """Fax number of the contact.

    Example: +49 (123) 456789-999
    """


@dataclass(kw_only=True, slots=True)
class EmailURI(Element):
    tag: ClassVar[str] = "EmailURIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.COMFORT

    address: str | None = field(
        default=None, metadata={"tag": "URIID", "profile": Profile.COMFORT}
    )
    """Email address of the contact.

    Example: karin.mustermann@seller.tld

    EN 16931-ID: BT-43 (Seller), BT-58 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class TradeContact(Element):
    tag: ClassVar[str] = "DefinedTradeContact"
    profile: ClassVar[Profile] = Profile.COMFORT

    person_name: str | None = field(
        default=None, metadata={"tag": "PersonName", "profile": Profile.COMFORT}
    )
    """Seller / Buyer contact point name.

    A contact point for a legal entity or person, e.g. the name of the
    contact person.

    EN 16931-ID: BT-41 (Seller), BT-56 (Buyer)
    """
    department_name: str | None = field(
        default=None, metadata={"tag": "DepartmentName", "profile": Profile.COMFORT}
    )
    """Seller / Buyer contact department name.

    A contact point for a legal entity or person, e.g. the name of the
    department or office.

    EN 16931-ID: BT-41-0 (Seller), BT-56-0 (Buyer)
    """
    telephone: PhoneNumber | None = None
    """Seller / Buyer telephone number."""
    fax: FaxNumber | None = None
    """Seller / Buyer fax number."""
    email: EmailURI | None = None
    """Seller / Buyer email address."""


@dataclass(kw_only=True, slots=True)
class LegalOrganization(Element):
    """Legal organization details."""

    tag: ClassVar[str] = "SpecifiedLegalOrganization"

    id: ISO6523SchemeId | None = None
    """Seller / Buyer legal registration identifier.

    An identifier issued by an official registrar that identifies the
    Seller / Buyer as a legal entity or person.

    EN 16931-ID: BT-30 (Seller), BT-47 (Buyer)
    """
    trade_name: str | None = field(
        default=None,
        metadata={"tag": "TradingBusinessName", "profile": Profile.BASIC_WL},
    )
    """Seller / Buyer trading name.

    A name by which the Seller / Buyer is known, if different from the
    Seller's / Buyer's name (also known as Business name).

    EN 16931-ID: BT-28 (Seller), BT-45 (Buyer)
    """
    trade_address: PostalTradeAddress | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Business address details."""


@dataclass(kw_only=True, slots=True)
class URIUniversalCommunication(Element):
    """Electronic address details."""

    tag: ClassVar[str] = "URIUniversalCommunication"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    uri_id: URIID
    """Seller / Buyer electronic address.

    Seller: identifies the electronic address of the Seller to which
    the application level response to the Invoice may be sent.

    Buyer: identifies the electronic address of the Buyer to which the
    Invoice is sent.

    EN 16931-ID: BT-34 (Seller), BT-49 (Buyer)
    """


@dataclass(kw_only=True, slots=True)
class TaxSchemeId(ISO6523SchemeId):
    """VAT identification number / local tax identifier (BT-31, BT-32, BT-48).

    Allowed ``scheme_id`` codes:

    * ``VA`` — VAT identification number (BT-31, BT-48)
    * ``FC`` — local tax identifier / Steuernummer (BT-32)

    Rendered as ``<ram:ID schemeID="VA|FC">…</ram:ID>`` inside
    :class:`SpecifiedTaxRegistration`. The element name is plain ``ID``
    (inherited from :class:`SchemeID`); earlier versions of this module
    incorrectly emitted ``<ram:GlobalID>``.

    EN 16931-ID: BT-31-0 / BT-32-0 (Seller); BT-48-0 (Buyer).
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
    """Buyer / Seller tax registration details."""

    tag: ClassVar[str] = "SpecifiedTaxRegistration"

    id: TaxSchemeId


@dataclass(kw_only=True, slots=True)
class SellerTradeParty(Element):
    """Seller — details about the Seller (supplier of goods or services).

    A group of business terms providing information about the Seller.

    Field order follows the ``ram:TradePartyType`` XSD ``<xs:sequence>``:
    ID, GlobalID, Name, Description, SpecifiedLegalOrganization,
    DefinedTradeContact, PostalTradeAddress, URIUniversalCommunication,
    SpecifiedTaxRegistration.

    EN 16931-ID: BG-4
    """

    tag: ClassVar[str] = "SellerTradeParty"

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.BASIC_WL}
    )
    """Seller identifier / supplier number assigned by the customer.

    Note: In many systems the Seller identifier is key information.
    Several Seller identifiers may be assigned or specified. They may
    be differentiated by using different identification schemes. If no
    scheme is given, it should be known to Buyer and Seller, e.g. a
    previously exchanged Seller identifier assigned by the Buyer.

    Application: If the Seller has a Global ID it should be used.
    Otherwise the ID field is used.

    EN 16931-ID: BT-29
    """
    global_ids: list[GlobalID] | None = None
    """Seller global identifier: GLN, DUNS, BIC, ODETTE, …

    Note: The identification scheme of the Seller identifier is an
    identifier uniquely assigned to a Seller by a global registration
    organisation.

    EN 16931-ID: BT-29-0
    """
    name: str = field(metadata={"tag": "Name"})
    """Seller name.

    The full formal name by which the Seller is registered in the
    national registry of legal entities or as a taxable person, or
    otherwise trades as a person or persons.

    EN 16931-ID: BT-27
    """
    description: str | None = field(
        default=None, metadata={"tag": "Description", "profile": Profile.COMFORT}
    )
    """Seller additional legal information.

    Additional legal information relevant for the Seller, such as
    share capital.

    EN 16931-ID: BT-33
    """
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""
    contact: TradeContact | None = None
    """Seller contact details.

    A group of business terms providing contact information relevant
    for the Seller.

    EN 16931-ID: BG-6
    """
    address: PostalTradeAddressExtended
    """Seller postal address.

    A group of business terms providing information about the Seller's
    address. Sufficient components of the address are to be filled in
    in order to comply with legal requirements.

    EN 16931-ID: BG-5
    """
    electronic_address: URIUniversalCommunication | None = None
    """Electronic address details."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Seller tax registration / VAT identifier.

    The local identification (defined by the Seller's address) of the
    Seller for tax purposes, or a reference that enables the Seller to
    state his registered tax status. The Seller VAT identifier.

    EN 16931-ID: BT-31, BT-32
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
    """Buyer — details about the Buyer (recipient of goods or services).

    A group of business terms providing information about the Buyer.

    EN 16931-ID: BG-7
    """

    tag: ClassVar[str] = "BuyerTradeParty"

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.BASIC_WL}
    )
    """Buyer identifier / customer number.

    Note: If no scheme is given, it should be known to Buyer and
    Seller, e.g. a previously exchanged Buyer identifier assigned by
    the Seller.

    EN 16931-ID: BT-46
    """
    global_ids: list[GlobalID] | None = None
    """Buyer global identifier: GLN, DUNS, BIC, ODETTE, …

    Note: The identification scheme of the Buyer identifier is an
    identifier uniquely assigned to a Buyer by a global registration
    organisation.

    EN 16931-ID: BT-46-0
    """
    name: str = field(metadata={"tag": "Name"})
    """Buyer name.

    The full name of the Buyer.

    EN 16931-ID: BT-44
    """
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""
    contact: TradeContact | None = None
    """Buyer contact details.

    A group of business terms providing contact information relevant
    for the Buyer. Contact information may be given by the Buyer when
    ordering, or exchanged before ordering as master data. Contact
    information should not be used for internal routing of received
    Invoices by the recipient; for this the Buyer reference should be
    used.

    EN 16931-ID: BG-9
    """
    address: PostalTradeAddressExtended | None = None
    """Buyer postal address.

    Optional at MINIMUM (the Factur-X 1.08 MINIMUM XSD makes the whole
    ``PostalTradeAddress`` element ``minOccurs="0"`` on ``TradePartyType``,
    and the MINIMUM appendix narrative does NOT list BG-8 as required).
    BR-10 enforces presence from BASIC_WL onwards in
    :meth:`BuyerTradeParty.validate_internal`.

    EN 16931-ID: BG-8
    """
    electronic_address: URIUniversalCommunication | None = None
    """Electronic address details."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Buyer tax registration / VAT identifier.

    The XSD permits up to two ``SpecifiedTaxRegistration`` siblings on
    ``ram:TradePartyType`` — one VAT identifier (``schemeID="VA"``,
    BT-48) and one local tax identifier (``schemeID="FC"``).
    Bilingual buyers therefore need a list, not a single value.

    EN 16931-ID: BT-48 (VA), BT-48-0 (FC)
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
                    "BR-10",
                    "An Invoice shall contain the Buyer postal address (BG-8).",
                )
            )
        errors.extend(
            super(BuyerTradeParty, self).validate_internal(profile)
        )
        return errors


@dataclass(kw_only=True, slots=True)
class SellerTaxRepresentativeTradeParty(Element):
    """Seller tax representative party.

    EN 16931-ID: BG-11
    """

    tag: ClassVar[str] = "SellerTaxRepresentativeTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: str | None = field(
        default=None, metadata={"tag": "ID", "profile": Profile.EXTENDED}
    )
    """Tax representative identifier."""
    global_ids: list[GlobalID] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Tax representative global identifier."""
    name: str = field(metadata={"tag": "Name"})
    """Seller tax representative name.

    EN 16931-ID: BT-62
    """
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Legal organization details."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Contact details."""
    address: PostalTradeAddressExtended
    """Seller tax representative postal address.

    A group of business terms providing information about the postal
    address of the Seller's tax representative. If the Seller is
    represented by a tax representative responsible for paying the VAT
    due, the name and postal address of the Seller's tax
    representative must be stated on the Invoice. Sufficient
    components of the address are to be filled in in order to comply
    with legal requirements.

    EN 16931-ID: BG-12
    """
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Electronic address details."""
    tax_registrations: SpecifiedTaxRegistration
    """Seller tax representative VAT identifier details.

    VAT identifier with country code prefix according to EN ISO 3166-1
    alpha-2 "Codes for the representation of names of countries and
    their subdivisions".

    EN 16931-ID: BT-63
    """


@dataclass(kw_only=True, slots=True)
class ProductEndUserTradeParty(Element):
    """Details about the product end user."""

    tag: ClassVar[str] = "ProductEndUserTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    id: str | None = field(default=None, metadata={"tag": "ID"})
    """Identifier of the product end user."""
    global_ids: list[GlobalID] | None = None
    """Global identifier of the product end user."""
    name: str = field(metadata={"tag": "Name"})
    """End user name / business name."""
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""
    contact: TradeContact | None = None
    """Product end user contact details."""
    address: PostalTradeAddressExtended | None = None
    """Product end user address details."""
    electronic_address: URIUniversalCommunication | None = None
    """Electronic address details."""
    tax_registrations: SpecifiedTaxRegistration | None = field(
        default=None, metadata={"profile": Profile.BASIC_WL}
    )
    """Tax registration details for the product end user.

    Tax number, VAT identifier.
    """


@dataclass(kw_only=True, slots=True)
class ShipToTradeParty(Element):
    """Deliver to party / ship-to details.

    A group of business terms providing information about where and
    when the goods and services invoiced are delivered.

    EN 16931-ID: BG-13
    """

    tag: ClassVar[str] = "ShipToTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Deliver to location identifier / ship-to party identifier.

    An identifier of the location to which the goods are delivered or
    where the services are provided.

    If no scheme is given, it should be known to Buyer and Seller,
    e.g. a previously exchanged identifier assigned by the Buyer or
    Seller.

    EN 16931-ID: BT-71
    """
    global_id: GlobalID | None = None
    """Global identifier of the deliver-to location.

    EN 16931-ID: BT-71-0
    """
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Deliver to party name / business name.

    The name of the party to which the goods are delivered or for
    which the services are provided. Must be used if the deliver-to
    party is not identical to the Buyer.

    EN 16931-ID: BT-70
    """
    legal_organization: LegalOrganization | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Legal organization details."""
    contact: TradeContact | None = field(
        default=None, metadata={"profile": Profile.COMFORT}
    )
    """Deliver to party contact details."""
    address: PostalTradeAddressExtended | None = None
    """Deliver to address.

    A group of business terms providing information about the address
    to which goods invoiced are delivered or at which services
    invoiced are provided.

    In the case of pickup, the deliver-to address is the pickup
    address. Sufficient components of the address are to be filled in
    in order to comply with legal requirements.

    EN 16931-ID: BG-15
    """
    electronic_address: URIUniversalCommunication | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Electronic address details."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = field(
        default=None, metadata={"profile": Profile.EXTENDED}
    )
    """Deliver to party tax registration details.

    Tax number, VAT identifier.
    """


@dataclass(kw_only=True, slots=True)
class ShipFromTradeParty(Element):
    """Identification of the ship-from party."""

    tag: ClassVar[str] = "ShipFromTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ship-from party identifier.

    The ship-from identifier is a unique, bilaterally agreed
    identifier of the sender.
    """
    global_id: GlobalID | None = None
    """Global identifier of the ship-from party."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ship-from party name / business name."""
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""
    contact: TradeContact | None = None
    """Ship-from party contact details."""
    address: PostalTradeAddressExtended | None = None
    """Ship-from party address details."""
    electronic_address: URIUniversalCommunication | None = None
    """Electronic address details."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ship-from party tax registration details.

    Tax number, VAT identifier.
    """


@dataclass(kw_only=True, slots=True)
class UltimateShipToTradeParty(Element):
    """Details about the ultimate ship-to party."""

    tag: ClassVar[str] = "UltimateShipToTradeParty"
    profile: ClassVar[Profile] = Profile.EXTENDED

    # TODO: check other parties: 0..n
    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Ultimate ship-to party identifier.

    The ultimate ship-to identifier is a unique, bilaterally agreed
    identifier of the final recipient.
    """
    global_ids: list[GlobalID] | None = None
    """Global identifier of the ultimate ship-to party."""
    name: str | None = field(default=None, metadata={"tag": "Name"})
    """Ultimate ship-to party name / business name."""
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""
    contact: TradeContact | None = None
    """Ultimate ship-to party contact details."""
    address: PostalTradeAddressExtended | None = None
    """Ultimate ship-to party address details."""
    electronic_address: URIUniversalCommunication | None = None
    """Electronic address details."""
    tax_registrations: list[SpecifiedTaxRegistration] | None = None
    """Ultimate ship-to party tax registration details.

    Tax number, VAT identifier.
    """


@dataclass(kw_only=True, slots=True)
class PayeeTradeParty(Element):
    """Payee — party that receives the payment.

    A group of business terms providing information about the Payee,
    i.e. the party that receives the payment.

    The role of Payee may also be filled by a party other than the
    Seller, e.g. a factoring service.

    EN 16931-ID: BG-10
    """

    tag: ClassVar[str] = "PayeeTradeParty"
    profile: ClassVar[Profile] = Profile.BASIC_WL

    id: list[str] | None = field(default=None, metadata={"tag": "ID"})
    """Payee identifier.

    An identifier for the Payee.

    If no scheme is given, it should be known to Buyer and Seller,
    e.g. a previously exchanged identifier assigned by the Buyer or
    Seller.

    EN 16931-ID: BT-60
    """
    global_id: GlobalID | None = None
    """Global identifier of the Payee."""
    name: str = field(metadata={"tag": "Name"})
    """Payee name / business name.

    Must be used if the Payee is not identical to the Seller. The
    Payee name may however be the same as the Seller name.

    EN 16931-ID: BT-59
    """
    legal_organization: LegalOrganization | None = None
    """Legal organization details."""

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
