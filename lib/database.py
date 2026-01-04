"""
Supabase Database Client

This module provides a wrapper around the Supabase client for
license management operations.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from supabase import create_client, Client


class Database:
    """
    Database wrapper for Supabase operations.

    This class handles all database interactions for the licensing system,
    including license creation, retrieval, updates, and validation logging.
    """

    def __init__(self):
        """Initialize Supabase client with service role credentials."""
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
            )

        self.client: Client = create_client(supabase_url, supabase_key)

    def insert_license(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new license into the database.

        Args:
            license_data: Dictionary containing license information:
                - license_key: The license key
                - signature: HMAC signature
                - email: Customer email
                - tier: License tier
                - status: License status (default: ACTIVE)
                - stripe_customer_id: Stripe customer ID
                - stripe_subscription_id: Stripe subscription ID
                - expires_at: Expiration timestamp (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Dict containing the inserted license record

        Raises:
            Exception: If database insert fails
        """
        try:
            response = self.client.table('licenses').insert(license_data).execute()

            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to insert license: No data returned")

        except Exception as e:
            raise Exception(f"Database insert failed: {str(e)}")

    def get_license(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a license by license key.

        Args:
            license_key: The license key to query

        Returns:
            Dict containing license data, or None if not found

        Raises:
            Exception: If database query fails
        """
        try:
            response = self.client.table('licenses').select('*').eq(
                'license_key', license_key
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                return None

        except Exception as e:
            raise Exception(f"Database query failed: {str(e)}")

    def update_license_validation(
        self,
        license_key: str,
        validation_count: int
    ) -> Dict[str, Any]:
        """
        Update license validation metadata.

        This updates the last_validated_at timestamp and increments
        the validation counter.

        Args:
            license_key: The license key to update
            validation_count: New validation count

        Returns:
            Dict containing the updated license record

        Raises:
            Exception: If database update fails
        """
        try:
            update_data = {
                'last_validated_at': datetime.utcnow().isoformat(),
                'validation_count': validation_count
            }

            response = self.client.table('licenses').update(update_data).eq(
                'license_key', license_key
            ).execute()

            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to update license: No data returned")

        except Exception as e:
            raise Exception(f"Database update failed: {str(e)}")

    def log_validation(
        self,
        license_key: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a license validation attempt.

        This creates an audit trail of all validation attempts for
        security monitoring and analytics.

        Args:
            license_key: The license key being validated
            success: Whether validation succeeded
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            error_message: Error message if validation failed (optional)

        Returns:
            Dict containing the inserted validation log record

        Raises:
            Exception: If database insert fails
        """
        try:
            log_data = {
                'license_key': license_key,
                'validated_at': datetime.utcnow().isoformat(),
                'success': success,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'error_message': error_message
            }

            response = self.client.table('validations').insert(log_data).execute()

            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to log validation: No data returned")

        except Exception as e:
            # Don't fail validation if logging fails - just log the error
            print(f"Warning: Validation logging failed: {str(e)}")
            return {}

    def get_license_by_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get license by Stripe subscription ID.

        This method is used to find licenses when processing Stripe webhook
        events related to subscriptions (payment failures, cancellations, etc.).

        Args:
            subscription_id: Stripe subscription ID (sub_xxxxx)

        Returns:
            Dict containing license data if found, None otherwise

        Raises:
            Exception: If database query fails
        """
        try:
            response = self.client.table('licenses').select('*').eq(
                'stripe_subscription_id', subscription_id
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                return None

        except Exception as e:
            raise Exception(f"Database query failed: {str(e)}")

    def update_license_status(self, license_key: str, new_status: str) -> Dict[str, Any]:
        """
        Update license status.

        This method is used to change license status based on subscription
        events (e.g., ACTIVE → SUSPENDED on payment failure, SUSPENDED → CANCELLED
        on subscription deletion).

        Valid statuses: ACTIVE, SUSPENDED, CANCELLED

        Args:
            license_key: License key to update
            new_status: New status (ACTIVE, SUSPENDED, or CANCELLED)

        Returns:
            Dict containing the updated license record

        Raises:
            Exception: If database update fails or invalid status provided
        """
        # Validate status
        valid_statuses = ['ACTIVE', 'SUSPENDED', 'CANCELLED']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

        try:
            update_data = {
                'status': new_status,
                'last_validated_at': datetime.utcnow().isoformat()
            }

            response = self.client.table('licenses').update(update_data).eq(
                'license_key', license_key
            ).execute()

            if response.data:
                print(f"✅ License {license_key} status updated to {new_status}")
                return response.data[0]
            else:
                raise Exception("Failed to update license status: No data returned")

        except Exception as e:
            raise Exception(f"Failed to update license status: {str(e)}")
