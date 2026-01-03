import json
import logging
from event_bus.consumer import BaseConsumer
from event_bus.registry import register
from .models import Institution


@register
class VerisafeInstitutionEventConsumer(BaseConsumer):
    def __init__(self) -> None:
        self.queue_name = "io.opencrafts.professor.institution.events"
        self.exchange_name = "professor.exchange"
        self.exchange_type = "direct"
        self.routing_key = "institution.events"
        self.logger = logging.getLogger(f"{type(self).__name__}")

    def handle_message(self, body: str, routing_key=None):
        try:
            event = json.loads(body)
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to decode message", extra={"body": body, "exception": str(e)}
            )
            return

        payload = event.get("institution", {})
        metadata = event.get("meta", {})
        try:

            match metadata.get("event_type"):
                case "institution.created" | "institution.updated":
                    institution, created = Institution.objects.update_or_create(
                        institution_id=int(payload["institution_id"]),
                        defaults={
                            "name": payload.get("name"),
                            "web_pages": payload.get("web_pages"),
                            "domains": payload.get("domains"),
                            "country": payload.get("country"),
                            "state_province": payload.get("state_province"),
                        },
                    )
                    action = "created" if created else "updated"
                    self.logger.info(
                        f"Institution @{institution.name} {action} successfully",
                    )

                case "institution.deleted":
                    institution_id = int(payload.get("institution_id"))
                    deleted_count, _ = Institution.objects.filter(
                        institution_id=institution_id
                    ).delete()
                    if deleted_count:
                        self.logger.info(
                            f"User {institution_id} deleted successfully",
                            extra={
                                "institution_id": institution_id,
                                "event": "institution.deleted",
                            },
                        )
                    else:
                        self.logger.error(
                            f"User {institution_id} not found for deletion",
                            extra={
                                "institution_id": institution_id,
                                "event": "institution.deleted",
                            },
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
