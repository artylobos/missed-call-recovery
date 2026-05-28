from __future__ import annotations

import base64
import hashlib
import hmac
import io
import tempfile
import unittest
from pathlib import Path

from ai_receptionist_autopilot.server import (
    Config,
    RequestTooLarge,
    Store,
    demo_page,
    extract_tool_args,
    is_admin_authorized,
    missed_call_to_lead,
    parse_request_body,
    twilio_rest_credentials,
    validate_twilio_signature,
)


def make_config(**overrides: object) -> Config:
    values = {
        "port": 8787,
        "data_dir": Path("./data"),
        "dry_run": True,
        "business_name": "Test Business",
        "business_phone": "",
        "public_base_url": "https://example.com",
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_api_key_sid": "",
        "twilio_api_key_secret": "",
        "twilio_from_number": "",
        "twilio_messaging_service_sid": "",
        "sheets_webhook_url": "",
        "ghl_inbound_webhook_url": "",
        "crm_webhook_url": "",
        "owner_notify_webhook_url": "",
        "admin_api_token": "",
        "webhook_token": "",
        "max_body_bytes": 1024,
        "requests_per_minute": 120,
        "allow_unauthenticated_loopback": True,
    }
    values.update(overrides)
    return Config(**values)


class FakeHandler:
    def __init__(
        self,
        headers: dict[str, str] | None = None,
        path: str = "/webhooks/missed-call",
        body: bytes = b"",
        client_ip: str = "203.0.113.10",
    ):
        self.headers = headers or {}
        self.path = path
        self.rfile = io.BytesIO(body)
        self.client_address = (client_ip, 12345)


class PayloadParsingTest(unittest.TestCase):
    def test_extracts_vapi_arguments_json_string(self) -> None:
        payload = {
            "message": {
                "toolCalls": [
                    {
                        "function": {
                            "arguments": '{"name":"Sam","phone":"+15555550123","service":"roof leak"}'
                        }
                    }
                ]
            }
        }

        lead = extract_tool_args(payload)

        self.assertEqual(lead["name"], "Sam")
        self.assertEqual(lead["phone"], "+15555550123")
        self.assertEqual(lead["service"], "roof leak")

    def test_extracts_vapi_arguments_before_function_name(self) -> None:
        payload = {
            "message": {
                "toolCalls": [
                    {
                        "function": {
                            "name": "capture_lead",
                            "arguments": '{"name":"Jamie Chen","phone":"+15555550124","service":"AC repair"}',
                        }
                    }
                ]
            }
        }

        lead = extract_tool_args(payload)

        self.assertEqual(lead["name"], "Jamie Chen")
        self.assertEqual(lead["phone"], "+15555550124")
        self.assertEqual(lead["service"], "AC repair")

    def test_normalizes_twilio_missed_call(self) -> None:
        lead = missed_call_to_lead({"From": "+15555550123", "TranscriptionText": "Need help today"})

        self.assertEqual(lead["phone"], "+15555550123")
        self.assertEqual(lead["service"], "missed call follow-up")
        self.assertEqual(lead["transcript"], "Need help today")


class StoreTest(unittest.TestCase):
    def test_adds_lead(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "demo.db")
            lead_id, created = store.add_lead("test", {"phone": "+15555550123", "service": "dental"}, {})

            rows = store.list_rows("leads")

        self.assertTrue(created)
        self.assertEqual(rows[0]["id"], lead_id)
        self.assertEqual(rows[0]["source"], "test")

    def test_deduplicates_by_provider_call_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "demo.db")
            first_id, first_created = store.add_lead(
                "missed_call",
                {"phone": "+15555550123", "service": "roof leak"},
                {"CallSid": "CA123"},
            )
            second_id, second_created = store.add_lead(
                "missed_call",
                {"phone": "+15555550123", "service": "roof leak"},
                {"CallSid": "CA123"},
            )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_id, second_id)


class SecurityTest(unittest.TestCase):
    def test_admin_token_required_for_remote_request(self) -> None:
        config = make_config(admin_api_token="admin-secret")

        self.assertFalse(is_admin_authorized(FakeHandler(), config))
        self.assertTrue(is_admin_authorized(FakeHandler({"Authorization": "Bearer admin-secret"}), config))

    def test_loopback_can_use_local_admin_without_token(self) -> None:
        config = make_config(admin_api_token="", allow_unauthenticated_loopback=True)

        self.assertTrue(is_admin_authorized(FakeHandler(client_ip="127.0.0.1"), config))
        self.assertFalse(is_admin_authorized(FakeHandler(client_ip="203.0.113.10"), config))

    def test_validates_twilio_signature(self) -> None:
        auth_token = "twilio-auth-token"
        payload = {"CallSid": "CA123", "From": "+15555550123"}
        url = "https://example.com/webhooks/missed-call"
        signed = url + "".join(f"{key}{payload[key]}" for key in sorted(payload))
        signature = base64.b64encode(
            hmac.new(auth_token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1).digest()
        ).decode("ascii")
        handler = FakeHandler({"X-Twilio-Signature": signature})
        config = make_config(twilio_auth_token=auth_token)

        self.assertTrue(validate_twilio_signature(handler, config, payload))

    def test_rejects_oversized_body_before_reading(self) -> None:
        handler = FakeHandler(headers={"Content-Length": "20"}, body=b"0123456789")

        with self.assertRaises(RequestTooLarge):
            parse_request_body(handler, max_body_bytes=10)


class ConfigTest(unittest.TestCase):
    def test_config_defaults_to_dry_run(self) -> None:
        config = Config.from_env()

        self.assertTrue(config.dry_run)

    def test_twilio_rest_credentials_prefer_api_key(self) -> None:
        config = make_config(
            twilio_account_sid="AC_account",
            twilio_auth_token="auth-token",
            twilio_api_key_sid="SK_key",
            twilio_api_key_secret="api-secret",
        )

        self.assertEqual(twilio_rest_credentials(config), ("SK_key", "api-secret"))

    def test_twilio_rest_credentials_fall_back_to_auth_token(self) -> None:
        config = make_config(twilio_account_sid="AC_account", twilio_auth_token="auth-token")

        self.assertEqual(twilio_rest_credentials(config), ("AC_account", "auth-token"))


class DemoPageTest(unittest.TestCase):
    def test_demo_page_escapes_business_name_and_exposes_demo_actions(self) -> None:
        config = make_config(business_name="A&B <HVAC>")

        html = demo_page(config)

        self.assertIn("A&amp;B &lt;HVAC&gt;", html)
        self.assertIn("/webhooks/missed-call", html)
        self.assertIn("/webhooks/vapi/tool", html)
        self.assertIn("Create Missed-Call Lead", html)
        self.assertNotIn("A&B <HVAC>", html)


if __name__ == "__main__":
    unittest.main()
