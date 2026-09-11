import pytest

from notes.convert.base import ConversionError
from notes.convert.fake import FakeConverter
from notes.convert.ilovepdf import ILovePDFConverter
from notes.services.generation import get_converter


def test_fake_converter_returns_pdf_and_records_calls():
    converter = FakeConverter()
    result = converter.to_pdf(b"PK\x03\x04 body", "notes.docx")
    assert result.startswith(b"%PDF-")
    assert converter.calls == ["notes.docx"]


def test_fake_converter_can_be_scripted_to_fail():
    converter = FakeConverter(error=ConversionError("upstream down"))
    with pytest.raises(ConversionError):
        converter.to_pdf(b"PK\x03\x04", "notes.docx")


class StubHTTP:
    """Routes the ilovepdf request sequence; body/status overridable per step."""

    def __init__(self, download_body=b"%PDF-1.4 converted", statuses=None):
        self.download_body = download_body
        self.statuses = statuses or {}
        self.requests = []

    class Response:
        def __init__(self, status_code, payload=None, content=b""):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = content
            self.text = str(payload)

        def json(self):
            return self._payload

    def _respond(self, step, payload=None, content=b""):
        return self.Response(self.statuses.get(step, 200), payload, content)

    def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        if url.endswith("/auth"):
            return self._respond("auth", {"token": "tok123"})
        if url.endswith("/upload"):
            return self._respond("upload", {"server_filename": "srv.docx"})
        if url.endswith("/process"):
            return self._respond("process", {"status": "TaskSuccess"})
        raise AssertionError(f"unexpected POST {url}")

    def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if "/start/officepdf" in url:
            return self._respond("start", {"server": "srv.ilovepdf.com", "task": "t1"})
        if "/download/" in url:
            return self._respond("download", content=self.download_body)
        raise AssertionError(f"unexpected GET {url}")


def test_ilovepdf_converter_happy_path(monkeypatch):
    stub = StubHTTP()
    monkeypatch.setattr("notes.convert.ilovepdf.requests", stub)
    converter = ILovePDFConverter(public_key="pk")
    result = converter.to_pdf(b"PK\x03\x04 body", "notes.docx")
    assert result == b"%PDF-1.4 converted"
    urls = [u for _, u, _ in stub.requests]
    assert urls[0].endswith("/auth")
    assert "/start/officepdf" in urls[1]
    assert all(
        k["headers"]["Authorization"] == "Bearer tok123" for _, _, k in stub.requests[1:]
    )


def test_ilovepdf_converter_raises_on_auth_failure(monkeypatch):
    stub = StubHTTP(statuses={"auth": 401})
    monkeypatch.setattr("notes.convert.ilovepdf.requests", stub)
    with pytest.raises(ConversionError):
        ILovePDFConverter(public_key="bad").to_pdf(b"PK\x03\x04", "notes.docx")


def test_ilovepdf_converter_raises_when_result_is_not_pdf(monkeypatch):
    stub = StubHTTP(download_body=b"<html>error page</html>")
    monkeypatch.setattr("notes.convert.ilovepdf.requests", stub)
    with pytest.raises(ConversionError):
        ILovePDFConverter(public_key="pk").to_pdf(b"PK\x03\x04", "notes.docx")


def test_get_converter_honours_settings_backend(settings):
    assert isinstance(get_converter(), FakeConverter)  # conftest forces "fake"
    settings.AI_CONVERTER_BACKEND = "ilovepdf"
    settings.ILOVEAPI_PUBLIC_KEY = "pk"
    assert isinstance(get_converter(), ILovePDFConverter)
