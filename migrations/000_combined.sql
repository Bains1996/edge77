-- EDGE77: Combined Migration (001 + 002 + 003)
-- Paste this into Supabase SQL Editor and click "Run"

-- ============================================
-- MIGRATION 001: Client API Keys
-- ============================================
CREATE TABLE IF NOT EXISTS client_api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 100
);
CREATE INDEX IF NOT EXISTS idx_client_api_keys_client_id ON client_api_keys(client_id);
CREATE INDEX IF NOT EXISTS idx_client_api_keys_key_hash ON client_api_keys(key_hash);
ALTER TABLE client_api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON client_api_keys FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- MIGRATION 002: Samsara Integration
-- ============================================
CREATE TABLE IF NOT EXISTS samsara_credentials (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope TEXT,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_samsara_client ON samsara_credentials(client_id);
ALTER TABLE client_contracts ADD COLUMN IF NOT EXISTS samsara_connected BOOLEAN DEFAULT FALSE;
ALTER TABLE client_contracts ADD COLUMN IF NOT EXISTS samsara_vehicle_count INTEGER DEFAULT 0;
ALTER TABLE client_contracts ADD COLUMN IF NOT EXISTS samsara_driver_count INTEGER DEFAULT 0;
ALTER TABLE freight_audits ADD COLUMN IF NOT EXISTS samsara_vehicle_id VARCHAR(255);
ALTER TABLE freight_audits ADD COLUMN IF NOT EXISTS samsara_driver_id VARCHAR(255);
ALTER TABLE freight_audits ADD COLUMN IF NOT EXISTS samsara_trip_id VARCHAR(255);
ALTER TABLE freight_audits ADD COLUMN IF NOT EXISTS samsara_match_data JSONB;

-- ============================================
-- MIGRATION 003: Stripe Billing
-- ============================================
CREATE TABLE IF NOT EXISTS stripe_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL UNIQUE,
    stripe_customer_id TEXT NOT NULL UNIQUE,
    email TEXT,
    tier TEXT NOT NULL DEFAULT 'starter',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL UNIQUE,
    stripe_subscription_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'starter',
    status TEXT NOT NULL DEFAULT 'trialing',
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stripe_customers_client ON stripe_customers(client_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_client ON subscriptions(client_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_usage_events_client ON usage_events(client_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON usage_events(created_at);
ALTER TABLE stripe_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON stripe_customers FOR ALL USING (true);
CREATE POLICY "Service role full access" ON subscriptions FOR ALL USING (true);
CREATE POLICY "Service role full access" ON usage_events FOR ALL USING (true);
