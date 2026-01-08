from django.shortcuts import render
from rest_framework.generics import CreateAPIView, RetrieveAPIView

from magnet.models import MagnetScrappingCommand
from .serializers import MagnetScrappingCommandSerializer


class CreateMagnetCommandApiView(CreateAPIView):
    """
    Creates a MagnetScrappingCommand
    """

    serializer_class = MagnetScrappingCommandSerializer
    queryset = MagnetScrappingCommand.objects.all()


class RetrieveMagnetCommandApiView(RetrieveAPIView):
    lookup_field = "institution_id"
    lookup_url_kwarg = "institution_id"
    serializer_class = MagnetScrappingCommandSerializer

    def get_object(self, *args, **kwargs):
        institution_id = self.kwargs["institution_id"]
        return MagnetScrappingCommand.objects.filter(
            institution_id=institution_id,
        ).latest("created_at")
