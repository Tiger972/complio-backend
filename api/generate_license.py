"""
Stripe Webhook Handler - License Generation

This endpoint handles Stripe checkout.session.completed events,
generates license keys, and sends activation emails to customers.
"""

import os
import json
import stripe
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

# Import library modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.license_generator import generate_license_key, sign_license
from lib.database import Database
from lib.email_sender import send_license_email


class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler for Stripe webhooks.
    """

    def do_POST(self):
        """Handle POST requests from Stripe webhooks."""
        try:
            # Get environment variables
            stripe_api_key = os.environ.get('STRIPE_SECRET_KEY')
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            signing_key = os.environ.get('LICENSE_SIGNING_KEY')

            if not all([stripe_api_key, webhook_secret, signing_key]):
                self._send_error(500, "Server configuration error")
                return

            # Set Stripe API key
            stripe.api_key = stripe_api_key

            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            payload = self.rfile.read(content_length)

            # Get Stripe signature header
            sig_header = self.headers.get('Stripe-Signature')

            if not sig_header:
                self._send_error(400, "Missing Stripe signature")
                return

            # Verify webhook signature
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except stripe.error.SignatureVerificationError as e:
                self._send_error(400, f"Invalid signature: {str(e)}")
                return
            except Exception as e:
                self._send_error(400, f"Webhook error: {str(e)}")
                return

            # Handle checkout.session.completed event
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']

                # Extract customer information
                customer_email = session.get('customer_email')
                customer_id = session.get('customer')
                subscription_id = session.get('subscription')

                # Extract tier from metadata (set in Stripe checkout)
                tier = session.get('metadata', {}).get('tier', 'STARTER')

                if not customer_email:
                    self._send_error(400, "Missing customer email in session")
                    return

                # Generate license key
                license_key = generate_license_key()

                # Generate HMAC signature
                signature = sign_license(license_key, customer_email, tier, signing_key)

                # Calculate expiration (30 days from now for monthly subscriptions)
                expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

                # Prepare license data for database
                license_data = {
                    'license_key': license_key,
                    'signature': signature,
                    'email': customer_email,
                    'tier': tier,
                    'status': 'ACTIVE',
                    'stripe_customer_id': customer_id,
                    'stripe_subscription_id': subscription_id,
                    'expires_at': expires_at,
                    'validation_count': 0,
                    'metadata': {
                        'stripe_session_id': session.get('id'),
                        'created_via': 'stripe_webhook'
                    }
                }

                # Store license in database
                try:
                    db = Database()
                    db.insert_license(license_data)
                except Exception as e:
                    self._send_error(500, f"Database error: {str(e)}")
                    return

                # Send activation email
                try:
                    send_license_email(customer_email, license_key, tier)
                except Exception as e:
                    # Log error but don't fail the webhook
                    # License is already created, email can be resent manually
                    print(f"Warning: Failed to send email: {str(e)}")

                # Send success response
                self._send_success({
                    'message': 'License generated successfully',
                    'license_key': license_key,
                    'email': customer_email,
                    'tier': tier
                })

            else:
                # Event type not handled
                self._send_success({
                    'message': f'Event type {event["type"]} received but not processed'
                })

        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")

    def _send_success(self, data: dict):
        """Send successful JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code: int, message: str):
        """Send error JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
