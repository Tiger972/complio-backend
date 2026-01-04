"""
License Key Generation and HMAC Signing

This module provides cryptographically secure license key generation
and HMAC-SHA256 signing for the Complio licensing system.
"""

import secrets
import hmac
import hashlib


def generate_license_key() -> str:
    """
    Generate a cryptographically secure license key.

    Format: COMPL-XXXX-XXXX-XXXX-XXXX
    - 4 parts of 4 hexadecimal characters each
    - 64 bits of entropy (16 hex chars = 64 bits)

    Returns:
        str: License key in format COMPL-XXXX-XXXX-XXXX-XXXX
    """
    # Generate 8 bytes (64 bits) of cryptographically secure random data
    random_bytes = secrets.token_bytes(8)

    # Convert to hexadecimal string (16 characters)
    hex_string = random_bytes.hex().upper()

    # Split into 4 parts of 4 characters each
    parts = [hex_string[i:i+4] for i in range(0, 16, 4)]

    # Format as COMPL-XXXX-XXXX-XXXX-XXXX
    license_key = f"COMPL-{'-'.join(parts)}"

    return license_key


def sign_license(license_key: str, email: str, tier: str, signing_key: str) -> str:
    """
    Generate HMAC-SHA256 signature for a license.

    This creates a cryptographic signature that prevents license forgery.
    The signature is computed over the concatenation of:
    - license_key
    - email
    - tier

    Args:
        license_key: The license key (e.g., COMPL-XXXX-XXXX-XXXX-XXXX)
        email: Customer email address
        tier: License tier (EARLY_ACCESS, STARTER, PRO, ENTERPRISE)
        signing_key: Secret signing key (hex string)

    Returns:
        str: Hexadecimal HMAC-SHA256 signature (64 characters)
    """
    # Create message by concatenating license components
    message = f"{license_key}|{email}|{tier}"

    # Convert signing key from hex to bytes
    key_bytes = bytes.fromhex(signing_key)

    # Compute HMAC-SHA256
    signature = hmac.new(
        key_bytes,
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_signature(
    license_key: str,
    email: str,
    tier: str,
    signature: str,
    signing_key: str
) -> bool:
    """
    Verify a license signature using constant-time comparison.

    This prevents timing attacks by using hmac.compare_digest() which
    compares the signatures in constant time regardless of where they differ.

    Args:
        license_key: The license key to verify
        email: Customer email address
        tier: License tier
        signature: The signature to verify
        signing_key: Secret signing key (hex string)

    Returns:
        bool: True if signature is valid, False otherwise
    """
    # Generate expected signature
    expected_signature = sign_license(license_key, email, tier, signing_key)

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)
