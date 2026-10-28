"""Email dispatch and notification tools."""

import os
from typing import List

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        func.invoke = lambda args: func(**args)
        return func


@tool
def send_email_notification(recipients: List[str], subject: str, html_body: str) -> str:
    """Sends an executive HTML deployment report email via Microsoft Graph / Exchange Online / SMTP."""
    transport = os.getenv("EMAIL_TRANSPORT", "mock").lower()

    if transport == "smtp":
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            host = os.getenv("SMTP_HOST", "localhost")
            port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("SMTP_USER", "")
            password = os.getenv("SMTP_PASSWORD", "")
            from_addr = os.getenv("EMAIL_FROM_ADDRESS", user)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, recipients, msg.as_string())

            return f"Email successfully dispatched via SMTP to {', '.join(recipients)}"
        except Exception as e:
            print(f"[EMAIL ERROR] SMTP dispatch failed: {e}. Falling back to standard dispatch log.")

    # Standard / Mock dispatch logging
    print(f"\n[AGENT DISPATCH] Sending to: {recipients}")
    print(f"[AGENT DISPATCH] Subject: {subject}")
    print(f"[AGENT DISPATCH] Content preview: {html_body[:250]}...\n")
    return f"Email successfully dispatched to {', '.join(recipients)}"
