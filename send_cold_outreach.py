import os, sys, time, logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cold-outreach")

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "admin@edge77.app")
BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", "Arshveer Singh Bains")

TARGETS = [
    ("C.H. Robinson", "info@chrobinson.com"),
    ("Total Quality Logistics", "info@tql.com"),
    ("XPO Logistics", "info@xpo.com"),
    ("Echo Global Logistics", "info@echo.com"),
    ("Worldwide Express", "info@worldwideexpress.com"),
    ("RXO", "info@rxo.com"),
    ("Landstar System", "info@landstar.com"),
    ("Schneider National", "info@schneider.com"),
    ("GlobalTranz", "info@globaltranz.com"),
    ("JB Hunt ICS", "info@jbhunt.com"),
]

def build_email_body(company):
    return f"""<html><body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto;">
<p>Hi {company} Team,</p>
<p>I noticed {company} handles a lot of freight shipments. Quick question — how are you currently auditing carrier invoices for overcharges?</p>
<p>We built <strong>EDGE77</strong>, an AI-powered freight audit tool that:</p>
<ul>
<li>Scans invoices against contract rates in seconds</li>
<li>Detects fuel surcharge overcharges, accessorial fee errors, and rate discrepancies</li>
<li>Auto-generates carrier dispute emails</li>
<li>Works on a contingency basis (you only pay 10-15% of what we recover)</li>
</ul>
<p>Most of our clients recover <strong>3-8% of their total freight spend</strong> in the first 90 days.</p>
<p>Would you be open to a 15-minute demo? I can show you exactly how it works with your actual invoices.</p>
<p>Best,<br>
<strong>Arshveer Singh Bains</strong><br>
Founder, Axal Global Inc.<br>
<a href="mailto:admin@edge77.app">admin@edge77.app</a> | <a href="https://edge77.app">https://edge77.app</a></p>
</div></body></html>"""

def send_via_brevo(to_email, subject, html_body):
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
            logger.info("SENT to %s (status=%d)", to_email, resp.status_code)
            return True
        else:
            logger.error("FAILED %s: status=%d %s", to_email, resp.status_code, resp.text[:200])
            return False
    except Exception as e:
        logger.error("ERROR %s: %s", to_email, e)
        return False

def main():
    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY not set")
        sys.exit(1)

    subject = "Quick question about your freight invoice audits"
    sent = 0
    failed = 0

    for company, email in TARGETS:
        logger.info("Sending to %s (%s)", company, email)
        html = build_email_body(company)
        if send_via_brevo(email, subject, html):
            sent += 1
        else:
            failed += 1
        time.sleep(0.5)

    logger.info("Done. Sent=%d, Failed=%d", sent, failed)

if __name__ == "__main__":
    main()
