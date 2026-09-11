from typing import Protocol


class ConversionError(Exception):
    """A document could not be converted to PDF."""


class DocumentConverter(Protocol):
    def to_pdf(self, file_bytes, filename) -> bytes: ...
