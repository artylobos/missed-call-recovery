# Call And Demo Playbook

Use this to call Sydney plumbing businesses from the Google Places shortlist.
The call goal is not to explain AI. The goal is to find owners who miss valuable
calls and book a 5 minute demo or AUD 300 paid pilot.

## Before Calling

Have these open:

- `validation/google-places-outreach-drafts.csv`
- `validation/google-places-sydney-plumbing-scored.csv`
- Local demo: `http://127.0.0.1:8787/health`
- Payment link, if they say yes.

Use your real SIM number as the callback number.

## 15 Second Opener

```text
Hi, is this {business_name}?

This is Bo from El Web Sydney. I am calling with a quick idea for emergency
plumbing missed calls. Is the owner or whoever handles incoming jobs available
for 30 seconds?
```

If the owner answers:

```text
I am testing a simple missed-call recovery system for Sydney plumbers. When a
call is missed, it texts the caller back within about 60 seconds, collects the
suburb, problem, urgency, and callback time, then sends you a clean job lead.

I am not selling a full AI receptionist. I am trying to see whether this can
recover one extra emergency job per week. Do you miss calls when you are on jobs
or after hours?
```

## Gatekeeper

If staff answer and ask what it is about:

```text
It is about recovering missed emergency job calls, not advertising. If a blocked
drain call is missed, the system texts back immediately and passes the details
to the owner. Who is the best person to ask about missed calls or after-hours
jobs?
```

If they ask you to send info:

```text
Sure. Before I send it, should I address it to the owner, operations manager, or
someone else?
```

## Qualification

Ask only enough to know whether a demo is worth it.

```text
Roughly how many calls do you miss in a normal week?
```

```text
What usually happens after hours: voicemail, call forwarding, or no answer?
```

```text
What is one emergency plumbing job worth to you on average?
```

```text
If this recovered even one job in a week, would a 7 day paid pilot be worth
looking at?
```

## 5 Minute Demo Invite

If they show interest:

```text
I can show you the exact flow in 5 minutes. I will use your business name in a
dry-run demo: missed call comes in, customer gets a text, job details are
captured, and you get the lead summary. No changes to your phone system today.

Are you free later today, or should I send the demo link and call back tomorrow?
```

## Demo Flow

Show only the money loop:

1. Open `/health` to show the runtime is live.
2. Trigger a dry-run missed-call payload.
3. Open `/leads` to show the structured lead.
4. Open `/events` to show the SMS/owner notification was logged.
5. Explain the live install path.

Say:

```text
This is the dry-run version. In live mode, Twilio receives the missed-call
event, sends the textback, and alerts you immediately. The first pilot does not
diagnose, quote, or promise dispatch. It only recovers the lead while intent is
fresh.
```

## Close For AUD 300 Pilot

Use this when they understand the demo:

```text
The smallest useful pilot is 7 days, AUD 300. We connect missed-call textback,
send you every recovered lead, and give you a daily report: missed calls,
replies, qualified jobs, and owner handoffs.

If it recovers useful leads, we can keep it running at AUD 499 per month. If it
does not, we stop instead of turning this into a bigger software project.
```

Ask directly:

```text
Do you want to run the 7 day pilot this week?
```

## If They Want To Try The Agent

Do not give them a complex setup. Offer a controlled dry-run first.

```text
Yes. The safest first test is a dry-run demo using your business name and my
test number. After that, if you want to run it on real missed calls, we connect
Twilio and keep rollback simple: set dry-run back on or remove the webhook.
```

Then ask:

```text
For the pilot, where should recovered job leads go: SMS to you, email, or both?
```

## Objections

### We Already Call Back

```text
That is good. This is for the gap before the callback. Emergency callers often
try the next plumber if nobody replies quickly. The textback keeps them engaged
until you can call.
```

### We Already Have Voicemail

```text
Voicemail waits for the customer to leave a message. This replies immediately
and captures the job in a format you can act on.
```

### I Do Not Want AI Talking To Customers

```text
Then we should not start with AI voice. The first pilot is just textback and
owner alert. No quoting, no diagnosis, no pretending to be the plumber.
```

### Send Me Info

```text
I can send the one-page summary. To make it relevant, is the bigger issue missed
calls during jobs, after-hours calls, or slow callbacks?
```

### Too Busy

```text
Understood. That is exactly the reason this may be useful. I only need 5 minutes
to show the flow. Should I call back at the end of the day?
```

### Not Interested

```text
No problem. If missed calls become painful later, I can show you a 5 minute
demo. Thanks for your time.
```

## Follow-Up Text Or Email

After a warm call:

```text
Hi {owner_name}, Bo from El Web Sydney here. Thanks for the quick chat.

The offer is missed-call recovery for emergency plumbing jobs: text missed
callers within 60 seconds, capture suburb/problem/urgency/callback time, and
send you the lead immediately.

Pilot: AUD 300 for 7 days. We do not diagnose, quote, promise dispatch, or
replace your team.

Payment/demo link: {payment_link}
Callback: {callback_phone}
```

## Call Outcomes

Use one status after every call:

- `no_answer`
- `gatekeeper`
- `send_info`
- `demo_booked`
- `paid_pilot_requested`
- `not_interested`
- `bad_fit`

Book a demo only when the owner admits missed calls matter or asks to see the
system.
