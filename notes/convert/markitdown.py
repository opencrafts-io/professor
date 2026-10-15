from io import BytesIO
from pathlib import Path

from markitdown import MarkItDown

from .base import ConversionError


class MarkItDownConverter:
    """
    Convert an uploaded document stream to Markdown without
    filesystem or network access.
    """

    def __init__(self):
        self._converter = MarkItDown(enable_plugins=False)

    def to_markdown(self, file_bytes, filename):
        extension = Path(filename).suffix.lower()
        if not extension:
            raise ConversionError("Uploaded document has no file extension.")
        try:
            result = self._converter.convert_stream(
                BytesIO(file_bytes), file_extension=extension
            )
            markdown = result.text_content
        except Exception as exc:
            raise ConversionError(
                "Could not convert uploaded document to Markdown."
            ) from exc
        if not isinstance(markdown, str) or not markdown.strip():
            raise ConversionError("Document contains no extractable text.")
        return markdown
