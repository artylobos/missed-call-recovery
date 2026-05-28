# First Money Goal

## Objective

Close the first paid Sydney AI receptionist / missed-call recovery pilot for an
emergency plumbing or blocked-drain business.

Target window: 2026-05-28 to 2026-06-04.

Definition of first money:

- A real merchant pays at least AUD 300 for a 7 day pilot, or pays a deposit
  toward setup.
- The merchant gives permission to test missed-call textback or after-hours
  intake on a real business phone flow.
- The agent runtime is deployed behind HTTPS, smoke-tested, and connected to the
  merchant's owner notification path.

## Default Offer

Sell this, using this name:

```text
Missed-call recovery for emergency plumbing jobs.
```

Message:

```text
We recover missed calls within 60 seconds, capture job details, notify the owner,
and report recovered leads daily.
```

First pilot price:

- AUD 300 for a 7 day paid pilot.
- Convert to AUD 499/month if it recovers useful leads.
- No free pilots unless the business provides real missed-call data and a clear
  install date.

## Default Vertical

Sydney emergency plumbing / blocked drains.

Reason:

- High job value.
- Emergency intent decays fast.
- After-hours and busy-on-site missed calls are common.
- The demo is easy to understand without explaining "AI".

## Agent-Owned Work

- Source prospects from Google Places and Yellow Pages.
- Score prospects by missed-call value, emergency signal, reviews, and likely
  install simplicity.
- Generate personalized outreach drafts.
- Prepare a demo using the business name, likely services, and owner-notification
  flow.
- Deploy and smoke-test the webhook runtime after credentials exist.
- Produce daily pilot reports once a merchant is live.

## Human-Owned Work

The user must provide or approve:

- Sender identity for outreach: name, business name if any, contact email, and
  callback phone number.
- Payment collection: Stripe, PayPal, Wise, bank transfer, or invoice link.
- Google Maps Platform API key with Places API enabled and billing active.
- Hosting target or repo access for deployment.
- Twilio account and phone number if testing real SMS or call forwarding.
- Vapi or Retell account only if the paid buyer wants a real AI voice call demo.
- Human approval before any cold outbound message is sent from a real account.
- Legal/compliance sign-off for Australian cold outreach and SMS flows.

## Compliance Guardrails

- Do not run bulk cold SMS marketing without consent.
- Every commercial email or SMS draft must identify the sender and include a
  working opt-out path.
- Do not use address-harvesting software or bought email lists.
- Prefer business phone calls, website contact forms, or one-to-one approved
  emails for first validation.
- For any telemarketing workflow, review the Do Not Call Register rules before
  calling personal or mixed-use numbers.

References checked 2026-05-28:

- ACMA spam guidance: https://www.acma.gov.au/avoid-sending-spam
- ACMA Do Not Call Register: https://www.acma.gov.au/do-not-call-register
- Google Places Text Search: https://developers.google.com/maps/documentation/places/web-service/text-search

## 7 Day Operating Loop

Day 0:

- Get required accounts and sender identity from the user.
- Import 60 Google Places prospects.
- Score prospects and generate top 20 outreach drafts.
- Deploy the runtime if repo/hosting is ready.

Day 1:

- Contact top 20 businesses with human-approved calls/messages.
- Goal: 5 conversations or 2 demos booked.

Day 2:

- Demo missed-call textback with each interested merchant's business name.
- Ask directly for AUD 300 paid pilot.

Day 3-4:

- Follow up every warm lead once.
- If no one pays, tighten pitch around "recover one extra emergency job this
  week" and call the next 30 prospects.

Day 5-7:

- Install the first paid pilot.
- Send daily report.
- Ask for conversion to AUD 499/month if useful leads appear.

## Kill Rules

- Pivot vertical if 100 targeted touches produce fewer than 5 qualified
  conversations.
- Pivot offer if 15 discovery calls produce zero payment or zero call-data
  access.
- Stop custom work if any install needs more than 2 hours before payment.
