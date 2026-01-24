from rest_framework import serializers

from utils.base_64_helper import (
    is_base64_image,
    is_url,
    upload_base64_to_default_storage,
)
from .models import User, StudentProfile, Administrator


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "user_id",
            "name",
            "email",
            "phone",
            "username",
            "avatar_url",
            "vibe_points",
            "created_at",
            "updated_at",
        ]


class StudentProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=User.objects.all()
    )

    def validate_profile_picture(self, value):
        try:
            if not value:
                return value

            if is_base64_image(value):
                return upload_base64_to_default_storage(value)

            if is_url(value):
                return value
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise e

    class Meta:
        model = StudentProfile
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class AdministratorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user.id"
    )

    class Meta:
        model = Administrator
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]
