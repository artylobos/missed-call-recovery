# Account And Environment Guide

## Outreach Identity

These fields control how outreach drafts identify you. They are not API keys.
They are the human/business identity a Sydney plumbing owner sees.

```text
OUTREACH_SENDER_NAME=
OUTREACH_REPLY_TO=
OUTREACH_CALLBACK_PHONE=
```

Use:

- `OUTREACH_SENDER_NAME`: the name shown in outreach copy. Example:
  `Bo from El Web Sydney` or `Bo Liu`.
- `OUTREACH_REPLY_TO`: the inbox prospects can reply to. Example:
  `elwebsydney@gmail.com` or a domain email.
- `OUTREACH_CALLBACK_PHONE`: the phone number prospects can call back. Ideally
  an Australian mobile or business number you answer. A Twilio number can work
  after it is tested, but a real local callback number builds more trust.

Recommended first version:

```text
OUTREACH_SENDER_NAME=Bo from El Web Sydney
OUTREACH_REPLY_TO=elwebsydney@gmail.com
OUTREACH_CALLBACK_PHONE=<your Australian callback number>
```

## Payment Link

Use `PAYMENT_LINK` for the AUD 300 monthly or pilot payment link. Keep it in
Zeabur environment variables or local `.env`, not hard-coded in source.

```text
PAYMENT_LINK=<your Stripe payment link>
```

## Google Maps

Use a Google Maps Platform API key with Places API enabled.

```text
GOOGLE_MAPS_API_KEY=<your Google Maps API key>
```

Do not commit this key. Add restrictions in Google Cloud:

- Limit it to the Places API.
- Restrict HTTP referrers/IPs when practical.
- Rotate it if it was pasted into chat or logs.

## Twilio

For the current runtime, the simplest working setup is:

```text
TWILIO_ACCOUNT_SID=<your Twilio Account SID>
TWILIO_AUTH_TOKEN=<your Twilio Auth Token>
TWILIO_FROM_NUMBER=<your Twilio number>
```

The runtime uses:

- `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to send SMS through Twilio's REST
  API.
- `TWILIO_AUTH_TOKEN` to verify Twilio webhook signatures.
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID` as the sender.

Twilio API Keys are better for production because they can be rotated and scoped,
and this runtime supports them for sending SMS:

```text
TWILIO_ACCOUNT_SID=<your Twilio Account SID>
TWILIO_API_KEY_SID=<your Twilio API Key SID>
TWILIO_API_KEY_SECRET=<your Twilio API Key Secret>
TWILIO_AUTH_TOKEN=<still needed for Twilio webhook signature validation>
```

Even if SMS sending uses API Key credentials, keep `TWILIO_AUTH_TOKEN` in the
environment before public deployment so Twilio webhook requests can be verified.

## Zeabur

Set these in Zeabur environment variables:

```text
PORT=8787
DRY_RUN=1
ALLOW_UNAUTHENTICATED_LOOPBACK=0
PUBLIC_BASE_URL=https://<your-zeabur-domain>
ADMIN_API_TOKEN=<generated>
WEBHOOK_TOKEN=<generated>
TWILIO_ACCOUNT_SID=<your Twilio Account SID>
TWILIO_AUTH_TOKEN=<your Twilio Auth Token>
TWILIO_API_KEY_SID=<optional Twilio API Key SID>
TWILIO_API_KEY_SECRET=<optional Twilio API Key Secret>
TWILIO_FROM_NUMBER=<your Twilio number>
OUTREACH_SENDER_NAME=Bo from El Web Sydney
OUTREACH_REPLY_TO=elwebsydney@gmail.com
OUTREACH_CALLBACK_PHONE=<your Australian callback number>
PAYMENT_LINK=<your Stripe payment link>
GOOGLE_MAPS_API_KEY=<your Google Maps API key>
```

Keep `DRY_RUN=1` until the public smoke test and one SMS test to your own phone
pass. Then switch `DRY_RUN=0`.
