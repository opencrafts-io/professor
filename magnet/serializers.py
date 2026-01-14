from rest_framework.serializers import (
    ModelSerializer,
)
from rest_framework import serializers
from .models import MagnetScrappingCommand

class WaitStrategySerializer(serializers.Serializer):
    runtimeType = serializers.CharField()
    timeoutMs = serializers.IntegerField(default=30000, required=False)
    pattern = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    selector = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quietDurationMs = serializers.IntegerField(required=False, allow_null=True)

    strategies = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

    def validate(self, data):
        # Note: When using 'source', the key in 'data' becomes the source name (runtimeType)
        wait_type = data.get("runtimeType")
        
        if wait_type == "waitForUrl" and not data.get("pattern"):
            raise serializers.ValidationError("URL strategy requires a pattern")
        
        if wait_type in ["waitForElement", "elementDisappear"] and not data.get("selector"):
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
    requires_interaction = serializers.BooleanField(default=False)

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
        instructions_data = validated_data.pop("instructions", [])
        instance = MagnetScrappingCommand.objects.create(**validated_data)
        instance.instructions = instructions_data
        instance.save()
        return instance

    def update(self, instance, validated_data):
        instructions = validated_data.pop("instructions", None)
        
        if instructions is not None:
            instance.instructions = instructions

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
     
