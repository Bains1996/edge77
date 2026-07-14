-- Samsara OAuth2 Credentials Table
-- Run this in Supabase SQL Editor

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

-- Add Samsara fields to client_contracts if not exists
ALTER TABLE client_contracts 
ADD COLUMN IF NOT EXISTS samsara_connected BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS samsara_vehicle_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS samsara_driver_count INTEGER DEFAULT 0;

-- Add Samsara match data to freight_audits if not exists
ALTER TABLE freight_audits
ADD COLUMN IF NOT EXISTS samsara_vehicle_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS samsara_driver_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS samsara_trip_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS samsara_match_data JSONB;
