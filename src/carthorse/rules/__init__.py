"""Business-rule validators for :mod:`carthorse.schema` elements.

Each submodule defines free-standing validator functions for the
``BR-*`` rules that apply to one section of the model (settlement,
accounting, party, line, trade). Element classes in
``carthorse.schema.<topic>`` import the validators they need
directly and wire them into a ``_validators: ClassVar[tuple[...]]``
attribute that ``Element.validate_internal`` iterates.

See ``docs/VALIDATOR_REFACTOR.md`` for the rework plan.
"""

from carthorse.rules._types import Validator as Validator
