import json
import logging
import uuid

from event_bus.consumer import BaseConsumer
from event_bus.registry import register
from institutions.models import Institution

from .models import StudentProfile, User


@register
class VerisafeUserEventConsumer(BaseConsumer):
    def __init__(self) -> None:
        self.queue_name = "io.opencrafts.keep_up.verisafe.user.events"
        self.exchange_name = "verisafe.exchange"
        self.exchange_type = "fanout"
        self.routing_key = "verisafe.user.events"
        self.logger = logging.getLogger(f"{type(self).__name__}")

    def handle_message(self, body: str, routing_key=None):
        try:
            event = json.loads(body)
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to decode message", extra={"body": body, "exception": str(e)}
            )
            return

        if not self.validate_event(event):
            return

        payload = event.get("user", {})
        metadata = event.get("meta", {})
        user = None
        try:

            match metadata.get("event_type"):
                case "user.created" | "user.updated":
                    user, created = User.objects.update_or_create(
                        user_id=uuid.UUID(payload["id"]),
                        defaults={
                            "name": payload.get("name"),
                            "username": payload.get("username"),
                            "email": payload.get("email"),
                            "phone": payload.get("phone"),
                            "avatar_url": payload.get("avatar_url"),
                            "vibe_points": payload.get("vibe_points", 0),
                        },
                    )
                    action = "created" if created else "updated"
                    self.logger.info(
                        f"User @{user.username} {action} successfully",
                        extra={"user_id": str(user.user_id), "event": "user.created"},
                    )

                case "user.deleted":
                    user_id = payload.get("id")
                    deleted_count, _ = User.objects.filter(
                        user_id=uuid.UUID(user_id)
                    ).delete()
                    if deleted_count:
                        self.logger.info(
                            f"User {user_id} deleted successfully",
                            extra={"user_id": user_id, "event": "user.deleted"},
                        )
                    else:
                        self.logger.warning(
                            f"User {user_id} not found for deletion",
                            extra={"user_id": user_id, "event": "user.deleted"},
                        )
                case _:
                    raise Exception(
                        "Failed to process user event due to incorrect event type"
                    )

        except Exception as e:
            self.logger.exception(
                "Failed to process user event",
                extra={"payload": payload, "exception": str(e)},
            )


@register
class InstitutionConnectionEventConsumer(BaseConsumer):
    def __init__(self) -> None:
        self.queue_name = "io.opencrafts.keep_up.verisafe.institution.connection.events"
        self.exchange_name = "verisafe.exchange"
        self.exchange_type = "fanout"
        self.routing_key = "verisafe.institution.connection.events"
        self.logger = logging.getLogger(f"{type(self).__name__}")

    def validate_event(
        self, event: dict, source_service: str = "io.opencrafts.verisafe"
    ):
        metadata = event.get("meta", {})
        expected_event_types = ["user.institution.connected"]
        if metadata.get("event_type") not in expected_event_types:
            self.logger.error(
                f"Wrong event_type: {expected_event_types}", extra={"abort": True}
            )
            return False
        if metadata.get("source_service_id") != source_service:
            self.logger.error(
                f"Wrong source_service_id: expected {source_service}",
                extra={"abort": True},
            )
            return False
        return True

    def handle_message(self, body: str, routing_key: str):
        try:
            event = json.loads(body)
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to decode message", extra={"body": body, "exception": str(e)}
            )
            return

        if not self.validate_event(event):
            return

        institution_connection = event.get("institution_connection", {})
        account_id = institution_connection.get("account_id")
        institution_id = institution_connection.get("institution_id")

        if not account_id or not institution_id:
            self.logger.error(
                "Missing account_id or institution_id", extra={"event": event}
            )
            return

        try:
            user = User.objects.get(user_id=uuid.UUID(account_id))
            institution = Institution.objects.get(institution_id=int(institution_id))
            student_profile, created = StudentProfile.objects.get_or_create(
                user=user,
                defaults={"student_id": account_id},
            )
            student_profile.institution = institution
            student_profile.save()

            self.logger.info(
                f"User @{user.username} connected to institution {institution.name}",
                extra={
                    "user_id": account_id,
                    "institution_id": institution_id,
                    "event": "user.institution.connected",
                },
            )
        except User.DoesNotExist:
            self.logger.error(
                f"User {account_id} not found",
                extra={
                    "account_id": account_id,
                    "event": "user.institution.connected",
                },
            )
        except Institution.DoesNotExist:
            self.logger.error(
                f"Institution {institution_id} not found",
                extra={
                    "institution_id": institution_id,
                    "event": "user.institution.connected",
                },
            )
        except Exception as e:
            self.logger.exception(
                "Failed to process institution connection event",
                extra={
                    "institution_connection": institution_connection,
                    "exception": str(e),
                },
            )
