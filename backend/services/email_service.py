import smtplib
from email.mime.text import MIMEText
from backend.config import settings

def smtp_configured() -> bool:
    return all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASS, settings.SMTP_FROM])

def send_email(to_email: str, subject: str, body: str):
    if not smtp_configured():
        raise RuntimeError("SMTP is not configured. Set SMTP_* env vars.")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
