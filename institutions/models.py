from django.db import models
from django.contrib.postgres.fields import ArrayField


# Create your models here.
class Institution(models.Model):
    """
    An institution model represents a real life institution e.g Stanford
    """

    institution_id = models.BigAutoField(
        primary_key=True,
    )
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
    )
    web_pages = ArrayField(
        models.URLField(),
    )
    domains = ArrayField(models.CharField(max_length=255))
    country = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f"{self.institution_id} - {self.name}"
