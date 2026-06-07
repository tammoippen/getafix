"""Embed and extract Factur-X / ZUGFeRD XML in PDF documents.

Importing this module requires the optional ``pypdf`` dependency::

    pip install 'getafix[pdf]'

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

from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter

STANDARD_LOCATIONS: tuple[str, ...] = (
    "factur-x.xml",  # Factur-X 1.x / ZUGFeRD 2.x
    "ZUGFeRD-invoice.xml",  # ZUGFeRD 1.0 (legacy)
    "zugferd-invoice.xml",  # ZUGFeRD 1.0 alt casing
    "xrechnung.xml",  # XRechnung
    "order-x.xml",  # Order-X
)
"""Conventional filenames getafix will search for, in priority order."""

DEFAULT_ATTACHMENT_NAME: str = STANDARD_LOCATIONS[0]
"""Name used by :func:`attach_xml` when the caller doesn't override it."""


def attach_xml(
    pdf_in: Path | bytes,
    xml: Path | bytes,
    *,
    pdf_out: Path | None = None,
    attachment_name: str = DEFAULT_ATTACHMENT_NAME,
    metadata: Mapping[str, str] | None = None,
) -> Path | bytes:
    """Embed ``xml`` in ``pdf_in`` as an embedded file and write the result.

    ``pdf_in`` may be a :class:`~pathlib.Path` to read from, or the raw
    bytes of a PDF. ``xml`` may likewise be a :class:`~pathlib.Path` to
    read from, or raw bytes to embed verbatim.

    ``pdf_out`` selects where the result goes. When given, the PDF is
    written there and that :class:`~pathlib.Path` is returned. When
    omitted, a :class:`~pathlib.Path` ``pdf_in`` is rewritten in place
    (and returned); a bytes ``pdf_in`` causes the result to be returned
    as bytes.

    The attachment is stored under ``attachment_name`` in the PDF's
    embedded-files name tree. The default matches the Factur-X 1.x /
    ZUGFeRD 2.x convention; override for ZUGFeRD 1.0 or XRechnung.

    ``metadata``, when given, extends the PDF's document information
    dictionary (e.g. ``{"/Title": "Invoice 42"}``); existing entries are
    kept unless a given key overrides them.

    Returns the path the PDF was written to, or the result bytes when
    ``pdf_in`` is bytes and no ``pdf_out`` is given.
    """
    xml_bytes = xml.read_bytes() if isinstance(xml, Path) else xml
    clone_from = BytesIO(pdf_in) if isinstance(pdf_in, bytes) else str(pdf_in)
    writer = PdfWriter(clone_from=clone_from)
    _ = writer.add_attachment(attachment_name, xml_bytes)
    if metadata:
        writer.add_metadata(dict(metadata))
    target = pdf_out if pdf_out is not None else pdf_in
    if isinstance(target, bytes):
        buffer = BytesIO()
        _ = writer.write(buffer)
        return buffer.getvalue()
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
