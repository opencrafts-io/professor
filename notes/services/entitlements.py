import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger("professor")


def has_ai_entitlement(user_id) -> bool:
    mode = settings.AI_ENTITLEMENT_MODE
    if mode == "stub-allow":
        return True
    # "verisafe" mode: real client lands when the endpoint contract is captured.
    # Fail closed until then.
    logger.warning(
        "AI entitlement check in verisafe mode but client not wired; denying user %s",
        user_id,
    )
    return False


class HasAIEntitlement(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        user_id = getattr(user, "user_id", None)
        if user_id is None:
            return False
        return has_ai_entitlement(user_id)
