import sys
from types import SimpleNamespace


def test_markitdown_converter_uses_an_in_memory_stream(monkeypatch):
    class StubMarkItDown:
        instances = []

        def __init__(self, **kwargs):
            self.calls = []
            self.instances.append(self)

        def convert_stream(self, stream, *, file_extension):
            self.calls.append((stream.read(), file_extension))
            return SimpleNamespace(text_content="## Budget\n\n| Year | Total |")

    monkeypatch.setitem(sys.modules, "markitdown", SimpleNamespace(MarkItDown=StubMarkItDown))
    sys.modules.pop("notes.convert.markitdown", None)
    from notes.convert.markitdown import MarkItDownConverter

    converter = MarkItDownConverter()
    assert converter.to_markdown(b"PK\x03\x04 workbook", "budget.xlsx") == "## Budget\n\n| Year | Total |"
    assert StubMarkItDown.instances[0].calls == [(b"PK\x03\x04 workbook", ".xlsx")]
