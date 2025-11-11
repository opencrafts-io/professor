from rest_framework import serializers
from .models import SemesterInfo, Course, Grade, ScheduleEntry, Transcript

class SemesterInfoSerializer(serializers.ModelSerializer):
  class Meta:
    model = SemesterInfo
    fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
  semester_code = serializers.CharField(source='semester.code')
  semester_name = serializers.CharField(source='semester.name')

  class Meta:
    model = Course
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

class GradeSerializer(serializers.ModelSerializer):
  semester_code = serializers.CharField(source='semester.code')
  semester_name = serializers.CharField(source='semester.name')

  class Meta:
    model = Grade
    fields = '__all__'
    read_only_fields = ['created_at']

class ScheduleEntrySerializer(serializers.ModelSerializer):
  class Meta:
    model = ScheduleEntry
    fields = '__all__'
    read_only_fields = ['created_at']

class TranscriptSerializer(serializers.ModelSerializer):
   student_id = serializers.CharField(source='student.student_id', read_only=True)
   student_name = serializers.CharField(source='student.user.username', read_only=True)
   program = serializers.CharField(source='student.program', read_only=True)
   grades = GradeSerializer(many=True, read_only=True, source='student.grades')

   class Meta:
      model = Transcript
      fields = '__all__'
      read_only_fields = ['created_at', 'updated_at']
