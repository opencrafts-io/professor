from rest_framework import serializers
from .models import SemesterInfo, Course, Grade, ScheduleEntry, Transcript, StudentCourseEnrollment
from users.models import StudentProfile

class SemesterInfoSerializer(serializers.ModelSerializer):
  class Meta:
    model = SemesterInfo
    fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
  semester_code = serializers.CharField(source='semester.code', read_only=True)
  semester_name = serializers.CharField(source='semester.name', read_only=True)
  semester_id = serializers.IntegerField(write_only=True, required=False)

  class Meta:
    model = Course
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

# TODO: Confirm if grades have to be linked to semesters or courses.
class GradeSerializer(serializers.ModelSerializer):
  semester_code = serializers.CharField(source='semester.code', read_only=True)
  semester_name = serializers.CharField(source='semester.name', read_only=True)
  semester_id = serializers.IntegerField(write_only=True, required=False)

  class Meta:
    model = Grade
    fields = '__all__'
    read_only_fields = ['created_at']

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

class ScheduleEntrySerializer(serializers.ModelSerializer):
  class Meta:
    model = ScheduleEntry
    fields = '__all__'
    read_only_fields = ['created_at']

  def validate(self, attrs):
    if attrs.get('start_time') and attrs.get('end_time'):
      if attrs['start_time'] >= attrs['end_time']:
        raise serializers.ValidationError("Start time must be before end time")
    return attrs

class TranscriptSerializer(serializers.ModelSerializer):
  student_id = serializers.CharField(source='student.student_id', read_only=True)
  student_name = serializers.CharField(source='student.user.username', read_only=True)
  program = serializers.CharField(source='student.program', read_only=True)
  grades = GradeSerializer(many=True, read_only=True)
  student_profile_id = serializers.IntegerField(write_only=True, required=False)

  class Meta:
    model = Transcript
    fields = '__all__'
    read_only_fields = ['created_at', 'updated_at']

  def create(self, validated_data):
    student_profile_id = validated_data.pop('student_profile_id', None)
    if student_profile_id:
      validated_data['student'] = StudentProfile.objects.get(id=student_profile_id)
    return super().create(validated_data)

  def update(self, instance, validated_data):
    student_profile_id = validated_data.pop('student_profile_id', None)
    if student_profile_id:
      validated_data['student'] = StudentProfile.objects.get(id=student_profile_id)
    return super().update(instance, validated_data)

class StudentCourseEnrollmentSerializer(serializers.ModelSerializer):
  student_id = serializers.CharField(source='student.student_id', read_only=True)
  student_name = serializers.CharField(source='student.user.username', read_only=True)
  course_code = serializers.CharField(source='course.course_code', read_only=True)
  course_name = serializers.CharField(source='course.course_name', read_only=True)
  semester_code = serializers.CharField(source='semester.code', read_only=True)
  semester_name = serializers.CharField(source='semester.name', read_only=True)
  
  student_profile_id = serializers.IntegerField(write_only=True, required=False)
  course_id = serializers.IntegerField(write_only=True, required=False)
  semester_id = serializers.IntegerField(write_only=True, required=False)

  class Meta:
    model = StudentCourseEnrollment
    fields = '__all__'
    read_only_fields = ['enrolled_at']

  def create(self, validated_data):
    student_profile_id = validated_data.pop('student_profile_id', None)
    course_id = validated_data.pop('course_id', None)
    semester_id = validated_data.pop('semester_id', None)
    
    if student_profile_id:
      validated_data['student'] = StudentProfile.objects.get(id=student_profile_id)
    if course_id:
      validated_data['course'] = Course.objects.get(id=course_id)
    if semester_id:
      validated_data['semester'] = SemesterInfo.objects.get(id=semester_id)
    
    return super().create(validated_data)

  def update(self, instance, validated_data):
    student_profile_id = validated_data.pop('student_profile_id', None)
    course_id = validated_data.pop('course_id', None)
    semester_id = validated_data.pop('semester_id', None)
    
    if student_profile_id:
      validated_data['student'] = StudentProfile.objects.get(id=student_profile_id)
    if course_id:
      validated_data['course'] = Course.objects.get(id=course_id)
    if semester_id:
      validated_data['semester'] = SemesterInfo.objects.get(id=semester_id)
    
    return super().update(instance, validated_data)
