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
        record_id = AuditLog.id
    elif report_type == ReportType.ALERTS:
        query = (select(Detection, Sensor.name, RestrictedZone.name, Alert)
                 .select_from(Alert).outerjoin(Detection, Alert.detection_id == Detection.id)
                 .outerjoin(Sensor, Detection.sensor_id == Sensor.id)
                 .outerjoin(RestrictedZone, Detection.zone_id == RestrictedZone.id))
        timestamp, record_id = Alert.created_at, Alert.id
    else:
        query = select(Detection, Sensor.name, RestrictedZone.name).outerjoin(Sensor, Detection.sensor_id == Sensor.id).outerjoin(RestrictedZone, Detection.zone_id == RestrictedZone.id)
        timestamp, record_id = Detection.created_at, Detection.id
    if date_from:
        query = query.where(timestamp >= date_from)
    if date_to:
        query = query.where(timestamp <= date_to)
    records = (await db.execute(query.order_by(timestamp, record_id).limit(5001))).all()
    incursions, audit = [], []
    for item in records[:5000]:
        if report_type == ReportType.AUDIT:
            log = item[0]
            audit.append({"id": log.id, "username": log.username, "action": log.action, "resource": log.resource,
                          "timestamp": utc(log.timestamp).isoformat(), "data_hash": log.data_hash})
            continue
        detection, sensor, zone = item[:3]
        alert = item[3] if report_type == ReportType.ALERTS else None
        record = alert if alert is not None else detection
        severity = alert.severity if alert is not None else detection.threat_level
        row = {"id": record.id, "sensor": sensor or "Sin sensor", "zone": zone or "Sin zona",
               "lat": getattr(detection, 'latitude', None), "lng": getattr(detection, 'longitude', None),
               "alt": getattr(detection, 'altitude', None), "speed": getattr(detection, 'speed', None),
               "heading": getattr(detection, 'heading', None), "severity": severity.value.upper(),
               "is_drone": getattr(detection, 'is_drone', None), "ai_confidence": getattr(detection, 'ai_confidence', None),
               "timestamp": utc(record.created_at).isoformat(), "alert_title": alert.title if alert is not None else ""}
        if alert is not None:
            row['detection_id'] = alert.detection_id
        incursions.append(row)
    counts = Counter(row['sensor'] for row in incursions)
    return {"data_source": "database", "report_type": report_type.value, "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(), "operator": operator,
            "organization": "AeroGuard — prototipo académico", "truncated": len(records) > 5000,
            "date_from": date_from.isoformat() if date_from else None, "date_to": date_to.isoformat() if date_to else None,
            "ai_verdict": "Sin dictamen visual validado asociado a este reporte.", "incursions": incursions, "audit_records": audit,
            "kpis": {"total_flights": len(incursions), "geofence_violations": sum(row['zone'] != 'Sin zona' for row in incursions),
                     "max_altitude_m": max((row['alt'] for row in incursions if row['alt'] is not None), default=0),
                     "top_sensor": counts.most_common(1)[0][0] if counts else "Sin registros",
                     "critical_threats": sum(row['severity'] == 'CRITICAL' for row in incursions)}}
