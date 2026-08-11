-- EDGE77 Database Schema
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS client_contracts (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    max_allowed_fuel NUMERIC(10, 2) NOT NULL DEFAULT 150.00,
    carrier_billing_email VARCHAR(255) NOT NULL,
    dispute_mode VARCHAR(50) DEFAULT 'MANUAL_GATE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS freight_audits (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    client_id VARCHAR(255) NOT NULL,
    tracking_id VARCHAR(255) NOT NULL,
    pdf_hash VARCHAR(64) NOT NULL,
    filename VARCHAR(500) DEFAULT '',
    file_size INTEGER DEFAULT 0,
    total_charge NUMERIC(12, 2) DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    fuel_surcharge NUMERIC(12, 2) NOT NULL DEFAULT 0,
    base_freight_rate NUMERIC(12, 2) NOT NULL DEFAULT 0,
    overcharge_amount NUMERIC(12, 2) DEFAULT 0.00,
    fee_earned NUMERIC(12, 2) DEFAULT 0.00,
    status VARCHAR(50) DEFAULT 'PROCESSING',
    dispute_sent BOOLEAN DEFAULT FALSE,
    overcharge_detected BOOLEAN DEFAULT FALSE,
    raw_text TEXT,
    ai_response JSONB,
    error_log TEXT,
    UNIQUE(client_id, tracking_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_lookup ON freight_audits(client_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_hash ON freight_audits(pdf_hash);
CREATE INDEX IF NOT EXISTS idx_audit_created ON freight_audits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contract_client ON client_contracts(client_id);

-- Client profiles (user account data)
CREATE TABLE IF NOT EXISTS client_profiles (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) DEFAULT '',
    company VARCHAR(255) DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profile_client ON client_profiles(client_id);
CREATE INDEX IF NOT EXISTS idx_profile_email ON client_profiles(email);

-- Client API keys (hashed, shown once at creation)
CREATE TABLE IF NOT EXISTS client_api_keys (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    key_hash VARCHAR(128) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    name VARCHAR(255) DEFAULT 'default',
    active BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_apikey_hash ON client_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_apikey_client ON client_api_keys(client_id);

-- Demo requests (from /api/demo form)
CREATE TABLE IF NOT EXISTS demo_requests (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    invoice_volume VARCHAR(50) DEFAULT '',
    phone VARCHAR(50) DEFAULT '',
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_demo_email ON demo_requests(email);
CREATE INDEX IF NOT EXISTS idx_demo_status ON demo_requests(status);

-- Stripe billing customers
CREATE TABLE IF NOT EXISTS stripe_customers (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255) NOT NULL,
    stripe_subscription_id VARCHAR(255) DEFAULT '',
    tier VARCHAR(50) DEFAULT 'starter',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_customer ON stripe_customers(client_id);
CREATE INDEX IF NOT EXISTS idx_stripe_sub ON stripe_customers(stripe_subscription_id);

-- Stripe subscriptions
CREATE TABLE IF NOT EXISTS stripe_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    stripe_subscription_id VARCHAR(255) NOT NULL,
    tier VARCHAR(50) DEFAULT 'starter',
    status VARCHAR(50) DEFAULT 'active',
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sub_client ON stripe_subscriptions(client_id);
CREATE INDEX IF NOT EXISTS idx_sub_status ON stripe_subscriptions(status);

-- Usage events (for metered billing)
CREATE TABLE IF NOT EXISTS usage_events (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_client ON usage_events(client_id);
CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_events(created_at DESC);
