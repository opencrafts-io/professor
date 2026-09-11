import logging

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("professor")


class ErrorCode:
    VALIDATION_ERROR = "validation_error"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    FILE_TOO_LARGE = "file_too_large"
    ENTITLEMENT_REQUIRED = "entitlement_required"
    ENTITLEMENT_UNAVAILABLE = "entitlement_unavailable"
    NOT_FOUND = "not_found"
    JOB_ALREADY_RUNNING = "job_already_running"
    INTERNAL_ERROR = "internal_error"


class APIError(APIException):
    def __init__(self, detail_message, *, code, status_code, details=None):
        super().__init__(detail=detail_message)
        self.status_code = status_code
        self.error_code = code
        self.error_details = details or {}


def _envelope(code, message, details, http_status):
    return Response(
        {"error": {"code": code, "message": message, "details": details}},
        status=http_status,
    )


def envelope_exception_handler(exc, context):
    if isinstance(exc, APIError):
        return _envelope(
            exc.error_code, str(exc.detail), exc.error_details, exc.status_code
        )
    if isinstance(exc, ValidationError):
        return _envelope(
            ErrorCode.VALIDATION_ERROR,
            "Invalid input.",
            exc.detail,
            status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, NotFound):
        return _envelope(
            ErrorCode.NOT_FOUND, str(exc.detail), {}, status.HTTP_404_NOT_FOUND
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        # Other DRF exceptions (auth, permission, throttle): keep the code stable per contract.
        code = getattr(exc, "error_code", None) or getattr(exc, "default_code", "error")
        message = (
            response.data.get("detail", str(exc.detail))
            if isinstance(response.data, dict)
            else str(exc.detail)
        )
        return _envelope(str(code), str(message), {}, response.status_code)

    logger.exception("Unhandled exception in notes API", exc_info=exc)
    return _envelope(
        ErrorCode.INTERNAL_ERROR,
        "An unexpected error occurred.",
        {},
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class NotesAPIView(APIView):
    def get_exception_handler(self):
        return envelope_exception_handler
