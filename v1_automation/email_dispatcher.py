import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

logger = logging.getLogger("edge77.engine")

AWS_SES_ACCESS_KEY = os.getenv("AWS_SES_ACCESS_KEY")
AWS_SES_SECRET_KEY = os.getenv("AWS_SES_SECRET_KEY")
AWS_SES_REGION = os.getenv("AWS_SES_REGION", "us-east-1")
AWS_SES_FROM_EMAIL = os.getenv("AWS_SES_FROM_EMAIL", "disputes@edge77.com")
AWS_SES_FROM_NAME = os.getenv("AWS_SES_FROM_NAME", "EDGE77 Audit Division")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "axalglobalinc@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_FROM_NAME = os.getenv("GMAIL_FROM_NAME", "EDGE77 Audit Division")

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "audit@edge77.com")
BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", "EDGE77 Audit Division")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "audit@edge77.com")

_email_provider = None
_sendgrid_client = None

if AWS_SES_ACCESS_KEY and AWS_SES_SECRET_KEY:
    _email_provider = "ses"
    logger.info("[EDGE77 ENGINE] Amazon SES provider initialized (best, ~$0.10/1000 emails)")
elif GMAIL_APP_PASSWORD:
    _email_provider = "gmail"
    logger.info("[EDGE77 ENGINE] Gmail SMTP provider initialized (free, 500/day)")
elif BREVO_API_KEY:
    _email_provider = "brevo"
    logger.info("[EDGE77 ENGINE] Brevo email provider initialized")
elif SENDGRID_API_KEY:
    try:
        from sendgrid import SendGridAPIClient
        _sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
        _email_provider = "sendgrid"
        logger.info("[EDGE77 ENGINE] SendGrid email provider initialized")
    except ImportError:
        logger.warning("[EDGE77 ENGINE] sendgrid package not installed")
        _sendgrid_client = None
    except Exception as e:
        logger.warning("[EDGE77 ENGINE] Failed to initialize SendGrid: %s", e)
        _sendgrid_client = None
else:
    logger.warning("[EDGE77 ENGINE] No email API key set. Email dispatch disabled.")


def build_dispute_html(
    tracking_id: str,
    overcharge: float,
    fee: float,
    currency: str,
    carrier_email: str,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EDGE77 — Fuel Surcharge Dispute Notice</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f6f8; padding: 40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr>
    <td style="background-color: #1a1a2e; padding: 28px 40px;">
      <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: 2px;">EDGE77</td>
        <td align="right" style="color: #8892b0; font-size: 12px; vertical-align: middle;">Axal Global Inc.</td>
      </tr>
      </table>
    </td>
  </tr>

  <!-- Banner -->
  <tr>
    <td style="background-color: #c0392b; padding: 14px 40px;">
      <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="color: #ffffff; font-size: 14px; font-weight: 600; letter-spacing: 1px;">
          FUEL SURCHARGE DISPUTE NOTICE
        </td>
        <td align="right" style="color: #ffffff; font-size: 12px;">
          REF: {tracking_id}
        </td>
      </tr>
      </table>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding: 36px 40px; color: #1a1a1a; font-size: 14px; line-height: 1.7;">

      <p style="margin: 0 0 16px 0;">Dear Valued Partner,</p>

      <p style="margin: 0 0 20px 0;">
        This correspondence constitutes formal notice of a fuel surcharge overcharge
        identified during an automated audit of shipment <strong>{tracking_id}</strong>,
        processed under the terms of the service agreement between your organization and
        Axal Global Inc. (EDGE77).
      </p>

      <!-- Overcharge Box -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0; border: 2px solid #c0392b; border-radius: 6px; overflow: hidden;">
        <tr>
          <td style="background-color: #c0392b; color: #ffffff; padding: 10px 20px; font-size: 13px; font-weight: 600;">
            OVERCHARGE DETECTED
          </td>
        </tr>
        <tr>
          <td style="padding: 24px 20px; background-color: #fdf2f2;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding: 6px 0; font-size: 14px; color: #555;">Shipment Tracking ID</td>
                <td align="right" style="padding: 6px 0; font-size: 14px; font-weight: 600;">{tracking_id}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-size: 14px; color: #555;">Audit Date</td>
                <td align="right" style="padding: 6px 0; font-size: 14px;">{timestamp}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-size: 14px; color: #555;">Billing Contact</td>
                <td align="right" style="padding: 6px 0; font-size: 14px;">{carrier_email}</td>
              </tr>
              <tr>
                <td colspan="2" style="padding: 8px 0;"><hr style="border: none; border-top: 1px solid #ddd; margin: 0;"></td>
              </tr>
              <tr>
                <td style="padding: 8px 0; font-size: 16px; font-weight: 700; color: #1a1a1a;">Overcharge Amount</td>
                <td align="right" style="padding: 8px 0; font-size: 20px; font-weight: 700; color: #c0392b;">{currency} {overcharge:.2f}</td>
              </tr>
              <tr>
                <td style="padding: 4px 0 0 0; font-size: 13px; color: #777;">Recovery Fee (15%)</td>
                <td align="right" style="padding: 4px 0 0 0; font-size: 13px; color: #555;">{currency} {fee:.2f}</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <!-- CTA -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin: 28px 0;">
        <tr>
          <td>
            <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600;">Required Action</p>
            <p style="margin: 0 0 12px 0; font-size: 13px; color: #444;">
              Please issue a credit of <strong>{currency} {overcharge:.2f}</strong> to the
              account associated with this shipment within <strong>15 business days</strong>
              of receipt of this notice. Failure to respond may result in escalation in
              accordance with the terms of the applicable service agreement.
            </p>
          </td>
        </tr>
      </table>

      <p style="margin: 0 0 12px 0; font-size: 13px; color: #444;">
        Direct any questions or remittance confirmations to
        <a href="mailto:billing@edge77.com" style="color: #2563eb; text-decoration: none;">billing@edge77.com</a>,
        referencing tracking ID <strong>{tracking_id}</strong>.
      </p>

      <p style="margin: 24px 0 0 0; font-size: 13px; color: #444;">
        Respectfully,<br>
        <strong>EDGE77 Audit Division</strong><br>
        Axal Global Inc.
      </p>

    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background-color: #f0f2f5; padding: 20px 40px; border-top: 1px solid #e0e0e0;">
      <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="font-size: 11px; color: #888; line-height: 1.5;">
          This message was generated by the EDGE77 automated freight audit platform.<br>
          Axal Global Inc. &bull; edge77.com &bull; This is a formal dispute notice.
        </td>
      </tr>
      </table>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _send_via_ses(to_email: str, subject: str, html_body: str) -> bool:
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client(
            "ses",
            aws_access_key_id=AWS_SES_ACCESS_KEY,
            aws_secret_access_key=AWS_SES_SECRET_KEY,
            region_name=AWS_SES_REGION,
        )

        response = client.send_email(
            Source=f"{AWS_SES_FROM_NAME} <{AWS_SES_FROM_EMAIL}>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )

        logger.info("[EDGE77 ENGINE] SES email sent to %s (messageId=%s)", to_email, response["MessageId"])
        return True
    except ClientError as e:
        logger.error("[EDGE77 ENGINE] SES error for %s: %s", to_email, e.response["Error"]["Message"])
        return False
    except Exception as e:
        logger.error("[EDGE77 ENGINE] SES send failed for %s: %s", to_email, e)
        return False


def _send_via_gmail(to_email: str, subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{GMAIL_FROM_NAME} <{GMAIL_ADDRESS}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        logger.info("[EDGE77 ENGINE] Gmail email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("[EDGE77 ENGINE] Gmail send failed for %s: %s", to_email, e)
        return False


def _send_via_brevo(to_email: str, subject: str, html_body: str) -> bool:
    import httpx

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "sender": {"email": BREVO_FROM_EMAIL, "name": BREVO_FROM_NAME},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            logger.info("[EDGE77 ENGINE] Brevo email sent to %s (status=%d)", to_email, resp.status_code)
            return True
        else:
            logger.error("[EDGE77 ENGINE] Brevo returned status %d for %s: %s", resp.status_code, to_email, resp.text[:200])
            return False
    except Exception as e:
        logger.error("[EDGE77 ENGINE] Brevo send failed for %s: %s", to_email, e)
        return False


def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> bool:
    if not _email_provider == "sendgrid":
        return False

    try:
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(SENDGRID_FROM_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )

        response = _sendgrid_client.send(message)

        if 200 <= response.status_code < 300:
            logger.info("[EDGE77 ENGINE] SendGrid email sent to %s (status=%d)", to_email, response.status_code)
            return True
        else:
            logger.error("[EDGE77 ENGINE] SendGrid returned status %d for %s", response.status_code, to_email)
            return False
    except Exception as e:
        logger.error("[EDGE77 ENGINE] SendGrid send failed for %s: %s", to_email, e)
        return False


def send_dispute_email(to_email: str, subject: str, html_body: str) -> bool:
    if not _email_provider:
        logger.warning("[EDGE77 ENGINE] No email provider configured — cannot send to %s", to_email)
        return False

    if not to_email:
        logger.warning("[EDGE77 ENGINE] No recipient email provided — skipping")
        return False

    if _email_provider == "ses":
        return _send_via_ses(to_email, subject, html_body)
    elif _email_provider == "gmail":
        return _send_via_gmail(to_email, subject, html_body)
    elif _email_provider == "brevo":
        return _send_via_brevo(to_email, subject, html_body)
    elif _email_provider == "sendgrid":
        return _send_via_sendgrid(to_email, subject, html_body)
    return False


def send_processing_complete(to_email: str, tracking_id: str, status: str) -> bool:
    if not _email_provider:
        logger.warning("[EDGE77 ENGINE] No email provider — cannot notify %s", to_email)
        return False

    if not to_email:
        logger.warning("[EDGE77 ENGINE] No recipient email — skipping")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"EDGE77 Audit Complete — {tracking_id} [{status}]"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #1a1a1a; line-height: 1.6; padding: 20px;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td>
  <div style="background-color: #1a1a2e; padding: 20px 30px; border-radius: 6px 6px 0 0;">
    <span style="color: #ffffff; font-size: 18px; font-weight: 700; letter-spacing: 2px;">EDGE77</span>
    <span style="color: #8892b0; font-size: 11px; float: right; padding-top: 6px;">Axal Global Inc.</span>
  </div>
  <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
    <h3 style="margin: 0 0 16px 0; font-size: 16px;">Audit Processing Complete</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr><td style="padding: 8px 0; color: #555;">Tracking ID</td><td style="padding: 8px 0; font-weight: 600;">{tracking_id}</td></tr>
      <tr><td style="padding: 8px 0; color: #555;">Final Status</td><td style="padding: 8px 0; font-weight: 600; color: #2563eb;">{status}</td></tr>
      <tr><td style="padding: 8px 0; color: #555;">Processed At</td><td style="padding: 8px 0;">{timestamp}</td></tr>
    </table>
  </div>
  <div style="background-color: #f0f2f5; padding: 16px 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 6px 6px;">
    <p style="margin: 0; font-size: 11px; color: #888;">Automated notification — EDGE77 Freight Audit Platform &bull; Axal Global Inc.</p>
  </div>
</td></tr>
</table>
</body>
</html>"""

    return send_dispute_email(to_email, subject, html_body)
