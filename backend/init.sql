-- ============================================================
-- AeroGuard — Database Initialization Script
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable PostGIS geospatial extension (RF-012, RF-017)
DO $$ BEGIN
    CREATE EXTENSION IF NOT EXISTS postgis;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'PostGIS extension not available in this environment; falling back to in-memory spatial engine.';
END $$;

-- Enums
DO $$ BEGIN
    CREATE TYPE userrole AS ENUM ('admin', 'operator', 'analyst');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE detectionstatus AS ENUM ('active', 'pending', 'resolved', 'discarded');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE threatlevel AS ENUM ('low', 'medium', 'high', 'critical');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE sensortype AS ENUM ('radar', 'acoustic', 'rf', 'optical', 'thermal');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE sensorstatus AS ENUM ('active', 'inactive', 'maintenance', 'calibrating');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE alerttype AS ENUM ('restricted_zone', 'anomalous_behavior', 'system');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE alertstatus AS ENUM ('open', 'assigned', 'resolved', 'closed');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE alertseverity AS ENUM ('low', 'medium', 'high', 'critical');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE reporttype AS ENUM ('detections', 'alerts', 'audit', 'summary');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE reportformat AS ENUM ('pdf', 'csv', 'excel');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(64) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role userrole NOT NULL DEFAULT 'operator',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Restricted Zones table
CREATE TABLE IF NOT EXISTS restricted_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    description TEXT,
    threat_level threatlevel NOT NULL DEFAULT 'high',
    color VARCHAR(16) NOT NULL DEFAULT '#ef4444',
    max_altitude FLOAT NOT NULL DEFAULT 500.0,
    min_altitude FLOAT NOT NULL DEFAULT 0.0,
    coordinates JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PostGIS Geometry column and GiST Spatial Index (RF-012, RF-017)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        ALTER TABLE restricted_zones ADD COLUMN IF NOT EXISTS geom GEOMETRY(Polygon, 4326);
        CREATE INDEX IF NOT EXISTS idx_restricted_zones_geom ON restricted_zones USING GIST (geom);
    END IF;
EXCEPTION WHEN OTHERS THEN null; END $$;

-- 3. Sensors table
CREATE TABLE IF NOT EXISTS sensors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    type sensortype NOT NULL DEFAULT 'radar',
    status sensorstatus NOT NULL DEFAULT 'active',
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    altitude FLOAT DEFAULT 0.0,
    range_km FLOAT DEFAULT 5.0,
    detections_count INT DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Detections table
CREATE TABLE IF NOT EXISTS detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sensor_id UUID REFERENCES sensors(id) ON DELETE SET NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    altitude FLOAT NOT NULL,
    speed FLOAT NOT NULL,
    heading FLOAT NOT NULL,
    status detectionstatus NOT NULL DEFAULT 'active',
    threat_level threatlevel NOT NULL DEFAULT 'low',
    ai_analyzed BOOLEAN DEFAULT FALSE,
    ai_confidence FLOAT,
    is_drone BOOLEAN DEFAULT FALSE,
    image_url VARCHAR(512),
    zone_id UUID REFERENCES restricted_zones(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    detection_id UUID REFERENCES detections(id) ON DELETE SET NULL,
    type alerttype NOT NULL DEFAULT 'restricted_zone',
    severity alertseverity NOT NULL DEFAULT 'high',
    status alertstatus NOT NULL DEFAULT 'open',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Audit Logs table (RF-029)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent VARCHAR(512),
    data_hash VARCHAR(64) NOT NULL,
    prev_hash VARCHAR(64) NOT NULL DEFAULT '',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Sin cuentas ni datos de demostración. Bootstrap controlado por la aplicación.
