import logging
from datetime import datetime, timezone

from v1_database.supabase_client import (
    get_client_contract,
    save_audit_record,
    update_audit_status,
)
from v1_ai_brain.schemas import AuditResult, DisputeResult

logger = logging.getLogger("edge77.engine")

DEFAULT_FEE_PERCENTAGE = 0.15
DEFAULT_MIN_OVERCHARGE = 1.00


def _calculate_fee(overcharge: float, percentage: float = DEFAULT_FEE_PERCENTAGE) -> float:
    return round(overcharge * percentage, 2)


def _build_dispute_email(audit_record: dict, contract: dict, violations: list[dict]) -> tuple[str, str]:
    tracking_id = audit_record.get("tracking_id", "N/A")
    overcharge = audit_record.get("overcharge_amount", 0.0)
    fee = audit_record.get("fee_earned", 0.0)
    currency = audit_record.get("currency", "USD")
    carrier_name = contract.get("carrier_name", "Carrier")

    violation_rows = ""
    for v in violations:
        violation_rows += f"""
      <tr>
        <td style="padding: 8px; border: 1px solid #ddd;">{v['rule']}</td>
        <td style="padding: 8px; border: 1px solid #ddd;">{v['billed']}</td>
        <td style="padding: 8px; border: 1px solid #ddd;">{v['allowed']}</td>
        <td style="padding: 8px; border: 1px solid #ddd; color: #c0392b;"><strong>{currency} {v['overcharge']:.2f}</strong></td>
      </tr>"""

    subject = (
        f"Billing Overcharge — Invoice {tracking_id} "
        f"[{currency} {overcharge:.2f} Recovery Required]"
    )

    body = f"""<html>
<body style="font-family: Arial, sans-serif; color: #1a1a1a; line-height: 1.6;">
<p>Dear {carrier_name} Billing Department,</p>

<p>
This correspondence constitutes formal notice of billing overcharges
identified on shipment <strong>{tracking_id}</strong>, processed under contract
terms executed between your organization and Axal Global Inc. (EDGE77).
</p>

<h3>Charge Summary</h3>
<table style="border-collapse: collapse; width: 100%; max-width: 600px;">
  <tr style="background: #f5f5f5;">
    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Rule Violated</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Billed Amount</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Contract Limit</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Overcharge</th>
  </tr>
  {violation_rows}
  <tr style="background: #fff3cd;">
    <td colspan="3" style="padding: 8px; border: 1px solid #ddd;"><strong>Total Overcharge</strong></td>
    <td style="padding: 8px; border: 1px solid #ddd; color: #c0392b;"><strong>{currency} {overcharge:.2f}</strong></td>
  </tr>
  <tr style="background: #f5f5f5;">
    <td colspan="3" style="padding: 8px; border: 1px solid #ddd;">Audit Fee (15%)</td>
    <td style="padding: 8px; border: 1px solid #ddd;">{currency} {fee:.2f}</td>
  </tr>
</table>

<h3>Required Action</h3>
<p>
We request that the overcharge of <strong>{currency} {overcharge:.2f}</strong> be
credited to the account associated with this shipment within <strong>15 business
days</strong> of receipt of this notice. Failure to respond may result in escalation
in accordance with the terms of the applicable service agreement.
</p>

<p>
Please direct any questions or remittance confirmations to
<a href="mailto:billing@edge77.app">billing@edge77.app</a>, referencing tracking
ID <strong>{tracking_id}</strong>.
</p>

<p style="margin-top: 24px;">
Respectfully,<br>
<strong>EDGE77 Audit Division</strong><br>
Axal Global Inc.<br>
<a href="https://edge77.app">edge77.app</a>
</p>
</body>
</html>"""

    return subject, body


def evaluate_and_dispute(extracted_json: dict, client_id: str) -> DisputeResult:
    logger.info(
        "[EDGE77 ENGINE] Evaluating invoice %s for client %s",
        extracted_json.get("tracking_id", "UNKNOWN"),
        client_id,
    )

    tracking_id = extracted_json.get("tracking_id", "PARSE_ERROR")
    fuel_surcharge = extracted_json.get("fuel_surcharge", 0.0)
    total_charge = extracted_json.get("total_charge", 0.0)
    currency = extracted_json.get("currency", "USD")
    base_freight_rate = extracted_json.get("base_freight_rate", 0.0)
    accessorial_charges = extracted_json.get("accessorial_charges", 0.0)
    insurance_charge = extracted_json.get("insurance_charge", 0.0)
    tax_amount = extracted_json.get("tax_amount", 0.0)

    contract = get_client_contract(client_id)
    dispute_mode = contract.get("dispute_mode", "MANUAL_GATE")
    fee_percentage = contract.get("dispute_fee_percentage", DEFAULT_FEE_PERCENTAGE)
    min_overcharge = contract.get("minimum_overcharge_to_dispute", DEFAULT_MIN_OVERCHARGE)

    violations: list[dict] = []

    max_fuel = contract.get("max_allowed_fuel", 0.0)
    if max_fuel > 0 and fuel_surcharge > max_fuel:
        overcharge_amt = round(fuel_surcharge - max_fuel, 2)
        if overcharge_amt >= min_overcharge:
            violations.append({
                "rule": "Fuel Surcharge Over Limit",
                "billed": f"{currency} {fuel_surcharge:.2f} ({fuel_surcharge/max(total_charge,1)*100:.1f}%)",
                "allowed": f"{currency} {max_fuel:.2f} ({max_fuel/max(total_charge,1)*100:.1f}%)",
                "overcharge": overcharge_amt,
            })

    max_accessorial = contract.get("max_accessorial_charges", 0.0)
    if max_accessorial > 0 and accessorial_charges > max_accessorial:
        overcharge_amt = round(accessorial_charges - max_accessorial, 2)
        if overcharge_amt >= min_overcharge:
            violations.append({
                "rule": "Accessorial Charges Over Limit",
                "billed": f"{currency} {accessorial_charges:.2f}",
                "allowed": f"{currency} {max_accessorial:.2f}",
                "overcharge": overcharge_amt,
            })

    max_base_rate = contract.get("max_base_freight_rate", 0.0)
    if max_base_rate > 0 and base_freight_rate > max_base_rate:
        overcharge_amt = round(base_freight_rate - max_base_rate, 2)
        if overcharge_amt >= min_overcharge:
            violations.append({
                "rule": "Base Rate Over Contract",
                "billed": f"{currency} {base_freight_rate:.2f}",
                "allowed": f"{currency} {max_base_rate:.2f}",
                "overcharge": overcharge_amt,
            })

    max_insurance = contract.get("max_insurance_charge", 0.0)
    if max_insurance > 0 and insurance_charge > max_insurance:
        overcharge_amt = round(insurance_charge - max_insurance, 2)
        if overcharge_amt >= min_overcharge:
            violations.append({
                "rule": "Insurance Charge Over Limit",
                "billed": f"{currency} {insurance_charge:.2f}",
                "allowed": f"{currency} {max_insurance:.2f}",
                "overcharge": overcharge_amt,
            })

    max_tax = contract.get("max_tax_amount", 0.0)
    if max_tax > 0 and tax_amount > max_tax:
        overcharge_amt = round(tax_amount - max_tax, 2)
        if overcharge_amt >= min_overcharge:
            violations.append({
                "rule": "Tax Amount Over Limit",
                "billed": f"{currency} {tax_amount:.2f}",
                "allowed": f"{currency} {max_tax:.2f}",
                "overcharge": overcharge_amt,
            })

    total_overcharge = round(sum(v["overcharge"] for v in violations), 2)
    fee = _calculate_fee(total_overcharge, fee_percentage) if total_overcharge > 0 else 0.0

    if total_overcharge > 0:
        status = "PENDING_APPROVAL" if dispute_mode == "MANUAL_GATE" else "APPROVED"
    else:
        status = "PASS"

    audit_data = {
        "client_id": client_id,
        "tracking_id": tracking_id,
        "total_charge": total_charge,
        "currency": currency,
        "fuel_surcharge": fuel_surcharge,
        "base_freight_rate": base_freight_rate,
        "accessorial_charges": accessorial_charges,
        "billed_weight": extracted_json.get("billed_weight", 0.0),
        "carrier_name": extracted_json.get("carrier_name", ""),
        "overcharge_amount": total_overcharge,
        "fee_earned": fee,
        "status": status,
        "max_allowed_fuel": max_fuel,
        "dispute_mode": dispute_mode,
        "overcharge_detected": total_overcharge > 0,
        "violations": violations,
    }

    record = save_audit_record(audit_data)
    audit_id = record.get("id", 0)

    dispute_sent = False

    if total_overcharge > 0:
        subject, body = _build_dispute_email(record, contract, violations)

        if dispute_mode == "AUTONOMOUS":
            try:
                from v1_automation.email_dispatcher import send_dispute_email

                carrier_email = contract.get("carrier_billing_email", "")
                if carrier_email:
                    dispute_sent = send_dispute_email(carrier_email, subject, body)
                    if dispute_sent:
                        update_audit_status(audit_id, "DISPUTE_SENT", dispute_sent=True)
                        status = "DISPUTE_SENT"
                        logger.info(
                            "[EDGE77 ENGINE] Autonomous dispute sent for %s to %s",
                            tracking_id,
                            carrier_email,
                        )
                    else:
                        update_audit_status(audit_id, "DISPUTE_FAILED")
                        status = "DISPUTE_FAILED"
                        logger.warning(
                            "[EDGE77 ENGINE] Failed to send autonomous dispute for %s",
                            tracking_id,
                        )
                else:
                    logger.warning(
                        "[EDGE77 ENGINE] No carrier billing email for %s — cannot send dispute",
                        tracking_id,
                    )
                    update_audit_status(audit_id, "NO_EMAIL")
                    status = "NO_EMAIL"
            except Exception as e:
                logger.error(
                    "[EDGE77 ENGINE] Error sending autonomous dispute for %s: %s",
                    tracking_id,
                    e,
                )
                update_audit_status(audit_id, "DISPUTE_FAILED")
                status = "DISPUTE_FAILED"
        else:
            logger.info(
                "[EDGE77 ENGINE] Dispute queued (MANUAL_GATE) for %s — awaiting approval",
                tracking_id,
            )
    else:
        logger.info(
            "[EDGE77 ENGINE] No overcharge for %s — status=PASS",
            tracking_id,
        )

    result = DisputeResult(
        audit_id=audit_id,
        tracking_id=tracking_id,
        overcharge=total_overcharge,
        fee_earned=fee,
        status=status,
        dispute_sent=dispute_sent,
    )

    logger.info(
        "[EDGE77 ENGINE] Evaluation complete: tracking=%s overcharge=%.2f fee=%.2f status=%s violations=%d",
        tracking_id,
        total_overcharge,
        fee,
        status,
        len(violations),
    )

    return result
