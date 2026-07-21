import os, sys, time, logging, smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cold-outreach")

EMAIL_MODE = os.getenv("EMAIL_MODE", "gmail")  # gmail, brevo

TARGETS_ALL = [
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
    ("Hub Group", "info@hubgroup.com"),
    ("BNSF Logistics", "info@bnsflogistics.com"),
    ("KAG Logistics", "info@kaglogistics.com"),
    ("Yusen Logistics", "info@yusen-logistics.com"),
    ("England Logistics", "info@englandlogistics.com"),
    ("Uber Freight", "support@uberfreight.com"),
    ("ArcBest Corporation", "info@arcbest.com"),
    ("Allen Lund Company", "info@allenlund.com"),
    ("Redwood Logistics", "info@redwoodlogistics.com"),
    ("Mode Transportation", "info@modetp.com"),
    ("Priority-1 Inc", "info@priority-1.com"),
    ("Corporate Traffic", "info@corporatetraffic.com"),
    ("Motus Freight", "info@motusfreight.com"),
    ("FreightVana", "info@freightvana.com"),
    ("Genpro", "info@genpro.com"),
    ("SPI Logistics", "info@spilogistics.com"),
    ("Best Logistics Group", "info@bestlogistics.com"),
    ("Freedom Trans USA", "info@freedomtransusa.com"),
    ("Destination Transport", "info@destinationtransport.com"),
    ("Fifth Wheel Freight", "info@fifthwheelfreight.com"),
    ("Penske Logistics", "info@penskelogistics.com"),
    ("Y Force Logistics", "info@yforcelogistics.com"),
    ("T Logistics 4B", "info@tlogistics4b.com"),
    ("Badger Logistics", "info@badgerlogistics.com"),
    ("Navia USA", "info@naviausa.com"),
    ("Nexterus", "info@nexterus.com"),
    ("CargoWise Logistics", "info@cargowiselogistics.com"),
    ("Noble Worldwide", "info@nobleworldwide.com"),
    ("Noatum Logistics", "info@noatum.com"),
    ("NNR Global Logistics", "info@nnrglobal.com"),
    ("Nippon Express", "info@nipponexpress.com"),
    ("Nissin Group", "info@nissin.com"),
    ("AIT Worldwide", "info@aitworldwide.com"),
    ("World Logistics", "info@worldlogistics.com"),
    ("MIQ Logistics", "info@miq.com"),
    ("Pilot Freight Services", "info@pilotdelivers.com"),
    ("SEKO Logistics", "info@seko.com"),
    ("R+L Global Logistics", "info@rnglobal.com"),
    ("International Export", "info@internationalexport.com"),
]

BOUNCES = {"info@landstar.com", "info@schneider.com", "info@jbhunt.com"}
ALTERNATES = {"info@schneider.com": ("Schneider National", "inquiries@schneider.com"),
              "info@jbhunt.com": ("JB Hunt ICS", "customer.experience@jbhunt.com")}

TARGETS_FILTERED = []
for company, email in TARGETS_ALL:
    if email in BOUNCES:
        if email in ALTERNATES:
            TARGETS_FILTERED.append(ALTERNATES[email])
    else:
        TARGETS_FILTERED.append((company, email))

EMAIL_TEMPLATES = {
    1: {
        "subject": "Quick question about your freight invoice audits",
        "body": """<p>Hi {company} Team,</p>
<p>I noticed {company} handles a lot of freight shipments. Quick question — how are you currently auditing carrier invoices for overcharges?</p>
<p>We built <strong>EDGE77</strong>, an AI-powered freight audit tool that:</p>
<ul>
<li>Scans invoices against contract rates in seconds</li>
<li>Detects fuel surcharge overcharges, accessorial fee errors, and rate discrepancies</li>
<li>Auto-generates carrier dispute emails</li>
<li>Works on a contingency basis (you only pay 10-15% of what we recover)</li>
</ul>
<p>Most of our clients recover <strong>3-8% of their total freight spend</strong> in the first 90 days.</p>
<p>Would you be open to a 15-minute demo? I can show you exactly how it works with your actual invoices.</p>""",
    },
    2: {
        "subject": "Following up — freight invoice auditing",
        "body": """<p>Hi {company} Team,</p>
<p>Following up on my previous note — we're helping freight brokers recover 3-8% of their total freight spend by catching carrier overcharges that slip through manual audits.</p>
<p><strong>EDGE77</strong> automates the entire process:</p>
<ul>
<li>AI parses every invoice line item</li>
<li>Cross-references against your contracted rates and fuel caps</li>
<li>Auto-generates and sends carrier dispute emails</li>
<li>No upfront cost — we take 10-15% of what we recover</li>
</ul>
<p>Would you be open to a 15-minute demo? Happy to walk through it with your actual invoices.</p>""",
    },
    3: {
        "subject": "Last call — freight audit savings",
        "body": """<p>Hi {company} Team,</p>
<p>I wanted to reach out one last time. We've been helping freight brokers automate their invoice auditing and recover overcharges they didn't know they were leaving on the table.</p>
<p><strong>EDGE77</strong> runs on a pure contingency model — if we don't find overcharges, you pay nothing. Typical clients recover <strong>3-8% of their total freight spend</strong> in the first 90 days.</p>
<p>If auditing is something you're looking into, I'd be happy to show you how it works. If not, no worries at all.</p>
<p>Best regards,<br>
<strong>Arshveer Singh Bains</strong><br>
Founder, Axal Global Inc.<br>
<a href="mailto:admin@edge77.app">admin@edge77.app</a> | <a href="https://edge77.app">edge77.app</a></p>""",
    },
}

SIGNATURE = """
<p>Best regards,<br>
<strong>Arshveer Singh Bains</strong><br>
Founder, Axal Global Inc.<br>
<a href="mailto:admin@edge77.app">admin@edge77.app</a> | <a href="https://edge77.app">edge77.app</a></p>
</div></body></html>"""


def build_email_body(company, template_body):
    html = f"""<html><body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto;">
{template_body.format(company=company)}
{SIGNATURE}"""
    return html


def send_via_gmail(to_email, subject, html_body):
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_user or not gmail_pass:
        logger.error("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Arshveer Singh Bains <{gmail_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())
        logger.info("SENT (gmail) to %s", to_email)
        return True
    except Exception as e:
        logger.error("FAILED (gmail) %s: %s", to_email, e)
        return False


def send_via_brevo(to_email, subject, html_body):
    import httpx
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("BREVO_FROM_EMAIL", "admin@edge77.app")
    from_name = os.getenv("BREVO_FROM_NAME", "Arshveer Singh Bains")
    if not api_key:
        logger.error("BREVO_API_KEY not set")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            logger.info("SENT (brevo) to %s", to_email)
            return True
        logger.error("FAILED (brevo) %s: status=%d %s", to_email, resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        logger.error("ERROR (brevo) %s: %s", to_email, e)
        return False


def send_email(to_email, subject, html_body):
    if EMAIL_MODE == "gmail":
        ok = send_via_gmail(to_email, subject, html_body)
        if not ok:
            logger.info("Falling back to Brevo...")
            return send_via_brevo(to_email, subject, html_body)
        return ok
    return send_via_brevo(to_email, subject, html_body)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="EDGE77 Cold Outreach")
    parser.add_argument("--email-number", type=int, default=1, choices=[1, 2, 3],
                        help="Which email in the sequence (1, 2, or 3)")
    parser.add_argument("--limit", type=int, default=0, help="Max emails to send (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without sending")
    parser.add_argument("--company", type=str, default=None, help="Send to specific company only")
    args = parser.parse_args()

    template = EMAIL_TEMPLATES.get(args.email_number)
    if not template:
        logger.error("Invalid email number: %d", args.email_number)
        sys.exit(1)

    targets = TARGETS_FILTERED
    if args.company:
        targets = [t for t in targets if t[0].lower() == args.company.lower()]
        if not targets:
            logger.error("Company '%s' not found in target list", args.company)
            sys.exit(1)

    subject = template["subject"]
    sent = 0
    failed = 0

    for i, (company, email) in enumerate(targets):
        if args.limit and i >= args.limit:
            break

        html = build_email_body(company, template["body"])
        if args.dry_run:
            logger.info("[DRY-RUN] Would send Email %d to %s (%s)", args.email_number, company, email)
            sent += 1
            continue

        logger.info("[%d/%d] Sending Email %d to %s (%s)", i + 1, len(targets), args.email_number, company, email)
        if send_email(email, subject, html):
            sent += 1
        else:
            failed += 1
        time.sleep(1.5 + (i * 0.1))

    logger.info("Done. Email %d: Sent=%d, Failed=%d", args.email_number, sent, failed)


if __name__ == "__main__":
    main()
