class ConversionError(Exception):
    """A document could not be converted to Markdown."""


class InputTooLargeError(ConversionError):
    """Converted Markdown exceeds the LLM input cap.

    Distinct from a failed conversion so the oversized-document case never
    takes the scanned-PDF native fallback, which would send the whole file
    to the model and void the cost bound the cap exists for.
    """
