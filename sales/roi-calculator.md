# EDGE77 ROI Calculator

## Prospect Inputs

| Field | Description | Default |
|-------|-------------|---------|
| Monthly Invoice Volume | Number of freight invoices audited per month | — |
| Average Invoice Amount | Mean dollar value per invoice | — |
| Estimated Error Rate | % of invoices containing billing errors | 3% |
| Manual Cost per Invoice | Internal cost to manually audit one invoice (labor + overhead) | $4.50 |

## Calculated Outputs

| Metric | Formula | Example (1000 inv, $2500 avg, 3%) |
|--------|---------|-----------------------------------|
| Monthly Freight Spend | Inv Volume × Avg Amount | $2,500,000 |
| Annual Freight Spend | Monthly × 12 | $30,000,000 |
| Annual Errors | Annual Spend × Error Rate | $900,000 |
| Annual Recoverable | Annual Errors × 85% recovery | $765,000 |
| **Monthly Recovery** | Annual Recoverable ÷ 12 | **$63,750** |
| Manual Audit Cost/Yr | Manual Cost × Inv Volume × 12 | $54,000 |
| **EDGE77 Monthly Savings** | Monthly Recovery − Contingency − Subscription | See below |
| **Net Annual Savings** | (Monthly Savings × 12) + Manual Audit Savings | **$620,250** |
| **Payback Period** | Implementation Cost ÷ Monthly Net Savings | Day 1 (zero implementation) |

## Plan Comparison

### Starter — $0/mo (15% contingency)

Best for: Small 3PLs and brokers (< 500 invoices/mo)

**Annual Recovery (1000 inv, $2500 avg):** $765,000 recovery − $114,750 contingency = **$650,250**
**Plus manual audit elimination:** +$54,000
**Net Annual Savings: $704,250**

### Growth — $499/mo (12% contingency)

Best for: Mid-size 3PLs and logistics teams (500–3000 invoices/mo)

**Annual Recovery (1000 inv, $2500 avg):** $765,000 recovery − $91,800 contingency − $5,988 subscription = **$667,212**
**Plus manual audit elimination:** +$54,000
**Net Annual Savings: $721,212**

### Enterprise — $2,999/mo (10% contingency)

Best for: Large 3PLs, enterprise shippers (> 3000 invoices/mo)

**Annual Recovery (1000 inv, $2500 avg):** $765,000 recovery − $76,500 contingency − $35,988 subscription = **$652,512**
**Plus manual audit elimination:** +$54,000
**Net Annual Savings: $706,512**

> **Note:** The Growth plan delivers the highest net savings at this volume. Enterprise scales better at higher volumes (>3000 invoices) due to lower contingency.

## Example Scenarios

### Scenario 1: Small 3PL (Midwest Logistics Co.)

| Input | Value |
|-------|-------|
| Monthly Invoice Volume | 200 |
| Average Invoice Amount | $1,800 |
| Error Rate | 3% |
| Manual Cost per Invoice | $4.50 |
| Recommended Plan | **Starter ($0/mo)** |

**Results**

| Metric | Amount |
|--------|--------|
| Annual Freight Spend | $4,320,000 |
| Annual Errors | $129,600 |
| Annual Recoverable | $110,160 |
| Contingency (15%) | $16,524 |
| **Net Annual Savings** | **$93,636** |
| Manual Audit Cost Saved | $10,800/yr |
| Payback Period | Immediate |

---

### Scenario 2: Mid-Size 3PL (National Logistics, Inc.)

| Input | Value |
|-------|-------|
| Monthly Invoice Volume | 1,000 |
| Average Invoice Amount | $2,500 |
| Error Rate | 3% |
| Manual Cost per Invoice | $4.50 |
| Recommended Plan | **Growth ($499/mo)** |

**Results**

| Metric | Amount |
|--------|--------|
| Annual Freight Spend | $30,000,000 |
| Annual Errors | $900,000 |
| Annual Recoverable | $765,000 |
| Contingency (12%) | $91,800 |
| Subscription | $5,988 |
| **Net Annual Savings** | **$667,212** |
| Manual Audit Cost Saved | $54,000/yr |
| Payback Period | Immediate |

---

### Scenario 3: Enterprise Shipper (Global Freight Corp)

| Input | Value |
|-------|-------|
| Monthly Invoice Volume | 5,000 |
| Average Invoice Amount | $3,200 |
| Error Rate | 3% |
| Manual Cost per Invoice | $4.50 |
| Recommended Plan | **Enterprise ($2,999/mo)** |

**Results**

| Metric | Amount |
|--------|--------|
| Annual Freight Spend | $192,000,000 |
| Annual Errors | $5,760,000 |
| Annual Recoverable | $4,896,000 |
| Contingency (10%) | $489,600 |
| Subscription | $35,988 |
| **Net Annual Savings** | **$4,370,412** |
| Manual Audit Cost Saved | $270,000/yr |
| Payback Period | Immediate |

## Assumptions & Methodology

1. **Industry error rate:** 3% is the industry average for freight billing errors per TIA and independent studies. Rate may vary by carrier mix and contract complexity.
2. **Recovery rate:** EDGE77's AI extraction and contract rate validation typically recovers 85% of total billing errors. Some errors are below dispute thresholds or involve non-contractual discrepancies.
3. **Manual audit cost:** $4.50/invoice is the fully-loaded average across labor, training, and audit tooling. Enterprise operations with dedicated teams may see higher per-invoice costs.
4. **Contingency fee:** Charged on recovered amounts only. If EDGE77 finds no errors, you pay $0 contingency.
5. **Implementation:** EDGE77 requires no upfront investment. Typical onboarding: 5–10 business days.
6. **Payback period:** Zero upfront cost means positive ROI from the first recovery cycle (typically 30 days).

## Interactive HTML Version

To deploy this calculator as an interactive web tool, capture the inputs above and apply the formulas in this section. See `roi-calculator.html` for the reference implementation.

```javascript
// Core calculation logic
function calculateROI(inputs) {
  const monthlySpend = inputs.invoiceVolume * inputs.avgAmount;
  const annualSpend = monthlySpend * 12;
  const annualErrors = annualSpend * (inputs.errorRate / 100);
  const recoverable = annualErrors * 0.85;

  const plan = getPlan(inputs.invoiceVolume);
  const contingency = recoverable * (plan.contingency / 100);
  const subscription = plan.monthly * 12;
  const manualCost = inputs.manualCostPerInvoice * inputs.invoiceVolume * 12;

  return {
    monthlySpend,
    annualSpend,
    annualErrors,
    recoverable,
    netAnnual: recoverable - contingency - subscription + manualCost,
    paybackMonths: 0,
    plan: plan.name
  };
}
```
