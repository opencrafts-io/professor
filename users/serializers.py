from rest_framework import serializers
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
  class Meta:
    model = StudentProfile
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

class AdministratorSerializer(serializers.ModelSerializer):
  user = UserSerializer(read_only=True)
  user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user.id')

  class Meta:
    model = Administrator
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

