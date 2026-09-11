import json

from django.test import RequestFactory
from rest_framework import serializers

from notes.errors import APIError, ErrorCode, NotesAPIView


class BoomView(NotesAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise APIError(
            "Unsupported file type.", code=ErrorCode.UNSUPPORTED_FILE_TYPE, status_code=400
        )


class ValidationView(NotesAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise serializers.ValidationError({"file": ["This field is required."]})


def _body(response):
    response.render()
    return json.loads(response.content)


def test_api_error_renders_envelope():
    response = BoomView.as_view()(RequestFactory().get("/x"))
    assert response.status_code == 400
    assert _body(response) == {
        "error": {
            "code": "unsupported_file_type",
            "message": "Unsupported file type.",
            "details": {},
        }
    }


def test_drf_validation_error_becomes_validation_error_code():
    response = ValidationView.as_view()(RequestFactory().get("/x"))
    assert response.status_code == 400
    body = _body(response)
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"] == {"file": ["This field is required."]}


def test_unhandled_exception_becomes_internal_error():
    from notes.errors import envelope_exception_handler

    response = envelope_exception_handler(RuntimeError("boom"), {})
    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
