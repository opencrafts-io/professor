from rest_framework import status
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    CreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView, PermissionDenied, Response
from users.models import StudentProfile, User, Administrator
from users.serializers import (
    StudentProfileSerializer,
    UserSerializer,
    AdministratorSerializer,
)


class UserManagementView(ListCreateAPIView):
    """Creates a user"""

    serializer_class = UserSerializer
    queryset = User.objects.all()


class AdministratorManagementView(ListCreateAPIView):
    """
    Allows creating and listing administrators.
    """

    serializer_class = AdministratorSerializer
    queryset = Administrator.objects.all()


class StudentProfileCreateView(CreateAPIView):
    """Create a new student profile"""

    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user_id = self.request.data.get("user_id")
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
                serializer.save(user=user)
            except User.DoesNotExist:
                raise NotFound("User not found")
        else:
            serializer.save()


class StudentProfileRetrieveView(RetrieveAPIView):
    """Retrieve a student profile by ID"""

    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()
    lookup_field = "pk"

    def get_object(self):
        try:
            return StudentProfile.objects.get(pk=self.kwargs[self.lookup_field])
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")


class StudentProfileListView(ListAPIView):
    """List all student profiles"""

    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()

    def get_queryset(self):
        queryset = StudentProfile.objects.all()

        # Filter by institution if provided
        institution_id = self.request.query_params.get("institution_id")
        if institution_id:
            queryset = queryset.filter(institution_id=institution_id)

        # Filter by student_id if provided
        student_id = self.request.query_params.get("student_id")
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # Filter by program if provided
        program = self.request.query_params.get("program")
        if program:
            queryset = queryset.filter(program=program)

        return queryset


class StudentProfileUpdateView(UpdateAPIView):
    """Update a student profile (partial or full)"""

    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()
    lookup_field = "pk"

    def get_object(self):
        try:
            profile = StudentProfile.objects.get(pk=self.kwargs[self.lookup_field])
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")

        # Check if user owns this profile or is an admin
        if (
            profile.user_id != self.request.user.user_id
            and not self.request.user.is_staff
        ):
            raise PermissionDenied("You don't have permission to update this profile")

        return profile

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests"""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class StudentProfileDeleteView(DestroyAPIView):
    """Delete a student profile"""

    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()
    lookup_field = "pk"

    def get_object(self):
        try:
            profile = StudentProfile.objects.get(pk=self.kwargs[self.lookup_field])
        except StudentProfile.DoesNotExist:
            raise NotFound("Student profile not found")

        # Check if user owns this profile or is an admin
        if (
            profile.user_id != self.request.user.user_id
            and not self.request.user.is_staff
        ):
            raise PermissionDenied("You don't have permission to delete this profile")

        return profile

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Student profile deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


class StudentProfileDetailView(APIView):
    """
    Retrieve student profile for the authenticated user
    """

    def get(self, request):
        profiles = StudentProfile.objects.filter(user=request.user)
        serializer = StudentProfileSerializer(profiles, many=True)
        return Response(serializer.data)
