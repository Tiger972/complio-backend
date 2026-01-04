"""
Stripe Webhook Handler - License Generation

This endpoint handles Stripe checkout.session.completed events,
generates license keys, and sends activation emails to customers.
"""

import os
import json
import stripe
import traceback
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

# Import library modules
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
            # Debug logging - Log incoming request details
            print(f"🔍 Webhook URL called: /api/generate-license")
            print(f"📦 Headers: {dict(self.headers)}")
            print(f"📏 Content-Length: {self.headers.get('Content-Length')}")

            # Get environment variables
            stripe_api_key = os.environ.get('STRIPE_SECRET_KEY')
            webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            signing_key = os.environ.get('LICENSE_SIGNING_KEY')

            # Log configuration status
            print(f"🔐 Stripe-Signature present: {bool(self.headers.get('Stripe-Signature'))}")
            print(f"🔑 STRIPE_SECRET_KEY configured: {bool(stripe_api_key)}")
            print(f"🔑 WEBHOOK_SECRET configured: {bool(webhook_secret)}")
            print(f"🔑 WEBHOOK_SECRET starts with: {webhook_secret[:10] if webhook_secret else 'None'}...")
            print(f"🔑 LICENSE_SIGNING_KEY configured: {bool(signing_key)}")

            if not all([stripe_api_key, webhook_secret, signing_key]):
                missing = []
                if not stripe_api_key:
                    missing.append('STRIPE_SECRET_KEY')
                if not webhook_secret:
                    missing.append('STRIPE_WEBHOOK_SECRET')
                if not signing_key:
                    missing.append('LICENSE_SIGNING_KEY')
                error_msg = f"Server configuration error: Missing {', '.join(missing)}"
                print(f"❌ {error_msg}")
                self._send_error(500, error_msg)
                return

            # Set Stripe API key
            stripe.api_key = stripe_api_key

            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            payload = self.rfile.read(content_length)
            print(f"📄 Payload length: {len(payload)} bytes")
            print(f"📄 Payload preview: {payload[:200] if payload else 'Empty'}...")

            # Get Stripe signature header
            sig_header = self.headers.get('Stripe-Signature')

            if not sig_header:
                error_msg = "Missing Stripe signature"
                print(f"❌ {error_msg}")
                print(f"Available headers: {list(self.headers.keys())}")
                self._send_error(400, error_msg)
                return

            print(f"✅ Stripe signature present: {sig_header[:50]}...")

            # Verify webhook signature
            try:
                print(f"🔐 Verifying webhook signature...")
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
                print(f"✅ Webhook signature verified successfully")
                print(f"📋 Event type: {event.get('type')}")
            except stripe.error.SignatureVerificationError as e:
                error_details = traceback.format_exc()
                print(f"❌ SignatureVerificationError occurred:")
                print(error_details)
                print(f"🔍 Webhook secret being used: {webhook_secret[:10]}...")
                print(f"🔍 Signature header: {sig_header}")
                self._send_error(400, f"Invalid signature: {str(e)}")
                return
            except ValueError as e:
                error_details = traceback.format_exc()
                print(f"❌ ValueError occurred during webhook verification:")
                print(error_details)
                self._send_error(400, f"Invalid payload: {str(e)}")
                return
            except Exception as e:
                error_details = traceback.format_exc()
                print(f"❌ Unexpected error during webhook verification:")
                print(error_details)
                self._send_error(400, f"Webhook error: {str(e)}")
                return

            # Handle checkout.session.completed event
            if event['type'] == 'checkout.session.completed':
                print(f"🎯 Processing checkout.session.completed event")
                session = event['data']['object']

                # Extract customer email from Stripe session
                # Stripe can put email in different locations depending on checkout configuration
                customer_email = None

                # Try customer_details first (most common in Checkout Sessions)
                if session.get('customer_details'):
                    customer_email = session['customer_details'].get('email')
                    if customer_email:
                        print(f"📧 Email found in customer_details: {customer_email}")

                # Fallback to customer_email field (legacy/alternative location)
                if not customer_email:
                    customer_email = session.get('customer_email')
                    if customer_email:
                        print(f"📧 Email found in customer_email field: {customer_email}")

                # If still no email, check if we have a customer ID
                customer_id = session.get('customer')
                subscription_id = session.get('subscription')

                if not customer_email and customer_id:
                    error_msg = f"No customer email found in session. Customer ID: {customer_id}. Please ensure email collection is enabled in Stripe Checkout."
                    print(f"❌ {error_msg}")
                    print(f"Session keys available: {list(session.keys())}")
                    print(f"Customer details: {session.get('customer_details')}")
                    self._send_error(400, error_msg)
                    return

                if not customer_email:
                    error_msg = "Missing customer email in session"
                    print(f"❌ {error_msg}")
                    print(f"Session keys available: {list(session.keys())}")
                    print(f"Session object: {session}")
                    self._send_error(400, error_msg)
                    return

                print(f"✅ Customer email confirmed: {customer_email}")
                print(f"👤 Customer ID: {customer_id}")
                print(f"📋 Subscription ID: {subscription_id}")

                # Extract tier from metadata (set in Stripe checkout)
                tier = session.get('metadata', {}).get('tier', 'STARTER')
                print(f"🏷️  Tier from metadata: {tier}")

                print(f"🔑 Generating license key...")
                # Generate license key
                license_key = generate_license_key()
                print(f"✅ License key generated: {license_key}")

                print(f"🔐 Signing license...")
                # Generate HMAC signature
                signature = sign_license(license_key, customer_email, tier, signing_key)
                print(f"✅ License signed: {signature[:20]}...")

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
                    print(f"💾 Storing license in database...")
                    db = Database()
                    db.insert_license(license_data)
                    print(f"✅ License stored successfully in database")
                except Exception as e:
                    error_details = traceback.format_exc()
                    print(f"❌ Database error occurred:")
                    print(error_details)
                    print(f"License data: {license_data}")
                    self._send_error(500, f"Database error: {str(e)}")
                    return

                # Send activation email
                try:
                    print(f"📧 Sending activation email to {customer_email}...")
                    send_license_email(customer_email, license_key, tier)
                    print(f"✅ Email sent successfully")
                except Exception as e:
                    # Log error but don't fail the webhook
                    # License is already created, email can be resent manually
                    error_details = traceback.format_exc()
                    print(f"⚠️  Warning: Failed to send email:")
                    print(error_details)

                # Send success response
                print(f"🎉 License generation completed successfully!")
                self._send_success({
                    'message': 'License generated successfully',
                    'license_key': license_key,
                    'email': customer_email,
                    'tier': tier
                })

            else:
                # Event type not handled
                print(f"ℹ️  Event type '{event['type']}' received but not processed")
                self._send_success({
                    'message': f'Event type {event["type"]} received but not processed'
                })

        except Exception as e:
            error_details = traceback.format_exc()
            print(f"❌ Unexpected error in do_POST:")
            print(error_details)
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
