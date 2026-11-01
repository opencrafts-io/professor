from datetime import date, datetime, timezone

import pytest
from django.core.files.base import ContentFile

from notes.models import Note, StudyPlan
from notes.services.sessions import suggested_sessions

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def plan(user):
    notes = []
    for i in range(2):
        note = Note(owner=user, original_filename=f"n{i}.pdf", size_bytes=9)
        note.file.save(f"n{i}.pdf", ContentFile(b"%PDF-x"), save=True)
        notes.append(note)
    plan = StudyPlan.objects.create(owner=user)
    plan.notes.set(notes)
    plan.topics = [
        {"name": "Fourier series", "priority": 1, "suggested_minutes": 90,
         "source_note_ids": [notes[0].pk]},
        {"name": "Laplace transforms", "priority": 2, "suggested_minutes": 60,
         "source_note_ids": [notes[1].pk]},
        {"name": "Z-transforms", "priority": 3, "suggested_minutes": 45,
         "source_note_ids": [notes[0].pk, notes[1].pk]},
    ]
    plan.save()
    return plan


def test_sessions_use_keep_up_field_names_and_priority_order(plan):
    sessions = suggested_sessions(plan, now=NOW)
    assert len(sessions) == 3
    first = sessions[0]
    # exact keep-up /agenda/add field names — postable verbatim
    assert set(first) >= {"summary", "description", "start_time", "end_time", "timezone"}
    assert "title" not in first and "start" not in first and "end" not in first
    assert first["summary"] == "Study: Fourier series"
    assert first["timezone"] == "UTC"
    assert [s["topic"] for s in sessions] == [
        "Fourier series", "Laplace transforms", "Z-transforms"
    ]


def test_sessions_start_tomorrow_one_per_day_with_duration(plan):
    sessions = suggested_sessions(plan, now=NOW)
    assert sessions[0]["start_time"] == "2026-10-14T17:00:00Z"
    assert sessions[0]["end_time"] == "2026-10-14T18:30:00Z"  # 90 min
    assert sessions[1]["start_time"] == "2026-10-15T17:00:00Z"
    assert sessions[2]["start_time"] == "2026-10-16T17:00:00Z"
    assert sessions[2]["end_time"] == "2026-10-16T17:45:00Z"  # 45 min


def test_sessions_carry_source_provenance(plan):
    sessions = suggested_sessions(plan, now=NOW)
    assert sessions[0]["source_note_ids"] == plan.topics[0]["source_note_ids"]
    assert "n0.pdf" in sessions[0]["description"]
    assert "90" in sessions[0]["description"]


def test_sessions_compress_to_fit_before_term_end(plan, user):
    from courses.models import StudentCourse
    from institutions.models import Institution
    from users.models import StudentProfile

    institution = Institution.objects.create(
        name="U", web_pages=["https://u.example"], domains=["u.example"], country="Kenya"
    )
    student = StudentProfile.objects.create(user=user, student_id="s-1")
    plan.course = StudentCourse.objects.create(
        student=student, institution=institution, title="Maths",
        term_end_date=date(2026, 10, 15),
    )
    plan.save()
    sessions = suggested_sessions(plan, now=NOW)
    # 3 topics, only 2 days before term end -> 2 on day one, breaks between
    assert len(sessions) == 3
    days = [s["start_time"][:10] for s in sessions]
    assert all(d <= "2026-10-15" for d in days)
    assert sessions[0]["start_time"] == "2026-10-14T17:00:00Z"
    assert sessions[1]["start_time"] == "2026-10-14T18:45:00Z"  # after 90min + 15min break
    assert sessions[2]["start_time"][:10] == "2026-10-15"


def test_past_term_end_is_ignored(plan, user):
    from courses.models import StudentCourse
    from institutions.models import Institution
    from users.models import StudentProfile

    institution = Institution.objects.create(
        name="U2", web_pages=["https://u2.example"], domains=["u2.example"], country="Kenya"
    )
    student = StudentProfile.objects.create(user=user, student_id="s-2")
    plan.course = StudentCourse.objects.create(
        student=student, institution=institution, title="Maths",
        term_end_date=date(2026, 10, 1),
    )
    plan.save()
    sessions = suggested_sessions(plan, now=NOW)
    assert sessions[0]["start_time"] == "2026-10-14T17:00:00Z"  # normal schedule


def test_deadline_starts_today_and_compresses(plan):
    # 3 topics, deadline tomorrow -> 2-day window, 2 per day, cram hours
    sessions = suggested_sessions(plan, now=NOW, deadline=date(2026, 10, 14))
    assert len(sessions) == 3
    # first session today, next full hour after 12:00, not the 09:00 cram slot already past
    assert sessions[0]["start_time"] == "2026-10-13T13:00:00Z"
    assert sessions[1]["start_time"] == "2026-10-13T14:45:00Z"  # 90min + 15min break
    assert sessions[2]["start_time"] == "2026-10-14T09:00:00Z"  # fresh cram day
    assert all(s["start_time"][:10] <= "2026-10-14" for s in sessions)


def test_deadline_overrides_term_end(plan, user):
    from courses.models import StudentCourse
    from institutions.models import Institution
    from users.models import StudentProfile

    institution = Institution.objects.create(
        name="U3", web_pages=["https://u3.example"], domains=["u3.example"], country="Kenya"
    )
    student = StudentProfile.objects.create(user=user, student_id="s-3")
    plan.course = StudentCourse.objects.create(
        student=student, institution=institution, title="Maths",
        term_end_date=date(2026, 12, 15),
    )
    plan.save()
    sessions = suggested_sessions(plan, now=NOW, deadline=date(2026, 10, 14))
    assert all(s["start_time"][:10] <= "2026-10-14" for s in sessions)


def test_generous_deadline_still_starts_today_relaxed_hours(plan):
    sessions = suggested_sessions(plan, now=NOW, deadline=date(2026, 10, 30))
    # uncompressed (1/day) keeps the 17:00 evening slot, but begins today
    assert sessions[0]["start_time"] == "2026-10-13T17:00:00Z"
    assert sessions[1]["start_time"] == "2026-10-14T17:00:00Z"


def test_endpoint_accepts_deadline_param(auth_client, plan):
    response = auth_client.get(
        f"/api/notes/study-plans/{plan.pk}/suggested-sessions/?deadline=2100-01-02"
    )
    assert response.status_code == 200
    assert len(response.data["sessions"]) == 3


def test_endpoint_rejects_bad_deadlines(auth_client, plan):
    response = auth_client.get(
        f"/api/notes/study-plans/{plan.pk}/suggested-sessions/?deadline=not-a-date"
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"

    response = auth_client.get(
        f"/api/notes/study-plans/{plan.pk}/suggested-sessions/?deadline=2020-01-01"
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_endpoint_returns_sessions_per_contract(auth_client, plan):
    response = auth_client.get(f"/api/notes/study-plans/{plan.pk}/suggested-sessions/")
    assert response.status_code == 200
    assert response.data["study_plan_id"] == plan.pk
    assert len(response.data["sessions"]) == 3
    assert response.data["sessions"][0]["summary"].startswith("Study: ")


def test_endpoint_404_before_topics_exist(auth_client, user):
    empty = StudyPlan.objects.create(owner=user)
    response = auth_client.get(f"/api/notes/study-plans/{empty.pk}/suggested-sessions/")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_endpoint_owner_scoped(api_client, plan):
    import uuid

    from users.models import User

    stranger = User.objects.create(user_id=uuid.uuid4(), name="Stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.get(f"/api/notes/study-plans/{plan.pk}/suggested-sessions/")
    assert response.status_code == 404
