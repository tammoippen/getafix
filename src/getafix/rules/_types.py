"""Validator type alias used across :mod:`getafix.rules`.

Each rule submodule defines free-standing functions of the shape::

    def br_co_25(m: TradeSettlement, profile: Profile) -> list[ValidationError]: ...

The corresponding :mod:`getafix.schema.<topic>` module imports the
functions it needs and exposes them via a
``_validators: ClassVar[tuple[Validator[...], ...]]`` attribute that
``Element.validate_internal`` iterates.

Also home to the :func:`max_decimals` factory used by the
``BR-DEC-*`` decimal-precision family — every monetary BT caps at
two decimals; one factory produces 21 single-field validators across
the schema.
"""

from collections.abc import Callable
from decimal import Decimal

from getafix.schema.element import Element, ValidationError
from getafix.schema.types import Profile

type Validator[T: Element] = Callable[[T, Profile], list[ValidationError]]
"""Signature of a business-rule validator function.

``T`` is the concrete :class:`~getafix.schema.element.Element`
subclass the rule reads from (e.g. ``TradeSettlement``,
``ApplicableTradeTax``, ``Trade``). The function decides for itself
whether the rule applies at the given profile and which guards are
satisfied; an empty list means "no violation".
"""


def max_decimals[T: Element](
    code: str, *, field_name: str, max_places: int = 2
) -> Validator[T]:
    """Build a validator that caps a single Decimal field at
    ``max_places`` fractional digits.

    Used by the ``BR-DEC-*`` family — every monetary BT in EN 16931
    has at most two decimal places. The factory captures both the
    error code and the attribute name in its closure so each call
    produces a self-contained validator.

    The check skips ``None`` (the field is optional) and any value
    whose normalised exponent is ``>= 0`` (i.e. integer / fewer than
    ``max_places`` fractional digits).
    """

    def _check(m: T, _profile: Profile) -> list[ValidationError]:
        value = getattr(m, field_name, None)
        if not isinstance(value, Decimal):
            return []
        # The decimal exponent is negative when fractional digits are
        # present; ``-exponent`` is the count.
        exp = value.as_tuple().exponent
        if isinstance(exp, int) and -exp > max_places:
            return [
                ValidationError(
                    code,
                    f"{field_name} (BT) carries more than {max_places} "
                    f"decimal places ({value}).",
                )
            ]
        return []

    return _check


def fields_only_at[T: Element](
    profile_required: Profile, *field_names: str
) -> Validator[T]:
    """Build a validator that asserts the listed fields are ``None``
    when the runtime profile is *below* ``profile_required``.

    Used for EXTENDED-only additions on elements that also live at
    lower profiles — e.g. ``LineBuyerOrderReferencedDocument``
    exists at COMFORT but its ``issuer_assigned_id`` /
    ``formatted_issue_date_time`` extensions only become valid at
    EXTENDED. Without the runtime check, setting one of those at
    BASIC_WL would silently disappear at render time (the
    ``_field_profile`` machinery skips it) — the validator catches
    it loudly instead.

    Emits ``GETAFIX-FIELD-PROFILE`` for each populated-but-out-of-
    profile field. (Synthetic code: this is a getafix runtime
    check, not a BR-* rule from the schematron — the schematron
    relies on the XSD to enforce the profile gate.)
    """

    def _check(m: T, profile: Profile) -> list[ValidationError]:
        if profile >= profile_required:
            return []
        return [
            ValidationError(
                "GETAFIX-FIELD-PROFILE",
                f"{type(m).__name__}.{name}: only allowed at "
                f"{profile_required.name}+ profiles "
                f"(current profile: {profile.name}).",
            )
            for name in field_names
            if getattr(m, name, None) is not None
        ]

    return _check


def list_max_cardinality_below[T: Element](
    profile_below: Profile, max_count: int, field_name: str
) -> Validator[T]:
    """Build a validator that caps the length of a list field when
    the runtime profile is *below* ``profile_below``.

    Used for collections whose XSD ``maxOccurs`` widens at EXTENDED
    — e.g. ``TradeSettlement.terms`` (singleton up to COMFORT,
    unbounded at EXTENDED). Constructing a multi-entry list at a
    lower profile would render fine but trip XSD validation against
    the lower-profile schema; the validator catches it earlier.

    Emits ``GETAFIX-FIELD-CARDINALITY`` on violation.
    """

    def _check(m: T, profile: Profile) -> list[ValidationError]:
        if profile >= profile_below:
            return []
        value: list[object] | None = getattr(m, field_name, None)
        if value is None or len(value) <= max_count:
            return []
        return [
            ValidationError(
                "GETAFIX-FIELD-CARDINALITY",
                f"{type(m).__name__}.{field_name}: at most {max_count} "
                f"entry permitted below {profile_below.name} "
                f"(current profile: {profile.name}, got {len(value)}).",
            )
        ]

    return _check
