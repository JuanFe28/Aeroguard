"""
AeroGuard — SQLAlchemy Models
Definición completa del esquema de base de datos PostgreSQL.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


def utcnow():
    return datetime.now(timezone.utc)

def new_uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


def enum_col(enum_cls, name=None, **kwargs):
    return SAEnum(
        enum_cls,
        values_callable=lambda x: [e.value for e in x],
        name=name or enum_cls.__name__.lower(),
        native_enum=True,
        create_type=False,
        **kwargs
    )


# ============================================================
# Enums
# ============================================================

class UserRole(str, enum.Enum):
    ADMIN    = "admin"
    OPERATOR = "operator"
    ANALYST  = "analyst"

class DetectionStatus(str, enum.Enum):
    ACTIVE    = "active"
    PENDING   = "pending"
    RESOLVED  = "resolved"
    DISCARDED = "discarded"

class ThreatLevel(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class SensorStatus(str, enum.Enum):
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"

class SensorType(str, enum.Enum):
    RADAR    = "radar"
    ACOUSTIC = "acoustic"
    RF       = "rf"
    OPTICAL  = "optical"
    THERMAL  = "thermal"

class AlertType(str, enum.Enum):
    RESTRICTED_ZONE     = "restricted_zone"
    ANOMALOUS_BEHAVIOR  = "anomalous_behavior"
    SYSTEM              = "system"

class AlertStatus(str, enum.Enum):
    OPEN     = "open"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CLOSED   = "closed"

class AlertSeverity(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class ReportType(str, enum.Enum):
    DETECTIONS = "detections"
    ALERTS     = "alerts"
    AUDIT      = "audit"
    SUMMARY    = "summary"

class ReportFormat(str, enum.Enum):
    PDF   = "pdf"
    CSV   = "csv"
    EXCEL = "excel"


# ============================================================
# User Model
# ============================================================

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    first_name    = Column(String(64), nullable=False)
    last_name     = Column(String(64), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(enum_col(UserRole, name="userrole"), nullable=False, default=UserRole.OPERATOR)
    is_active     = Column(Boolean, default=True, nullable=False)
    last_login    = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at    = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    audit_logs    = relationship("AuditLog", back_populates="user", lazy="select")
    reports       = relationship("Report",   back_populates="created_by_user", lazy="select")

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"


# ============================================================
# Sensor Model
# ============================================================

class Sensor(Base):
    __tablename__ = "sensors"

    id               = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name             = Column(String(128), nullable=False)
    type             = Column(enum_col(SensorType, name="sensortype"), nullable=False, default=SensorType.RADAR)
    status           = Column(enum_col(SensorStatus, name="sensorstatus"), nullable=False, default=SensorStatus.ACTIVE)
    latitude         = Column(Float, nullable=False)
    longitude        = Column(Float, nullable=False)
    altitude         = Column(Float, default=0.0)
    range_km         = Column(Float, default=5.0)
    detections_count = Column(Integer, default=0)
    last_active      = Column(DateTime(timezone=True), default=utcnow, nullable=True)
    config           = Column(JSON, default=dict)
    created_at       = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at       = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    detections = relationship("Detection", back_populates="sensor", lazy="select")


# ============================================================
# Restricted Zone Model
# ============================================================

class RestrictedZone(Base):
    __tablename__ = "restricted_zones"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name         = Column(String(128), nullable=False)
    description  = Column(Text, nullable=True)
    threat_level = Column(enum_col(ThreatLevel, name="threatlevel"), nullable=False, default=ThreatLevel.HIGH)
    color        = Column(String(16), default="#ef4444")
    max_altitude = Column(Float, default=500.0)
    min_altitude = Column(Float, default=0.0)
    coordinates  = Column(JSON, default=list)  # [[lat, lng], ...]
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    detections = relationship("Detection", back_populates="zone")

    @property
    def wkt(self) -> str:
        """Representación WKT OGC POLYGON((lng lat, ...)) para PostGIS."""
        from app.services.geospatial_service import geospatial_service
        try:
            return geospatial_service.to_wkt_polygon(self.coordinates or [])
        except Exception:
            return ""

    @property
    def geojson(self) -> dict:
        """Representación GeoJSON Polygon estándar."""
        from app.services.geospatial_service import geospatial_service
        try:
            return geospatial_service.to_geojson_polygon(self.coordinates or [])
        except Exception:
            return {}



# ============================================================
# Detection Model
# ============================================================

class Detection(Base):
    __tablename__ = "detections"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    sensor_id     = Column(UUID(as_uuid=False), ForeignKey("sensors.id"), nullable=True)
    latitude      = Column(Float, nullable=False)
    longitude     = Column(Float, nullable=False)
    altitude      = Column(Float, nullable=False)
    speed         = Column(Float, nullable=False)
    heading       = Column(Float, nullable=False)
    status        = Column(enum_col(DetectionStatus, name="detectionstatus"), nullable=False, default=DetectionStatus.ACTIVE)
    threat_level  = Column(enum_col(ThreatLevel, name="threatlevel"), nullable=False, default=ThreatLevel.LOW)

    # AI Analysis
    ai_analyzed   = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    is_drone      = Column(Boolean, default=False)
    image_url     = Column(String(512), nullable=True)

    # Zone association
    zone_id       = Column(UUID(as_uuid=False), ForeignKey("restricted_zones.id"), nullable=True)
    notes         = Column(Text, nullable=True)

    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at    = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    sensor       = relationship("Sensor", back_populates="detections")
    zone         = relationship("RestrictedZone", back_populates="detections")
    alerts       = relationship("Alert", back_populates="detection")


# ============================================================
# Trajectory Point
# ============================================================

class TrajectoryPoint(Base):
    __tablename__ = "trajectory_points"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    detection_id = Column(UUID(as_uuid=False), ForeignKey("detections.id", ondelete="CASCADE"), nullable=False)
    latitude     = Column(Float, nullable=False)
    longitude    = Column(Float, nullable=False)
    altitude     = Column(Float, nullable=False)
    speed        = Column(Float, nullable=False)
    heading      = Column(Float, nullable=False)
    timestamp    = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    sequence     = Column(Integer, default=0)


# ============================================================
# Alert Model
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    detection_id   = Column(UUID(as_uuid=False), ForeignKey("detections.id"), nullable=True)
    type           = Column(enum_col(AlertType, name="alerttype"), nullable=False, default=AlertType.RESTRICTED_ZONE)
    severity       = Column(enum_col(AlertSeverity, name="alertseverity"), nullable=False, default=AlertSeverity.HIGH)
    status         = Column(enum_col(AlertStatus, name="alertstatus"), nullable=False, default=AlertStatus.OPEN)
    title          = Column(String(255), nullable=False)
    message        = Column(Text, nullable=False)
    assigned_to_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    notes          = Column(Text, nullable=True)
    resolved_at    = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at     = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    detection      = relationship("Detection", back_populates="alerts")


# ============================================================
# Alert Comment
# ============================================================

class AlertComment(Base):
    __tablename__ = "alert_comments"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    alert_id   = Column(UUID(as_uuid=False), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    user_id    = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    comment    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================
# Event
# ============================================================

class Event(Base):
    __tablename__ = "events"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    detection_id = Column(UUID(as_uuid=False), ForeignKey("detections.id"), nullable=True)
    event_type   = Column(String(64), nullable=False)
    description  = Column(Text, nullable=True)
    data         = Column(JSON, default=dict)
    timestamp    = Column(DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================
# Audit Log (RF-027, RF-028, RF-029 — immutable)
# ============================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id     = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    username    = Column(String(64), nullable=False)   # Denormalized for immutability
    action      = Column(String(64), nullable=False)
    resource    = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details     = Column(JSON, default=dict)
    ip_address  = Column(String(45), nullable=True)
    user_agent  = Column(String(512), nullable=True)
    data_hash   = Column(String(64), nullable=False)   # SHA-256 hash
    prev_hash   = Column(String(64), nullable=False, default="")  # Chain link
    timestamp   = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")


# ============================================================
# Report
# ============================================================

class Report(Base):
    __tablename__ = "reports"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    type          = Column(enum_col(ReportType, name="reporttype"), nullable=False)
    format        = Column(enum_col(ReportFormat, name="reportformat"), nullable=False, default=ReportFormat.PDF)
    title         = Column(String(255), nullable=False)
    status        = Column(String(32), default="pending")
    file_url      = Column(String(512), nullable=True)
    file_size     = Column(Integer, nullable=True)
    date_from     = Column(DateTime(timezone=True), nullable=True)
    date_to       = Column(DateTime(timezone=True), nullable=True)
    params        = Column(JSON, default=dict)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at  = Column(DateTime(timezone=True), nullable=True)

    created_by_user = relationship("User", back_populates="reports")


# ============================================================
# Report Schedule
# ============================================================

class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name        = Column(String(128), nullable=False)
    report_type = Column(enum_col(ReportType, name="reporttype"), nullable=False)
    format      = Column(enum_col(ReportFormat, name="reportformat"), nullable=False, default=ReportFormat.PDF)
    cron_expr   = Column(String(64), nullable=False)
    is_active   = Column(Boolean, default=True)
    params      = Column(JSON, default=dict)
    created_by  = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_run    = Column(DateTime(timezone=True), nullable=True)
    next_run    = Column(DateTime(timezone=True), nullable=True)


# ============================================================
# System Config
# ============================================================

class SystemConfig(Base):
    __tablename__ = "system_config"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    key        = Column(String(128), unique=True, nullable=False, index=True)
    value      = Column(JSON, nullable=False)
    category   = Column(String(64), nullable=True)
    updated_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuthState(Base):
    """Revocación por usuario y recuperación de un solo uso, persistente entre reinicios."""
    __tablename__ = "auth_state"
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    version = Column(Integer, nullable=False, default=0)
    reset_digest = Column(String(64), nullable=True)
    reset_expires_at = Column(DateTime(timezone=True), nullable=True)


class AuthAttempt(Base):
    __tablename__ = "auth_attempts"
    key = Column(String(64), primary_key=True)
    bucket = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False, default=1)


class AuditCheckpoint(Base):
    __tablename__ = "audit_checkpoint"
    id = Column(Integer, primary_key=True)
    head = Column(String(64), nullable=False)
    records = Column(Integer, nullable=False, default=0)


class SensorTrack(Base):
    __tablename__ = "sensor_tracks"
    sensor_id = Column(UUID(as_uuid=False), ForeignKey("sensors.id", ondelete="CASCADE"), primary_key=True)
    object_key = Column(String(128), primary_key=True)
    detection_id = Column(UUID(as_uuid=False), ForeignKey("detections.id", ondelete="CASCADE"), nullable=False)
