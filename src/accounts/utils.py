import secrets
import string
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def generate_reset_token():
    """Generate a simple random token for password reset"""
    return secrets.token_urlsafe(32)

def send_password_reset_email(email, reset_url, username):
    """Send password reset email"""
    subject = 'Password Reset Request - Pharmacy Management System'
    message = f"""
Hello {username},

You recently requested to reset your password for your Pharmacy Management System account.
Click the link below to reset it:

{reset_url}

This link will expire in 24 hours.

If you did not request a password reset, please ignore this email.

Thank you,
Pharmacy Management System Team
"""
    
    html_message = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2>Password Reset Request</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>You recently requested to reset your password for your Pharmacy Management System account.</p>
    <p>Click the button below to reset it:</p>
    <p>
        <a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link: {reset_url}</p>
    <p><small>This link will expire in 24 hours.</small></p>
    <p>If you did not request a password reset, please ignore this email.</p>
    <hr>
    <p>Thank you,<br>Pharmacy Management System Team</p>
</body>
</html>
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )

def generate_secure_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for i in range(length))