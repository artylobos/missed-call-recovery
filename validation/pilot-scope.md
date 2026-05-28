# AUD 300 Paid Pilot Scope

## Offer Name

Missed-call recovery for emergency plumbing jobs.

Do not sell this as "AI receptionist" in the first conversation. Sell the missed
revenue recovery.

## Pilot

- Price: AUD 300.
- Duration: 7 days.
- Vertical: Sydney emergency plumbing / blocked drains.
- Scope: missed-call textback plus instant owner alert.
- Renewal ask: AUD 499/month if the pilot recovers useful qualified jobs.

## What The System Does

- Replies to missed callers within 60 seconds.
- Captures name, phone, suburb, plumbing problem, urgency, and preferred call
  back time.
- Sends the owner a clean lead summary immediately.
- Produces a daily report.

## What The System Does Not Do

- It does not diagnose plumbing problems.
- It does not quote prices.
- It does not promise dispatch or availability.
- It does not pretend to be the plumber.
- It does not replace emergency escalation or human judgment.

## Success Metric

Pick one with the owner before install:

- Recovered qualified jobs.
- Recovered quote requests.
- Recovered booked emergency calls.

Every recovered lead should be marked:

```text
won / lost / bad_fit / no_response
```

## Install Boundary

No custom work before payment unless the owner provides real missed-call data
and a booked install time.

## Rollback

If anything feels wrong:

- Disable the Twilio webhook, or
- Set `DRY_RUN=1`, or
- Route calls/SMS back to the old flow.
