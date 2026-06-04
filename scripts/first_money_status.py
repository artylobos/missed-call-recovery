#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "validation"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def file_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="") as handle:
        return max(sum(1 for _ in csv.DictReader(handle)), 0)


def env_present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def twilio_send_credentials_present() -> bool:
    account_auth = env_present("TWILIO_ACCOUNT_SID") and env_present("TWILIO_AUTH_TOKEN")
    api_key_auth = (
        env_present("TWILIO_ACCOUNT_SID")
        and env_present("TWILIO_API_KEY_SID")
        and env_present("TWILIO_API_KEY_SECRET")
    )
    return account_auth or api_key_auth


def health() -> dict:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8787").rstrip("/")
    try:
        with request.urlopen(f"{base_url}/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"ok": payload.get("status") == "ok", "payload": payload}
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def status_item(name: str, ok: bool, detail: str) -> dict[str, str | bool]:
    return {"name": name, "ok": ok, "detail": detail}


def main() -> None:
    load_env_file(ROOT / ".env")
    seed_rows = file_rows(VALIDATION / "sydney-emergency-plumbing-seed.csv")
    scored_rows = file_rows(VALIDATION / "sydney-emergency-plumbing-scored.csv")
    draft_rows = file_rows(VALIDATION / "outreach-drafts.csv")
    google_rows = file_rows(VALIDATION / "google-places-sydney-plumbing.csv")
    report_rows = file_rows(VALIDATION / "daily-report-template.csv")
    runtime_health = health()
    google_ready = google_rows >= 40
    public_runtime_secrets_ready = all(
        env_present(name)
        for name in ("ADMIN_API_TOKEN", "WEBHOOK_TOKEN", "TWILIO_AUTH_TOKEN")
    )
    twilio_sender_ready = twilio_send_credentials_present() and (
        env_present("TWILIO_FROM_NUMBER") or env_present("TWILIO_MESSAGING_SERVICE_SID")
    )
    real_sms_enabled = os.getenv("DRY_RUN", "1").lower() in {"0", "false", "no"}
    payment_ready = env_present("PAYMENT_LINK") or env_present("INVOICE_LINK")
    sender_identity_ready = all(
        env_present(name)
        for name in ("OUTREACH_SENDER_NAME", "OUTREACH_REPLY_TO", "OUTREACH_CALLBACK_PHONE")
    )

    items = [
        status_item(
            "vertical_selected",
            True,
            "Sydney emergency plumbing / blocked drains",
        ),
        status_item(
            "seed_prospects",
            seed_rows >= 20,
            f"{seed_rows} seeded Yellow Pages prospects",
        ),
        status_item(
            "scored_prospects",
            scored_rows >= 20,
            f"{scored_rows} scored prospects",
        ),
        status_item(
            "outreach_drafts",
            draft_rows >= 20,
            f"{draft_rows} human-approval outreach drafts",
        ),
        status_item(
            "google_places_import",
            google_ready,
            f"{google_rows} Google Places prospects imported"
            if google_ready
            else f"{google_rows} Google Places prospects; needs GOOGLE_MAPS_API_KEY for live import",
        ),
        status_item(
            "runtime_local",
            bool(runtime_health["ok"]),
            json.dumps(runtime_health, ensure_ascii=False),
        ),
        status_item(
            "pilot_scope",
            (VALIDATION / "pilot-scope.md").exists() and report_rows == 0,
            "AUD 300 pilot scope and daily report template exist",
        ),
        status_item(
            "public_runtime_secrets",
            public_runtime_secrets_ready,
            "Public runtime secrets present"
            if public_runtime_secrets_ready
            else "Needed before public deployment: ADMIN_API_TOKEN, WEBHOOK_TOKEN, TWILIO_AUTH_TOKEN",
        ),
        status_item(
            "twilio_real_sms",
            twilio_sender_ready and real_sms_enabled,
            "Twilio real SMS enabled"
            if twilio_sender_ready and real_sms_enabled
            else (
                "Twilio credentials and sender present; keep DRY_RUN=1 until verified"
                if twilio_sender_ready
                else "Needs Twilio sender plus Account SID/Auth Token or API Key credentials; keep DRY_RUN=1 until verified"
            ),
        ),
        status_item(
            "payment_ready",
            payment_ready,
            "Payment link or invoice link present"
            if payment_ready
            else "Needed to close first money: PAYMENT_LINK or INVOICE_LINK",
        ),
        status_item(
            "sender_identity_ready",
            sender_identity_ready,
            "Outreach sender identity present"
            if sender_identity_ready
            else "Needed before outreach: OUTREACH_SENDER_NAME, OUTREACH_REPLY_TO, OUTREACH_CALLBACK_PHONE",
        ),
    ]

    blockers = [item for item in items if not item["ok"]]
    payload = {
        "ok": not blockers,
        "ready_for": "paid_outreach_and_install" if not blockers else "next_setup",
        "items": items,
        "next_actions": [
            item["detail"] for item in blockers[:5]
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
