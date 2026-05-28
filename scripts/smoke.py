#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from urllib import request


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8787").rstrip("/")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")


def get(path: str, token: str = "") -> dict:
    req = request.Request(f"{BASE_URL}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post(path: str, payload: dict, token: str = "") -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    health = get("/health")
    assert health["status"] == "ok", health

    missed = post(
        "/webhooks/missed-call",
        {
            "From": "+15555550123",
            "CallSid": "CA_demo_missed_call",
            "CallStatus": "no-answer",
            "service": "emergency tooth pain",
            "preferred_time": "today afternoon",
        },
        WEBHOOK_TOKEN,
    )
    assert missed["ok"] is True, missed

    vapi = post(
        "/webhooks/vapi/tool",
        {
            "message": {
                "toolCalls": [
                    {
                        "function": {
                            "name": "capture_lead",
                            "arguments": json.dumps(
                                {
                                    "name": "Jamie Chen",
                                    "phone": "+15555550124",
                                    "service": "new patient cleaning",
                                    "preferred_time": "Friday morning",
                                    "transcript": "Caller wants a cleaning appointment.",
                                    "urgency": "normal",
                                }
                            ),
                        }
                    }
                ]
            }
        },
        WEBHOOK_TOKEN,
    )
    assert "lead_id" in vapi, vapi
    assert "Jamie Chen" in vapi["summary"], vapi
    assert "+15555550124" in vapi["summary"], vapi
    assert "new patient cleaning" in vapi["summary"], vapi

    leads = get("/leads", ADMIN_API_TOKEN)
    assert len(leads["leads"]) >= 2, leads

    events = get("/events", ADMIN_API_TOKEN)
    assert any(event["type"] == "sms" for event in events["events"]), events

    print(
        json.dumps(
            {
                "ok": True,
                "health": health,
                "missed_call_lead_id": missed["lead_id"],
                "vapi_lead_id": vapi["lead_id"],
                "lead_count": len(leads["leads"]),
                "event_count": len(events["events"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
