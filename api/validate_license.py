"""
License Validation API Endpoint

This endpoint validates license keys for the Complio CLI.
It checks signature validity, license status, and expiration.
"""

import os
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# Import library modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.license_generator import verify_signature
from lib.database import Database


class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler for license validation.
    """

    def do_POST(self):
        """Handle POST requests for license validation."""
        try:
            # Get environment variable
            signing_key = os.environ.get('LICENSE_SIGNING_KEY')

            if not signing_key:
                self._send_error(500, "Server configuration error")
                return

            # Read and parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON in request body")
                return

            # Extract license key from request
            license_key = data.get('license_key')

            if not license_key:
                self._send_error(400, "Missing license_key in request")
                return

            # Validate license key format
            if not license_key.startswith('COMPL-') or len(license_key) != 24:
                self._send_json_response({
                    'valid': False,
                    'error': 'Invalid license key format'
                })
                return

            # Get client information for logging
            ip_address = self.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            user_agent = self.headers.get('User-Agent', '')

            # Query database for license
            try:
                db = Database()
                license_data = db.get_license(license_key)
            except Exception as e:
                self._send_error(500, f"Database error: {str(e)}")
                return

            # Check if license exists
            if not license_data:
                # Log failed validation attempt
                try:
                    db.log_validation(
                        license_key=license_key,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        error_message='License not found'
                    )
                except Exception:
                    pass  # Don't fail validation if logging fails

                self._send_json_response({
                    'valid': False,
                    'error': 'License not found'
                })
                return

            # Extract license information
            email = license_data.get('email')
            tier = license_data.get('tier')
            status = license_data.get('status')
            signature = license_data.get('signature')
            expires_at = license_data.get('expires_at')
            validation_count = license_data.get('validation_count', 0)

            # Verify HMAC signature
            if not verify_signature(license_key, email, tier, signature, signing_key):
                # Log failed validation attempt
                try:
                    db.log_validation(
                        license_key=license_key,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        error_message='Invalid signature'
                    )
                except Exception:
                    pass

                self._send_json_response({
                    'valid': False,
                    'error': 'Invalid license signature'
                })
                return

            # Check license status
            if status != 'ACTIVE':
                # Log failed validation attempt
                try:
                    db.log_validation(
                        license_key=license_key,
                        success=False,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        error_message=f'License status is {status}'
                    )
                except Exception:
                    pass

                self._send_json_response({
                    'valid': False,
                    'error': f'License is {status.lower()}'
                })
                return

            # Check expiration
            if expires_at:
                try:
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.utcnow() > expiry_date:
                        # Log failed validation attempt
                        try:
                            db.log_validation(
                                license_key=license_key,
                                success=False,
                                ip_address=ip_address,
                                user_agent=user_agent,
                                error_message='License expired'
                            )
                        except Exception:
                            pass

                        self._send_json_response({
                            'valid': False,
                            'error': 'License has expired'
                        })
                        return
                except Exception as e:
                    # If we can't parse the date, log but don't fail validation
                    print(f"Warning: Failed to parse expiry date: {str(e)}")

            # License is valid - update validation metadata
            try:
                db.update_license_validation(license_key, validation_count + 1)
            except Exception as e:
                # Don't fail validation if update fails
                print(f"Warning: Failed to update validation metadata: {str(e)}")

            # Log successful validation
            try:
                db.log_validation(
                    license_key=license_key,
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                # Don't fail validation if logging fails
                print(f"Warning: Failed to log validation: {str(e)}")

            # Return success response
            self._send_json_response({
                'valid': True,
                'tier': tier,
                'email': email,
                'status': status
            })

        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _send_json_response(self, data: dict):
        """Send successful JSON response with CORS headers."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status_code: int, message: str):
        """Send error JSON response with CORS headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
