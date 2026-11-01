"""Per-user usage quotas over calendar windows (UTC day and UTC month).

Limits come from a provider so their source can change without touching the
views: today a settings dict, later Verisafe plan entitlements. Usage is
counted from the window's existing rows (notes, jobs), so there is no counter
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


_QUOTA_MESSAGES = {
    "day": "Daily quota reached. It resets at midnight UTC.",
    "month": "Monthly quota reached. It resets on the first of the month, midnight UTC.",
}


def _window_start(period):
    start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "day":
        return start_of_day
    if period == "month":
        return start_of_day.replace(day=1)
    raise ValueError(f"unknown quota period {period!r}")


def _used_since(user, metric, start):
    if metric == "uploads":
        return Note.objects.filter(owner=user, uploaded_at__gte=start).count()
    if metric == "generations":
        return GenerationJob.objects.filter(owner=user, created_at__gte=start).count()
    if metric == "podcasts":
        return GenerationJob.objects.filter(
            owner=user,
            created_at__gte=start,
            requested_outputs__contains=[OutputType.PODCAST.value],
        ).count()
    raise ValueError(f"unknown quota metric {metric!r}")


def enforce_quota(user, metric):
    """Raise 429 if the user exhausted any configured window for the metric.

    The daily window is checked first so the error names the limit that
    resets soonest.
    """
    limits = get_quota_provider().limits_for(user)
    for period in ("day", "month"):
        quota = f"{metric}_per_{period}"
        limit = limits.get(quota)
        if limit is None:
            continue
        used = _used_since(user, metric, _window_start(period))
        if used >= limit:
            raise APIError(
                _QUOTA_MESSAGES[period],
                code=ErrorCode.QUOTA_EXCEEDED,
                status_code=429,
                details={"quota": quota, "limit": limit, "used": used},
            )
