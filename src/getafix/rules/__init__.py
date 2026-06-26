"""Business-rule validators for :mod:`getafix.schema` elements.

Each submodule defines free-standing validator functions for the
``BR-*`` rules that apply to one section of the model (settlement,
accounting, party, line, trade). Element classes in
``getafix.schema.<topic>`` import the validators they need
directly and wire them into a ``_validators: ClassVar[tuple[...]]``
attribute that ``Element.validate_internal`` iterates.

See ``CONTRIBUTING.md`` "Validator architecture" for the design.
"""

from getafix.rules._types import Validator as Validator
