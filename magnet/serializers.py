from rest_framework.serializers import (
    ModelSerializer,
)
from rest_framework import serializers
from .models import MagnetScrappingCommand


class WaitStrategySerializer(serializers.Serializer):
    # 'url', 'element', 'elementDisappear', 'networkIdle', 'any', 'all'
    type = serializers.CharField()
    timeoutMs = serializers.IntegerField(default=30000, required=False)

    # Specific fields based on type
    pattern = serializers.CharField(required=False)
    selector = serializers.CharField(required=False)
    quietDurationMs = serializers.IntegerField(required=False)

    strategies = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

    def validate(self, data, *args, **kwargs):
        """Logic to ensure the right fields exist for the right type."""
        wait_type = data.get("type")
        if wait_type == "url" and not data.get("pattern"):
            raise serializers.ValidationError("URL strategy requires a pattern")
        if wait_type in ["element", "elementDisappear"] and not data.get("selector"):
            raise serializers.ValidationError(
                f"{wait_type} strategy requires a selector"
            )
        return data


class ScrapingInstructionSerializer(serializers.Serializer):
    type = serializers.CharField()  # extract, click, fill-form, etc.
    selector = serializers.CharField(required=False, allow_null=True)
    xpath = serializers.CharField(required=False, allow_null=True)
    attribute = serializers.CharField(required=False, allow_null=True)
    value = serializers.CharField(required=False, allow_null=True)
    waitMilliseconds = serializers.IntegerField(required=False, allow_null=True)
    outputKey = serializers.CharField(required=False, allow_null=True)
    jsCode = serializers.CharField(required=False, allow_null=True)
    waitAfterExecution = serializers.BooleanField(default=False)

    # Nested Wait Strategy
    waitStrategy = WaitStrategySerializer(required=False, allow_null=True)


class MagnetScrappingCommandSerializer(ModelSerializer):
    instructions = ScrapingInstructionSerializer(many=True)
    requires_interaction = serializers.BooleanField(
        source="requiresInteraction", default=False
    )

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

    def create(self, validated_data):
        return super().create(validated_data)
