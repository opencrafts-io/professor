import uuid

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    from users.models import User

    return User.objects.create(user_id=uuid.uuid4(), name="Test User")


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def fake_llm_backend(settings):
    # No test may ever reach the real Gemini text or TTS services.
    settings.AI_LLM_BACKEND = "fake"
    settings.AI_TTS_BACKEND = "fake"


@pytest.fixture(autouse=True)
def in_memory_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
            "OPTIONS": {"base_url": "/media/"},
        },
    }
