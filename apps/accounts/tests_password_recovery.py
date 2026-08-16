from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from apps.api.views import signer

User = get_user_model()


class PasswordRecoveryAndChangeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="OldPassword123!",
        )
        self.client = APIClient()

    def test_forgot_password_generic_response_existing_email(self):
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "testuser@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"],
            "If an account exists for this email, a password reset link has been sent.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("GameArena Password Reset", mail.outbox[0].subject)

    def test_forgot_password_generic_response_unknown_email(self):
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "nonexistent@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "If an account exists for this email, a password reset link has been sent.",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_token_generation_and_validity(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        self.assertTrue(default_token_generator.check_token(self.user, token))

    def test_authenticated_change_password_request_and_verify(self):
        self.client.force_authenticate(user=self.user)

        req_res = self.client.post("/api/auth/change-password/request/", format="json")
        self.assertEqual(req_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        # Token must NOT be in API response
        self.assertNotIn("token", req_res.data)

        token = signer.sign(f"{self.user.pk}:{self.user.email}")

        verify_res = self.client.post(
            "/api/auth/change-password/verify/",
            {
                "token": token,
                "new_password": "NewStrongPassword456!",
                "confirm_password": "NewStrongPassword456!",
            },
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword456!"))

    def test_invalid_verification_token_rejected(self):
        self.client.force_authenticate(user=self.user)

        verify_res = self.client.post(
            "/api/auth/change-password/verify/",
            {
                "token": "invalid_token_signature",
                "new_password": "NewStrongPassword456!",
                "confirm_password": "NewStrongPassword456!",
            },
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or expired", verify_res.data["detail"])

    def test_mismatched_password_confirmation_rejected(self):
        self.client.force_authenticate(user=self.user)
        token = signer.sign(f"{self.user.pk}:{self.user.email}")

        verify_res = self.client.post(
            "/api/auth/change-password/verify/",
            {
                "token": token,
                "new_password": "NewStrongPassword456!",
                "confirm_password": "DifferentPassword789!",
            },
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.api.views.send_mail")
    def test_change_password_request_email_failure_handled(self, mock_send_mail):
        mock_send_mail.side_effect = Exception("SMTP connection refused")
        self.client.force_authenticate(user=self.user)

        req_res = self.client.post("/api/auth/change-password/request/", format="json")
        self.assertEqual(req_res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Failed to send verification email", req_res.data["detail"])

    def test_password_reset_web_views(self):
        # Reset form view
        res = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(res.status_code, 200)

        # Submit reset request via web form
        res_post = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "testuser@example.com"},
        )
        self.assertEqual(res_post.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
