"""Validator type alias used across :mod:`carthorse.rules`.

Each rule submodule defines free-standing functions of the shape::

    def br_co_25(m: TradeSettlement, profile: Profile) -> list[ValidationError]:
        ...

The corresponding :mod:`carthorse.schema.<topic>` module imports the
functions it needs and exposes them via a
``_validators: ClassVar[tuple[Validator[...], ...]]`` attribute that
``Element.validate_internal`` iterates. See
``docs/VALIDATOR_REFACTOR.md`` for the architecture.
"""

from collections.abc import Callable

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
