# AI Receptionist Autopilot

Minimal runtime for a sellable local-service phone automation demo. It is built
to prove the money loop first:

```text
missed call or AI voice tool call
  -> webhook runtime
  -> structured lead
  -> SMS confirmation or dry-run event
  -> Sheets/GHL/CRM/owner webhook or dry-run event
```

This project intentionally does not use n8n. Codex owns the code. Vapi, Retell,
or Twilio own the telephony and AI voice layer.

## Quick Start

```bash
cd /Users/boliu/ai-receptionist-autopilot
cp .env.example .env
make autopilot
```

`make autopilot` starts the runtime in the background if needed, waits for
`/health`, runs the smoke test, and leaves the webhook server running.

Manual foreground run:

```bash
cd /Users/boliu/ai-receptionist-autopilot
make run
```

In another terminal:

```bash
cd /Users/boliu/ai-receptionist-autopilot
make smoke
```

The server runs at `http://127.0.0.1:8787` by default.

For any public deployment, set `ADMIN_API_TOKEN`, `WEBHOOK_TOKEN`, and
`TWILIO_AUTH_TOKEN` before exposing the service.

Stop the background runtime:

```bash
make stop
```

## Endpoints

- `GET /health`
- `GET /leads`
- `GET /events`
- `POST /api/leads`
- `POST /webhooks/missed-call`
- `POST /webhooks/twilio/transcription`
- `POST /webhooks/vapi/tool`
- `POST /webhooks/retell/tool`
- `POST /twilio/voice`

## AI Voice Setup

Use Vapi or Retell for speech recognition, turn-taking, LLM dialogue, and text
to speech. Add a `capture_lead` tool/function with:

```json
{
  "name": "string",
  "phone": "string",
  "service": "string",
  "preferred_time": "string",
  "transcript": "string",
  "urgency": "low|normal|high|emergency"
}
```

Point the provider tool URL to:

```text
POST {PUBLIC_BASE_URL}/webhooks/vapi/tool
```

or:

```text
POST {PUBLIC_BASE_URL}/webhooks/retell/tool
```

## Production Notes

Before connecting a real phone number:

- Deploy this server behind HTTPS.
- Set `PUBLIC_BASE_URL` to the deployed URL.
- Set `ADMIN_API_TOKEN` and `WEBHOOK_TOKEN` to random secrets.
- Set `DRY_RUN=0` only after Twilio credentials are correct.
- Use provider webhook signing if available.
- Add uptime monitoring and log shipping.

## First Money Workflow

The current wedge is Sydney emergency plumbing / blocked drains. The operating
goal is tracked in `validation/first-money-goal.md`.

Prospecting helpers:

```bash
make score-seed
make draft-outreach
make first-money-status
make generate-secrets
```

With a Google Maps Platform API key:

```bash
export GOOGLE_MAPS_API_KEY=...
make import-google-places
python3 scripts/score_prospects.py validation/google-places-sydney-plumbing.csv
```

Outreach drafts are intentionally not sent automatically. The user must approve
sender identity, compliance, and each real outbound channel before messages are
sent from a live account.

Setup handoff docs:

- `validation/user-required-inputs.md`
- `validation/account-and-env-guide.md`
- `validation/deployment-checklist.md`
- `validation/pilot-scope.md`

Deploy helpers included:

- `Dockerfile`
- `Procfile`
- `render.yaml`
