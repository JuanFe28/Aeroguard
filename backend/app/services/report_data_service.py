"""Datasets consultados en BD con filtros; nunca sustituye errores por ejemplos."""
from collections import Counter
from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from app.models.models import Detection, Alert, AuditLog, Sensor, RestrictedZone, ReportType

def utc(value):
    return None if value is None else value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

async def build_dataset(db, report_type=ReportType.DETECTIONS, date_from=None, date_to=None, operator=""):
    report_type = ReportType(report_type)
    date_from, date_to = utc(date_from), utc(date_to)
    if date_from and date_to and date_from > date_to:
        raise ValueError("Rango de fechas inválido.")
    if report_type == ReportType.AUDIT:
        query, timestamp = select(AuditLog), AuditLog.timestamp
    else:
        query = select(Detection, Sensor.name, RestrictedZone.name).outerjoin(Sensor, Detection.sensor_id == Sensor.id).outerjoin(RestrictedZone, Detection.zone_id == RestrictedZone.id)
        timestamp = Detection.created_at
        if report_type == ReportType.ALERTS:
            query = query.join(Alert, Alert.detection_id == Detection.id).add_columns(Alert.title, Alert.severity, Alert.message)
            timestamp = Alert.created_at
    if date_from:
        query = query.where(timestamp >= date_from)
    if date_to:
        query = query.where(timestamp <= date_to)
    records = (await db.execute(query.order_by(timestamp).limit(5001))).all()
    incursions, audit = [], []
    for item in records[:5000]:
        if report_type == ReportType.AUDIT:
            log = item[0]
            audit.append({"id": log.id, "username": log.username, "action": log.action, "resource": log.resource,
                          "timestamp": utc(log.timestamp).isoformat(), "data_hash": log.data_hash})
            continue
        detection, sensor, zone = item[:3]
        severity = item[4] if report_type == ReportType.ALERTS else detection.threat_level
        incursions.append({"id": detection.id, "sensor": sensor or "Sin sensor", "zone": zone or "Sin zona",
                           "lat": detection.latitude, "lng": detection.longitude, "alt": detection.altitude,
                           "speed": detection.speed, "heading": detection.heading, "severity": severity.value.upper(),
                           "is_drone": detection.is_drone, "ai_confidence": detection.ai_confidence or 0,
                           "timestamp": utc(detection.created_at).isoformat(),
                           "alert_title": item[3] if report_type == ReportType.ALERTS else ""})
    counts = Counter(row['sensor'] for row in incursions)
    return {"data_source": "database", "report_type": report_type.value, "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(), "operator": operator,
            "organization": "AeroGuard — prototipo académico", "truncated": len(records) > 5000,
            "date_from": date_from.isoformat() if date_from else None, "date_to": date_to.isoformat() if date_to else None,
            "ai_verdict": "Sin dictamen visual validado asociado a este reporte.", "incursions": incursions, "audit_records": audit,
            "kpis": {"total_flights": len(incursions), "geofence_violations": sum(row['zone'] != 'Sin zona' for row in incursions),
                     "max_altitude_m": max((row['alt'] for row in incursions), default=0),
                     "top_sensor": counts.most_common(1)[0][0] if counts else "Sin registros",
                     "critical_threats": sum(row['severity'] == 'CRITICAL' for row in incursions)}}
