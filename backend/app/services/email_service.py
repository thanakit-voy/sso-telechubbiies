"""
Email service for sending emails via SMTP (Gmail).
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_name = settings.SMTP_FROM_NAME
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.use_tls = settings.SMTP_USE_TLS

    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.user and self.password)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Optional plain text content

        Returns:
            True if email was sent successfully
        """
        if not self.is_configured:
            logger.warning("Email service not configured, skipping email send")
            return False

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add plain text part
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_invitation_email(
        self,
        to_email: str,
        invitation_link: str,
        team_name: Optional[str] = None,
        inviter_name: Optional[str] = None,
    ) -> bool:
        """
        Send an invitation email.

        Args:
            to_email: Recipient email address
            invitation_link: The invitation link
            team_name: Optional team name for team invitations
            inviter_name: Optional inviter's name
        """
        if team_name:
            subject = f"You've been invited to join {team_name} on Telechubbiies"
            heading = f"Join {team_name}"
            intro = (
                f"{inviter_name or 'Someone'} has invited you to join "
                f"<strong>{team_name}</strong> on Telechubbiies."
            )
        else:
            subject = "Welcome to Telechubbiies - Complete your registration"
            heading = "Welcome to Telechubbiies"
            intro = "You've been invited to join Telechubbiies as a System Owner."

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">{heading}</h1>
    </div>

    <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="margin-top: 0;">{intro}</p>

        <p>Click the button below to accept this invitation and complete your registration:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{invitation_link}"
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 14px 30px; border-radius: 6px; font-weight: 600; font-size: 16px;">
                Accept Invitation
            </a>
        </div>

        <p style="color: #6b7280; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{invitation_link}" style="color: #667eea; word-break: break-all;">{invitation_link}</a>
        </p>

        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">

        <p style="color: #6b7280; font-size: 12px; margin-bottom: 0;">
            This invitation link will expire in {settings.INVITATION_EXPIRE_HOURS} hours.<br>
            If you didn't request this invitation, you can safely ignore this email.
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        <p style="margin: 0;">&copy; {settings.APP_NAME}</p>
    </div>
</body>
</html>
"""

        text_content = f"""
{heading}

{intro.replace('<strong>', '').replace('</strong>', '')}

Click the link below to accept this invitation:
{invitation_link}

This invitation link will expire in {settings.INVITATION_EXPIRE_HOURS} hours.

If you didn't request this invitation, you can safely ignore this email.

- {settings.APP_NAME}
"""

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_welcome_email(
        self,
        to_email: str,
        first_name: str,
    ) -> bool:
        """Send a welcome email after registration."""
        subject = f"Welcome to {settings.APP_NAME}!"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Welcome, {first_name}!</h1>
    </div>

    <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
        <p style="margin-top: 0;">Your account has been successfully created on {settings.APP_NAME}.</p>

        <p>You can now:</p>
        <ul>
            <li>Manage your teams and members</li>
            <li>Set up roles and permissions</li>
            <li>Configure workspaces</li>
            <li>Create OAuth applications for SSO</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard"
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 14px 30px; border-radius: 6px; font-weight: 600; font-size: 16px;">
                Go to Dashboard
            </a>
        </div>

        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">

        <p style="color: #6b7280; font-size: 12px; margin-bottom: 0;">
            If you have any questions, please don't hesitate to contact us.
        </p>
    </div>

    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        <p style="margin: 0;">&copy; {settings.APP_NAME}</p>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome, {first_name}!

Your account has been successfully created on {settings.APP_NAME}.

You can now:
- Manage your teams and members
- Set up roles and permissions
- Configure workspaces
- Create OAuth applications for SSO

Visit your dashboard: {settings.FRONTEND_URL}/dashboard

- {settings.APP_NAME}
"""

        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
