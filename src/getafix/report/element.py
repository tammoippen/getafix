"""Rendering for the base :mod:`getafix.schema.element` types.

The schema base module owns :class:`~getafix.schema.element.ValidationError`;
its report counterpart owns :func:`render_validation_errors`, the public
entry point that turns the output of ``Document.validate_internal`` into
a console table (or a green success note when the list is empty).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from getafix.errors import ValidationError


def render_validation_errors(
    errors: Sequence[ValidationError], console: Console | None = None
) -> None:
    """Print ``errors`` as a red-bordered table; print a success note when empty."""
    console = console or Console()
    if not errors:
        console.print("[green]✓ No validation errors[/green]")
        return
    table = Table(
        title=f"Validation errors ({len(errors)})",
        title_style="bold red",
        border_style="red",
        show_lines=False,
    )
    table.add_column("Rule", style="yellow", no_wrap=True)
    table.add_column("Message")
    for err in errors:
        table.add_row(err.code, err.message)
    console.print(table)
