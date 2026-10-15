from datetime import timedelta

import pytest
from django.utils import timezone

from courses.models import StudentCourse
from examtimetable.models import ExamSchedule
from institutions.models import Institution
from users.models import StudentProfile


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
def second_institution(db):
    return Institution.objects.create(
        name="Academia Polytechnic",
        web_pages=["https://polytechnic.example"],
        domains=["polytechnic.example"],
        country="Kenya",
    )


def create_exam(institution, course_code):
    start_time = timezone.now()
    return ExamSchedule.objects.create(
        course_code=course_code,
        institution=institution,
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        venue="Main Hall",
        hrs="2",
    )


def test_student_exam_schedule_returns_exam_at_course_institution(
    auth_client, student_profile, institution
):
    StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Computer Science",
        code="CS101",
    )
    create_exam(institution, "CS101")

    response = auth_client.get(
        "/api/exams/student/", {"student_id": student_profile.student_id}
    )

    assert response.status_code == 200
    assert [(exam["course_code"], exam["institution"]) for exam in response.json()] == [
        ("CS101", institution.pk)
    ]


def test_student_exam_schedule_normalizes_course_code_case_and_whitespace(
    auth_client, student_profile, institution
):
    StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Computer Science",
        code="cs 101",
    )
    create_exam(institution, "CS101")

    response = auth_client.get(
        "/api/exams/student/", {"student_id": student_profile.student_id}
    )

    assert response.status_code == 200
    assert [(exam["course_code"], exam["institution"]) for exam in response.json()] == [
        ("CS101", institution.pk)
    ]


def test_student_exam_schedule_returns_matching_exams_for_each_course_institution(
    auth_client, student_profile, institution, second_institution
):
    StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Computer Science",
        code="CS101",
    )
    StudentCourse.objects.create(
        student=student_profile,
        institution=second_institution,
        title="Computer Science",
        code="CS101",
    )
    create_exam(institution, "CS101")
    create_exam(second_institution, "CS101")

    response = auth_client.get(
        "/api/exams/student/", {"student_id": student_profile.student_id}
    )

    assert response.status_code == 200
    assert {
        (exam["course_code"], exam["institution"]) for exam in response.json()
    } == {
        ("CS101", institution.pk),
        ("CS101", second_institution.pk),
    }


def test_student_exam_schedule_excludes_matching_exam_at_unenrolled_institution(
    auth_client, student_profile, institution, second_institution
):
    StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Computer Science",
        code="CS101",
    )
    create_exam(institution, "CS101")
    create_exam(second_institution, "CS101")

    response = auth_client.get(
        "/api/exams/student/", {"student_id": student_profile.student_id}
    )

    assert response.status_code == 200
    assert [(exam["course_code"], exam["institution"]) for exam in response.json()] == [
        ("CS101", institution.pk)
    ]


def test_student_exam_schedule_excludes_archived_course_codes(
    auth_client, student_profile, institution
):
    StudentCourse.objects.create(
        student=student_profile,
        institution=institution,
        title="Computer Science",
        code="CS101",
        archived_at=timezone.now(),
    )
    create_exam(institution, "CS101")

    response = auth_client.get(
        "/api/exams/student/", {"student_id": student_profile.student_id}
    )

    assert response.status_code == 200
    assert response.json() == []
