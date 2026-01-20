from rest_framework.serializers import (
    ModelSerializer,
)
from rest_framework import serializers
from .models import MagnetScrappingCommand


class WaitStrategySerializer(serializers.Serializer):
    type = serializers.CharField()
    timeoutMs = serializers.IntegerField(default=30000, required=False)
    pattern = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    selector = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quietDurationMs = serializers.IntegerField(required=False, allow_null=True)
    strategies = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

    def validate(self, attrs):
        wait_type = attrs.get("type")

        if wait_type == "url" and not attrs.get("pattern"):
            raise serializers.ValidationError("URL strategy requires a pattern")

        if wait_type in ["element", "elementDisappear"] and not attrs.get("selector"):
            raise serializers.ValidationError(
                f"{wait_type} strategy requires a selector"
            )

        if wait_type in ["any", "all"] and not attrs.get("strategies"):
            raise serializers.ValidationError(
                f"{wait_type} strategy requires strategies list"
            )

        return attrs


class ScrapingInstructionSerializer(serializers.Serializer):
    type = serializers.CharField()  # extract, click, fill-form, wait, etc.

    # Targeting
    selector = serializers.CharField(required=False, allow_null=True)
    xpath = serializers.CharField(required=False, allow_null=True)
    attribute = serializers.CharField(required=False, allow_null=True)

    # Values and output
    value = serializers.CharField(required=False, allow_null=True)
    outputKey = serializers.CharField(required=False, allow_null=True)
    valueKey = serializers.CharField(required=False, allow_null=True)

    # Execution behavior
    waitMilliseconds = serializers.IntegerField(required=False, allow_null=True)
    waitAfterExecution = serializers.BooleanField(default=False)
    jsCode = serializers.CharField(required=False, allow_null=True)

    # Retry/fault handling
    faultStrategy = serializers.ChoiceField(
        choices=["abort", "ignore", "retry"],
        default="abort",
        required=False,
    )
    maxRetries = serializers.IntegerField(default=0, required=False)
    retryDelay = serializers.IntegerField(default=1000, required=False)  # milliseconds

    # Form configuration
    inputType = serializers.ChoiceField(
        choices=["password", "text", "number", "email", "phone"],
        allow_null=True,
        required=False,
    )
    inputLabel = serializers.CharField(required=False, allow_null=True)

    # Nested Wait Strategy
    waitStrategy = WaitStrategySerializer(required=False, allow_null=True)

    def validate(self, attrs):
        instruction_type = attrs.get("type")

        if instruction_type == "fill-form":
            if not attrs.get("valueKey"):
                raise serializers.ValidationError(
                    "instructions of type 'fill-form' must have a non-null valueKey"
                )

        if instruction_type == "extract":
            if not attrs.get("outputKey"):
                raise serializers.ValidationError(
                    "instructions of type 'extract' must have a non-null outputKey"
                )

        return attrs


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
