-- EDGE77: Client API Keys table
-- Run this in Supabase SQL Editor

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

-- Service role can do everything
CREATE POLICY "Service role full access" ON client_api_keys
    FOR ALL
    USING (auth.role() = 'service_role');
