"""Validator type alias used across :mod:`carthorse.rules`.

Each rule submodule defines free-standing functions of the shape::

    def br_co_25(m: TradeSettlement, profile: Profile) -> list[ValidationError]: ...

The corresponding :mod:`carthorse.schema.<topic>` module imports the
functions it needs and exposes them via a
``_validators: ClassVar[tuple[Validator[...], ...]]`` attribute that
``Element.validate_internal`` iterates. See
``docs/VALIDATOR_REFACTOR.md`` for the architecture.

Also home to the :func:`max_decimals` factory used by the
``BR-DEC-*`` decimal-precision family — every monetary BT caps at
two decimals; one factory produces 21 single-field validators across
the schema.
"""

from collections.abc import Callable
from decimal import Decimal

from carthorse.schema.element import Element, ValidationError
from carthorse.schema.types import Profile

type Validator[T: Element] = Callable[[T, Profile], list[ValidationError]]
"""Signature of a business-rule validator function.

``T`` is the concrete :class:`~carthorse.schema.element.Element`
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

    def _check(m: T, profile: Profile) -> list[ValidationError]:
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
