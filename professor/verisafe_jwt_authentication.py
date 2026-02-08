import logging
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.models import User
from .verisafe_jwt import verify_verisafe_jwt  # from earlier

logger = logging.getLogger("django")


class VerisafeJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if request.path == "/ping":
            return None

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.error("Request sent without valid authorization token")
            raise AuthenticationFailed(
                "Wrong token format. Expected 'Bearer token'", status.HTTP_403_FORBIDDEN
            )
        token = auth_header.split(" ")[1]

        try:
            payload = verify_verisafe_jwt(token)
            request.verisafe_claims = payload
            request.user_id = payload["sub"]
            user = User.objects.filter(user_id=request.user_id).first()

            if not user:
                logger.warning(
                    f"User {request.user_id} authenticated via JWT but not found in DB."
                )
                raise AuthenticationFailed(
                    "User account not provisioned. Please contact support.",
                    code="user_not_found",
                )

            # Success: User exists in DB and JWT is valid
            request.verisafe_claims = payload
            return (user, token)
        except Exception as e:
            raise AuthenticationFailed(str(e))
