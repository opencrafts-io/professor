from rest_framework import serializers
from .models import ExamSchedule
from courses.models import SemesterInfo


class ExamScheduleSerializer(serializers.ModelSerializer):
    semester_code = serializers.CharField(source='semester.code', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    semester_id = serializers.IntegerField(write_only=True, required=False)
    class Meta:
        model = ExamSchedule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


    def create(self, validated_data):
        semester_id = validated_data.pop('semester_id', None)
        if semester_id:
            validated_data['semester'] = SemesterInfo.objects.get(id=semester_id)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        semester_id = validated_data.pop('semester_id', None)
        if semester_id:
            validated_data['semester'] = SemesterInfo.objects.get(id=semester_id)
        return super().update(instance, validated_data)