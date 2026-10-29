import { safeColor } from '../utils/html.js';
/**
 * AeroGuard — Models (MVVM - Model Layer)
 * Representa las estructuras de datos del dominio.
 */

// ============================================================
// User & Auth Models
// ============================================================

export class UserModel {
  constructor(data = {}) {
    this.id          = data.id || null;
    this.username    = data.username || '';
    this.email       = data.email || '';
    this.firstName   = data.first_name || data.firstName || '';
    this.lastName    = data.last_name  || data.lastName  || '';
    this.role        = data.role || 'operator';
    this.isActive    = data.is_active ?? data.isActive ?? true;
    this.lastLogin   = data.last_login || data.lastLogin || null;
    this.createdAt   = data.created_at || data.createdAt || null;
    this.avatar      = data.avatar || null;
  }

  get fullName() { return `${this.firstName} ${this.lastName}`.trim() || this.username; }
  get initials() {
    const parts = this.fullName.split(' ');
    return parts.length >= 2
      ? `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      : this.fullName.slice(0, 2).toUpperCase();
  }
  get roleLabel() {
    const labels = { admin: 'Administrador', operator: 'Operador de Seguridad', analyst: 'Analista/Auditor' };
    return labels[this.role] || this.role;
  }
}

export class AuthTokenModel {
  constructor(data = {}) {
    this.accessToken  = data.access_token  || data.accessToken  || '';
    this.refreshToken = data.refresh_token || data.refreshToken || '';
    this.tokenType    = data.token_type    || data.tokenType    || 'bearer';
    this.expiresIn    = data.expires_in    || data.expiresIn    || 3600;
    this.expiresAt    = data.expires_at    || Date.now() + (this.expiresIn * 1000);
  }
  get isExpired() { return Date.now() >= this.expiresAt; }
}

// ============================================================
// Detection Models
// ============================================================

export const DetectionStatus = {
  ACTIVE:    'active',
  RESOLVED:  'resolved',
  PENDING:   'pending',
  DISCARDED: 'discarded',
};

export const ThreatLevel = {
  LOW:      'low',
  MEDIUM:   'medium',
  HIGH:     'high',
  CRITICAL: 'critical',
};

export class DetectionModel {
  constructor(data = {}) {
    this.id             = data.id || null;
    this.sensorId       = data.sensor_id    || data.sensorId    || null;
    this.sensorName     = data.sensor_name  || data.sensorName  || '';
    this.latitude       = data.latitude     || 0;
    this.longitude      = data.longitude    || 0;
    this.altitude       = data.altitude     || 0;     // metros
    this.speed          = data.speed        || 0;     // km/h
    this.heading        = data.heading      || 0;     // grados 0-360
    this.status         = data.status       || DetectionStatus.ACTIVE;
    this.threatLevel    = data.threat_level || data.threatLevel || ThreatLevel.LOW;
    this.aiAnalyzed     = data.ai_analyzed  || data.aiAnalyzed  || false;
    this.aiConfidence   = data.ai_confidence ?? data.aiConfidence ?? null;
    this.isDrone        = data.is_drone     || data.isDrone     || false;
    this.timestamp      = data.timestamp || data.created_at || new Date().toISOString();
    this.updatedAt      = data.updated_at   || data.updatedAt   || null;
    this.trajectory     = data.trajectory   || [];
    this.alerts         = data.alerts       || [];
    this.imageUrl       = data.image_url    || data.imageUrl    || null;
    this.zoneId         = data.zone_id      || data.zoneId      || null;
    this.zoneName       = data.zone_name    || data.zoneName    || null;
    this.hash           = data.hash         || null;
  }

  get threatBadgeClass() {
    const map = {
      [ThreatLevel.LOW]:      'badge-low',
      [ThreatLevel.MEDIUM]:   'badge-medium',
      [ThreatLevel.HIGH]:     'badge-high',
      [ThreatLevel.CRITICAL]: 'badge-critical',
    };
    return map[this.threatLevel] || 'badge-neutral';
  }

  get statusBadgeClass() {
    const map = {
      [DetectionStatus.ACTIVE]:    'badge-danger',
      [DetectionStatus.PENDING]:   'badge-warning',
      [DetectionStatus.RESOLVED]:  'badge-success',
      [DetectionStatus.DISCARDED]: 'badge-neutral',
    };
    return map[this.status] || 'badge-neutral';
  }

  get formattedAltitude() { return `${this.altitude.toFixed(0)} m`; }
  get formattedSpeed()    { return `${this.speed.toFixed(1)} km/h`; }
  get formattedHeading()  {
    const dirs = ['N','NE','E','SE','S','SO','O','NO'];
    return dirs[Math.round(this.heading / 45) % 8];
  }
  get confidencePercent() {
    return this.aiConfidence !== null ? `${(this.aiConfidence * 100).toFixed(1)}%` : 'N/A';
  }
  get formattedTime() {
    return new Date(this.timestamp).toLocaleString('es-CO', {
      dateStyle: 'short', timeStyle: 'medium'
    });
  }
}

// ============================================================
// Sensor Models
// ============================================================

export const SensorStatus = {
  ACTIVE:   'active',
  INACTIVE: 'inactive',
  ERROR:    'error',
};

export const SensorType = {
  RADAR:    'radar',
  ACOUSTIC: 'acoustic',
  RF:       'rf',
  OPTICAL:  'optical',
  THERMAL:  'thermal',
};

export class SensorModel {
  constructor(data = {}) {
    this.id          = data.id       || null;
    this.name        = data.name     || '';
    this.type        = data.type     || SensorType.RADAR;
    this.status      = data.status   || SensorStatus.INACTIVE;
    this.latitude    = data.latitude  || 0;
    this.longitude   = data.longitude || 0;
    this.altitude    = data.altitude  || 0;
    this.rangeKm     = data.range_km  || data.rangeKm || 5;
    this.detectionsCount = data.detections_count || data.detectionsCount || 0;
    this.lastActive  = data.last_active || data.lastActive || null;
    this.config      = data.config   || {};
    this.createdAt   = data.created_at || data.createdAt || null;
  }

  get typeLabel() {
    const labels = {
      [SensorType.RADAR]:    'Radar',
      [SensorType.ACOUSTIC]: 'Acústico',
      [SensorType.RF]:       'RF',
      [SensorType.OPTICAL]:  'Óptico',
      [SensorType.THERMAL]:  'Térmico',
    };
    return labels[this.type] || this.type;
  }

  get typeIcon() {
    const icons = {
      [SensorType.RADAR]:    '📡',
      [SensorType.ACOUSTIC]: '🎙️',
      [SensorType.RF]:       '📻',
      [SensorType.OPTICAL]:  '📷',
      [SensorType.THERMAL]:  '🌡️',
    };
    return icons[this.type] || '⚙️';
  }
}

// ============================================================
// Alert Models
// ============================================================

export const AlertType = {
  RESTRICTED_ZONE: 'restricted_zone',
  ANOMALOUS_BEHAVIOR: 'anomalous_behavior',
  SYSTEM: 'system',
};

export const AlertStatus = {
  OPEN:     'open',
  ASSIGNED: 'assigned',
  RESOLVED: 'resolved',
  CLOSED:   'closed',
};

export const AlertSeverity = {
  LOW:      'low',
  MEDIUM:   'medium',
  HIGH:     'high',
  CRITICAL: 'critical',
};

export class AlertModel {
  constructor(data = {}) {
    this.id           = data.id           || null;
    this.type         = data.type         || AlertType.SYSTEM;
    this.severity     = data.severity     || AlertSeverity.MEDIUM;
    this.status       = data.status       || AlertStatus.OPEN;
    this.title        = data.title        || '';
    this.description  = data.description ?? data.message ?? '';
    this.detectionId  = data.detection_id || data.detectionId || null;
    this.zoneId       = data.zone_id      || data.zoneId      || null;
    this.zoneName     = data.zone_name    || data.zoneName    || null;
    this.assignedTo   = data.assigned_to  || data.assignedTo  || null;
    this.resolvedAt   = data.resolved_at  || data.resolvedAt  || null;
    this.comments     = data.comments     || [];
    this.createdAt    = data.created_at   || data.createdAt   || new Date().toISOString();
    this.latitude     = data.latitude     || null;
    this.longitude    = data.longitude    || null;
  }

  get severityClass() {
    const map = {
      [AlertSeverity.LOW]:      'badge-low',
      [AlertSeverity.MEDIUM]:   'badge-medium',
      [AlertSeverity.HIGH]:     'badge-high',
      [AlertSeverity.CRITICAL]: 'badge-critical',
    };
    return map[this.severity] || 'badge-neutral';
  }

  get severityIcon() {
    const icons = {
      [AlertSeverity.LOW]:      '🔵',
      [AlertSeverity.MEDIUM]:   '🟡',
      [AlertSeverity.HIGH]:     '🟠',
      [AlertSeverity.CRITICAL]: '🔴',
    };
    return icons[this.severity] || '⚪';
  }

  get typeLabel() {
    const labels = {
      [AlertType.RESTRICTED_ZONE]:    'Zona Restringida',
      [AlertType.ANOMALOUS_BEHAVIOR]: 'Comportamiento Anómalo',
      [AlertType.SYSTEM]:             'Sistema',
    };
    return labels[this.type] || this.type;
  }

  get formattedTime() {
    return new Date(this.createdAt).toLocaleString('es-CO', {
      dateStyle: 'short', timeStyle: 'medium'
    });
  }
}

// ============================================================
// Restricted Zone Model
// ============================================================

export class RestrictedZoneModel {
  constructor(data = {}) {
    this.id          = data.id           || null;
    this.name        = data.name         || '';
    this.description = data.description  || '';
    this.polygon     = data.polygon      || data.coordinates || [];  // Array de {lat, lng} o [lat, lng]
    this.minAltitude = data.min_altitude || data.minAltitude || 0;
    this.maxAltitude = data.max_altitude ?? data.maxAltitude ?? 500;
    this.severity    = data.threat_level || data.severity     || AlertSeverity.HIGH;
    this.isActive    = data.is_active    ?? data.isActive ?? true;
    this.color       = data.color        || '#ff1744';
    this.createdAt   = data.created_at   || data.createdAt || null;
    this.updatedAt   = data.updated_at   || data.updatedAt || null;
    this.createdBy   = data.created_by   || data.createdBy || null;
  }

  get bounds() {
    if (!this.polygon.length) return null;
    const lats = this.polygon.map(p => p.lat || p[0]);
    const lngs = this.polygon.map(p => p.lng || p[1]);
    return {
      north: Math.max(...lats), south: Math.min(...lats),
      east:  Math.max(...lngs), west:  Math.min(...lngs),
    };
  }

  get center() {
    if (!this.polygon.length) return null;
    const lats = this.polygon.map(p => p.lat || p[0]);
    const lngs = this.polygon.map(p => p.lng || p[1]);
    return {
      lat: (Math.max(...lats) + Math.min(...lats)) / 2,
      lng: (Math.max(...lngs) + Math.min(...lngs)) / 2,
    };
  }

  get severityColor() {
    const colors = {
      [AlertSeverity.LOW]:      '#00e676',
      [AlertSeverity.MEDIUM]:   '#ffb300',
      [AlertSeverity.HIGH]:     '#ff6d00',
      [AlertSeverity.CRITICAL]: '#ff1744',
    };
    return colors[this.severity] || safeColor(this.color);
  }
}

// ============================================================
// Report Model
// ============================================================

export const ReportType = {
  DETECTIONS: 'detections',
  ALERTS:     'alerts',
  AUDIT:      'audit',
  SUMMARY:    'summary',
};

export const ReportFormat = {
  PDF:   'pdf',
  CSV:   'csv',
  EXCEL: 'excel',
};

export class ReportModel {
  constructor(data = {}) {
    this.id         = data.id         || null;
    this.type       = data.type       || ReportType.DETECTIONS;
    this.format     = data.format     || ReportFormat.PDF;
    this.title      = data.title      || '';
    this.status     = data.status     || 'pending';
    this.fileUrl    = data.file_url   || data.fileUrl || null;
    this.fileSize   = data.file_size  || data.fileSize || null;
    this.dateFrom   = data.date_from  || data.dateFrom || null;
    this.dateTo     = data.date_to    || data.dateTo   || null;
    this.createdAt  = data.created_at || data.createdAt || null;
    this.createdBy  = data.created_by || data.createdBy || null;
    this.params     = data.params     || {};
  }
}

// ============================================================
// Audit Log Model
// ============================================================

export class AuditLogModel {
  constructor(data = {}) {
    this.id         = data.id          || null;
    this.userId     = data.user_id     || data.userId     || null;
    this.username   = data.username    || '';
    this.action     = data.action      || '';
    this.resource   = data.resource    || '';
    this.resourceId = data.resource_id || data.resourceId || null;
    this.details    = data.details     || {};
    this.ip         = data.ip || data.ip_address || '';
    this.userAgent  = data.user_agent  || data.userAgent  || '';
    this.timestamp  = data.timestamp   || new Date().toISOString();
    this.hash       = data.hash || data.data_hash || '';
    this.prevHash   = data.prev_hash   || data.prevHash   || '';
    this.integrityOk = data.integrity_ok ?? data.integrityOk ?? null;
  }

  get formattedTime() {
    return new Date(this.timestamp).toLocaleString('es-CO', {
      dateStyle: 'short', timeStyle: 'medium'
    });
  }
}

// ============================================================
// Telemetry (sensor data packet)
// ============================================================

export class TelemetryModel {
  constructor(data = {}) {
    this.sensorId   = data.sensor_id   || data.sensorId   || '';
    this.latitude   = data.latitude    || 0;
    this.longitude  = data.longitude   || 0;
    this.altitude   = data.altitude    || 0;
    this.speed      = data.speed       || 0;
    this.heading    = data.heading     || 0;
    this.timestamp  = data.timestamp   || new Date().toISOString();
    this.raw        = data;
  }
}

// ============================================================
// Detection Config
// ============================================================

export class DetectionConfigModel {
  constructor(data = {}) {
    this.minConfidence     = data.min_confidence     || data.minConfidence     || 0.7;
    this.maxAltitude       = data.max_altitude       || data.maxAltitude       || 1000;
    this.minSpeed          = data.min_speed          || data.minSpeed          || 0;
    this.maxSpeed          = data.max_speed          || data.maxSpeed          || 300;
    this.anomalyThreshold  = data.anomaly_threshold  || data.anomalyThreshold  || 2.5;
    this.processingEnabled = data.processing_enabled ?? data.processingEnabled ?? true;
    this.aiEnabled         = data.ai_enabled         ?? data.aiEnabled         ?? true;
    this.alertEnabled      = data.alert_enabled      ?? data.alertEnabled      ?? true;
  }
}
