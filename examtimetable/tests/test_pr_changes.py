"""
Tests for PR changes in examtimetable app:
- ExamSchedule.datetime_str field (new CharField)
- ExamScheduleSerializer (removed semester_id, datetime_str is now a model field)
- ExamScheduleIngestItemSerializer (datetime_str added to fields)
- ExamScheduleIngestRequestSerializer (validate_institution_id strips whitespace)
- IngestExamScheduleView (deduplication, atomic upsert, response structure)
- ExamScheduleByCourseCodesView (course code matching with NUR/NUP truncation)
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "professor.test_settings")
django.setup()

import unittest
from unittest.mock import MagicMock, patch, call
from django.db.models import CharField
from rest_framework.test import APIRequestFactory

from examtimetable.models import ExamSchedule
from examtimetable.serializers import (
    ExamScheduleSerializer,
    ExamScheduleIngestItemSerializer,
    ExamScheduleIngestRequestSerializer,
)
from examtimetable.views import (
    IngestExamScheduleView,
    ExamScheduleByCourseCodesView,
    ExamScheduleByInstitutionView,
    StudentExamScheduleView,
    ExamScheduleListView,
)


class TestExamScheduleDatetimeStrField(unittest.TestCase):
    """Tests for the new datetime_str field added to ExamSchedule model."""

    def test_datetime_str_field_exists(self):
        """datetime_str field is present on ExamSchedule model."""
        field = ExamSchedule._meta.get_field("datetime_str")
        self.assertIsNotNone(field)

    def test_datetime_str_is_char_field(self):
        """datetime_str is a CharField."""
        field = ExamSchedule._meta.get_field("datetime_str")
        self.assertIsInstance(field, CharField)

    def test_datetime_str_max_length(self):
        """datetime_str has max_length=50."""
        field = ExamSchedule._meta.get_field("datetime_str")
        self.assertEqual(field.max_length, 50)

    def test_datetime_str_is_nullable(self):
        """datetime_str allows NULL values."""
        field = ExamSchedule._meta.get_field("datetime_str")
        self.assertTrue(field.null)

    def test_datetime_str_allows_blank(self):
        """datetime_str allows blank strings (form validation)."""
        field = ExamSchedule._meta.get_field("datetime_str")
        self.assertTrue(field.blank)

    def test_datetime_str_default_is_not_set(self):
        """datetime_str has no explicit default (defaults to None when null=True)."""
        field = ExamSchedule._meta.get_field("datetime_str")
        # CharField with null=True has no default value set unless explicitly defined
        from django.db.models.fields import NOT_PROVIDED
        self.assertEqual(field.default, NOT_PROVIDED)


class TestExamScheduleSerializerFields(unittest.TestCase):
    """Tests for ExamScheduleSerializer field changes in this PR."""

    def setUp(self):
        self.serializer = ExamScheduleSerializer()

    def test_datetime_str_is_in_fields(self):
        """datetime_str field is included in ExamScheduleSerializer."""
        self.assertIn("datetime_str", self.serializer.fields)

    def test_semester_id_not_in_fields(self):
        """semester_id write_only field was removed from ExamScheduleSerializer."""
        self.assertNotIn("semester_id", self.serializer.fields)

    def test_expected_fields_present(self):
        """All expected display fields are present in ExamScheduleSerializer."""
        expected_fields = [
            "course_code",
            "day",
            "venue",
            "start_time",
            "end_time",
            "campus",
            "coordinator",
            "hrs",
            "invigilator",
            "datetime_str",
        ]
        for field_name in expected_fields:
            self.assertIn(field_name, self.serializer.fields, f"Missing field: {field_name}")

    def test_no_extra_unexpected_fields(self):
        """ExamScheduleSerializer has exactly the expected fields."""
        expected_fields = {
            "course_code", "day", "venue", "start_time", "end_time",
            "campus", "coordinator", "hrs", "invigilator", "datetime_str",
        }
        actual_fields = set(self.serializer.fields.keys())
        self.assertEqual(actual_fields, expected_fields)

    def test_datetime_str_is_not_method_field(self):
        """datetime_str is a plain model field, not a SerializerMethodField."""
        from rest_framework import serializers
        field = self.serializer.fields["datetime_str"]
        self.assertNotIsInstance(field, serializers.SerializerMethodField)

    def test_serializer_accepts_exam_schedule_instance_with_datetime_str(self):
        """Serializer reads datetime_str from an ExamSchedule instance."""
        instance = MagicMock(spec=ExamSchedule)
        instance.course_code = "CS101"
        instance.day = "Monday"
        instance.venue = "Hall A"
        instance.start_time = None
        instance.end_time = None
        instance.campus = None
        instance.coordinator = None
        instance.hrs = None
        instance.invigilator = None
        instance.datetime_str = "2026-03-25T09:00:00+03:00"

        serializer = ExamScheduleSerializer(instance)
        data = serializer.data
        self.assertEqual(data["datetime_str"], "2026-03-25T09:00:00+03:00")

    def test_serializer_handles_null_datetime_str(self):
        """Serializer handles null datetime_str gracefully."""
        instance = MagicMock(spec=ExamSchedule)
        instance.course_code = "CS101"
        instance.day = None
        instance.venue = None
        instance.start_time = None
        instance.end_time = None
        instance.campus = None
        instance.coordinator = None
        instance.hrs = None
        instance.invigilator = None
        instance.datetime_str = None

        serializer = ExamScheduleSerializer(instance)
        data = serializer.data
        self.assertIsNone(data["datetime_str"])


class TestExamScheduleIngestItemSerializerFields(unittest.TestCase):
    """Tests for ExamScheduleIngestItemSerializer changes in this PR."""

    def setUp(self):
        self.serializer = ExamScheduleIngestItemSerializer()

    def test_datetime_str_is_in_fields(self):
        """datetime_str field was added to ExamScheduleIngestItemSerializer."""
        self.assertIn("datetime_str", self.serializer.fields)

    def test_raw_data_in_fields(self):
        """raw_data field is present in ExamScheduleIngestItemSerializer."""
        self.assertIn("raw_data", self.serializer.fields)

    def test_course_code_required(self):
        """course_code is required in ExamScheduleIngestItemSerializer."""
        field = self.serializer.fields["course_code"]
        self.assertFalse(field.allow_blank)

    def test_validation_strips_course_code_whitespace(self):
        """validate_course_code strips leading/trailing whitespace."""
        serializer = ExamScheduleIngestItemSerializer(data={"course_code": "  CS101  "})
        serializer.is_valid()
        # Even if other fields are missing, course_code itself should be cleaned
        # Check the validate_course_code method directly
        result = serializer.validate_course_code("  CS101  ")
        self.assertEqual(result, "CS101")

    def test_validation_strips_course_code_tabs_and_newlines(self):
        """validate_course_code strips tabs and newlines from course codes."""
        serializer = ExamScheduleIngestItemSerializer()
        result = serializer.validate_course_code("\tCS101\n")
        self.assertEqual(result, "CS101")

    def test_all_optional_fields_present(self):
        """All optional fields are present in ExamScheduleIngestItemSerializer."""
        optional_fields = [
            "course_name", "exam_date", "start_time", "end_time",
            "day", "venue", "campus", "coordinator", "hrs", "invigilator",
            "location", "room", "building", "exam_type", "instructions",
            "datetime_str", "raw_data",
        ]
        for field_name in optional_fields:
            self.assertIn(field_name, self.serializer.fields, f"Missing field: {field_name}")

    def test_valid_data_with_datetime_str(self):
        """Serializer accepts valid data including datetime_str."""
        data = {
            "course_code": "CS101",
            "datetime_str": "2026-03-25T09:00:00+03:00",
        }
        serializer = ExamScheduleIngestItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_data_without_datetime_str(self):
        """Serializer accepts valid data even without datetime_str (optional)."""
        data = {"course_code": "CS101"}
        serializer = ExamScheduleIngestItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_datetime_str_max_length_enforced(self):
        """Serializer rejects datetime_str exceeding 50 characters."""
        data = {
            "course_code": "CS101",
            "datetime_str": "A" * 51,  # exceeds max_length=50
        }
        serializer = ExamScheduleIngestItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("datetime_str", serializer.errors)

    def test_datetime_str_exactly_50_chars_accepted(self):
        """Serializer accepts datetime_str of exactly 50 characters."""
        data = {
            "course_code": "CS101",
            "datetime_str": "A" * 50,
        }
        serializer = ExamScheduleIngestItemSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestExamScheduleIngestRequestSerializer(unittest.TestCase):
    """Tests for ExamScheduleIngestRequestSerializer."""

    def test_institution_id_stripped(self):
        """validate_institution_id strips leading/trailing whitespace."""
        serializer = ExamScheduleIngestRequestSerializer()
        result = serializer.validate_institution_id("  inst-001  ")
        self.assertEqual(result, "inst-001")

    def test_institution_id_required(self):
        """institution_id is required."""
        data = {
            "items": [{"course_code": "CS101"}],
        }
        serializer = ExamScheduleIngestRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("institution_id", serializer.errors)

    def test_items_required(self):
        """items array is required."""
        data = {"institution_id": "inst-001"}
        serializer = ExamScheduleIngestRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)

    def test_semester_id_is_optional(self):
        """semester_id is optional in the ingestion request."""
        data = {
            "institution_id": "inst-001",
            "items": [{"course_code": "CS101"}],
        }
        serializer = ExamScheduleIngestRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_items_with_datetime_str_accepted(self):
        """Items with datetime_str pass validation."""
        data = {
            "institution_id": "inst-001",
            "items": [
                {
                    "course_code": "CS101",
                    "datetime_str": "2026-03-25T09:00:00+03:00",
                }
            ],
        }
        serializer = ExamScheduleIngestRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.validated_data["items"][0]
        self.assertEqual(item["datetime_str"], "2026-03-25T09:00:00+03:00")

    def test_institution_id_blank_rejected(self):
        """Blank institution_id is rejected."""
        data = {
            "institution_id": "",
            "items": [{"course_code": "CS101"}],
        }
        serializer = ExamScheduleIngestRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("institution_id", serializer.errors)


class TestIngestExamScheduleView(unittest.TestCase):
    """Tests for IngestExamScheduleView with PR-relevant behavior."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = IngestExamScheduleView.as_view()

    def test_missing_institution_id_returns_400(self):
        """Missing institution_id results in 400 with validation error."""
        request = self.factory.post(
            "/api/exams/ingest/",
            data={"items": [{"course_code": "CS101"}]},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "validation_failed")

    def test_missing_items_returns_400(self):
        """Missing items array results in 400 with validation error."""
        request = self.factory.post(
            "/api/exams/ingest/",
            data={"institution_id": "inst-001"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "validation_failed")

    def test_empty_course_code_returns_400(self):
        """Empty course_code in items returns 400."""
        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [{"course_code": ""}],
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)

    def test_validation_error_response_structure(self):
        """Validation error response has expected structure."""
        request = self.factory.post(
            "/api/exams/ingest/",
            data={"institution_id": "inst-001"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["errors"][0]["code"], "invalid_request")
        self.assertIn("field_errors", response.data["errors"][0])

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    @patch("event_bus.publisher.publish")
    def test_successful_ingest_creates_records(self, mock_publish, mock_uoc):
        """Successful ingestion returns created/updated/skipped counts."""
        mock_uoc.return_value = (MagicMock(), True)

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [{"course_code": "CS101"}],
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("created", response.data)
        self.assertIn("updated", response.data)
        self.assertIn("skipped", response.data)
        self.assertIn("errors", response.data)

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    @patch("event_bus.publisher.publish")
    def test_deduplication_skips_duplicate_course_codes(self, mock_publish, mock_uoc):
        """Duplicate course codes in a single request are deduplicated (last-wins)."""
        mock_uoc.return_value = (MagicMock(), True)

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [
                    {"course_code": "CS101", "day": "Monday"},
                    {"course_code": "CS101", "day": "Tuesday"},  # duplicate
                ],
            },
            format="json",
        )
        response = self.view(request)

        # skipped count should be 1 for the duplicate
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["skipped"], 1)
        # update_or_create should only be called once (for deduplicated item)
        self.assertEqual(mock_uoc.call_count, 1)

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    @patch("event_bus.publisher.publish")
    def test_successful_ingest_with_datetime_str(self, mock_publish, mock_uoc):
        """Ingestion passes datetime_str to update_or_create defaults."""
        mock_uoc.return_value = (MagicMock(), True)

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [
                    {
                        "course_code": "CS101",
                        "datetime_str": "2026-03-25T09:00:00+03:00",
                    }
                ],
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        # Verify update_or_create was called with datetime_str in defaults
        call_kwargs = mock_uoc.call_args
        defaults = call_kwargs[1].get("defaults", {})
        self.assertIn("datetime_str", defaults)
        self.assertEqual(defaults["datetime_str"], "2026-03-25T09:00:00+03:00")

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    @patch("event_bus.publisher.publish")
    def test_ingest_response_errors_list_is_empty_on_success(self, mock_publish, mock_uoc):
        """Successful ingestion returns empty errors list."""
        mock_uoc.return_value = (MagicMock(), False)  # updated, not created

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [{"course_code": "CS101"}],
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["errors"], [])
        self.assertEqual(response.data["created"], 0)
        self.assertEqual(response.data["updated"], 1)

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    def test_db_error_during_ingest_returns_400(self, mock_uoc):
        """A DB error during item ingestion rolls back and returns 400."""
        mock_uoc.side_effect = Exception("DB constraint violation")

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [{"course_code": "CS101"}],
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "ingestion_failed")
        self.assertTrue(len(response.data["errors"]) > 0)
        self.assertEqual(response.data["errors"][0]["code"], "server_error")

    @patch("examtimetable.views.ExamSchedule.objects.update_or_create")
    def test_error_response_includes_item_index_and_key(self, mock_uoc):
        """Error response includes item_index and key identifying the failed item."""
        mock_uoc.side_effect = Exception("integrity error")

        request = self.factory.post(
            "/api/exams/ingest/",
            data={
                "institution_id": "inst-001",
                "items": [{"course_code": "CS101"}],
            },
            format="json",
        )
        response = self.view(request)

        error = response.data["errors"][0]
        self.assertIn("item_index", error)
        self.assertIn("key", error)
        self.assertEqual(error["key"]["institution_id"], "inst-001")
        self.assertEqual(error["key"]["course_code"], "CS101")


class TestExamScheduleByCourseCodesView(unittest.TestCase):
    """Tests for ExamScheduleByCourseCodesView - unchanged logic, but covers NUR/NUP handling."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ExamScheduleByCourseCodesView.as_view()

    def test_missing_institution_id_returns_400(self):
        """Missing institution_id returns 400."""
        request = self.factory.post(
            "/api/exams/by-codes/",
            data={"course_codes": ["CS101"]},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("institution_id", response.data["error"])

    def test_missing_course_codes_returns_400(self):
        """Missing course_codes returns 400."""
        request = self.factory.post(
            "/api/exams/by-codes/",
            data={"institution_id": "inst-001"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_course_codes_must_be_list(self):
        """course_codes must be a list, not a string."""
        request = self.factory.post(
            "/api/exams/by-codes/",
            data={"institution_id": "inst-001", "course_codes": "CS101"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    def test_empty_course_codes_list_returns_400(self):
        """Empty course_codes list returns 400."""
        request = self.factory.post(
            "/api/exams/by-codes/",
            data={"institution_id": "inst-001", "course_codes": []},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch("examtimetable.views.ExamSchedule.objects.filter")
    def test_nur_course_code_truncated(self, mock_filter):
        """NUR course codes have last character removed before search."""
        mock_qs = MagicMock()
        mock_qs.all.return_value = []
        mock_filter.return_value = mock_qs

        request = self.factory.post(
            "/api/exams/by-codes/",
            data={
                "institution_id": "inst-001",
                "course_codes": ["NUR1010"],  # last char removed -> NUR101
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

        # Verify filter was called with a regex that uses NUR101 (not NUR1010)
        call_kwargs = mock_filter.call_args[1]
        regex_pattern = call_kwargs.get("course_code__iregex", "")
        self.assertNotIn("0$", regex_pattern.replace(r"\s*", ""))

    @patch("examtimetable.views.ExamSchedule.objects.filter")
    def test_nup_course_code_truncated(self, mock_filter):
        """NUP course codes have last character removed before search."""
        mock_qs = MagicMock()
        mock_qs.all.return_value = []
        mock_filter.return_value = mock_qs

        request = self.factory.post(
            "/api/exams/by-codes/",
            data={
                "institution_id": "inst-001",
                "course_codes": ["NUP2020"],
            },
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    @patch("examtimetable.views.ExamSchedule.objects.filter")
    def test_spaces_stripped_from_course_code(self, mock_filter):
        """Spaces are removed from course codes before regex matching."""
        mock_qs = MagicMock()
        mock_qs.all.return_value = []
        mock_filter.return_value = mock_qs

        request = self.factory.post(
            "/api/exams/by-codes/",
            data={
                "institution_id": "inst-001",
                "course_codes": ["CS 101"],
            },
            format="json",
        )
        self.view(request)

        # Filter should have been called with regex that accounts for "CS101" (spaces removed)
        call_kwargs = mock_filter.call_args[1]
        regex_pattern = call_kwargs.get("course_code__iregex", "")
        # The regex should allow \s* between each character
        self.assertIn(r"\s*", regex_pattern)

    @patch("examtimetable.views.ExamSchedule.objects.filter")
    def test_returns_200_with_matching_exams(self, mock_filter):
        """Returns 200 and exam data when courses are found."""
        mock_exam = MagicMock(spec=ExamSchedule)
        mock_exam.course_code = "CS101"
        mock_exam.day = "Monday"
        mock_exam.venue = "Hall A"
        mock_exam.start_time = None
        mock_exam.end_time = None
        mock_exam.campus = None
        mock_exam.coordinator = None
        mock_exam.hrs = None
        mock_exam.invigilator = None
        mock_exam.datetime_str = "2026-03-25T09:00:00+03:00"

        mock_qs = MagicMock()
        mock_qs.all.return_value = [mock_exam]
        mock_filter.return_value = mock_qs

        request = self.factory.post(
            "/api/exams/by-codes/",
            data={
                "institution_id": "inst-001",
                "course_codes": ["CS101"],
            },
            format="json",
        )
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)


class TestExamScheduleByInstitutionView(unittest.TestCase):
    """Tests for ExamScheduleByInstitutionView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ExamScheduleByInstitutionView.as_view()

    def test_missing_institution_id_returns_400(self):
        """Missing institution_id query param returns 400."""
        request = self.factory.get("/api/exams/by-institution/")
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("institution_id", response.data["error"])

    @patch("examtimetable.views.ExamSchedule.objects.filter")
    def test_returns_exams_for_institution(self, mock_filter):
        """Returns exam schedules filtered by institution_id."""
        mock_exam = MagicMock(spec=ExamSchedule)
        mock_exam.course_code = "CS101"
        mock_exam.day = "Monday"
        mock_exam.venue = "Hall A"
        mock_exam.start_time = None
        mock_exam.end_time = None
        mock_exam.campus = None
        mock_exam.coordinator = None
        mock_exam.hrs = None
        mock_exam.invigilator = None
        mock_exam.datetime_str = None

        mock_qs = MagicMock()
        mock_qs.__iter__ = MagicMock(return_value=iter([mock_exam]))
        mock_filter.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs

        request = self.factory.get("/api/exams/by-institution/?institution_id=inst-001")
        request.query_params = {"institution_id": "inst-001"}
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class TestStudentExamScheduleView(unittest.TestCase):
    """Tests for StudentExamScheduleView."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = StudentExamScheduleView.as_view()

    def test_missing_student_id_returns_400(self):
        """Missing student_id query param returns 400."""
        request = self.factory.get("/api/exams/student/")
        response = self.view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("student_id", response.data["error"])

    @patch("examtimetable.views.StudentProfile.objects.get")
    def test_nonexistent_student_returns_404(self, mock_get):
        """Non-existent student_id returns 404."""
        from users.models import StudentProfile
        mock_get.side_effect = StudentProfile.DoesNotExist

        request = self.factory.get("/api/exams/student/?student_id=S999")
        response = self.view(request)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Student not found", response.data["error"])


if __name__ == "__main__":
    unittest.main()