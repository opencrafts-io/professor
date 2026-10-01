from unittest.mock import MagicMock

import pytest
from django.core.cache import cache

from notes.errors import APIError
from notes.services.entitlements import (
    EntitlementUnavailable,
    HasAIEntitlement,
    has_ai_entitlement,
)

VERISAFE_URL = "https://verisafe.test"


@pytest.fixture(autouse=True)
def entitlement_cache():
    cache.clear()
    yield
    cache.clear()


class StubResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class StubRequests:
    exceptions = __import__("requests").exceptions

    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._error is not None:
            raise self._error
        return self._response


def _verisafe(settings, monkeypatch, response=None, error=None):
    settings.AI_ENTITLEMENT_MODE = "verisafe"
    settings.VERISAFE_URL = VERISAFE_URL
    stub = StubRequests(response=response, error=error)
    monkeypatch.setattr("notes.services.entitlements.requests", stub)
    return stub


def test_stub_allow_grants(settings, user):
    settings.AI_ENTITLEMENT_MODE = "stub-allow"
    assert has_ai_entitlement(user.user_id) is True


def test_active_subscription_grants_and_forwards_token(settings, monkeypatch, user):
    stub = _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": True}))
    assert has_ai_entitlement(user.user_id, token="jwt123") is True
    url, kwargs = stub.calls[0]
    assert url == f"{VERISAFE_URL}/subscriptions/me"
    assert kwargs["headers"]["Authorization"] == "Bearer jwt123"
    assert kwargs["timeout"] > 0


def test_inactive_subscription_denies(settings, monkeypatch, user):
    _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": False}))
    assert has_ai_entitlement(user.user_id, token="jwt123") is False


def test_missing_token_fails_closed_without_calling_verisafe(settings, monkeypatch, user):
    stub = _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": True}))
    assert has_ai_entitlement(user.user_id) is False
    assert stub.calls == []


def test_verisafe_error_raises_unavailable(settings, monkeypatch, user):
    _verisafe(settings, monkeypatch, response=StubResponse(status_code=503))
    with pytest.raises(EntitlementUnavailable):
        has_ai_entitlement(user.user_id, token="jwt123")


def test_network_failure_raises_unavailable(settings, monkeypatch, user):
    import requests as real_requests

    _verisafe(settings, monkeypatch, error=real_requests.exceptions.ConnectTimeout("slow"))
    with pytest.raises(EntitlementUnavailable):
        has_ai_entitlement(user.user_id, token="jwt123")


def test_active_result_is_cached(settings, monkeypatch, user):
    stub = _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": True}))
    assert has_ai_entitlement(user.user_id, token="jwt123") is True
    assert has_ai_entitlement(user.user_id, token="jwt123") is True
    assert len(stub.calls) == 1


def test_inactive_result_is_not_cached(settings, monkeypatch, user):
    # A student who just paid must not wait out a cached denial.
    stub = _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": False}))
    has_ai_entitlement(user.user_id, token="jwt123")
    has_ai_entitlement(user.user_id, token="jwt123")
    assert len(stub.calls) == 2


def test_permission_raises_required_when_inactive(settings, monkeypatch, user):
    _verisafe(settings, monkeypatch, response=StubResponse(payload={"active": False}))
    request = MagicMock(user=user, auth="jwt123")
    with pytest.raises(APIError) as exc:
        HasAIEntitlement().has_permission(request, MagicMock())
    assert exc.value.error_code == "entitlement_required"
    assert exc.value.status_code == 403


def test_permission_raises_unavailable_on_verisafe_failure(settings, monkeypatch, user):
    _verisafe(settings, monkeypatch, response=StubResponse(status_code=500))
    request = MagicMock(user=user, auth="jwt123")
    with pytest.raises(APIError) as exc:
        HasAIEntitlement().has_permission(request, MagicMock())
    assert exc.value.error_code == "entitlement_unavailable"
    assert exc.value.status_code == 403


def test_permission_grants_in_stub_mode(settings, user):
    settings.AI_ENTITLEMENT_MODE = "stub-allow"
    request = MagicMock(user=user, auth=None)
    assert HasAIEntitlement().has_permission(request, MagicMock()) is True
