from django.urls import path

from magnet.views import CreateMagnetCommandApiView, RetrieveMagnetCommandApiView

urlpatterns = [
    path(
        "command/create",
        CreateMagnetCommandApiView.as_view(),
        name="create-magnet-command",
    ),
    path(
        "command/for/<int:institution_id>",
        RetrieveMagnetCommandApiView.as_view(),
        name="retrieve-magnet-command-for-institution",
    ),
]
