from rest_framework import serializers
from .models import CustomUser, StudentProfile, Administrator

class CustomUserSerializer(serializers.ModelSerializer):
  class Meta:
    model = CustomUser
    fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'institution_id', 'created_at', 'updated_at'
    ]
    read_only_fields = ['id', 'created_at', 'updated_at']

class StudentProfileSerializer(serializers.ModelSerializer):
  user = CustomUserSerializer(read_only=True)
  user_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), source='user.id')

  class Meta:
    model = StudentProfile
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

class AdministratorSerializer(serializers.ModelSerializer):
  user = CustomUserSerializer(read_only=True)
  user_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), source='user.id')

  class Meta:
    model = Administrator
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

