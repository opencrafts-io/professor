from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch
from users.models import User
from courses.models import Course, StudentCourseEnrollment, SemesterInfo
from institutions.models import Institution
from users.models import StudentProfile
import json

class TestExamNotification(APITestCase):
    def setUp(self):
        # Setup Data
        self.user = User.objects.create(username="teststudent", name="Test Student")
        self.student = StudentProfile.objects.create(user=self.user, student_id="S123")
        self.institution = Institution.objects.create(
            name="Test Inst",
            country="Test",
            web_pages=["http://test.com"],
            domains=["test.com"]
        )
        self.semester = SemesterInfo.objects.create(code="SEM1", name="Semester 1", start_date="2025-01-01", end_date="2025-05-01", year=2025)
        self.course = Course.objects.create(
            course_code="TEST101",
            course_name="Test Course",
            semester=self.semester,
            institution=self.institution
        )
        StudentCourseEnrollment.objects.create(student=self.student, course=self.course, semester=self.semester)

    @patch('event_bus.publisher.publish')
    def test_ingest_triggers_publish(self, mock_publish):
        """
        Verify that the view calls publisher.publish
        """
        admin_user = User.objects.create(username='admin', name='Admin')
        self.client.force_authenticate(user=admin_user)

        payload = {
            "institution_id": str(self.institution.institution_id),
            "semester_id": self.semester.id,
            "items": [
                {
                    "course_code": "TEST101",
                    "day": "MONDAY 08/12/25",
                    "time": "9:00AM-11:00AM",
                    "venue": "TestVenue",
                    "hrs": "2.0",
                    "exam_date": "2025-12-08",
                    "start_time": "09:00",
                    "end_time": "11:00"
                }
            ]
        }

        url = reverse('ingest-exam-schedule')
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, 200, f"Response: {response.content}")
        self.assertTrue(mock_publish.called)

        # Check args
        args, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['queue_name'], "batch.exam_schedule.ingested")

        message = json.loads(kwargs['message'])
        self.assertEqual(message['institution_id'], str(self.institution.institution_id))
        self.assertIn("TEST101", message['course_codes'])

    def test_consumer_logic_with_institution(self):
        """
        Test the consumer logic filters by institution
        """
        # We need to import the Registered class.
        # Note: Since @register returns the list CONSUMERS, importing directly might be tricky if we want the class itself for testing.
        # But wait, @register in registry.py returns CONSUMERS list.
        # So ExamScheduleIngestedConsumer in examtimetable.consumers IS the list!
        # This makes unit testing the class hard if the decorator replaces it.
        # Let's check registry.py again. Yes, it returns CONSUMERS.

        # However, for testing, we can just grab the instance from the CONSUMERS list if it's there?
        # Or we can bypass the decorator import if possible? No.

        # Actually, if we import 'examtimetable.consumers', the code runs and adds to CONSUMERS.
        # The symbol 'ExamScheduleIngestedConsumer' will result in the list CONSUMERS.
        from examtimetable import consumers

        # Find the consumer in the list? No, the list contains CLASSES.
        # Wait, registry code:
        # CONSUMERS.append(consumer_cls)
        # return CONSUMERS

        # So `ExamScheduleIngestedConsumer` variable in that module will be `CONSUMERS` (List).
        # But the class object itself is inside that list.
        # We can find it by class name string?

        consumer_cls = None
        # We need to access the class definition. Since the name is rebound, we have to look in the list.
        # But wait, we just appended the class to the global CONSUMERS list in `event_bus.registry`.
        # So we can search `event_bus.registry.CONSUMERS`.

        from event_bus.registry import CONSUMERS
        for cls in CONSUMERS:
            if cls.__name__ == 'ExamScheduleIngestedConsumer':
                consumer_cls = cls
                break

        self.assertIsNotNone(consumer_cls, "Consumer class should be registered")

        consumer = consumer_cls() # Instantiate

        # Create another course/enrollment in a DIFFERENT institution
        other_inst = Institution.objects.create(
            name="Other Inst",
            country="Test",
            web_pages=["http://other.com"],
            domains=["other.com"]
        )
        other_course = Course.objects.create(
            course_code="TEST101", # Same code, diff institution
            course_name="Test Course Other",
            semester=self.semester,
            institution=other_inst
        )
        other_user = User.objects.create(username="otherstudent", name="Other Student")
        other_student = StudentProfile.objects.create(user=other_user, student_id="S456")
        StudentCourseEnrollment.objects.create(student=other_student, course=other_course, semester=self.semester)

        # Message for the FIRST institution
        message = {
            "institution_id": self.institution.institution_id,
            "semester_id": self.semester.id,
            "course_codes": ["TEST101"]
        }

        # Use simple structure as used in View, Consumer supports it via fallback

        with self.assertLogs('ExamScheduleIngestedConsumer', level='INFO') as cm:
            consumer.handle_message(json.dumps(message), "routing_key")

            # Check we notified the correct student
            self.assertTrue(any(f"Notifying Student {self.user.username}" in log for log in cm.output), "Should notify student in correct institution")

            # Check we DID NOT notify the other student
            self.assertFalse(any(f"Notifying Student {other_user.username}" in log for log in cm.output), "Should NOT notify student in wrong institution")
