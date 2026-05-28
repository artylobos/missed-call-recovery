# Required User Inputs

You only need to provide these once. After that, the agent can run prospecting,
scoring, demo preparation, reporting, and follow-up drafting mostly on its own.

## Required Now

1. Sender identity

```text
OUTREACH_SENDER_NAME=
OUTREACH_REPLY_TO=
OUTREACH_CALLBACK_PHONE=
```

Use a real name and a reply channel you control. Do not use fake identity.

Meaning:

- `OUTREACH_SENDER_NAME`: the name shown in outreach copy, for example
  `Bo from El Web Sydney`.
- `OUTREACH_REPLY_TO`: the email address or inbox prospects can reply to.
- `OUTREACH_CALLBACK_PHONE`: the Australian phone number prospects can call if
  they prefer to talk.

2. Payment collection

```text
PAYMENT_LINK=
```

Stripe Payment Link is easiest. Wise, PayPal, bank transfer, or invoice link is
also fine.

3. Google Places prospecting

```text
GOOGLE_MAPS_API_KEY=
```

Enable Google Maps Platform Places API with billing. This lets the agent import
real Sydney prospect data rather than relying on the seed list.

4. Deployment target

Pick one:

- GitHub repo + Render/Railway/Fly/Zeabur deploy.
- A VPS with HTTPS reverse proxy.
- A temporary ngrok-style tunnel for demo only.

The production runtime must have HTTPS before Twilio, Vapi, or Retell can call
it reliably.

## Required For Real Missed-Call Textback

```text
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
PUBLIC_BASE_URL=
ADMIN_API_TOKEN=
WEBHOOK_TOKEN=
DRY_RUN=0
```

Generate runtime secrets with:

```bash
make generate-secrets
```

Keep `DRY_RUN=1` until the webhook URL, SMS copy, opt-out language, and owner
handoff are verified.

The current runtime can send SMS using either Account SID + Auth Token, or a
Twilio API Key SID + API Key Secret. It still needs `TWILIO_AUTH_TOKEN` for
Twilio webhook signature validation.

## Required Only If Buyer Wants AI Voice

Use Vapi or Retell first. Do not build telephony turn-taking from scratch for the
first paid pilot.

```text
VAPI_API_KEY=
```

or:

```text
RETELL_API_KEY=
```

The voice provider should call:

```text
POST {PUBLIC_BASE_URL}/webhooks/vapi/tool
```

or:

```text
POST {PUBLIC_BASE_URL}/webhooks/retell/tool
```

## Human Approval Boundaries

The agent can prepare drafts and run the system. The user must approve:

- Real outbound messages before sending.
- Any paid ads or API spend.
- Any live merchant phone/SMS integration.
- Any statement that could be interpreted as legal, medical, financial, or
  emergency advice.
