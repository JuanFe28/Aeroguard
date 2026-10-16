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

-- Initial Users (Pass: Admin@12345, Operator@12345, Analyst@12345)
INSERT INTO users (username, email, first_name, last_name, password_hash, role, is_active)
VALUES
    ('admin', 'admin@aeroguard.co', 'Admin', 'AeroGuard', crypt('Admin@12345', gen_salt('bf', 12)), 'admin', TRUE),
    ('operador', 'operador@aeroguard.co', 'Carlos', 'Operador', crypt('Operator@12345', gen_salt('bf', 12)), 'operator', TRUE),
    ('analista', 'analista@aeroguard.co', 'Laura', 'Analista', crypt('Analyst@12345', gen_salt('bf', 12)), 'analyst', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Initial Restricted Zones (Bogotá & Bucaramanga Strategic Infrastructure)
INSERT INTO restricted_zones (name, description, threat_level, color, max_altitude, min_altitude, coordinates, is_active)
VALUES
    ('Aeropuerto El Dorado', 'Zona de aproximación y pista de aterrizaje principal Bogotá.', 'critical', '#ef4444', 1200.0, 0.0,
     '[[4.6980,-74.1500],[4.7150,-74.1350],[4.7050,-74.1200],[4.6890,-74.1380]]'::jsonb, TRUE),
    ('Centro de Operaciones Bogotá', 'Instalación militar y centro de control aéreo regional.', 'high', '#f97316', 500.0, 0.0,
     '[[4.6400,-74.1000],[4.6500,-74.0900],[4.6420,-74.0800],[4.6320,-74.0920]]'::jsonb, TRUE),
    ('Zona Residencial Norte Bogotá', 'Área urbana densamente poblada con restricción de sobrevuelo.', 'medium', '#eab308', 250.0, 0.0,
     '[[4.7200,-74.0400],[4.7350,-74.0300],[4.7280,-74.0180],[4.7120,-74.0280]]'::jsonb, TRUE),
    ('Aeropuerto Palonegro (Área Crítica)', 'Zona de aproximación y pista de aterrizaje principal.', 'critical', '#ef4444', 1200.0, 0.0,
     '[[7.1265,-73.1848],[7.1350,-73.1720],[7.1210,-73.1650],[7.1140,-73.1780]]'::jsonb, TRUE),
    ('Complejo Gubernamental Santander', 'Edificios administrativos centrales y centro de mando.', 'high', '#f59e0b', 300.0, 0.0,
     '[[7.1190,-73.1250],[7.1240,-73.1200],[7.1210,-73.1140],[7.1150,-73.1190]]'::jsonb, TRUE)
ON CONFLICT DO NOTHING;

-- Initial Sensors
INSERT INTO sensors (name, type, status, latitude, longitude, altitude, range_km, detections_count)
VALUES
    ('Radar Alfa (Palonegro)', 'radar', 'active', 7.1265, -73.1848, 1180.0, 15.0, 14),
    ('Sensor Óptico/IR Bravo', 'optical', 'active', 7.1220, -73.1750, 1150.0, 4.0, 8),
    ('Sensor RF Charlie (Espectro)', 'rf', 'active', 7.1180, -73.1220, 960.0, 8.0, 5),
    ('Sensor Acústico Delta', 'acoustic', 'active', 7.1250, -73.1280, 950.0, 2.5, 2)
ON CONFLICT DO NOTHING;
