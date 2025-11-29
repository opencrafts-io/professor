from rest_framework import serializers
from .models import ExamSchedule
from courses.models import SemesterInfo


class ExamScheduleSerializer(serializers.ModelSerializer):
    semester_id = serializers.IntegerField(write_only=True, required=False)
    time = serializers.SerializerMethodField()

    class Meta:
        model = ExamSchedule
        fields = ['course_code', 'institution_id', 'day', 'time', 'venue', 'hrs', 'semester_id']
        read_only_fields = ['course_code', 'institution_id', 'day', 'time', 'venue', 'hrs']

    def get_time(self, obj):
        if obj.raw_data and 'time' in obj.raw_data:
            return obj.raw_data['time']

        if obj.start_time and obj.end_time:
            start_str = obj.start_time.strftime('%I:%M%p').lstrip('0')
            end_str = obj.end_time.strftime('%I:%M%p').lstrip('0')
            return f"{start_str}-{end_str}"

        return ""

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