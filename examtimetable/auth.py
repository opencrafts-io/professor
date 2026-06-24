from rest_framework.permissions import BasePermission
from django.conf import settings


class IngestAPIKeyPermission(BasePermission):
    def has_permission(self, request, view):
        api_key = request.META.get("HTTP_X_API_KEY")
        expected = getattr(settings, "INGEST_API_KEY", None)
        if not api_key or not expected:
            return False
        return api_key == expected
