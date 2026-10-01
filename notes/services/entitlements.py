import logging

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import BasePermission

from ..errors import APIError, ErrorCode

logger = logging.getLogger("professor")

CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 5


class EntitlementUnavailable(Exception):
    """Verisafe could not confirm or deny the subscription."""


def has_ai_entitlement(user_id, token="") -> bool:
    if settings.AI_ENTITLEMENT_MODE == "stub-allow":
        return True
    if not token:
        return False

    cache_key = f"ai-entitlement:{user_id}"
    if cache.get(cache_key):
        return True

    try:
        response = requests.get(
            f"{settings.VERISAFE_URL}/subscriptions/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        raise EntitlementUnavailable(str(exc)) from exc
    if response.status_code != 200:
        raise EntitlementUnavailable(f"verisafe returned {response.status_code}")

    active = bool(response.json().get("active"))
    if active:
        # Positives only: a student who just paid must never wait out a cached denial.
        cache.set(cache_key, True, CACHE_TTL_SECONDS)
    return active


class HasAIEntitlement(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        user_id = getattr(user, "user_id", None)
        if user_id is None:
            return False
        try:
            allowed = has_ai_entitlement(user_id, token=getattr(request, "auth", "") or "")
        except EntitlementUnavailable as exc:
            logger.error("entitlement check unavailable for user %s: %s", user_id, exc)
            raise APIError(
                "Your subscription could not be verified. Please try again shortly.",
                code=ErrorCode.ENTITLEMENT_UNAVAILABLE,
                status_code=403,
            )
        if not allowed:
            raise APIError(
                "An active subscription is required for AI features.",
                code=ErrorCode.ENTITLEMENT_REQUIRED,
                status_code=403,
            )
        return True
