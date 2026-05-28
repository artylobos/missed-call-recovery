#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


FIELDNAMES = [
    "business_name",
    "phone",
    "website",
    "agent_score",
    "subject",
    "first_message",
    "call_opener",
    "paid_pilot_close",
    "status",
]


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    load_env_file()
    parser = argparse.ArgumentParser(
        description="Generate human-approved outreach drafts from a prospect CSV."
    )
    parser.add_argument("prospects_csv")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--city", default="Sydney")
    parser.add_argument("--price", default="AUD 300 7-day paid pilot")
    parser.add_argument("--currency", default="AUD")
    parser.add_argument("--sender", default=os.getenv("OUTREACH_SENDER_NAME", "Bo"))
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(newline="")))
    if rows and "agent_score" in rows[0]:
        rows.sort(key=lambda row: float(row.get("agent_score") or 0), reverse=True)
    return rows


def build_draft(row: dict[str, str], args: argparse.Namespace) -> dict[str, str]:
    name = row.get("business_name", "").strip()
    missed = row.get("estimated_weekly_missed_calls", "").strip() or "3-5"
    value = row.get("estimated_new_customer_value_usd", "").strip() or "650"
    emergency = row.get("emergency_or_after_hours", "").lower() in {"yes", "true", "1"}
    wedge = "blocked-drain and emergency plumbing" if emergency else "plumbing"

    first_message = (
        f"Hi, this is {args.sender}. I am testing missed-call recovery for "
        f"{wedge} jobs in {args.city}. It texts missed callers "
        "within 60 seconds, captures the job details, and sends the owner a clean "
        f"lead summary. If {name} misses even {missed} calls a week, one recovered "
        f"job could be worth around {args.currency} {value}. Would a 5 minute demo "
        "be useful?"
    )

    call_opener = (
        "I am not trying to replace your receptionist. I am testing whether we "
        "can recover calls that already get missed when staff are on a job, busy, "
        "or after hours. Roughly how many missed calls did you have last week?"
    )

    paid_pilot_close = (
        f"I can set up a {args.price} with missed-call textback only. You get a "
        "daily report: missed calls, replies, qualified jobs, and owner handoffs. "
        "We do not diagnose, quote, promise dispatch, or answer as the plumber. "
        "If it does not recover useful leads, we stop instead of turning this "
        "into a bigger software project."
    )

    return {
        "business_name": name,
        "phone": row.get("phone", ""),
        "website": row.get("website", ""),
        "agent_score": row.get("agent_score", ""),
        "subject": "missed calls after hours",
        "first_message": first_message,
        "call_opener": call_opener,
        "paid_pilot_close": paid_pilot_close,
        "status": "draft_requires_human_approval",
    }


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.prospects_csv))[: args.limit]
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(build_draft(row, args))


if __name__ == "__main__":
    main()
