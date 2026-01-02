from rest_framework.generics import RetrieveAPIView
from rest_framework.views import Response, status


class PingApiView(RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        return Response(
            data={"message": "he is risen"},
            status=status.HTTP_200_OK,
        )
