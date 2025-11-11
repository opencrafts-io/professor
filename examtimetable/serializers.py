from rest_framework import serializers
from .models import ExamSchedule


class ExamScheduleSerializer(serializers.ModelSerializer):
    semester_code = serializers.CharField(source='semester.code', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)

    class Meta:
        model = ExamSchedule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']