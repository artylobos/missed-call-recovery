#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import http.client
import json
import os
import sys
import time


API_HOST = "places.googleapis.com"
API_PATH = "/v1/places:searchText"
DEFAULT_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.googleMapsUri",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.regularOpeningHours",
        "nextPageToken",
    ]
)
DEFAULT_QUERIES = [
    "emergency plumber Sydney NSW",
    "blocked drain plumber Sydney NSW",
    "24 hour plumber Sydney NSW",
    "after hours plumber Sydney NSW",
    "hot water emergency plumber Sydney NSW",
    "plumber Inner West Sydney NSW",
    "plumber North Shore Sydney NSW",
    "plumber Eastern Suburbs Sydney NSW",
]

FIELDNAMES = [
    "business_name",
    "vertical",
    "city",
    "website",
    "phone",
    "google_rating",
    "google_reviews",
    "estimated_weekly_missed_calls",
    "estimated_new_customer_value_usd",
    "current_callback_delay_minutes",
    "has_online_booking",
    "emergency_or_after_hours",
    "notes",
]


def load_env_file(path: str = ".env") -> None:
    env_path = os.path.abspath(path)
    if not os.path.exists(env_path):
        return
    with open(env_path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Google Places prospects into the scoring CSV format."
    )
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Google Places text query. Can be used more than once.",
    )
    parser.add_argument("--city", default="Sydney")
    parser.add_argument("--vertical", default="plumbing")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--out", help="Write CSV to this path instead of stdout.")
    parser.add_argument(
        "--api-key-env",
        default="GOOGLE_MAPS_API_KEY",
        help="Environment variable that contains the Google Maps API key.",
    )
    return parser.parse_args()


def post_places(api_key: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    connection = http.client.HTTPSConnection(API_HOST, timeout=20)
    try:
        connection.request(
            "POST",
            API_PATH,
            body=data,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": DEFAULT_FIELD_MASK,
            },
        )
        response = connection.getresponse()
        detail = response.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"Google Places request failed: {exc}") from exc
    finally:
        connection.close()

    if response.status >= 400:
        raise SystemExit(f"Google Places request failed: {response.status} {detail}")

    return json.loads(detail)


def place_name(place: dict) -> str:
    display = place.get("displayName") or {}
    return display.get("text") or ""


def has_emergency_signal(name: str, query: str, hours: dict) -> bool:
    text = f"{name} {query}".lower()
    terms = ("24", "24/7", "emergency", "after hour", "blocked drain", "drain")
    if any(term in text for term in terms):
        return True
    weekday = " ".join(hours.get("weekdayDescriptions") or []).lower()
    return "24 hours" in weekday


def looks_like_booking_site(website: str) -> bool:
    text = website.lower()
    return any(term in text for term in ("book", "booking", "servicem8", "simpro"))


def to_row(place: dict, args: argparse.Namespace, query: str) -> dict[str, str]:
    name = place_name(place)
    website = place.get("websiteUri", "")
    hours = place.get("regularOpeningHours") or {}
    emergency = has_emergency_signal(name, query, hours)
    maps_url = place.get("googleMapsUri", "")
    address = place.get("formattedAddress", "")
    place_id = place.get("id", "")

    return {
        "business_name": name,
        "vertical": args.vertical,
        "city": args.city,
        "website": website,
        "phone": place.get("nationalPhoneNumber", ""),
        "google_rating": str(place.get("rating", "")),
        "google_reviews": str(place.get("userRatingCount", "")),
        "estimated_weekly_missed_calls": "8" if emergency else "5",
        "estimated_new_customer_value_usd": "650",
        "current_callback_delay_minutes": "240" if emergency else "120",
        "has_online_booking": "yes" if looks_like_booking_site(website) else "no",
        "emergency_or_after_hours": "yes" if emergency else "no",
        "notes": f"source=google_places; place_id={place_id}; maps={maps_url}; address={address}",
    }


def fetch_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"Set {args.api_key_env} before running this script.")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for query in args.queries or DEFAULT_QUERIES:
        next_page_token = ""
        while len(rows) < args.limit:
            before_count = len(rows)
            body = {
                "textQuery": query,
                "regionCode": "AU",
                "pageSize": min(args.page_size, args.limit),
            }
            if next_page_token:
                body["pageToken"] = next_page_token

            payload = post_places(api_key, body)
            for place in payload.get("places", []):
                key = place.get("id") or place_name(place)
                if not key or key in seen:
                    continue
                seen.add(key)
                rows.append(to_row(place, args, query))
                if len(rows) >= args.limit:
                    break

            next_page_token = payload.get("nextPageToken", "")
            if len(rows) == before_count:
                break
            if not next_page_token:
                break
            time.sleep(2)
        if len(rows) >= args.limit:
            break

    return rows


def main() -> None:
    load_env_file()
    args = parse_args()
    rows = fetch_rows(args)
    output = open(args.out, "w", newline="") if args.out else sys.stdout
    try:
        writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.out:
            output.close()


if __name__ == "__main__":
    main()
