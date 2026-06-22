import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    EMAIL_FROM,
)

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, to_email, msg.as_string())
        server.quit()

        logger.info(f"Email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_otp_email(to_email: str, otp: str, purpose: str):
    if purpose == "forgot_password":
        subject = "Enfield Monk - Password Reset OTP"
        body = f"""
        <h2>Password Reset Request</h2>
        <p>Your OTP for password reset is:</p>
        <h1 style="color: #E63946;">{otp}</h1>
        <p>This OTP is valid for <b>10 minutes</b>.</p>
        <p>If you did not request this, please ignore this email.</p>
        """
    else:
        subject = "Enfield Monk - Email Verification OTP"
        body = f"""
        <h2>Email Verification</h2>
        <p>Your OTP for verification is:</p>
        <h1 style="color: #E63946;">{otp}</h1>
        <p>This OTP is valid for <b>10 minutes</b>.</p>
        """

    return send_email(to_email, subject, body)
