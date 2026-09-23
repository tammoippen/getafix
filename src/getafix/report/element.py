"""Rendering for the base :mod:`getafix.schema.element` types.

The schema base module owns :class:`~getafix.schema.element.ValidationError`;
its report counterpart owns :func:`render_validation_errors`, the public
entry point that turns the output of ``Document.validate_internal`` into
a console table (or a green success note when the list is empty), with
warnings in a separate table.
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
    """Print errors as a red-bordered table and warnings as a yellow one;
    print a success note when there are no errors."""
    from getafix.errors import ValidationWarning

    console = console or Console()
    warnings = [e for e in errors if isinstance(e, ValidationWarning)]
    hard = [e for e in errors if not isinstance(e, ValidationWarning)]
    if hard:
        console.print(_findings_table(f"Validation errors ({len(hard)})", "red", hard))
    else:
        console.print("[green]✓ No validation errors[/green]")
    if warnings:
        console.print(
            _findings_table(
                f"Validation warnings ({len(warnings)})", "yellow", warnings
            )
        )


def _findings_table(title: str, color: str, items: Sequence[ValidationError]) -> Table:
    table = Table(
        title=title, title_style=f"bold {color}", border_style=color, show_lines=False
    )
    table.add_column("Rule", style="yellow", no_wrap=True)
    table.add_column("Message")
    for err in items:
        table.add_row(err.code, err.message)
    return table
