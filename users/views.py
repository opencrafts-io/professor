from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from users.models import User, Administrator
from users.serializers import UserSerializer, AdministratorSerializer


class UserManagementView(ListCreateAPIView):
    """Creates a user"""

    serializer_class = UserSerializer
    queryset = User.objects.all()

class AdministratorManagementView(ListCreateAPIView):
    """
    Allows creating and listing administrators.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AdministratorSerializer
    queryset = Administrator.objects.all()
