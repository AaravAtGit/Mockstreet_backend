import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

def send_email(
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    """
    Sends an email using the SMTP settings from config.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP settings not configured. Email not sent.")
        logger.info(f"--- MOCK EMAIL TO {email_to} ---\nSubject: {subject}\n{html_content}\n-----------------------")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = email_to

    part1 = MIMEText(html_content, "html")
    msg.attach(part1)

    try:
        smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
        if settings.SMTP_TLS:
            smtp_options["timeout"] = 10
            
        with smtplib.SMTP(**smtp_options) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, email_to, msg.as_string())
        logger.info(f"Email sent successfully to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {e}")


def send_verification_email(email_to: str, token: str) -> None:
    """
    Sends a verification email with a modern, full-page black & white design.
    """
    link = f"https://www.mockstreet.com/verify-mail?token={token}"
    subject = f"Verify your Mockstreet Account"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Email</title>
</head>
<body style="margin: 0; padding: 0; background-color: #000000; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #ffffff;">

    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #000000;">
        <tr>
            <td align="center" style="padding: 80px 20px;">
                
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 480px; text-align: left;">
                    
                    <tr>
                        <td style="padding-bottom: 40px;">
                            <span style="font-size: 16px; font-weight: 700; letter-spacing: 1px; color: #ffffff; text-transform: uppercase;">
                                Mockstreet
                            </span>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding-bottom: 20px;">
                            <h1 style="margin: 0; font-size: 32px; font-weight: 600; letter-spacing: -1px; color: #ffffff; line-height: 1.1;">
                                Verify your email.
                            </h1>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding-bottom: 32px;">
                            <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #a0a0a0;">
                                To finish setting up your Mockstreet account, please confirm your email address. This link expires in <strong>{settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours</strong>.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding-bottom: 40px;">
                            <a href="{link}" target="_blank" style="display: inline-block; background-color: #ffffff; color: #000000; padding: 14px 30px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.2px;">
                                Confirm Email
                            </a>
                        </td>
                    </tr>

                    <tr>
                        <td style="border-top: 1px solid #222222; padding-top: 32px;"></td>
                    </tr>

                    <tr>
                        <td style="padding-bottom: 24px;">
                            <p style="margin: 0; font-size: 12px; color: #666666; line-height: 1.5;">
                                Button not working? Copy and paste this URL:
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 12px; color: #444444; word-break: break-all;">
                                <a href="{link}" style="color: #888888; text-decoration: none;">{link}</a>
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td>
                            <p style="margin: 0; font-size: 11px; color: #444444; letter-spacing: 0.1px;">
                                &copy; 2026 Mockstreet. All rights reserved.
                            </p>
                        </td>
                    </tr>

                </table>
                </td>
        </tr>
    </table>

</body>
</html>
"""
    
    send_email(
        email_to=email_to,
        subject=subject,
        html_content=html_content,
    )
