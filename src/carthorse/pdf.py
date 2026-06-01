"""Embed and extract Factur-X / ZUGFeRD XML in PDF documents.

Importing this module requires the optional ``pypdf`` dependency::

    pip install 'carthorse[pdf]'

Two operations:

* :func:`attach_xml` — embed an XML file in a PDF under a configurable
  attachment name. Defaults to ``factur-x.xml`` (the Factur-X 1.x /
  ZUGFeRD 2.x convention); pass ``"zugferd-invoice.xml"`` for the
  legacy ZUGFeRD 1.0 layout, ``"xrechnung.xml"`` for XRechnung, etc.
* :func:`extract_xml` — return the bytes of the first embedded file
  whose name matches one of the standard Factur-X / ZUGFeRD /
  XRechnung / Order-X filenames.

Caveat: :func:`attach_xml` produces a valid PDF with a generic embedded
file, but does *not* upgrade the document to PDF/A-3 — the formal
compliance requirement for Factur-X and ZUGFeRD invoices. Use a
dedicated PDF/A-3 converter when full conformance is needed; this
module only handles the file-attachment step.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pypdf import PdfReader, PdfWriter

STANDARD_LOCATIONS: tuple[str, ...] = (
    "factur-x.xml",  # Factur-X 1.x / ZUGFeRD 2.x
    "ZUGFeRD-invoice.xml",  # ZUGFeRD 1.0 (legacy)
    "zugferd-invoice.xml",  # ZUGFeRD 1.0 alt casing
    "xrechnung.xml",  # XRechnung
    "order-x.xml",  # Order-X
)
"""Conventional filenames carthorse will search for, in priority order."""

DEFAULT_ATTACHMENT_NAME: str = STANDARD_LOCATIONS[0]
"""Name used by :func:`attach_xml` when the caller doesn't override it."""


def attach_xml(
    pdf_in: Path,
    xml: Path | bytes,
    *,
    pdf_out: Path | None = None,
    attachment_name: str = DEFAULT_ATTACHMENT_NAME,
) -> Path:
    """Embed ``xml`` in ``pdf_in`` as an embedded file and write the result.

    ``xml`` may be a :class:`~pathlib.Path` to read from, or raw bytes
    to embed verbatim. ``pdf_out`` defaults to ``pdf_in`` (in-place
    rewrite); pass an explicit target to write to a different file.

    The attachment is stored under ``attachment_name`` in the PDF's
    embedded-files name tree. The default matches the Factur-X 1.x /
    ZUGFeRD 2.x convention; override for ZUGFeRD 1.0 or XRechnung.

    Returns the path the PDF was written to.
    """
    xml_bytes = xml.read_bytes() if isinstance(xml, Path) else xml
    writer = PdfWriter(clone_from=str(pdf_in))
    _ = writer.add_attachment(attachment_name, xml_bytes)
    target = pdf_out if pdf_out is not None else pdf_in
    with target.open("wb") as fp:
        _ = writer.write(fp)
    return target


def extract_xml(
    pdf: Path, *, candidates: Sequence[str] = STANDARD_LOCATIONS
) -> bytes | None:
    """Return the bytes of the first embedded file matching ``candidates``.

    Names are compared case-insensitively, so e.g. ``factur-x.xml``,
    ``Factur-X.xml`` and ``FACTUR-X.XML`` are all accepted. Search
    order follows ``candidates``; the first hit wins.

    Returns ``None`` when the PDF has no embedded files or none of
    them matches a candidate.
    """
    reader = PdfReader(str(pdf))
    attachments = reader.attachments
    if not attachments:
        return None
    by_lowercase = {name.lower(): name for name in attachments}
    for candidate in candidates:
        original = by_lowercase.get(candidate.lower())
        if original is None:
            continue
        # ``pypdf`` returns a list of byte payloads per attachment name
        # (an attachment name can be re-used inside one PDF — rare in
        # the Factur-X corpus but allowed). Return the first payload.
        payload = attachments[original]
        if payload:
            return payload[0]
    return None
