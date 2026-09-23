from unittest.mock import MagicMock

from notes.services.entitlements import HasAIEntitlement, has_ai_entitlement


def test_stub_allow_grants(settings, user):
    settings.AI_ENTITLEMENT_MODE = "stub-allow"
    assert has_ai_entitlement(user.user_id) is True


def test_verisafe_mode_fails_closed_until_wired(settings, user):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    assert has_ai_entitlement(user.user_id) is False


def test_permission_denies_in_verisafe_mode(settings, user):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    request = MagicMock(user=user)
    assert HasAIEntitlement().has_permission(request, MagicMock()) is False


def test_permission_grants_in_stub_mode(settings, user):
    settings.AI_ENTITLEMENT_MODE = "stub-allow"
    request = MagicMock(user=user)
    assert HasAIEntitlement().has_permission(request, MagicMock()) is True
