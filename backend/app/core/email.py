"""Outgoing email over SMTP (standard library); used for password-reset links."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def email_enabled() -> bool:
    return bool(settings.SMTP_HOST)


def _send(message: EmailMessage) -> None:
    host, port = settings.SMTP_HOST or "", settings.SMTP_PORT
    context = ssl.create_default_context()
    server: smtplib.SMTP = (
        smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        if settings.SMTP_SECURITY == "ssl"
        else smtplib.SMTP(host, port, timeout=15)
    )
    with server:
        if settings.SMTP_SECURITY == "starttls":
            server.starttls(context=context)
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD.get_secret_value())
        server.send_message(message)


async def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email off the event loop; raises on SMTP errors."""
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    await asyncio.to_thread(_send, message)
