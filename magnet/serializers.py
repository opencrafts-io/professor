from django.db.models import fields
from rest_framework.serializers import ModelSerializer
from .models import MagnetScrappingCommand


class MagnetScrappingCommandSerializer(ModelSerializer):
    class Meta:
        model = MagnetScrappingCommand
        fields = [
            "institution",
            "name",
            "description",
            "requires_interaction",
            "command_id",
            "url",
            "instructions",
        ]
