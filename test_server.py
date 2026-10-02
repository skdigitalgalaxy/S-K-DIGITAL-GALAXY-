import unittest
from unittest.mock import patch

import server


VALID_INQUIRY = {
    "name": "Sam Example",
    "email": "sam@example.com",
    "phone": "+1 (415) 555-0123",
    "business": "Example Co",
    "service": "Software and IT",
    "message": "Please contact me about a project.",
    "website": "",
}


class InquiryValidationTests(unittest.TestCase):
    def test_accepts_valid_inquiry(self):
        values = server.validate_inquiry(VALID_INQUIRY)
        self.assertEqual(values["email"], "sam@example.com")
        self.assertEqual(values["phone"], "+1 (415) 555-0123")
        self.assertEqual(values["service"], "Software and IT")

    def test_rejects_invalid_phone(self):
        payload = {**VALID_INQUIRY, "phone": "call me at +1 555\r\nBcc: bad"}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_sheet_sync_requires_server_configuration(self):
        values = server.validate_inquiry(VALID_INQUIRY)
        with patch.object(server, "SHEETS_WEB_APP_URL", ""), patch.object(server, "SHEETS_WEBHOOK_SECRET", ""):
            with self.assertRaises(RuntimeError):
                server.append_inquiry_to_google_sheet(values)

    def test_rejects_invalid_email(self):
        payload = {**VALID_INQUIRY, "email": "not-an-email"}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_rejects_unsupported_service(self):
        payload = {**VALID_INQUIRY, "service": "Send money"}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_rejects_control_characters_in_headers(self):
        payload = {**VALID_INQUIRY, "name": "Sam\r\nBcc: attacker@example.com"}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_rejects_extra_fields(self):
        payload = {**VALID_INQUIRY, "admin": True}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_rejects_file_upload_fields(self):
        payload = {**VALID_INQUIRY, "file": "malicious.exe"}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)

    def test_rejects_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            server._unique_json_object([("name", "first"), ("name", "second")])

    def test_script_like_message_is_plain_text_email(self):
        payload = {**VALID_INQUIRY, "message": "<script>alert('x')</script>"}
        values = server.validate_inquiry(payload)
        with patch.object(server, "SMTP_USER", "sender@example.com"), patch.object(
            server, "INQUIRY_TO", "inquiries@example.com"
        ):
            message = server.build_inquiry_message(values)

        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertFalse(message.is_multipart())
        self.assertIn("<script>alert('x')</script>", message.get_content())

    def test_rejects_oversized_message(self):
        payload = {**VALID_INQUIRY, "message": "x" * 4001}
        with self.assertRaises(ValueError):
            server.validate_inquiry(payload)


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        with server.RATE_LOCK:
            server.RATE_REQUESTS.clear()

    def test_limits_requests_per_client_and_expires_old_entries(self):
        for request_number in range(server.RATE_MAX_REQUESTS):
            self.assertFalse(server.rate_limit_exceeded("192.0.2.10", now=1000 + request_number))
        self.assertTrue(server.rate_limit_exceeded("192.0.2.10", now=1005))
        self.assertFalse(
            server.rate_limit_exceeded(
                "192.0.2.10",
                now=1005 + server.RATE_WINDOW_SECONDS + 1,
            )
        )


if __name__ == "__main__":
    unittest.main()