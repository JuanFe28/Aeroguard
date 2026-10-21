"""Migración aditiva de geometría PostGIS y consulta espacial indexada."""
from sqlalchemy import text


async def initialize_spatial(conn):
    statements = [
        'CREATE EXTENSION IF NOT EXISTS postgis',
        'ALTER TABLE restricted_zones ADD COLUMN IF NOT EXISTS geom geometry(Polygon,4326)',
        '''CREATE OR REPLACE FUNCTION aeroguard_zone_geometry() RETURNS trigger AS $$
        DECLARE point jsonb; line geometry;
        BEGIN
          FOR point IN SELECT value FROM jsonb_array_elements(NEW.coordinates::jsonb) LOOP
            IF line IS NULL THEN
              line := ST_MakeLine(ST_MakePoint((point->>1)::float, (point->>0)::float), ST_MakePoint((point->>1)::float, (point->>0)::float));
            ELSE
              line := ST_AddPoint(line, ST_MakePoint((point->>1)::float, (point->>0)::float));
            END IF;
          END LOOP;
          IF line IS NOT NULL AND ST_NPoints(line) >= 4 THEN
            line := ST_RemovePoint(line, 0);
            IF NOT ST_IsClosed(line) THEN line := ST_AddPoint(line, ST_StartPoint(line)); END IF;
            NEW.geom := ST_SetSRID(ST_MakePolygon(line),4326);
          ELSE NEW.geom := NULL;
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql''',
        'DROP TRIGGER IF EXISTS aeroguard_zone_geometry_trigger ON restricted_zones',
        'CREATE TRIGGER aeroguard_zone_geometry_trigger BEFORE INSERT OR UPDATE OF coordinates ON restricted_zones FOR EACH ROW EXECUTE FUNCTION aeroguard_zone_geometry()',
        'UPDATE restricted_zones SET coordinates=coordinates WHERE geom IS NULL',
        'CREATE INDEX IF NOT EXISTS ix_zones_geom ON restricted_zones USING GIST(geom)',
    ]
    for statement in statements:
        await conn.execute(text(statement))


async def zone_candidates(db, query, latitude, longitude):
    if db.bind.dialect.name != 'postgresql':
        return query
    from app.models.models import RestrictedZone
    ids = (await db.execute(text('SELECT id FROM restricted_zones WHERE is_active AND ST_Covers(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326))'),
                            {'lon': longitude, 'lat': latitude})).scalars().all()
    return query.where(RestrictedZone.id.in_([str(value) for value in ids]))
