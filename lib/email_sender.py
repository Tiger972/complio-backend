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
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Votre Clé de Licence Complio</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Bienvenue sur Complio !</h1>
        <p style="color: #f0f0f0; margin: 10px 0 0 0; font-size: 16px;">Votre Solution de Conformité ISO 27001 pour AWS</p>
    </div>

    <div style="background: #ffffff; padding: 40px 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Votre Licence est Prête ! 🚀</h2>

        <p>Merci d'avoir souscrit à Complio <strong>{tier_display}</strong>. Votre licence a été activée et est prête à l'emploi.</p>

        <div style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 30px 0; border-radius: 4px;">
            <p style="margin: 0 0 10px 0; color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Votre Clé de Licence</p>
            <code style="font-family: 'Courier New', Courier, monospace; font-size: 18px; color: #667eea; font-weight: bold; word-break: break-all;">{license_key}</code>
        </div>

        <h3 style="color: #333; margin-top: 30px;">📦 Premiers Pas</h3>

        <p><strong>Étape 1 : Installer Complio CLI</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">pip install complio</code>
        </div>

        <p><strong>Étape 2 : Activer Votre Licence</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">complio activate --license-key {license_key}</code>
        </div>

        <p><strong>Étape 3 : Lancer Votre Premier Scan de Conformité</strong></p>
        <div style="background: #2d3748; color: #fff; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <code style="font-family: 'Courier New', Courier, monospace;">complio scan --region eu-west-3</code>
        </div>

        <div style="background: #e6fffa; border-left: 4px solid #38b2ac; padding: 20px; margin: 30px 0; border-radius: 4px;">
            <p style="margin: 0; color: #234e52;"><strong>💡 Astuce :</strong> Lancez <code style="background: #b2f5ea; padding: 2px 6px; border-radius: 3px;">complio --help</code> pour voir toutes les commandes et options disponibles.</p>
        </div>

        <h3 style="color: #333; margin-top: 30px;">🔐 Informations de Licence</h3>
        <ul style="color: #666; line-height: 1.8;">
            <li><strong>Formule :</strong> {tier_display}</li>
            <li><strong>Email :</strong> {email}</li>
            <li><strong>Statut :</strong> Active</li>
        </ul>

        <h3 style="color: #333; margin-top: 30px;">📚 Ressources</h3>
        <ul style="color: #666; line-height: 1.8;">
            <li><a href="https://www.complio.tech/documentation/getting-started/introduction" style="color: #667eea; text-decoration: none;">📖 Documentation</a></li>
        </ul>

        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">

        <p style="color: #999; font-size: 12px; margin: 20px 0 0 0;">
            Cette clé de licence est personnelle et confidentielle. Ne la partagez pas avec d'autres personnes.
        </p>
    </div>
</body>
</html>
    """

    # Plain text version for email clients that don't support HTML
    text_content = f"""
Bienvenue sur Complio !

Votre Clé de Licence : {license_key}

Formule : {tier_display}
Email : {email}
Statut : Active

Premiers Pas :

1. Installer Complio CLI :
   pip install complio

2. Activer Votre Licence :
   complio activate --license-key {license_key}

3. Lancer Votre Premier Scan de Conformité :
   complio scan --region eu-west-3

Ressources :
- Documentation : https://www.complio.tech/documentation/getting-started/introduction

Cette clé de licence est personnelle et confidentielle. Ne la partagez pas avec d'autres personnes.
    """

    try:
        # Send email via Resend
        params = {
            "from": "Complio <andy.piquionne@complio.tech>",
            "to": [email],
            "subject": f"🎉 Votre Licence Complio {tier_display} est Prête !",
            "html": html_content,
            "text": text_content,
        }

        response = resend.Emails.send(params)
        return response

    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")
