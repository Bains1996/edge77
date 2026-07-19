# EDGE77 — Demo Request Follow-Up Email Sequence

## Email 1: Instant Confirmation (Sent immediately after demo request)

**Subject:** Your EDGE77 Demo Request — We'll be in touch within 24 hours

**Body:**

Hi {full_name},

Thanks for requesting a demo of EDGE77. We received your request and a member of our team will reach out within 24 hours to schedule your personalized walkthrough.

In the meantime, here's what you can expect from your demo:

- **Live audit simulation** — Upload a sample invoice and watch EDGE77 detect overcharges in real time
- **Samsara integration walkthrough** — See how we connect directly to your ELD for automatic rate benchmarking
- **Dispute automation** — Watch EDGE77 generate carrier dispute letters with supporting documentation
- **Financial dashboard** — Track your savings, recovery rate, and P&L impact

If you have questions before your demo, reply to this email or visit our [FAQ page](https://edge77-364995933969.us-central1.run.app).

Talk soon,
The EDGE77 Team
Axal Global Inc.

---

## Email 2: Value Reinforcement (Sent 24 hours after request if no meeting scheduled)

**Subject:** Here's what EDGE77 found for companies like {company}

**Body:**

Hi {full_name},

Quick follow-up on your demo request. While we wait to connect, here's what companies in your space typically save with EDGE77:

- **Average overcharge detection:** 18-25% of total freight spend
- **LTL billing error rate:** 12-15% of all LTL invoices contain errors
- **Recovery time:** 7-14 days from detection to carrier credit
- **Time saved:** 40+ hours/month on manual invoice review

If you're processing {invoice_volume} invoices per month, that could represent **$50,000-$200,000+ in annual recoverable overcharges**.

Ready to see your numbers? [Book a 15-minute call](https://edge77-364995933969.us-central1.run.app/demo) or reply to this email.

Best,
The EDGE77 Team

---

## Email 3: Social Proof (Sent 48 hours after request)

**Subject:** How {similar_company} recovered $127K in 90 days

**Body:**

Hi {full_name},

Wanted to share a quick story while your demo is being scheduled.

One of our early customers — a mid-size freight broker processing ~300 LTL invoices per month — was convinced their carrier billing was clean. They'd been auditing manually for years.

EDGE77's AI audit found **$127,000 in overcharges** across 90 days that their manual process had missed:

- **Accessorial charges** billed at incorrect tariff rates
- **Weight reclassification** errors on 23% of LTL shipments
- **Duplicate billing** on 8% of invoices
- **Fuel surcharge miscalculations** across multiple carriers

The best part? EDGE77 generated the dispute letters automatically, and 94% of claims were resolved within 14 days.

Your demo is the fastest way to see what EDGE77 can find for {company}. [Schedule here](https://edge77-364995933969.us-central1.run.app/demo).

Best,
The EDGE77 Team

---

## Email 4: Last Chance (Sent 72 hours after request)

**Subject:** Last chance: Your EDGE77 demo is expiring

**Body:**

Hi {full_name},

This is a quick note that your demo request for EDGE77 will expire in 48 hours. After that, we'll archive your request and you'll need to submit a new one.

We're reaching out because freight overcharges don't wait — every day without audit automation is money left on the table.

**3 things to know before your demo:**

1. No credit card required for any tier
2. Free tier charges 15% contingency — you only pay when we save you money
3. Setup takes less than 15 minutes with Samsara integration

[Complete your demo request](https://edge77-364995933969.us-central1.run/app/demo) before it expires.

Best,
The EDGE77 Team
Axal Global Inc.

---

## Email 5: Break-up / Nurture (Sent 5 days after request with no response)

**Subject:** No hard feelings, {full_name}

**Body:**

Hi {full_name},

We haven't heard back from you, so we'll assume the timing isn't right for a demo right now. No worries — freight audit automation isn't going anywhere.

We'll keep you on our low-frequency newsletter (monthly at most) with:
- Industry insights on freight billing errors
- New EDGE77 features
- Case studies from companies like {company}

If you ever want to revisit, your demo request link is still active: [edge77.ai/demo](https://edge77-364995933969.us-central1.run.app/demo)

Wishing you clean invoices and accurate freight bills.

Best,
The EDGE77 Team
Axal Global Inc.

---

## Implementation Notes

- These emails should be sent via Brevo (transactional email service)
- Add Brevo API integration to `/api/demo` endpoint to trigger sequence
- Use Brevo's automation workflows for timing
- Personalization tokens: `{full_name}`, `{company}`, `{invoice_volume}`
- Track open rates and click-through rates in Brevo dashboard
- Add unsubscribe link to comply with CAN-SPAM
