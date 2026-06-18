"""High-level factories for building profile-shaped invoices.

The :mod:`getafix.schema` dataclasses deliberately mirror the CII XML
tree one-to-one: every business term is set explicitly and nothing is
derived behind the caller's back. This package is the convenience layer
on top — factories that take the business inputs and compute everything
that *can* be computed. One module per profile, plus shared helpers:

* :mod:`getafix.build.minimum` — :func:`minimum_invoice` (header totals
  only) plus the MINIMUM-restricted :func:`~getafix.build.minimum.seller_party`
  / :func:`~getafix.build.minimum.buyer_party`.
* :mod:`getafix.build.basic_wl` — :func:`basic_wl_invoice` (VAT
  breakdown, still no line items) plus the full party builders.
* :mod:`getafix.build.basic` — :func:`line_item`, :func:`vat_breakdown`,
  :func:`basic_invoice` (full line-item document) plus the full party
  builders.
* :mod:`getafix.build._shared` — the cross-profile internals and the
  BG-22 totals computer (:func:`monetary_summation`).

This top level re-exports only the helpers whose valid-field set does
not depend on the profile (the invoice constructors, ``line_item``,
``vat_breakdown``, ``monetary_summation``). The **party builders are
profile-specific** — at MINIMUM only the country code is rendered, while
BASIC_WL+ additionally permits postcode / city / street lines — so they
are *not* re-exported here. Import ``seller_party`` / ``buyer_party``
from the module for the profile you are building
(``getafix.build.minimum`` vs. ``getafix.build.basic`` /
``getafix.build.basic_wl``); the profile-specific builders delegate to a
shared full-field worker.

The high-level builders stop at BASIC on purpose: COMFORT (EN 16931)
and EXTENDED add far more optional structure than a convenience
constructor can usefully default. Build those by hand against
:mod:`getafix.schema`.

Monetary inputs accept ``Decimal``, ``int`` or ``str`` (``float`` is
rejected — binary floats carry representation noise that leaks into
amounts). The factories return ordinary schema dataclasses, so any
field a factory does not expose can still be set afterwards before
calling :meth:`~getafix.schema.document.Document.validate` /
:meth:`~getafix.schema.document.Document.to_xml`.
"""

from getafix.build._shared import Numeric as Numeric
from getafix.build._shared import monetary_summation as monetary_summation
from getafix.build.basic import basic_invoice as basic_invoice
from getafix.build.basic import line_item as line_item
from getafix.build.basic import vat_breakdown as vat_breakdown
from getafix.build.basic_wl import basic_wl_invoice as basic_wl_invoice
from getafix.build.minimum import minimum_invoice as minimum_invoice

__all__ = [
    "Numeric",
    "basic_invoice",
    "basic_wl_invoice",
    "line_item",
    "minimum_invoice",
    "monetary_summation",
    "vat_breakdown",
]
