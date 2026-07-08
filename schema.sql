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
