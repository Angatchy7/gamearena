from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import PasswordResetOTP

User = get_user_model()


class PasswordRecoveryOTPTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="OldPassword123!",
        )
        self.client = APIClient()

    def test_forgot_password_sends_email_and_otp(self):
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "testuser@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("GameArena Password Reset Code", mail.outbox[0].subject)

        # Check database for created OTP record
        otp = PasswordResetOTP.objects.filter(email="testuser@example.com").first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertTrue(otp.otp_code.isdigit())
        self.assertFalse(otp.is_used)

        # Ensure OTP code is NOT in response body or headers
        self.assertNotIn(otp.otp_code, str(response.data))

    def test_forgot_password_generic_response_unknown_email(self):
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "nonexistent@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_otp_success_returns_reset_token(self):
        # Generate OTP
        self.client.post("/api/auth/forgot-password/", {"email": "testuser@example.com"}, format="json")
        otp = PasswordResetOTP.objects.get(email="testuser@example.com")

        verify_res = self.client.post(
            "/api/auth/forgot-password/verify/",
            {"email": "testuser@example.com", "code": otp.otp_code},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)
        self.assertIn("reset_token", verify_res.data)
        self.assertIsNotNone(verify_res.data["reset_token"])

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        self.assertEqual(otp.reset_token, verify_res.data["reset_token"])

    def test_verify_otp_invalid_code_rejected(self):
        self.client.post("/api/auth/forgot-password/", {"email": "testuser@example.com"}, format="json")

        verify_res = self.client.post(
            "/api/auth/forgot-password/verify/",
            {"email": "testuser@example.com", "code": "000000"},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid verification code", verify_res.data["detail"])

    def test_verify_otp_expired_code_rejected(self):
        now = timezone.now()
        PasswordResetOTP.objects.create(
            email="testuser@example.com",
            otp_code="123456",
            expires_at=now - timedelta(minutes=1),
        )

        verify_res = self.client.post(
            "/api/auth/forgot-password/verify/",
            {"email": "testuser@example.com", "code": "123456"},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", verify_res.data["detail"].lower())

    def test_verify_otp_attempt_limit_exceeded(self):
        self.client.post("/api/auth/forgot-password/", {"email": "testuser@example.com"}, format="json")
        otp = PasswordResetOTP.objects.get(email="testuser@example.com")
        otp.attempts = 5
        otp.save()

        verify_res = self.client.post(
            "/api/auth/forgot-password/verify/",
            {"email": "testuser@example.com", "code": "000000"},
            format="json",
        )
        self.assertEqual(verify_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("too many failed attempts", verify_res.data["detail"].lower())

    def test_full_reset_password_flow_success(self):
        # 1. Send Code
        self.client.post("/api/auth/forgot-password/", {"email": "testuser@example.com"}, format="json")
        otp = PasswordResetOTP.objects.get(email="testuser@example.com")

        # 2. Verify Code
        verify_res = self.client.post(
            "/api/auth/forgot-password/verify/",
            {"email": "testuser@example.com", "code": otp.otp_code},
            format="json",
        )
        reset_token = verify_res.data["reset_token"]

        # 3. Reset Password
        reset_res = self.client.post(
            "/api/auth/forgot-password/reset/",
            {
                "reset_token": reset_token,
                "new_password": "BrandNewPassword789!",
                "confirm_password": "BrandNewPassword789!",
            },
            format="json",
        )
        self.assertEqual(reset_res.status_code, status.HTTP_200_OK)

        # Verify password updated in DB
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPassword789!"))

    def test_reset_password_invalid_token_rejected(self):
        reset_res = self.client.post(
            "/api/auth/forgot-password/reset/",
            {
                "reset_token": "fake_invalid_token",
                "new_password": "BrandNewPassword789!",
                "confirm_password": "BrandNewPassword789!",
            },
            format="json",
        )
        self.assertEqual(reset_res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.accounts.services.send_mail")
    def test_send_mail_failure_returns_error(self, mock_send_mail):
        mock_send_mail.side_effect = Exception("SMTP error")
        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": "testuser@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
