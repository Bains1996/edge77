# EDGE77 — DNS & Marketplace Action Plan

## STATUS: DNS Setup Complete ✅

### Already Done:
- ✅ MX record: `smtp.google.com` (priority 1)
- ✅ SPF: `v=spf1 include:_spf.google.com ~all`
- ✅ DKIM: Auto-configured by Google (Authenticating email with DKIM)

### YOU MUST DO: Add DMARC Record

**Where:** Squarespace DNS Management (domain registrar for edge77.app)

1. Log in to Squarespace: https://account.squarespace.com
2. Go to **Settings** → **Domains** → **edge77.app** → **DNS Settings**
3. Add this TXT record:

| Type | Host | Value |
|------|------|-------|
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:admin@edge77.app` |

4. Save and wait 15-30 minutes for propagation

---

## Marketplace Registrations

### G2 (Free Basic Listing)
**URL:** https://www.g2.com/products/new

**Fill in:**
- Product Name: EDGE77
- Company: Axal Global Inc.
- Website: https://edge77.app
- Category: Freight Audit Software
- Pricing: Free tier available, paid plans from $499/mo
- Contact: admin@edge77.app

### Capterra (Free Basic Listing)
**URL:** https://www.capterra.com/signup/

**Fill in:**
- Product Name: EDGE77
- Company: Axal Global Inc.
- Website: https://edge77.app
- Category: Transportation Management Systems
- Contact: admin@edge77.app

### Samsara Marketplace
**URL:** https://www.samsara.com/resources/marketplace (or partner portal)

**Contact:** partners@samsara.com

**Email template:**
```
Subject: EDGE77 Integration Partnership — AI-Powered Freight Audit

Hi Samsara Partners Team,

I'm Arshveer Singh Bains, founder of Axal Global Inc. We've built EDGE77, 
an AI-powered freight invoice audit and dispute engine that integrates 
directly with Samsara's telematics data.

What EDGE77 does:
- Audits carrier invoices against actual GPS/ELD data from Samsara
- Detects overcharges on fuel surcharges, accessorial charges, and base rates
- Auto-generates and dispatches carrier dispute emails
- Clients pay only 10-15% of recovered overcharges (contingency model)

We'd love to list on the Samsara App Marketplace. Can we schedule a call 
to discuss the integration partnership?

Best regards,
Arshveer Singh Bains
Founder, Axal Global Inc.
admin@edge77.app
https://edge77.app
```

---

## Email Verification Test

After DMARC is set up, send a test email:
1. Go to Gmail (logged in as admin@edge77.app)
2. Send email to: bainsarshveer1@gmail.com
3. Verify it arrives in inbox (not spam)
4. Check headers for DKIM pass

---

## Cold Outreach Ready

The cold email sequence is ready at `sales/cold-email-500.html`.
First batch of 50 freight broker emails can be sent once email is verified.
