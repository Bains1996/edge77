# EDGE77 — Sales & Onboarding Guide

## What Is EDGE77?

EDGE77 is a **risk-free automated freight audit engine** built by Axal Global Inc. It uses AI to detect carrier billing errors on autopilot with 99.7% accuracy. 

**Business model:** 15% contingency fee — if we find nothing, customers pay nothing.

---

## Live URLs

| Resource | URL |
|----------|-----|
| **Landing Page** | https://edge77.app |
| **Client Dashboard** | https://edge77.app/dashboard |
| **API Endpoint** | https://edge77.app/v1/ |
| **GitHub** | https://github.com/Bains1996/edge77 |

---

## Pricing

| Tier | Price | Invoices/Month | Features |
|------|-------|----------------|----------|
| **Starter** | $49/mo + 15% contingency | 100 | Basic audit, email reports |
| **Business** | $149/mo + 15% contingency | 500 | Full AI audit, API access, priority support |
| **Enterprise** | Custom | Unlimited | Custom contracts, SLA, dedicated support |

**No upfront cost. Cancel anytime.**

---

## How to Onboard a New Customer

### Step 1: Create Their Client ID
Each customer gets a unique `client_id` (e.g., `acme_logistics_001`).

### Step 2: Generate API Key
Use the admin endpoint:
```bash
curl -X POST https://edge77.app/v1/admin/api-keys \
  -H "Authorization: Bearer YOUR_INTERNAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "acme_logistics_001", "name": "Production"}'
```

Response:
```json
{
  "api_key": "e77_abc123...",
  "key_prefix": "e77_abc1...",
  "client_id": "acme_logistics_001",
  "message": "Store this key securely — it will not be shown again"
}
```

### Step 3: Set Up Their Contract
```bash
curl -X POST https://edge77.app/v1/client/acme_logistics_001/contract \
  -H "Authorization: Bearer e77_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "max_allowed_fuel": 30.00,
    "carrier_billing_email": "billing@carrier.com",
    "dispute_mode": "MANUAL_GATE"
  }'
```

### Step 4: Share Dashboard Access
Send them: `https://edge77.app/dashboard`

They can:
- View audit queue
- Approve/reject disputes
- Configure contract settings
- See stats and fees earned

---

## API Usage

### Submit Invoice
```bash
curl -X POST https://edge77.app/v1/invoice/ingest \
  -H "Authorization: Bearer e77_THEIR_API_KEY" \
  -H "x-client-id: acme_logistics_001" \
  -F "file=@invoice.pdf"
```

### Check Audit Status
```bash
curl https://edge77.app/v1/client/acme_logistics_001/audits \
  -H "Authorization: Bearer e77_THEIR_API_KEY"
```

### Get Stats
```bash
curl https://edge77.app/v1/client/acme_logistics_001/stats \
  -H "Authorization: Bearer e77_THEIR_API_KEY"
```

---

## Where to Sell

### 1. Product Hunt
- Create a launch page
- Title: "EDGE77 — AI-Powered Freight Audit That Pays for Itself"
- Tagline: "We find carrier overcharges. You only pay 15% of what we recover."

### 2. Hacker News (Show HN)
- Post in Show HN format
- Focus on the technical architecture and AI accuracy

### 3. LinkedIn Outreach
- Target: Logistics managers, CFOs at mid-market shippers
- Message: "Your carriers are overcharging you. We find it automatically."

### 4. Acquire.com
- List the business for sale
- Revenue: $0 (pre-revenue SaaS)
- Tech stack: Python, FastAPI, Supabase, Cloud Run
- Ask: $50K-$100K for the full codebase + deployed service

### 5. Cold Email Campaigns
- Target: 3PL companies, freight brokers, enterprise shippers
- Subject: "Your carrier invoices have errors. We find them for free."

---

## Database Setup (One-Time)

Run this SQL in Supabase SQL Editor:
```sql
-- See migrations/001_client_api_keys.sql
```

---

## Support

- **Email:** bainsarshveer1@gmail.com
- **Company:** Axal Global Inc.
