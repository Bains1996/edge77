# EDGE77 Cold Email A/B Testing Plan

## Objective

Maximize reply rate and demo booking conversions for the 3-email cold outreach sequence. Every variant is tested against the control to statistically validate which messaging drives the best results.

---

## 1. Subject Line Variants

Test on **Email 1 only** (most important — determines open rates for the entire sequence).

### Test Matrix

| Variant | Subject Line | Angle | Hypothesis |
|---------|-------------|-------|------------|
| **Control (A)** | We found overcharges in your freight bills | Direct/problem statement | Curiosity + specificity drives opens |
| **Variant B** | [NAME], your freight invoices are costing you 2–5% extra | Dollar-focused | Quantified loss creates urgency |
| **Variant C** | 85% of freight bills have errors — yours probably do too | Stat-driven | Authority + pattern interrupt |
| **Variant D** | Quick question about [COMPANY]'s carrier invoices | Curiosity gap | Low-pressure, high curiosity |
| **Variant E** | $127K recovered for one shipper — no upfront cost | Social proof | FOMO + risk reversal |

### Test Rules

- **Sample size:** Minimum 200 recipients per variant (1,000 total per test cycle)
- **Duration:** Run until each variant reaches 200 sends, then hold 5 days for replies
- **Winner:** Highest unique open rate (primary) + reply rate (secondary)
- **Success threshold:** Statistical significance at 95% confidence (p < 0.05)

---

## 2. Email Body Variants

Test on **Email 1** after subject line winner is determined.

### Variant A — Problem-Focused (Control)

*Angle:* Identify pain, create awareness of the problem.

```
Question: when was the last time your freight invoices were audited?
→ 85% contain errors
→ You're losing 2-5% of spend
→ EDGE77 catches it automatically
→ $0/mo, 15% contingency
→ CTA: Run My Free Audit
```

**Hypothesis:** Most brokers don't know they're overpaying. Creating awareness drives action.

### Variant B — ROI-Focused

*Angle:* Lead with the dollar amount they can recover.

```
Subject: [COMPANY] could recover $X/year in freight overcharges

If you spend $1M/year on freight, you're losing $20K-$50K to errors.
→ Most overcharges are in fuel surcharge, accessorials, and wrong freight classes
→ EDGE77 recovered $127K for one client in Q1
→ $0/mo starter, 15% contingency
→ CTA: Calculate Your Recovery
```

**Hypothesis:** Dollar-specific messaging appeals to analytically-minded decision makers (CFOs, owners).

### Variant C — Fear/Urgency-Focused

*Angle:* Frame inaction as a direct loss.

```
Subject: Your competitors are already recovering overcharges

If you're not auditing your freight bills, you're leaving money on the table.
→ Your competitors using EDGE77 are recovering 3-5% of spend
→ Carrier errors aren't rare — they're systematic
→ Every month without an audit is money you'll never get back
→ $0/mo, 15% contingency — no risk to start
→ CTA: Stop Leaving Money on the Table
```

**Hypothesis:** Loss aversion (fear of missing out) drives higher urgency than potential gain.

### Test Rules

- **Sample size:** Minimum 150 recipients per variant (450 total)
- **Winner determined by:** Reply rate (primary), CTA click rate (secondary)
- **A/B test within same sending platform** using random split
- **Hold email 2 and 3 constant** (use winning variant's body for the whole sequence)

---

## 3. CTA Variants (Secondary Test)

After body winner is determined, test CTA text/phrasing.

| Variant | CTA Text | Button or Link |
|---------|----------|----------------|
| A | Run My Free Audit | Button |
| B | See My Recovery Estimate | Button |
| C | Book a 15-Minute Demo | Button |
| D | Reply "yes" for a free analysis | Text reply (no button) |
| E | Start Free Audit | Button |

**Hypothesis:** Lower-friction CTAs ("See my recovery estimate") outperform higher-commitment CTAs ("Book a demo") by 2–3x on first touch.

---

## 4. Recommended Sample Sizes

| Test Type | Min Per Variant | Statistical Confidence | Time to Complete (at 50 sends/day) |
|-----------|----------------|----------------------|-----------------------------------|
| Subject line (5 variants) | 200 | 95% | ~20 days |
| Email body (3 variants) | 150 | 95% | ~9 days |
| CTA (5 variants) | 200 | 95% | ~20 days |
| Send time (AM vs PM) | 100 each | 90% | ~4 days |
| Day of week (Tue vs Thu) | 100 each | 90% | ~4 days |

---

## 5. How to Measure Success

### Primary Metrics

| Metric | Target | How to Track |
|--------|--------|-------------|
| **Open rate** | >45% | Email platform (Outreach, HubSpot, SalesLoft) |
| **Reply rate** | >8% | Manual or reply detection tool |
| **CTA click rate** | >5% | UTM-tagged links + Google Analytics / email platform |
| **Bounce rate** | <3% | Verify list before send (NeverBounce, ZeroBounce) |
| **Unsubscribe rate** | <0.5% | Email platform |

### Secondary Metrics

| Metric | Target | How to Track |
|--------|--------|-------------|
| **Positive replies** (interested) | >3% | Manual classification |
| **Demo bookings** | >2% | Calendar link tracking |
| **Meetings set** | >1.5% | CRM attribution |
| **Opportunities created** | >0.5% | CRM pipeline tracking |

### Formula Reference

- **Open rate** = Unique opens / Delivered × 100
- **Reply rate** = Unique replies / Delivered × 100
- **Click-through rate (CTR)** = Unique clicks / Delivered × 100
- **Click-to-open rate (CTOR)** = Unique clicks / Unique opens × 100
- **Bounce rate** = Bounced / Sent × 100
- **Conversion rate** = Desired action / Delivered × 100

---

## 6. Iteration Strategy

### Cycle 1: Foundation (Weeks 1–4)
1. Test subject line variants (5 variants, 1,000 sends)
2. Identify winner, apply to all future emails

### Cycle 2: Optimization (Weeks 5–8)
1. Test email body variants (3 variants, 450 sends)
2. Test CTA variants (5 variants, 1,000 sends)
3. Identify winner combination

### Cycle 3: Timing (Weeks 9–10)
1. Test send time (8 AM vs 10 AM vs 12 PM recipient timezone)
2. Test day of week (Tuesday vs Wednesday vs Thursday)

### Cycle 4: Personalization (Weeks 11–12)
1. Test with and without [COMPANY] in subject line
2. Test first-line personalization (industry-specific vs generic)
3. Test video thumbnail vs text-only

### Ongoing
- Every quarter, re-run the winning subject line against 2 new variants
- Every 6 months, refresh the email body copy
- Track performance degradation — if reply rates drop >20%, re-test fundamentals

---

## 7. Implementation Checklist

- [ ] Set up UTM parameters for all CTA links
- [ ] Configure email tracking (opens, clicks, replies)
- [ ] Create separate landing pages per variant (optional but recommended)
- [ ] Set up CRM pipeline stages to track end-to-end conversion
- [ ] Exclude previous test variants from CRM (don't send to the same person twice)
- [ ] Document results in a shared tracking sheet
- [ ] Declare a winner only after statistical significance is reached
- [ ] Apply winning variant to the full 500-contact list
- [ ] Set calendar reminder for quarterly re-testing

---

## 8. Winning Criteria Summary

```
Primary KPI: Reply Rate
Secondary: CTA Click Rate
Tertiary: Demo Booking Rate

Statistically significant at: p < 0.05
Minimum viable sample: 150 per variant / 200 for subject lines
Test duration: Minimum 5 days after last send (to capture late replies)
```
