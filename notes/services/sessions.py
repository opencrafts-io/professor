"""Turn a study plan's topics into concrete sessions shaped for Keep Up.

Each session dict uses the exact field names Keep Up's agenda creation API
accepts (summary/start_time/end_time/description/timezone), so the frontend
can POST an accepted session verbatim. Extra keys (topic, source_note_ids)
are professor metadata; Keep Up ignores unknown fields.
"""

import math
from datetime import datetime, time, timedelta, timezone

SESSION_START_HOUR_UTC = 17  # early evening default study slot
BREAK_MINUTES = 15


def _day_slots(topics, days_available):
    """Topics per day: 1 by default, more when the term end squeezes us."""
    if days_available is None or days_available >= len(topics):
        return 1
    return math.ceil(len(topics) / max(days_available, 1))


def suggested_sessions(plan, now=None):
    now = now or datetime.now(timezone.utc)
    first_day = (now + timedelta(days=1)).date()

    days_available = None
    course = plan.course
    if course and course.term_end_date and course.term_end_date >= first_day:
        days_available = (course.term_end_date - first_day).days + 1

    topics = sorted(plan.topics, key=lambda t: t["priority"])
    per_day = _day_slots(topics, days_available)
    filenames = {n.pk: n.original_filename for n in plan.notes.all()}

    sessions = []
    cursor = datetime.combine(
        first_day, time(SESSION_START_HOUR_UTC, 0), tzinfo=timezone.utc
    )
    in_day = 0
    for topic in topics:
        if in_day == per_day:
            cursor = datetime.combine(
                cursor.date() + timedelta(days=1),
                time(SESSION_START_HOUR_UTC, 0),
                tzinfo=timezone.utc,
            )
            in_day = 0
        start = cursor
        end = start + timedelta(minutes=topic["suggested_minutes"])
        sources = topic.get("source_note_ids", [])
        source_names = ", ".join(filenames[i] for i in sources if i in filenames)
        sessions.append(
            {
                "summary": f"Study: {topic['name']}",
                "description": (
                    f"{topic['suggested_minutes']}-minute focused session "
                    f"(priority {topic['priority']} in your study plan). "
                    f"Sources: {source_names or 'your notes'}."
                ),
                "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "timezone": "UTC",
                "topic": topic["name"],
                "source_note_ids": sources,
            }
        )
        cursor = end + timedelta(minutes=BREAK_MINUTES)
        in_day += 1
    return sessions
