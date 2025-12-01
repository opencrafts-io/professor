from django.urls import path
from .views import (
    UserManagementView,
    AdministratorManagementView,
)

urlpatterns = [
    path("", UserManagementView.as_view(), name="verisafe-user-management"),
    path("administrators/", AdministratorManagementView.as_view(), name="administrators"),
]
