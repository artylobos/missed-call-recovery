#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float((value or "").strip())
    except ValueError:
        return default


def score(row: dict[str, str]) -> tuple[float, dict[str, float]]:
    weekly_missed = to_float(row.get("estimated_weekly_missed_calls", ""))
    lead_value = to_float(row.get("estimated_new_customer_value_usd", ""))
    speed_minutes = to_float(row.get("current_callback_delay_minutes", ""), 240)
    reviews = to_float(row.get("google_reviews", ""))
    rating = to_float(row.get("google_rating", ""))
    has_booking = 1.0 if row.get("has_online_booking", "").lower() in {"yes", "true", "1"} else 0.0
    emergency = 1.0 if row.get("emergency_or_after_hours", "").lower() in {"yes", "true", "1"} else 0.0

    missed_value = weekly_missed * lead_value
    urgency_score = min(speed_minutes / 60, 8) * 5 + emergency * 20
    trust_score = min(reviews / 50, 10) + max(rating - 3.5, 0) * 10
    integration_score = 10 if has_booking else 20
    total = missed_value / 100 + urgency_score + trust_score + integration_score

    return total, {
        "weekly_missed_value_usd": missed_value,
        "urgency_score": urgency_score,
        "trust_score": trust_score,
        "integration_score": integration_score,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: score_prospects.py <prospects.csv>")
    path = Path(sys.argv[1])
    rows = list(csv.DictReader(path.open(newline="")))
    scored = []
    for row in rows:
        total, parts = score(row)
        row = dict(row)
        row["agent_score"] = f"{total:.1f}"
        row.update({key: f"{value:.1f}" for key, value in parts.items()})
        scored.append(row)

    scored.sort(key=lambda item: float(item["agent_score"]), reverse=True)
    fieldnames = list(scored[0].keys()) if scored else []
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(scored)


if __name__ == "__main__":
    main()
