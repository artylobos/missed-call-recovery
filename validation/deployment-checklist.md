# Deployment Checklist

## Minimum Sellable Deployment

Deploy the runtime as a small HTTPS web service.

Recommended simplest path:

1. Use the GitHub repo `https://github.com/artylobos/missed-call-recovery`.
2. Deploy `/Users/boliu/missed-call-recovery`.
3. Deploy with Render, Railway, Fly, Zeabur, or a VPS. The repo includes a
   `Dockerfile`, `Procfile`, and `render.yaml`.
4. Set environment variables from `.env.example`.
5. Set `ADMIN_API_TOKEN`, `WEBHOOK_TOKEN`, and `TWILIO_AUTH_TOKEN` before exposing
   the service publicly.
6. Run the smoke test against the public URL:

```bash
BASE_URL=https://your-domain.example make smoke
```

## Demo-Only Deployment

For a fast demo, keep `DRY_RUN=1` and do not connect real Twilio SMS yet. The
demo can still prove:

- Missed-call payload creates a lead.
- Vapi/Retell tool call creates a lead.
- Owner notification webhook can receive lead summaries.
- Daily report can show recovered leads.

## Paid Pilot Deployment

Before a live merchant pilot:

- `PUBLIC_BASE_URL` uses HTTPS.
- `ADMIN_API_TOKEN` is set.
- `WEBHOOK_TOKEN` is set.
- `TWILIO_AUTH_TOKEN` is set.
- `DRY_RUN=0` only after SMS is verified.
- Owner notification URL is set.
- Opt-out and sender identity are reviewed.
- Rollback path exists: disable Twilio webhook or set `DRY_RUN=1`.

## Voice Provider

Use AI voice only after the missed-call textback offer gets buyer interest.

Fastest voice path:

1. Create a Vapi or Retell assistant.
2. Set the assistant's tool/function URL to the deployed webhook.
3. Use a short plumbing intake prompt.
4. Test with a demo phone number before connecting a merchant number.

Do not use raw OpenAI audio plus custom telephony bridge for the first paid
pilot. It adds engineering time before payment validation.
