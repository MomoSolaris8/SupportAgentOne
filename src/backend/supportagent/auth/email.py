import os
import smtplib
from email.message import EmailMessage


def get_frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def build_password_reset_url(token: str) -> str:
    return f"{get_frontend_url()}/?reset_token={token}"


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    if not smtp_configured():
        return False

    message = EmailMessage()
    message["Subject"] = "SupportAgent password reset"
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = to_email
    message.set_content(
        "Use this link to reset your SupportAgent password. "
        "The link expires soon and can be used once.\n\n"
        f"{reset_url}\n"
    )

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True
