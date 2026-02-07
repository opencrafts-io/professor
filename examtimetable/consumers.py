import json
import logging
from courses.models import StudentCourseEnrollment
from event_bus.consumer import BaseConsumer
from event_bus.registry import register

logger = logging.getLogger(__name__)

@register
class ExamScheduleIngestedConsumer(BaseConsumer):
    def __init__(self) -> None:
        super().__init__()
        self.queue_name = "batch.exam_schedule.ingested"
        self.exchange_name = "professor.events"
        self.exchange_type = "topic"
        self.routing_key = "batch.exam_schedule.ingested"
        self.logger = logging.getLogger(f"{type(self).__name__}")

    def handle_message(self, body: str, routing_key: str):
        try:
            data = json.loads(body)
            payload = data.get("payload", data)

            course_codes = payload.get("course_codes", [])
            institution_id = payload.get("institution_id")
            semester_id = payload.get("semester_id")

            if not course_codes:
                self.logger.info("No course codes in event.")
                return

            self.logger.info(f"Processing {len(course_codes)} courses for Institution {institution_id}")

            enrollments = StudentCourseEnrollment.objects.filter(
                course__course_code__in=course_codes,
            )

            if semester_id:
                enrollments = enrollments.filter(semester=semester_id)

            if institution_id:
                enrollments = enrollments.filter(course__institution__institution_id=institution_id)

            notified_count = 0
            for enrollment in enrollments:
                student_name = enrollment.student.user.username
                course_code = enrollment.course.course_code

                self.logger.info(f"NOTIFICATION: Notifying Student {student_name} about available Exam Schedule for {course_code}")
                notified_count += 1

            self.logger.info(f"Completed.")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
