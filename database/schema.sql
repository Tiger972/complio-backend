-- ============================================================================
-- Complio Backend - Supabase Database Schema
-- ============================================================================
-- This schema defines the database structure for the Complio licensing system
-- Run this in the Supabase SQL Editor to set up your database
-- ============================================================================

-- Enable UUID extension (required for UUID primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: licenses
-- ============================================================================
-- Stores all license keys and associated metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS licenses (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- License information
    license_key VARCHAR(24) UNIQUE NOT NULL,
    signature VARCHAR(64) NOT NULL,

    -- Customer information
    email VARCHAR(255) NOT NULL,

    -- License tier (EARLY_ACCESS, STARTER, PRO, ENTERPRISE)
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('EARLY_ACCESS', 'STARTER', 'PRO', 'ENTERPRISE')),

    -- License status (ACTIVE, SUSPENDED, CANCELLED)
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED')),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_validated_at TIMESTAMP WITH TIME ZONE,

    -- Usage tracking
    validation_count INTEGER DEFAULT 0,

    -- Stripe integration
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),

    -- Additional metadata (JSON for flexibility)
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(email);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
CREATE INDEX IF NOT EXISTS idx_licenses_stripe_customer ON licenses(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_licenses_stripe_subscription ON licenses(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_licenses_created_at ON licenses(created_at DESC);

-- ============================================================================
-- TABLE: validations
-- ============================================================================
-- Audit log of all license validation attempts
-- Enables security monitoring and analytics
-- ============================================================================

CREATE TABLE IF NOT EXISTS validations (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- License being validated
    license_key VARCHAR(24) NOT NULL,

    -- Timestamp
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Client information
    ip_address INET,
    user_agent VARCHAR(255),

    -- Validation result
    success BOOLEAN NOT NULL,
    error_message TEXT,

    -- Foreign key to licenses table (optional, for referential integrity)
    -- Note: We use license_key instead of id to maintain history even if license is deleted
    CONSTRAINT fk_license_key FOREIGN KEY (license_key)
        REFERENCES licenses(license_key)
        ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_validations_license_key ON validations(license_key);
CREATE INDEX IF NOT EXISTS idx_validations_validated_at ON validations(validated_at DESC);
CREATE INDEX IF NOT EXISTS idx_validations_success ON validations(success);
CREATE INDEX IF NOT EXISTS idx_validations_ip_address ON validations(ip_address);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Enable RLS to prevent unauthorized access
-- Only service role can access the data
-- ============================================================================

-- Enable RLS on licenses table
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;

-- Enable RLS on validations table
ALTER TABLE validations ENABLE ROW LEVEL SECURITY;

-- Policy for service role (full access)
-- The service role is used by the API functions
CREATE POLICY "Service role has full access to licenses"
    ON licenses
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to validations"
    ON validations
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================
-- Helper functions for common operations
-- ============================================================================

-- Function to automatically update last_validated_at timestamp
CREATE OR REPLACE FUNCTION update_last_validated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE licenses
    SET last_validated_at = NOW()
    WHERE license_key = NEW.license_key AND NEW.success = true;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_validated_at when a successful validation is logged
CREATE TRIGGER trigger_update_last_validated_at
    AFTER INSERT ON validations
    FOR EACH ROW
    WHEN (NEW.success = true)
    EXECUTE FUNCTION update_last_validated_at();

-- ============================================================================
-- VIEWS
-- ============================================================================
-- Useful views for analytics and monitoring
-- ============================================================================

-- View: Active licenses summary
CREATE OR REPLACE VIEW active_licenses_summary AS
SELECT
    tier,
    COUNT(*) as total_licenses,
    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_licenses,
    COUNT(CASE WHEN status = 'SUSPENDED' THEN 1 END) as suspended_licenses,
    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as cancelled_licenses,
    AVG(validation_count) as avg_validations,
    MAX(created_at) as most_recent_license
FROM licenses
GROUP BY tier;

-- View: Validation statistics
CREATE OR REPLACE VIEW validation_statistics AS
SELECT
    DATE(validated_at) as date,
    COUNT(*) as total_validations,
    COUNT(CASE WHEN success = true THEN 1 END) as successful_validations,
    COUNT(CASE WHEN success = false THEN 1 END) as failed_validations,
    COUNT(DISTINCT license_key) as unique_licenses,
    COUNT(DISTINCT ip_address) as unique_ips
FROM validations
GROUP BY DATE(validated_at)
ORDER BY date DESC;

-- View: Recent validation attempts (last 100)
CREATE OR REPLACE VIEW recent_validations AS
SELECT
    v.validated_at,
    v.license_key,
    l.email,
    l.tier,
    v.success,
    v.error_message,
    v.ip_address,
    v.user_agent
FROM validations v
LEFT JOIN licenses l ON v.license_key = l.license_key
ORDER BY v.validated_at DESC
LIMIT 100;

-- ============================================================================
-- SEED DATA (OPTIONAL - FOR TESTING)
-- ============================================================================
-- Uncomment to create a test license for development
-- WARNING: Do not use this in production!
-- ============================================================================

-- INSERT INTO licenses (
--     license_key,
--     signature,
--     email,
--     tier,
--     status,
--     stripe_customer_id,
--     stripe_subscription_id,
--     metadata
-- ) VALUES (
--     'COMPL-TEST-TEST-TEST-TEST',
--     'test_signature_do_not_use_in_production',
--     'test@example.com',
--     'STARTER',
--     'ACTIVE',
--     'cus_test_123',
--     'sub_test_123',
--     '{"note": "Test license for development"}'::jsonb
-- );

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================
-- Ensure service role has necessary permissions
-- ============================================================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO service_role;

-- Grant permissions on tables
GRANT ALL ON licenses TO service_role;
GRANT ALL ON validations TO service_role;

-- Grant permissions on sequences (for auto-increment)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Grant permissions on views
GRANT SELECT ON active_licenses_summary TO service_role;
GRANT SELECT ON validation_statistics TO service_role;
GRANT SELECT ON recent_validations TO service_role;

-- ============================================================================
-- COMMENTS
-- ============================================================================
-- Add helpful comments to tables and columns
-- ============================================================================

COMMENT ON TABLE licenses IS 'Stores all Complio license keys and metadata';
COMMENT ON COLUMN licenses.license_key IS 'Unique license key in format COMPL-XXXX-XXXX-XXXX-XXXX';
COMMENT ON COLUMN licenses.signature IS 'HMAC-SHA256 signature for license verification';
COMMENT ON COLUMN licenses.tier IS 'License tier: EARLY_ACCESS, STARTER, PRO, or ENTERPRISE';
COMMENT ON COLUMN licenses.status IS 'License status: ACTIVE, SUSPENDED, or CANCELLED';
COMMENT ON COLUMN licenses.validation_count IS 'Number of times this license has been validated';

COMMENT ON TABLE validations IS 'Audit log of all license validation attempts';
COMMENT ON COLUMN validations.success IS 'Whether the validation was successful';
COMMENT ON COLUMN validations.error_message IS 'Error message if validation failed';

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
-- Your Complio backend database is now ready!
--
-- Next steps:
-- 1. Copy your Supabase URL and service role key
-- 2. Add them to your Vercel environment variables
-- 3. Deploy your Vercel functions
-- 4. Test the license generation and validation endpoints
-- ============================================================================
