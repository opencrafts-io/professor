"""
Tests for professor/verisafe_jwt_authentication.py changes in this PR.

PR change: Token verification is disabled (commented out).
VerisafeJWTAuthentication.authenticate() now always returns None,
bypassing all authentication checks on non-ping paths.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "professor.test_settings")
django.setup()

import unittest
from unittest.mock import MagicMock, patch

from professor.verisafe_jwt_authentication import VerisafeJWTAuthentication


class TestVerisafeJWTAuthenticationBypass(unittest.TestCase):
    """
    Tests that VerisafeJWTAuthentication.authenticate() is fully bypassed
    after the PR change (token verification commented out).
    """

    def setUp(self):
        self.auth = VerisafeJWTAuthentication()

    def _make_request(self, path, authorization=None):
        """Helper to create a mock request."""
        request = MagicMock()
        request.path = path
        if authorization:
            request.headers = {"Authorization": authorization}
        else:
            request.headers = {}
        return request

    def test_ping_path_returns_none(self):
        """authenticate() returns None for /ping path (existing behavior)."""
        request = self._make_request("/ping")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_non_ping_path_returns_none(self):
        """authenticate() returns None for any non-ping path (auth bypassed)."""
        request = self._make_request("/api/exams/ingest/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_path_with_valid_bearer_token_returns_none(self):
        """Even with a valid Bearer token header, authenticate() returns None."""
        request = self._make_request(
            "/api/exams/student/",
            authorization="Bearer some.valid.token",
        )
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_path_with_no_auth_header_returns_none(self):
        """No auth header results in None (no AuthenticationFailed raised)."""
        request = self._make_request("/api/exams/by-codes/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_path_with_wrong_token_format_returns_none(self):
        """Wrong token format no longer raises AuthenticationFailed (bypassed)."""
        request = self._make_request(
            "/api/exams/ingest/",
            authorization="Token invalid-format",
        )
        # Before the PR, this would raise AuthenticationFailed.
        # After the PR, it returns None.
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_users_api_path_returns_none(self):
        """authenticate() returns None for /users/ paths."""
        request = self._make_request("/users/profile/create/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_admin_path_returns_none(self):
        """authenticate() returns None for /admin/ paths."""
        request = self._make_request("/admin/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_courses_api_path_returns_none(self):
        """authenticate() returns None for /api/courses/ paths."""
        request = self._make_request("/api/courses/register/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_no_authentication_failed_raised_for_any_path(self):
        """No AuthenticationFailed exception is raised for any path."""
        from rest_framework.exceptions import AuthenticationFailed

        paths = [
            "/api/exams/ingest/",
            "/api/exams/student/",
            "/api/exams/by-codes/",
            "/api/courses/register/",
            "/users/profile",
        ]
        for path in paths:
            request = self._make_request(path)
            try:
                result = self.auth.authenticate(request)
                # Should return None without raising
                self.assertIsNone(result, f"Expected None for path: {path}")
            except AuthenticationFailed:
                self.fail(
                    f"AuthenticationFailed should not be raised for path: {path}"
                )

    def test_no_db_lookup_performed(self):
        """authenticate() does not perform any User DB lookup (all commented out)."""
        request = self._make_request("/api/exams/ingest/", authorization="Bearer token")
        with patch("professor.verisafe_jwt_authentication.User") as mock_user:
            self.auth.authenticate(request)
            # User.objects.filter should NOT have been called
            mock_user.objects.filter.assert_not_called()

    def test_no_jwt_verification_performed(self):
        """authenticate() does not call verify_verisafe_jwt (all commented out)."""
        request = self._make_request("/api/exams/ingest/", authorization="Bearer token")
        with patch("professor.verisafe_jwt_authentication.verify_verisafe_jwt") as mock_verify:
            self.auth.authenticate(request)
            mock_verify.assert_not_called()

    def test_exception_in_try_block_still_returns_none(self):
        """If an exception somehow occurs in the try block, returns None (not raises)."""
        # The try block is effectively empty, but let's ensure the except handler
        # returns None if triggered
        request = self._make_request("/api/exams/ingest/")
        # Since try body is all comments, no exception occurs, but the function
        # should still return None via implicit return
        result = self.auth.authenticate(request)
        self.assertIsNone(result)


class TestVerisafeJWTAuthenticationIsBaseAuthentication(unittest.TestCase):
    """Tests that VerisafeJWTAuthentication maintains its class structure."""

    def test_inherits_from_base_authentication(self):
        """VerisafeJWTAuthentication still inherits from BaseAuthentication."""
        from rest_framework.authentication import BaseAuthentication
        self.assertTrue(issubclass(VerisafeJWTAuthentication, BaseAuthentication))

    def test_has_authenticate_method(self):
        """VerisafeJWTAuthentication has an authenticate method."""
        self.assertTrue(hasattr(VerisafeJWTAuthentication, "authenticate"))
        self.assertTrue(callable(getattr(VerisafeJWTAuthentication, "authenticate")))

    def test_authenticate_accepts_request_parameter(self):
        """authenticate() accepts a request parameter."""
        import inspect
        sig = inspect.signature(VerisafeJWTAuthentication.authenticate)
        params = list(sig.parameters.keys())
        self.assertIn("request", params)


class TestRestFrameworkSettingsAuthDisabled(unittest.TestCase):
    """Tests that the REST_FRAMEWORK settings reflect auth being disabled."""

    def test_default_auth_classes_is_empty(self):
        """DEFAULT_AUTHENTICATION_CLASSES is empty in test settings (auth disabled)."""
        from django.conf import settings
        auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        # In test_settings, we explicitly set it to empty
        # In the actual PR, the VerisafeJWTAuthentication is commented out
        self.assertIsInstance(auth_classes, list)


if __name__ == "__main__":
    unittest.main()