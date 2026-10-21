import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("todo_app.email")

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_SSL_PORT = 465


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"TaskMaster <{settings.SMTP_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_SSL_PORT, timeout=15) as smtp:
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns False instead of raising, so callers never leak delivery errors."""
    if not (settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.warning("Email not sent: SMTP_USER / SMTP_PASSWORD are not configured")
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, body)  # smtplib blocks
        return True
    except Exception as e:
        logger.error(f"Email to {to} failed: {e}")
        return False
