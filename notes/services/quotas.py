"""Per-user daily usage quotas.

Limits come from a provider so their source can change without touching the
views: today a settings dict, later Verisafe plan entitlements. Usage is
counted from the day's existing rows (notes, jobs), so there is no counter
table to drift. Every accepted generation request counts, including requests
whose job later fails.
"""

from django.conf import settings
from django.utils import timezone

from ..errors import APIError, ErrorCode
from ..llm.base import OutputType
from ..models import GenerationJob, Note


class SettingsQuotaProvider:
    """Limits from settings.AI_QUOTAS; a missing key means unlimited."""

    def limits_for(self, user):
        return settings.AI_QUOTAS


def get_quota_provider():
    return SettingsQuotaProvider()


def _used_today(user, quota):
    start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if quota == "uploads_per_day":
        return Note.objects.filter(owner=user, uploaded_at__gte=start_of_day).count()
    if quota == "generations_per_day":
        return GenerationJob.objects.filter(owner=user, created_at__gte=start_of_day).count()
    if quota == "podcasts_per_day":
        return GenerationJob.objects.filter(
            owner=user,
            created_at__gte=start_of_day,
            requested_outputs__contains=[OutputType.PODCAST.value],
        ).count()
    raise ValueError(f"unknown quota {quota!r}")


def enforce_quota(user, quota):
    limits = get_quota_provider().limits_for(user)
    limit = limits.get(quota)
    if limit is None:
        return
    used = _used_today(user, quota)
    if used >= limit:
        raise APIError(
            "Daily quota reached. It resets at midnight UTC.",
            code=ErrorCode.QUOTA_EXCEEDED,
            status_code=429,
            details={"quota": quota, "limit": limit, "used": used},
        )
