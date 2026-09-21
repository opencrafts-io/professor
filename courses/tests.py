import uuid

import pytest

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
