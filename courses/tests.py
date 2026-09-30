import uuid

import pytest
from django.utils import timezone

from courses.models import StudentCourse
from institutions.models import Institution
from rest_framework.test import APIClient
from users.models import StudentProfile, User


@pytest.fixture
def student_profile(user):
    return StudentProfile.objects.create(user=user, student_id="student-001")


@pytest.fixture
def institution(db):
    return Institution.objects.create(
        name="Academia University",
        web_pages=["https://academia.example"],
        domains=["academia.example"],
        country="Kenya",
    )


@pytest.fixture
def course(student_profile, institution):
    return StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Engineering Mathematics II",
        code="MAT 2201",
    )


@pytest.fixture
def other_auth_client(db):
    other_user = User.objects.create(user_id=uuid.uuid4(), name="Other User")
    api_client = APIClient()
    api_client.force_authenticate(user=other_user)
    return api_client


def test_create_requires_institution(auth_client, student_profile):
    response = auth_client.post(
        "/api/courses/create/",
        {"title": "Engineering Mathematics II"},
        format="json",
    )

    assert response.status_code == 400
    assert "institution" in response.json()


def test_course_detail_update_and_delete_are_owner_scoped(other_auth_client, course):
    detail_url = f"/api/courses/{course.pk}/"

    assert other_auth_client.get(detail_url).status_code == 403
    assert other_auth_client.patch(
        detail_url, {"title": "Changed"}, format="json"
    ).status_code == 403
    assert other_auth_client.delete(detail_url).status_code == 403
    assert StudentCourse.objects.filter(pk=course.pk).exists()


def test_archive_moves_course_to_history_while_delete_removes_it(
    auth_client, course
):
    detail_url = f"/api/courses/{course.pk}/"

    response = auth_client.post(f"{detail_url}archive/")

    assert response.status_code == 200
    course.refresh_from_db()
    assert course.archived_at is not None
    current_courses = auth_client.get("/api/courses/student/").json()["results"]
    history_courses = auth_client.get("/api/courses/student/history/").json()["results"]
    assert current_courses == []
    assert [item["id"] for item in history_courses] == [str(course.pk)]

    response = auth_client.delete(detail_url)

    assert response.status_code == 204
    assert not StudentCourse.objects.filter(pk=course.pk).exists()


def test_lecturer_mutations_are_owner_scoped(auth_client, other_auth_client, course):
    response = auth_client.post(
        f"/api/courses/{course.pk}/lecturers/",
        {"name": "Dr. Lecturer"},
        format="json",
    )

    assert response.status_code == 201
    lecturer_id = response.json()["id"]
    lecturer_url = f"/api/courses/lecturers/{lecturer_id}/"
    assert other_auth_client.patch(
        lecturer_url, {"name": "Changed"}, format="json"
    ).status_code == 403
    assert other_auth_client.delete(lecturer_url).status_code == 403


def test_legacy_course_endpoints_are_removed(auth_client):
    responses = [
        auth_client.get("/api/courses/"),
        auth_client.post("/api/courses/register/", {}, format="json"),
        auth_client.post("/api/courses/enrollments/", {}, format="json"),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]


SCHEDULE_PAYLOAD = {
    "day_of_week": "monday",
    "start_time": "09:00",
    "end_time": "10:00",
    "venue": "Room 12",
}


def create_schedule_entry(client, course, **overrides):
    payload = {**SCHEDULE_PAYLOAD, **overrides}
    response = client.post(
        f"/api/courses/{course.pk}/schedule/", payload, format="json"
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    ("start_time", "end_time"), [("09:00", "09:00"), ("10:00", "09:00")]
)
def test_schedule_entry_rejects_non_positive_duration(
    auth_client, course, start_time, end_time
):
    response = auth_client.post(
        f"/api/courses/{course.pk}/schedule/",
        {**SCHEDULE_PAYLOAD, "start_time": start_time, "end_time": end_time},
        format="json",
    )

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_schedule_entry_mutations_are_owner_scoped(
    auth_client, other_auth_client, course
):
    entry = create_schedule_entry(auth_client, course)
    schedule_url = f"/api/courses/schedule/{entry['id']}/"

    assert other_auth_client.post(
        f"/api/courses/{course.pk}/schedule/", SCHEDULE_PAYLOAD, format="json"
    ).status_code == 403
    assert other_auth_client.patch(
        schedule_url, {"venue": "Other room"}, format="json"
    ).status_code == 403
    assert other_auth_client.delete(schedule_url).status_code == 403


def test_course_detail_includes_its_schedule_entries(auth_client, course):
    entry = create_schedule_entry(auth_client, course)

    response = auth_client.get(f"/api/courses/{course.pk}/")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["schedule_entries"]] == [
        entry["id"]
    ]


def test_student_timetable_includes_active_courses_and_excludes_archived(
    auth_client, course, student_profile, institution
):
    archived_course = StudentCourse.objects.create(
        student=student_profile, institution=institution, title="Archived course"
    )
    archived_course.archived_at = timezone.now()
    archived_course.save(update_fields=["archived_at"])
    active_entry = create_schedule_entry(auth_client, course)
    archived_entry = create_schedule_entry(auth_client, archived_course)

    response = auth_client.get("/api/courses/schedule/student/")

    assert response.status_code == 200
    entries = response.json()
    entry_ids = {entry["id"] for entry in entries}
    assert active_entry["id"] in entry_ids
    assert archived_entry["id"] not in entry_ids
    active = next(entry for entry in entries if entry["id"] == active_entry["id"])
    assert active["course"] == {
        "id": str(course.pk),
        "title": course.title,
        "code": course.code,
        "color": None,
    }


def test_student_timetable_only_includes_requesting_students_entries(
    auth_client, course, institution
):
    own_entry = create_schedule_entry(auth_client, course)
    other_user = User.objects.create(user_id=uuid.uuid4(), name="Another Student")
    other_student = StudentProfile.objects.create(
        user=other_user, student_id="student-002"
    )
    other_course = StudentCourse.objects.create(
        student=other_student, institution=institution, title="Other student's course"
    )
    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    create_schedule_entry(other_client, other_course)

    response = auth_client.get("/api/courses/schedule/student/")

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()] == [own_entry["id"]]


@pytest.mark.parametrize("color", ["blue", "#GGGGGG", "#12345"])
def test_invalid_colors_are_rejected_for_courses_and_schedule_entries(
    auth_client, institution, course, color
):
    course_response = auth_client.post(
        "/api/courses/create/",
        {
            "title": "Colored course",
            "institution": institution.pk,
            "color": color,
        },
        format="json",
    )
    schedule_response = auth_client.post(
        f"/api/courses/{course.pk}/schedule/",
        {**SCHEDULE_PAYLOAD, "color": color},
        format="json",
    )

    assert course_response.status_code == 400
    assert "color" in course_response.json()
    assert schedule_response.status_code == 400
    assert "color" in schedule_response.json()


@pytest.mark.parametrize("color", ["#4F46E5", "#4F46E5FF"])
def test_six_and_eight_digit_hex_colors_are_accepted(
    auth_client, institution, course, color
):
    course_response = auth_client.post(
        "/api/courses/create/",
        {
            "title": "Colored course",
            "institution": institution.pk,
            "color": color,
        },
        format="json",
    )
    schedule_response = auth_client.post(
        f"/api/courses/{course.pk}/schedule/",
        {**SCHEDULE_PAYLOAD, "color": color},
        format="json",
    )

    assert course_response.status_code == 201
    created_course = StudentCourse.objects.get(pk=course_response.json()["id"])
    assert created_course.color == color
    assert course_response.json()["color"] == color
    assert schedule_response.status_code == 201
    assert schedule_response.json()["color"] == color


def test_recurring_schedule_entries_require_matching_specific_date(
    auth_client, course
):
    missing_date = auth_client.post(
        f"/api/courses/{course.pk}/schedule/",
        {**SCHEDULE_PAYLOAD, "is_recurring": False},
        format="json",
    )
    recurring_with_date = auth_client.post(
        f"/api/courses/{course.pk}/schedule/",
        {
            **SCHEDULE_PAYLOAD,
            "is_recurring": True,
            "specific_date": "2026-10-01",
        },
        format="json",
    )

    assert missing_date.status_code == 400
    assert recurring_with_date.status_code == 400


def test_create_idempotency_returns_the_original_course_and_schedule_entry(
    auth_client, institution, course
):
    course_data = {
        "title": "Idempotent course",
        "institution": institution.pk,
        "idempotency_key": "client-course-token",
    }
    first_course = auth_client.post(
        "/api/courses/create/", course_data, format="json"
    )
    second_course = auth_client.post(
        "/api/courses/create/", course_data, format="json"
    )

    assert first_course.status_code == 201
    assert second_course.status_code == 200
    assert first_course.json()["id"] == second_course.json()["id"]
    assert StudentCourse.objects.filter(
        student=course.student, idempotency_key="client-course-token"
    ).count() == 1

    schedule_data = {**SCHEDULE_PAYLOAD, "idempotency_key": "client-slot-token"}
    first_entry = auth_client.post(
        f"/api/courses/{course.pk}/schedule/", schedule_data, format="json"
    )
    second_entry = auth_client.post(
        f"/api/courses/{course.pk}/schedule/", schedule_data, format="json"
    )

    assert first_entry.status_code == 201
    assert second_entry.status_code == 200
    assert first_entry.json()["id"] == second_entry.json()["id"]
    assert course.schedule_entries.filter(
        idempotency_key="client-slot-token"
    ).count() == 1
