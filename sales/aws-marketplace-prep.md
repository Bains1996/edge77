# AWS Marketplace Preparation — EDGE77

> **Product:** EDGE77 — AI-powered freight invoice audit platform  
> **Pricing:** $0/mo Starter (contingency), $499/mo Growth, $2,999/mo Enterprise  
> **Core Features:** AI extraction, OCR, contract validation, dispute generation, Samsara integration

---

## 1. Listing Requirements Checklist

### Account & Legal

- [ ] **AWS account** — Create AWS account if one doesn't exist (use company email, not personal)
- [ ] **AWS Marketplace Seller account** — Register at [aws.amazon.com/marketplace/management](https://aws.amazon.com/marketplace/management)
- [ ] **W-9 or W-8BEN** — Completed and submitted (US-based companies: W-9 with EIN)
- [ ] **Bank account** — For disbursement (must be US bank account or eligible international account)
- [ ] **DUNS number** — Required for company verification (get at [dnb.com](https://www.dnb.com) — free, 3-5 business days)
- [ ] **Tax registration** — Seller tax interview completed in AWS Marketplace portal
- [ ] **Company verification** — AWS will verify company address and legal status

### Product Setup

- [ ] **Product name** — "EDGE77 AI Freight Invoice Audit"
- [ ] **Product description** — See Section 2 below (optimized for AWS Marketplace format)
- [ ] **Product logo** — 120x120 PNG, transparent background, < 50 KB
- [ ] **Product category** — Software Infrastructure → Business Applications → Supply Chain Management
- [ ] **Search keywords** — freight audit, invoice validation, OCR logistics, carrier billing, 3PL software
- [ ] **EULA** — AWS Marketplace standard EULA, or upload EDGE77's custom terms
- [ ] **Support URL** — [EDGE77 support page URL]
- [ ] **Documentation URL** — [EDGE77 docs/knowledge base URL]
- [ ] **Video URL** — YouTube or Vimeo demo (2-3 minutes, product walkthrough)

### Pricing

- [ ] **Pricing model** — SaaS Subscription (monthly)
- [ ] **Tiered pricing** — Configure in AWS Marketplace console (see Section 2)
- [ ] **Free trial** — 14-day trial enabled (maps to Starter plan)
- [ ] **Hourly/Annual** — Annual discount option (recommend: 15% off annual commitment)

### Technical Setup

- [ ] **Federation (IAM)** — Configure IAM roles for AWS Marketplace integration (see Section 3)
- [ ] **Subscription API** — Implement AWS Marketplace Entitlement API to check customer subscription status
- [ ] **SaaS registration endpoint** — POST endpoint for AWS to notify EDGE77 of new subscribers
- [ ] **Metering/Billing API** — If usage-based pricing, implement AWS Marketplace Metering API
- [ ] **Product TLD** — AWS requires HTTPS with valid SSL certificate
- [ ] **Redirect URI** — Configure redirect from AWS Marketplace to EDGE77 app after subscription

### Review & Launch

- [ ] **Preview listing** — Submit for AWS review (5-10 business days typical)
- [ ] **Test subscription flow** — Use sandbox to verify end-to-end (subscribe → provision → use → unsubscribe)
- [ ] **API integration validated** — Confirm entitlement/metering API works in test
- [ ] **Pricing reviewed** — Confirm all tiers show correctly in preview
- [ ] **Request for public launch** — Once approved, request go-live

---

## 2. Pricing Model Setup

### AWS Marketplace SaaS Subscription Model

AWS Marketplace supports **SaaS Subscription** (fixed recurring fee) and **SaaS Contracts with Usage** (base fee + metered usage).

**Recommended for EDGE77:** SaaS Subscription (Monthly)

### Pricing Tier Configuration

| Tier | AWS Marketplace Config | Monthly Price | Annual Equivalent | Notes |
|---|---|---|---|---|
| **Starter** | Free tier (14-day trial) | $0 | $0 | Contingency-based pricing; AWS Marketplace does not support contingency models natively. Use free trial with "Contact us" note. |
| **Growth** | SaaS Subscription (flat) | $499/mo | $5,089/yr (15% off) | Fixed monthly. No usage metering. |
| **Enterprise** | SaaS Subscription (flat) | $2,999/mo | $30,589/yr (15% off) | Fixed monthly. Include API access, dedicated support. |

### Pricing Display on AWS Marketplace

```
EDGE77 AI Freight Invoice Audit
─────────────────────────────────

Starter (Free Trial — 14 Days)
  • AI invoice extraction (500 invoices/mo)
  • Contract validation
  • Basic dispute generation
  • Email support
  $0/month — No credit card required

Growth (Most Popular)
  • Up to 5,000 invoices/month
  • All Starter features
  • Samsara integration
  • Advanced reporting
  • Email + chat support
  $499/month — $5,089/year (save 15%)

Enterprise
  • Unlimited invoices
  • All Growth features
  • Custom integrations (TMS, ERP)
  • API access
  • Dedicated account manager
  • Phone support + custom onboarding
  $2,999/month — $30,589/year (save 15%)
```

### Important AWS Marketplace Pricing Rules
- **AWS takes 3% referral fee** — EDGE77 receives 97% of transaction
- **AWS bills the customer** — EDGE77 doesn't need to handle billing directly
- **Annual commitments** — AWS handles the annual vs. monthly billing logic
- **Free trials** — Max 30 days on AWS Marketplace (14 days recommended)
- **No "contact us" for pricing** — AWS prefers transparent pricing (Enterprise can have custom pricing, but list a starting price)

### Contingency Tier Workaround
Since AWS Marketplace doesn't fully support contingency-based pricing:
1. List Starter as a 14-day free trial (no credit card required)
2. After trial ends, customers can self-serve upgrade to Growth ($499) or Enterprise ($2,999)
3. Add note in description: *"For contingency-based pricing and high-volume custom plans, contact edge77.com/sales"*
4. Use this as a lead gen pathway for the Starter tier

---

## 3. IAM Roles and Permissions

### AWS IAM User for Marketplace Integration

Create a dedicated IAM user for AWS Marketplace operations:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "aws-marketplace:ViewSubscriptions",
                "aws-marketplace:GetEntitlements",
                "aws-marketplace:RegisterUsage",
                "meteringmarketplace:BatchMeterUsage"
            ],
            "Resource": "*"
        }
    ]
}
```

### IAM Role for EDGE77 Application (Service Role)

If EDGE77 runs on AWS infrastructure, create a service role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "aws-marketplace:GetEntitlements",
                "ec2:DescribeInstances",
                "s3:GetObject",
                "s3:PutObject",
                "sns:Publish"
            ],
            "Resource": "*"
        }
    ]
}
```

### IAM Role for AWS Marketplace Subscription Verification

Used by EDGE77 backend to verify subscriber status:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "aws-marketplace:GetEntitlements"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws-marketplace:AWSMarketplaceProductCode": "EDGE77_PRODUCT_CODE"
                }
            }
        }
    ]
}
```

### Permissions Required by AWS Marketplace

| Action | Purpose |
|---|---|
| `aws-marketplace:ViewSubscriptions` | View customer subscriptions |
| `aws-marketplace:GetEntitlements` | Check current plan/tier for a customer |
| `aws-marketplace:RegisterUsage` | Report SaaS usage (for metered products) |
| `meteringmarketplace:BatchMeterUsage` | Submit metered usage records |

### Setting Up Cross-Account Role (Optional)

If EDGE77 infrastructure is separate from the Marketplace seller account:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::EDGE77_ACCOUNT_ID:root"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "EDGE77-Marketplace-Integration"
                }
            }
        }
    ]
}
```

---

## 4. CloudFormation Template Outline

CloudFormation is **not strictly required** for AWS Marketplace SaaS listings. It's only needed if you're offering infrastructure-based products (AMI, container, or desktop application). EDGE77 is a SaaS product, so the below is informational/optional.

### If You Want to Offer a Quick-Deploy Option for Enterprise Customers

```yaml
# EDGE77 SaaS Connector — CloudFormation Template
# Purpose: Provisions IAM roles and SNS topics for EDGE77 integration
# This is optional — only used for Enterprise customers wanting automated setup

AWSTemplateFormatVersion: "2010-09-09"
Description: "EDGE77 AI Freight Invoice Audit — SaaS Integration Setup"

Parameters:
  EDGE77Environment:
    Type: String
    Default: production
    AllowedValues:
      - production
      - staging
    Description: EDGE77 environment to connect to

  CustomerEmail:
    Type: String
    Description: Email for EDGE77 admin user provisioning

Resources:
  # IAM Role for EDGE77 to access customer's S3 for invoice files
  EDGE77ServiceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "edge77-service-role-${AWS::AccountId}"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: "arn:aws:iam::EDGE77_AWS_ACCOUNT:root"
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: !Ref EDGE77Environment
      Policies:
        - PolicyName: edge77-s3-access
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:ListBucket
                Resource:
                  - !Sub "arn:aws:s3:::edge77-invoice-${AWS::AccountId}"
                  - !Sub "arn:aws:s3:::edge77-invoice-${AWS::AccountId}/*"

  # SNS Topic for invoice processing notifications
  EDGE77NotificationTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub "edge77-notifications-${AWS::AccountId}"
      Subscription:
        - Protocol: https
          Endpoint: !Sub "https://api.edge77.com/webhooks/aws/${EDGE77Environment}"
        - Protocol: email
          Endpoint: !Ref CustomerEmail

Outputs:
  ServiceRoleARN:
    Description: "ARN of the IAM role for EDGE77 service access"
    Value: !GetAtt EDGE77ServiceRole.Arn
    Export:
      Name: !Sub "${AWS::StackName}-ServiceRoleARN"

  NotificationTopicARN:
    Description: "ARN of the SNS topic for EDGE77 notifications"
    Value: !Ref EDGE77NotificationTopic
    Export:
      Name: !Sub "${AWS::StackName}-NotificationTopicARN"
```

---

## 5. W-9 and Bank Account Requirements

### W-9 Requirements

| Item | Detail |
|---|---|
| **Form** | IRS W-9 (US companies) or W-8BEN (international) |
| **Business name** | Must match AWS account and DUNS record |
| **EIN** | 9-digit Employer Identification Number |
| **Legal structure** | LLC, Corp, S-Corp, etc. |
| **Address** | Physical address (not PO box) |
| **Submission** | Upload via AWS Marketplace Management Portal |

**Timeline:** 3-5 business days for AWS to verify

### Bank Account Requirements

| Item | Detail |
|---|---|
| **Bank location** | US bank account strongly preferred |
| **Account type** | Business checking account |
| **Currency** | USD only |
| **ACH enabled** | Account must support ACH deposits |
| **Verification** | AWS will make two micro-deposits ($0.01–$0.99) — verify amounts within portal |

**If non-US entity:**
EDGE77 can still register but will need:
- Non-US bank account (eligible countries list on AWS)
- W-8BEN instead of W-9
- Currency conversion fees apply (2.5% typical)

### Disbursement Schedule

| Frequency | Payment Processing | Funds Available |
|---|---|---|
| **Monthly** | AWS pays 30 days after month end | ~60 days after customer payment |
| **Minimum threshold** | $100 minimum disbursement | Below $100 rolls to next month |

---

## 6. Step-by-Step Registration Guide

### Phase 1: Pre-Registration (Week 1)

| Step | Action | Owner | Status |
|---|---|---|---|
| 1.1 | Obtain DUNS number via [dnb.com](https://www.dnb.com) | Legal/Finance | □ |
| 1.2 | Prepare W-9 (scan to PDF) | Finance | □ |
| 1.3 | Set up US business bank account (if needed) | Finance | □ |
| 1.4 | Register EDGE77.com domain with HTTPS/SSL | Engineering | □ |
| 1.5 | Create AWS account (if none exists) | Engineering | □ |
| 1.6 | Gather product screenshots and demo video | Marketing | □ |

### Phase 2: Seller Registration (Week 2)

| Step | Action | Notes |
|---|---|---|
| 2.1 | Go to [aws.amazon.com/marketplace/management](https://aws.amazon.com/marketplace/management) | Use AWS root account or admin IAM user |
| 2.2 | Click **"Register as a seller"** | |
| 2.3 | Complete company profile (name, address, DUNS) | Match W-9 exactly |
| 2.4 | Complete seller tax interview | Upload W-9, answer tax questions |
| 2.5 | Add bank account for disbursement | Routing + account number |
| 2.6 | Verify bank account (micro-deposits) | 1-2 business days |
| 2.7 | Accept AWS Marketplace seller agreement | Read carefully — 3% referral fee |

### Phase 3: Product Listing Creation (Week 3)

| Step | Action | Details |
|---|---|---|
| 3.1 | In Marketplace Management Portal, click **"Create product"** | Select: **SaaS Subscription** |
| 3.2 | Enter product name and description | Use optimized copy from Section 2 |
| 3.3 | Upload product logo | 120x120 PNG, transparent bg |
| 3.4 | Select product category | Software → Business Applications → Supply Chain |
| 3.5 | Configure pricing tiers | $0 (trial), $499/mo, $2,999/mo |
| 3.6 | Upload EULA | Use AWS Standard or custom |
| 3.7 | Add support/documentation URLs | |
| 3.8 | Add search keywords | See Section 1 |
| 3.9 | Upload screenshots (5 min) + demo video | See screenshots specs |

### Phase 4: Technical Integration (Weeks 3-4)

| Step | Action | Details |
|---|---|---|
| 4.1 | **Implement SaaS Registration endpoint** | POST endpoint at `edge77.com/api/aws/register` |
| 4.2 | **Implement SNS endpoint** | Receive subscription notifications |
| 4.3 | **Implement Entitlement API check** | Verify customer plan on login |
| 4.4 | **Create IAM user/role** | For EDGE77 to call AWS Marketplace APIs |
| 4.5 | **Set up redirect** | After AWS subscription -> EDGE77 onboarding |
| 4.6 | **Implement unsubcribe cleanup** | Deactivate customer on cancel |
| 4.7 | **Test in sandbox** | Use AWS Marketplace testing tools |

### Phase 5: Review & Submission (Week 4)

| Step | Action | Timeline |
|---|---|---|
| 5.1 | Submit product for AWS review | 5-10 business days |
| 5.2 | Respond to AWS feedback | Usually 1-2 rounds of questions |
| 5.3 | Fix any issues flagged by reviewer | Common: pricing display, EULA formatting |
| 5.4 | Receive approval notification | Email from AWS Marketplace team |
| 5.5 | Perform final end-to-end test | Subscribe → provision → use → unsubscribe |
| 5.6 | Request public launch | Or set launch date |

### Phase 6: Post-Launch (Week 5+)

| Step | Action | Frequency |
|---|---|---|
| 6.1 | Monitor subscription metrics | Daily (first week), weekly thereafter |
| 6.2 | Respond to customer inquiries via AWS | Within 24 hours |
| 6.3 | Process refund requests | Via AWS Marketplace console |
| 6.4 | Update listing (features, screenshots) | Quarterly |
| 6.5 | Review AWS Marketplace analytics | Monthly |
| 6.6 | Collect and respond to reviews | Ongoing |

### Common Pitfalls to Avoid

- **DUNS number mismatch** — Must exactly match company name and address on W-9
- **Bank account not ACH-enabled** — Many online-only banks need ACH enabled explicitly
- **Trial > 30 days** — AWS max is 30 days for free trial
- **No HTTPS on redirect URL** — AWS requires valid SSL on all endpoints
- **Missing SNS confirmation** — Must confirm SNS subscription before AWS sends events
- **Wrong product type selected** — Choose SaaS Subscription, not AMI or Container

---

*Last updated: July 2026*
