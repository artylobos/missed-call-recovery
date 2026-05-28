from __future__ import annotations

import base64
import hashlib
import hmac
from html import escape
import ipaddress
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse, request


LEAD_FIELDS = {"name", "phone", "service", "preferred_time", "transcript", "urgency"}
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|auth|api[_-]?key|webhook)", re.I)
URL_SECRET_RE = re.compile(r"([?&](?:token|secret|key|auth|code|password|sid)=)[^&\s]+", re.I)


class RequestTooLarge(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    port: int
    data_dir: Path
    dry_run: bool
    business_name: str
    business_phone: str
    public_base_url: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_api_key_sid: str
    twilio_api_key_secret: str
    twilio_from_number: str
    twilio_messaging_service_sid: str
    sheets_webhook_url: str
    ghl_inbound_webhook_url: str
    crm_webhook_url: str
    owner_notify_webhook_url: str
    admin_api_token: str
    webhook_token: str
    max_body_bytes: int
    requests_per_minute: int
    allow_unauthenticated_loopback: bool

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv(Path(".env"))
        return cls(
            port=int(os.getenv("PORT", "8787")),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            dry_run=os.getenv("DRY_RUN", "1").lower() not in {"0", "false", "no"},
            business_name=os.getenv("BUSINESS_NAME", "Local Service Business"),
            business_phone=os.getenv("BUSINESS_PHONE", ""),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8787"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_api_key_sid=os.getenv("TWILIO_API_KEY_SID", ""),
            twilio_api_key_secret=os.getenv("TWILIO_API_KEY_SECRET", ""),
            twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
            twilio_messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID", ""),
            sheets_webhook_url=os.getenv("SHEETS_WEBHOOK_URL", ""),
            ghl_inbound_webhook_url=os.getenv("GHL_INBOUND_WEBHOOK_URL", ""),
            crm_webhook_url=os.getenv("CRM_WEBHOOK_URL", ""),
            owner_notify_webhook_url=os.getenv("OWNER_NOTIFY_WEBHOOK_URL", ""),
            admin_api_token=os.getenv("ADMIN_API_TOKEN", ""),
            webhook_token=os.getenv("WEBHOOK_TOKEN", ""),
            max_body_bytes=int(os.getenv("MAX_BODY_BYTES", "1048576")),
            requests_per_minute=int(os.getenv("REQUESTS_PER_MINUTE", "120")),
            allow_unauthenticated_loopback=os.getenv("ALLOW_UNAUTHENTICATED_LOOPBACK", "1").lower()
            not in {"0", "false", "no"},
        )


class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    name TEXT,
                    phone TEXT,
                    service TEXT,
                    preferred_time TEXT,
                    transcript TEXT,
                    urgency TEXT,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    raw_json TEXT NOT NULL
                )
                """
            )
            self.ensure_column(conn, "leads", "dedupe_key", "TEXT NOT NULL DEFAULT ''")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_dedupe
                ON leads(dedupe_key)
                WHERE dedupe_key != ''
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    type TEXT NOT NULL,
                    lead_id TEXT,
                    ok INTEGER NOT NULL,
                    detail TEXT NOT NULL,
                    raw_json TEXT NOT NULL
                )
                """
            )

    def ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_lead(self, source: str, lead: dict[str, Any], raw: Any) -> tuple[str, bool]:
        lead_id = f"lead_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        score = score_lead(lead)
        dedupe_key = derive_dedupe_key(source, lead, raw)
        with self.connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO leads (
                        id, created_at, dedupe_key, source, name, phone, service, preferred_time,
                        transcript, urgency, status, score, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lead_id,
                        utc_now(),
                        dedupe_key,
                        source,
                        clean_text(lead.get("name")),
                        normalize_phone(lead.get("phone")),
                        clean_text(lead.get("service")),
                        clean_text(lead.get("preferred_time")),
                        clean_text(lead.get("transcript")),
                        clean_text(lead.get("urgency") or "normal"),
                        "new",
                        score,
                        safe_json(redact_payload(raw)),
                    ),
                )
                return lead_id, True
            except sqlite3.IntegrityError:
                row = conn.execute("SELECT id FROM leads WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
                if row:
                    return row["id"], False
                raise

    def add_event(self, event_type: str, lead_id: str | None, ok: bool, detail: str, raw: Any) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events (id, created_at, type, lead_id, ok, detail, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
                    utc_now(),
                    event_type,
                    lead_id,
                    1 if ok else 0,
                    redact_text(detail),
                    safe_json(redact_payload(raw)),
                ),
            )

    def list_rows(self, table: str, limit: int = 50) -> list[dict[str, Any]]:
        if table not in {"leads", "events"}:
            raise ValueError("invalid table")
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def redact_text(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = URL_SECRET_RE.sub(r"\1[redacted]", text)
    text = re.sub(r"(Authorization:\s*(?:Bearer|Basic)\s+)[A-Za-z0-9+/=._-]+", r"\1[redacted]", text, flags=re.I)
    if len(text) > 600:
        text = f"{text[:300]}...[truncated]...{text[-150:]}"
    return text


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(key):
                redacted[key] = "[redacted]"
            elif isinstance(item, str) and item.startswith("http"):
                redacted[key] = redact_url(item)
            else:
                redacted[key] = redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, str):
        return redact_url(value)
    return value


def redact_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        return value
    parsed = parse.urlsplit(value)
    return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def derive_dedupe_key(source: str, lead: dict[str, Any], raw: Any) -> str:
    raw_payload = maybe_json(raw)
    candidates = [
        "CallSid",
        "call_sid",
        "callSid",
        "RecordingSid",
        "TranscriptionSid",
        "MessageSid",
        "SmsSid",
        "toolCallId",
        "tool_call_id",
        "call_id",
        "callId",
        "conversation_id",
        "event_id",
        "eventId",
        "id",
    ]
    if isinstance(raw_payload, dict):
        for key in candidates:
            value = find_nested_value(raw_payload, {key})
            if value not in (None, ""):
                return f"{source}:{key}:{value}"

    canonical = {
        "source": source,
        "phone": normalize_phone(lead.get("phone")),
        "name": clean_text(lead.get("name")).lower(),
        "service": clean_text(lead.get("service")).lower(),
        "preferred_time": clean_text(lead.get("preferred_time")).lower(),
        "transcript": clean_text(lead.get("transcript")).lower(),
    }
    digest = hashlib.sha256(safe_json(canonical).encode("utf-8")).hexdigest()
    return f"{source}:sha256:{digest}"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True)
    return str(value).strip()


def normalize_phone(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if text.startswith("+"):
        return "+" + re.sub(r"\D", "", text[1:])
    digits = re.sub(r"\D", "", text)
    return f"+{digits}" if len(digits) > 10 else digits


def score_lead(lead: dict[str, Any]) -> int:
    text = " ".join(clean_text(lead.get(key)).lower() for key in LEAD_FIELDS)
    score = 30
    if lead.get("phone"):
        score += 25
    if lead.get("service"):
        score += 20
    if lead.get("preferred_time"):
        score += 10
    if any(word in text for word in ("emergency", "urgent", "today", "asap", "pain", "leak", "broken")):
        score += 25
    return min(score, 100)


def parse_request_body(handler: BaseHTTPRequestHandler, max_body_bytes: int = 1_048_576) -> Any:
    length = int(handler.headers.get("Content-Length") or "0")
    if length > max_body_bytes:
        raise RequestTooLarge(f"request body exceeds {max_body_bytes} bytes")
    body = handler.rfile.read(length) if length else b""
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return json.loads(body.decode("utf-8") or "{}")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        parsed = parse.parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in parsed.items()}
    if not body:
        return {}
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {"raw_body": body.decode("utf-8", errors="replace")}


def find_nested_value(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value not in (None, ""):
                return value
        for value in payload.values():
            found = find_nested_value(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_nested_value(item, keys)
            if found not in (None, ""):
                return found
    return None


def maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def extract_tool_args(payload: Any) -> dict[str, Any]:
    payload = maybe_json(payload)
    if isinstance(payload, dict):
        for key in ("arguments", "args", "parameters", "input", "toolInput"):
            if key in payload:
                candidate = maybe_json(payload[key])
                if isinstance(candidate, dict):
                    nested = extract_tool_args(candidate)
                    if any(nested.values()):
                        return nested
        if any(key in payload for key in LEAD_FIELDS):
            return {key: payload.get(key, "") for key in LEAD_FIELDS}
        for value in payload.values():
            nested = extract_tool_args(value)
            if any(nested.values()):
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = extract_tool_args(item)
            if any(nested.values()):
                return nested

    return {
        "name": find_nested_value(payload, {"name", "caller_name", "fullName"}) or "",
        "phone": find_nested_value(payload, {"phone", "caller_phone", "from", "From", "callback_number"}) or "",
        "service": find_nested_value(payload, {"service", "reason", "need", "requested_service"}) or "",
        "preferred_time": find_nested_value(payload, {"preferred_time", "appointment_time", "time"}) or "",
        "transcript": find_nested_value(payload, {"transcript", "summary", "TranscriptionText"}) or "",
        "urgency": find_nested_value(payload, {"urgency", "priority"}) or "normal",
    }


def missed_call_to_lead(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": payload.get("CallerName") or payload.get("name") or "",
        "phone": payload.get("From") or payload.get("Caller") or payload.get("phone") or "",
        "service": payload.get("service") or "missed call follow-up",
        "preferred_time": payload.get("preferred_time") or "",
        "transcript": payload.get("TranscriptionText") or payload.get("RecordingUrl") or payload.get("transcript") or "",
        "urgency": payload.get("urgency") or "normal",
    }


def lead_summary(lead: dict[str, Any]) -> str:
    name = clean_text(lead.get("name")) or "Unknown caller"
    phone = normalize_phone(lead.get("phone")) or "no phone"
    service = clean_text(lead.get("service")) or "unspecified service"
    preferred = clean_text(lead.get("preferred_time")) or "no preferred time"
    urgency = clean_text(lead.get("urgency")) or "normal"
    return f"{name} ({phone}) needs {service}; preferred time: {preferred}; urgency: {urgency}."


class Integrations:
    def __init__(self, config: Config, store: Store):
        self.config = config
        self.store = store

    def after_lead_created(self, lead_id: str, lead: dict[str, Any]) -> None:
        self.send_sms(lead_id, lead)
        for event_type, url in (
            ("sheets_webhook", self.config.sheets_webhook_url),
            ("ghl_webhook", self.config.ghl_inbound_webhook_url),
            ("crm_webhook", self.config.crm_webhook_url),
            ("owner_notify", self.config.owner_notify_webhook_url),
        ):
            self.post_webhook(event_type, url, lead_id, lead)

    def send_sms(self, lead_id: str, lead: dict[str, Any]) -> None:
        to_number = normalize_phone(lead.get("phone"))
        body = (
            f"Thanks for calling {self.config.business_name}. "
            "We received your request and will follow up shortly."
        )
        if not to_number:
            self.store.add_event("sms", lead_id, False, "skipped: no caller phone", lead)
            return
        if self.config.dry_run:
            self.store.add_event("sms", lead_id, True, f"dry-run to {to_number}: {body}", lead)
            return
        auth_username, auth_password = twilio_rest_credentials(self.config)
        if not (self.config.twilio_account_sid and auth_username and auth_password):
            self.store.add_event("sms", lead_id, False, "missing Twilio credentials", lead)
            return
        if not (self.config.twilio_from_number or self.config.twilio_messaging_service_sid):
            self.store.add_event("sms", lead_id, False, "missing Twilio sender", lead)
            return

        form = {"To": to_number, "Body": body}
        if self.config.twilio_messaging_service_sid:
            form["MessagingServiceSid"] = self.config.twilio_messaging_service_sid
        else:
            form["From"] = self.config.twilio_from_number
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.twilio_account_sid}/Messages.json"
        ok, detail = post_form_with_basic_auth(
            url,
            form,
            auth_username,
            auth_password,
        )
        self.store.add_event("sms", lead_id, ok, detail, {"to": to_number})

    def post_webhook(self, event_type: str, url: str, lead_id: str, lead: dict[str, Any]) -> None:
        payload = {
            "lead_id": lead_id,
            "created_at": utc_now(),
            "business_name": self.config.business_name,
            "summary": lead_summary(lead),
            "lead": lead,
        }
        if not url:
            self.store.add_event(event_type, lead_id, True, "skipped: no URL configured", payload)
            return
        if self.config.dry_run:
            self.store.add_event(event_type, lead_id, True, "dry-run POST configured endpoint", payload)
            return
        ok, detail = post_json(url, payload)
        self.store.add_event(event_type, lead_id, ok, detail, payload)


def post_json(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300, f"HTTP {response.status}"
    except Exception as exc:  # noqa: BLE001 - log exact integration failure
        return False, redact_text(str(exc))


def post_form_with_basic_auth(url: str, form: dict[str, str], username: str, password: str) -> tuple[bool, str]:
    data = parse.urlencode(form).encode("utf-8")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300, f"HTTP {response.status}"
    except Exception as exc:  # noqa: BLE001 - log exact integration failure
        return False, redact_text(str(exc))


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            recent = [stamp for stamp in self._requests[key] if stamp >= cutoff]
            if len(recent) >= self.limit:
                self._requests[key] = recent
                return False
            recent.append(now)
            self._requests[key] = recent
            return True


def twilio_rest_credentials(config: Config) -> tuple[str, str]:
    if config.twilio_api_key_sid and config.twilio_api_key_secret:
        return config.twilio_api_key_sid, config.twilio_api_key_secret
    return config.twilio_account_sid, config.twilio_auth_token


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    return str(handler.client_address[0] if handler.client_address else "")


def is_loopback_request(handler: BaseHTTPRequestHandler) -> bool:
    try:
        return ipaddress.ip_address(client_ip(handler)).is_loopback
    except ValueError:
        return False


def header_token(handler: BaseHTTPRequestHandler, names: tuple[str, ...]) -> str:
    auth = handler.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    for name in names:
        value = handler.headers.get(name, "")
        if value:
            return value.strip()
    return ""


def token_matches(actual: str, expected: str) -> bool:
    return bool(actual and expected and hmac.compare_digest(actual, expected))


def is_admin_authorized(handler: BaseHTTPRequestHandler, config: Config) -> bool:
    token = header_token(handler, ("X-Admin-Token",))
    if config.admin_api_token:
        return token_matches(token, config.admin_api_token)
    return config.allow_unauthenticated_loopback and is_loopback_request(handler)


def is_webhook_authorized(
    handler: BaseHTTPRequestHandler,
    config: Config,
    path: str,
    payload: Any,
) -> bool:
    if is_twilio_path(path) and validate_twilio_signature(handler, config, payload):
        return True

    token = header_token(handler, ("X-Webhook-Token",))
    if config.webhook_token:
        return token_matches(token, config.webhook_token)

    return config.allow_unauthenticated_loopback and is_loopback_request(handler)


def is_twilio_path(path: str) -> bool:
    return path in {"/webhooks/missed-call", "/webhooks/twilio/transcription", "/twilio/voice"}


def validate_twilio_signature(handler: BaseHTTPRequestHandler, config: Config, payload: Any) -> bool:
    signature = handler.headers.get("X-Twilio-Signature", "")
    if not (signature and config.twilio_auth_token):
        return False
    if not isinstance(payload, dict):
        return False

    url = f"{config.public_base_url.rstrip('/')}{handler.path}"
    signed = url + "".join(f"{key}{payload[key]}" for key in sorted(payload))
    digest = hmac.new(config.twilio_auth_token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(signature, expected)


def hide_raw_rows(rows: list[dict[str, Any]], include_raw: bool) -> list[dict[str, Any]]:
    if include_raw:
        return rows
    return [{key: value for key, value in row.items() if key != "raw_json"} for row in rows]


def make_handler(config: Config, store: Store, integrations: Integrations) -> type[BaseHTTPRequestHandler]:
    rate_limiter = RateLimiter(config.requests_per_minute)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AIReceptionistAutopilot/0.1"

        def setup(self) -> None:
            super().setup()
            self.request.settimeout(10)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"{self.address_string()} - {fmt % args}")

        def do_GET(self) -> None:  # noqa: N802 - stdlib API
            parsed = parse.urlparse(self.path)
            path = parsed.path
            if not self.check_rate_limit():
                return
            if path == "/health":
                self.respond_json(
                    {
                        "status": "ok",
                        "business_name": config.business_name,
                        "dry_run": config.dry_run,
                        "public_auth_configured": bool(config.admin_api_token and config.webhook_token),
                        "time": utc_now(),
                    }
                )
            elif path == "/leads":
                if not self.require_admin():
                    return
                include_raw = parse.parse_qs(parsed.query).get("raw", ["0"])[0] == "1"
                self.respond_json({"leads": hide_raw_rows(store.list_rows("leads"), include_raw)})
            elif path == "/events":
                if not self.require_admin():
                    return
                include_raw = parse.parse_qs(parsed.query).get("raw", ["0"])[0] == "1"
                self.respond_json({"events": hide_raw_rows(store.list_rows("events"), include_raw)})
            elif path == "/demo":
                self.respond_html(demo_page(config))
            else:
                self.respond_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802 - stdlib API
            path = parse.urlparse(self.path).path
            try:
                if not self.check_rate_limit():
                    return
                payload = parse_request_body(self, config.max_body_bytes)
                if path == "/api/leads":
                    if not self.require_admin():
                        return
                    self.handle_lead("api", extract_tool_args(payload), payload)
                elif path == "/webhooks/missed-call":
                    if not self.require_webhook(path, payload):
                        return
                    self.handle_lead("missed_call", missed_call_to_lead(payload), payload)
                elif path == "/webhooks/twilio/transcription":
                    if not self.require_webhook(path, payload):
                        return
                    self.handle_lead("twilio_transcription", missed_call_to_lead(payload), payload)
                elif path in {"/webhooks/vapi/tool", "/webhooks/retell/tool"}:
                    if not self.require_webhook(path, payload):
                        return
                    provider = path.strip("/").split("/")[1]
                    self.handle_voice_tool(provider, payload)
                elif path == "/twilio/voice":
                    if not self.require_webhook(path, payload):
                        return
                    self.respond_xml(twilio_voice_response(config))
                else:
                    self.respond_json({"error": "not found"}, status=404)
            except RequestTooLarge as exc:
                store.add_event("request_rejected", None, False, str(exc), {"path": path})
                self.respond_json({"error": "request too large"}, status=413)
            except json.JSONDecodeError:
                store.add_event("request_rejected", None, False, "invalid json", {"path": path})
                self.respond_json({"error": "invalid json"}, status=400)
            except Exception as exc:  # noqa: BLE001 - return useful webhook debug info
                store.add_event("handler_error", None, False, str(exc), {"path": path})
                self.respond_json({"error": "internal error"}, status=500)

        def handle_voice_tool(self, provider: str, payload: Any) -> None:
            lead = extract_tool_args(payload)
            if not lead.get("phone"):
                lead["phone"] = find_nested_value(payload, {"customer_number", "caller_number", "from", "From"}) or ""
            lead_id, created = store.add_lead(provider, lead, payload)
            if created:
                integrations.after_lead_created(lead_id, lead)
            self.respond_json(
                {
                    "result": f"Captured lead {lead_id}. {lead_summary(lead)}",
                    "lead_id": lead_id,
                    "duplicate": not created,
                    "summary": lead_summary(lead),
                }
            )

        def handle_lead(self, source: str, lead: dict[str, Any], raw: Any) -> None:
            lead_id, created = store.add_lead(source, lead, raw)
            if created:
                integrations.after_lead_created(lead_id, lead)
            self.respond_json(
                {
                    "ok": True,
                    "lead_id": lead_id,
                    "duplicate": not created,
                    "summary": lead_summary(lead),
                }
            )

        def check_rate_limit(self) -> bool:
            key = f"{client_ip(self)}:{parse.urlparse(self.path).path}"
            if rate_limiter.allow(key):
                return True
            self.respond_json({"error": "rate limited"}, status=429)
            return False

        def require_admin(self) -> bool:
            if is_admin_authorized(self, config):
                return True
            self.respond_json({"error": "admin auth required"}, status=403)
            return False

        def require_webhook(self, path: str, payload: Any) -> bool:
            if is_webhook_authorized(self, config, path, payload):
                return True
            self.respond_json({"error": "webhook auth required"}, status=403)
            return False

        def respond_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def respond_xml(self, xml: str, status: int = 200) -> None:
            body = xml.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def respond_html(self, html: str, status: int = 200) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def demo_page(config: Config) -> str:
    business_name = escape(config.business_name)
    dry_run = "true" if config.dry_run else "false"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Missed-Call Textback Runtime Demo</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #5f6b78;
      --line: #d9e1ea;
      --soft: #f5f7fa;
      --accent: #0b7285;
      --white: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--soft);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    header, main {{
      width: min(960px, calc(100% - 28px));
      margin: 0 auto;
    }}
    header {{ padding: 28px 0 16px; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(26px, 5vw, 42px); letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); }}
    main {{ display: grid; gap: 16px; padding-bottom: 36px; }}
    section {{
      background: var(--white);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfdff;
    }}
    .label {{ display: block; color: var(--muted); font-size: 13px; }}
    .value {{ display: block; margin-top: 4px; font-size: 18px; font-weight: 700; }}
    button {{
      min-height: 40px;
      border: 1px solid var(--accent);
      border-radius: 7px;
      background: var(--accent);
      color: #ffffff;
      padding: 9px 13px;
      cursor: pointer;
      font-size: 14px;
    }}
    button.secondary {{ background: #ffffff; color: var(--accent); }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    pre {{
      margin: 12px 0 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #101820;
      color: #e5edf5;
      border-radius: 8px;
      padding: 12px;
      min-height: 120px;
      font-size: 13px;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 700; }}
  </style>
</head>
<body>
  <header>
    <h1>Missed-Call Textback Runtime</h1>
    <p>Dry-run demo for {business_name}. No real SMS or external webhooks are sent while dry-run is enabled.</p>
  </header>
  <main>
    <section>
      <h2>Status</h2>
      <div class="grid">
        <div class="metric"><span class="label">Business</span><span class="value">{business_name}</span></div>
        <div class="metric"><span class="label">Dry run</span><span class="value">{dry_run}</span></div>
        <div class="metric"><span class="label">Runtime</span><span class="value" id="health-status">Checking...</span></div>
      </div>
    </section>
    <section>
      <h2>Run Demo</h2>
      <div class="actions">
        <button id="missed-call">Create Missed-Call Lead</button>
        <button id="vapi-tool" class="secondary">Create Vapi Tool Lead</button>
        <button id="refresh" class="secondary">Refresh Leads</button>
      </div>
      <pre id="output">Ready.</pre>
    </section>
    <section>
      <h2>Recent Leads</h2>
      <table>
        <thead><tr><th>Created</th><th>Source</th><th>Name</th><th>Phone</th><th>Service</th><th>Score</th></tr></thead>
        <tbody id="leads"><tr><td colspan="6">No leads loaded yet.</td></tr></tbody>
      </table>
    </section>
  </main>
  <script>
    const output = document.getElementById("output");
    const leadsBody = document.getElementById("leads");
    const healthStatus = document.getElementById("health-status");

    function show(value) {{
      output.textContent = JSON.stringify(value, null, 2);
    }}

    async function getJson(path) {{
      const response = await fetch(path);
      const data = await response.json();
      if (!response.ok) throw data;
      return data;
    }}

    async function postJson(path, payload) {{
      const response = await fetch(path, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      if (!response.ok) throw data;
      return data;
    }}

    async function refresh() {{
      const leads = await getJson("/leads");
      leadsBody.innerHTML = "";
      for (const lead of leads.leads.slice(0, 8)) {{
        const row = document.createElement("tr");
        row.innerHTML = `<td>${{lead.created_at || ""}}</td><td>${{lead.source || ""}}</td><td>${{lead.name || ""}}</td><td>${{lead.phone || ""}}</td><td>${{lead.service || ""}}</td><td>${{lead.score ?? ""}}</td>`;
        leadsBody.appendChild(row);
      }}
      if (!leads.leads.length) {{
        leadsBody.innerHTML = '<tr><td colspan="6">No leads yet.</td></tr>';
      }}
      return leads;
    }}

    async function boot() {{
      try {{
        const health = await getJson("/health");
        healthStatus.textContent = health.status;
        await refresh();
      }} catch (error) {{
        healthStatus.textContent = "error";
        show(error);
      }}
    }}

    document.getElementById("missed-call").addEventListener("click", async () => {{
      try {{
        const result = await postJson("/webhooks/missed-call", {{
          From: "+15555550123",
          CallSid: `CA_demo_${{Date.now()}}`,
          CallStatus: "no-answer",
          service: "emergency water leak",
          preferred_time: "today afternoon",
        }});
        show(result);
        await refresh();
      }} catch (error) {{
        show(error);
      }}
    }});

    document.getElementById("vapi-tool").addEventListener("click", async () => {{
      try {{
        const result = await postJson("/webhooks/vapi/tool", {{
          message: {{
            toolCalls: [{{
              function: {{
                name: "capture_lead",
                arguments: JSON.stringify({{
                  name: "Jamie Chen",
                  phone: "+15555550124",
                  service: "new patient cleaning",
                  preferred_time: "Friday morning",
                  transcript: "Caller wants a cleaning appointment.",
                  urgency: "normal",
                }}),
              }},
            }}],
          }},
        }});
        show(result);
        await refresh();
      }} catch (error) {{
        show(error);
      }}
    }});

    document.getElementById("refresh").addEventListener("click", async () => {{
      try {{
        show(await refresh());
      }} catch (error) {{
        show(error);
      }}
    }});

    boot();
  </script>
</body>
</html>"""


def twilio_voice_response(config: Config) -> str:
    callback = f"{config.public_base_url.rstrip('/')}/webhooks/twilio/transcription"
    escaped_name = (
        config.business_name.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Thanks for calling {escaped_name}. Please leave your name, phone number, and what you need after the tone. We will text you shortly.</Say>
  <Record maxLength="60" transcribe="true" transcribeCallback="{callback}" />
  <Say>Thanks. We received your message.</Say>
</Response>"""


def build_server(config: Config | None = None) -> ThreadingHTTPServer:
    config = config or Config.from_env()
    store = Store(config.data_dir / "ai_receptionist.db")
    integrations = Integrations(config, store)
    handler = make_handler(config, store, integrations)
    return ThreadingHTTPServer(("0.0.0.0", config.port), handler)


def main() -> None:
    config = Config.from_env()
    server = build_server(config)
    print(f"AI receptionist runtime listening on http://127.0.0.1:{config.port}")
    print(f"Business: {config.business_name} | dry_run={config.dry_run}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
