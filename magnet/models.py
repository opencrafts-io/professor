import uuid
from django.db import models
from institutions.models import Institution


# Create your models here.
class MagnetConfig(models.Model):
    """
    A model representing a magnet command composed of instructions
    """

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="institution_magnet_configs",
        null=True,
    )

    command_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
    )

    name = models.CharField(
        max_length=60,
        null=False,
    )

    description = models.TextField(default="")

    requires_interaction = models.BooleanField(
        default=False,
    )

    created_at = models.DateField(auto_now_add=True)

    instructions = models.JSONField(default=list)

    def __str__(self) -> str:
        return f"{self.name} - {self.description[:20]}"
