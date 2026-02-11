from django.urls import path
from .views import (
    StudentProfileCreateView,
    StudentProfileDeleteView,
    StudentProfileDetailView,
    StudentProfileListView,
    StudentProfileRetrieveView,
    StudentProfileUpdateView,
    UserManagementView,
    AdministratorManagementView,
)

urlpatterns = [
    path("", UserManagementView.as_view(), name="verisafe-user-management"),
    path(
        "administrators/", AdministratorManagementView.as_view(), name="administrators"
    ),
    path("profile", StudentProfileListView.as_view(), name="list"),
    path("profile/create/", StudentProfileCreateView.as_view(), name="create"),
    path("profile/mine", StudentProfileDetailView.as_view(), name="detail"),
    path("profile/<int:pk>/", StudentProfileRetrieveView.as_view(), name="retrieve"),
    path("profile/<int:pk>/update/", StudentProfileUpdateView.as_view(), name="update"),
    path("profile/<int:pk>/delete/", StudentProfileDeleteView.as_view(), name="delete"),
]
