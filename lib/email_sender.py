"""
Email Sender via Resend

This module handles sending license activation emails to customers
using the Resend email service.
"""

import os
from typing import Dict, Any
import resend


def send_license_email(email: str, license_key: str, tier: str) -> Dict[str, Any]:
    """
    Send license activation email to customer.

    This sends a beautifully formatted HTML email containing:
    - The license key
    - Activation instructions
    - CLI usage examples
    - Support information

    Args:
        email: Customer email address
        license_key: The generated license key
        tier: License tier (EARLY_ACCESS, STARTER, PRO, ENTERPRISE)

    Returns:
        Dict containing Resend API response

    Raises:
        Exception: If email sending fails
    """
    # Set Resend API key
    resend.api_key = os.environ.get('RESEND_API_KEY')

    if not resend.api_key:
        raise ValueError("RESEND_API_KEY must be set in environment")

    # Format tier name for display
    tier_display = tier.replace('_', ' ').title()

    # Create HTML email template
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Complio License Key</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Welcome to Complio!</h1>
        <p style="color: #f0f0f0; margin: 10px 0 0 0; font-size: 16px;">Your AWS ISO 27001 Compliance Solution</p>
    </div>

    <div style="background: #ffffff; padding: 40px 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Your License is Ready! 🚀</h2>

        <p>Thank you for subscribing to Complio <strong>{tier_display}</strong>. Your license has been activated and is ready to use.</p>

        <div style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 30px 0; border-radius: 4px;">
            <p style="margin: 0 0 10px 0; color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Your License Key</p>
            <code style="font-family: 'Courier New', Courier, monospace; font-size: 18px; color: #667eea; font-weight: bold; word-break: break-all;">{license_key}</code>
        </div>

        <h3 style="color: #333; margin-top: 30px;">📦 Getting Started</h3>

        <p><strong>Step 1: Install Complio CLI</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">pip install complio</code>
        </div>

        <p><strong>Step 2: Activate Your License</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">complio activate --license-key {license_key}</code>
        </div>

        <p><strong>Step 3: Run Your First Compliance Scan</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">complio scan --profile production</code>
        </div>

        <div style="background: #e6fffa; border-left: 4px solid #38b2ac; padding: 20px; margin: 30px 0; border-radius: 4px;">
            <p style="margin: 0; color: #234e52;"><strong>💡 Pro Tip:</strong> Run <code style="background: #b2f5ea; padding: 2px 6px; border-radius: 3px;">complio --help</code> to see all available commands and options.</p>
        </div>

        <h3 style="color: #333; margin-top: 30px;">🔐 License Information</h3>
        <ul style="color: #666; line-height: 1.8;">
            <li><strong>Plan:</strong> {tier_display}</li>
            <li><strong>Email:</strong> {email}</li>
            <li><strong>Status:</strong> Active</li>
        </ul>

        <h3 style="color: #333; margin-top: 30px;">📚 Resources</h3>
        <ul style="color: #666; line-height: 1.8;">
            <li><a href="https://github.com/Tiger972/Complio" style="color: #667eea; text-decoration: none;">📖 Documentation</a></li>
            <li><a href="https://github.com/Tiger972/Complio/issues" style="color: #667eea; text-decoration: none;">🐛 Report Issues</a></li>
            <li><a href="mailto:support@complio.dev" style="color: #667eea; text-decoration: none;">✉️ Contact Support</a></li>
        </ul>

        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">

        <p style="color: #999; font-size: 14px; margin: 0;">
            Need help? Reply to this email or contact us at <a href="mailto:support@complio.dev" style="color: #667eea;">support@complio.dev</a>
        </p>

        <p style="color: #999; font-size: 12px; margin: 20px 0 0 0;">
            This license key is personal and confidential. Do not share it with others.
        </p>
    </div>
</body>
</html>
    """

    # Plain text version for email clients that don't support HTML
    text_content = f"""
Welcome to Complio!

Your License Key: {license_key}

Plan: {tier_display}
Email: {email}
Status: Active

Getting Started:

1. Install Complio CLI:
   pip install complio

2. Activate Your License:
   complio activate --license-key {license_key}

3. Run Your First Compliance Scan:
   complio scan --profile production

Resources:
- Documentation: https://github.com/Tiger972/Complio
- Support: support@complio.dev

This license key is personal and confidential. Do not share it with others.
    """

    try:
        # Send email via Resend
        params = {
            "from": "Complio <licenses@complio.dev>",
            "to": [email],
            "subject": f"🎉 Your Complio {tier_display} License is Ready!",
            "html": html_content,
            "text": text_content,
        }

        response = resend.Emails.send(params)
        return response

    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")
