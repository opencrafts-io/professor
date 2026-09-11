FAKE_PDF = b"%PDF-1.4 fake converted document"


class FakeConverter:
    def __init__(self, pdf_bytes=FAKE_PDF, error=None):
        self._pdf_bytes = pdf_bytes
        self._error = error
        self.calls = []

    def to_pdf(self, file_bytes, filename):
        self.calls.append(filename)
        if self._error is not None:
            raise self._error
        return self._pdf_bytes
