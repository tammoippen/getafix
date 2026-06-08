"""Shared rendering primitives used across :mod:`getafix.report`.

Mirrors :mod:`getafix.rules._types`: where the rules package defines a
:data:`~getafix.rules.Validator` shape plus a couple of validator
factories, the report package defines a :data:`SectionRenderer` shape
plus the two helpers that give every section its consistent look —

* :func:`described_panel` — wrap a panel body under a one-line, dim
  description of *what the section means*;
* :func:`describe_table` — fold the same kind of description into the
  table's title block as a dim subtitle line.

Keeping these in one place is what lets each ``report/<topic>.py``
focus purely on turning its schema elements into rows / cells while the
framing (titles, borders, descriptions) stays uniform.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from getafix.schema.element import Element

type SectionRenderer[T: Element] = Callable[[T], RenderableType | None]
"""Signature of a report-section renderer.

``T`` is the concrete :class:`~getafix.schema.element.Element` the
section is built from. The function returns a Rich renderable
(:class:`~rich.panel.Panel` / :class:`~rich.table.Table`) or ``None``
to signal "nothing to show" so the caller can skip an empty section
rather than printing an empty box.

Not every renderer fits the shape exactly — money-bearing sections also
take the document currency, and :func:`getafix.report.party.party_panel`
takes the party role — but the ``element -> renderable | None`` core is
the common contract.
"""

# Per-section descriptions render in this style: muted, so the data
# stays the focus while the one-liner explains what the box is.
_DESCRIPTION_STYLE = "dim italic"


def described_panel(
    body: RenderableType, *, title: str, description: str, border_style: str
) -> Panel:
    """Frame ``body`` in a titled panel with a dim description on top.

    The description is a short, human sentence explaining what the
    section means (e.g. "The supplier issuing the invoice."). It is
    placed above the body so a reader skimming the report can orient
    themselves before reading the data.
    """
    content: RenderableType = (
        Group(Text(description, style=_DESCRIPTION_STYLE), body)
        if description
        else body
    )
    return Panel(content, title=title, border_style=border_style)


def describe_table(table: Table, description: str) -> Table:
    """Fold ``description`` into the table title as a dim subtitle line.

    The description sits directly under the title (above the header row),
    so it reads as the table's own subtitle. A bottom caption was
    avoided because, between two stacked sections, it reads like the
    heading of the *next* table.
    """
    name = "" if table.title is None else str(table.title)
    table.title = Text.assemble((name, "bold"), "\n", (description, _DESCRIPTION_STYLE))
    # Styles now live on the Text spans; drop the base title style so it
    # doesn't bleed bold onto the dim subtitle line.
    table.title_style = None
    return table
