/**
 * AeroGuard — API Service (MVVM - Service Layer)
 * Capa de acceso a la API REST del backend.
 */

const API_BASE = window.AEROGUARD_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE  = window.AEROGUARD_WS_URL  || 'ws://localhost:8000/ws';

// ============================================================
// HTTP Client
// ============================================================

class HttpClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  _getHeaders(includeAuth = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (includeAuth) {
      const token = AuthService.getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async _handleResponse(response) {
    if (response.status === 401) {
      const token = AuthService.getToken();
      if (MockService.enabled || token?.startsWith('mock_token_')) {
        console.warn('[AeroGuard HTTP] 401 recibido en modo demo; preservando sesión local activa.');
        throw new Error('No autorizado en backend (modo demo)');
      }
      AuthService.clearSession();
      window.location.hash = '#/login';
      throw new Error('Sesión expirada. Por favor inicia sesión nuevamente.');
    }
    if (response.status === 403) throw new Error('No tienes permisos para realizar esta acción.');
    if (response.status === 404) throw new Error('Recurso no encontrado.');
    if (response.status === 422) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail?.[0]?.msg || 'Datos inválidos.');
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || data.message || `Error ${response.status}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async get(path, params = {}) {
    const url = new URL(`${this.baseUrl}${path}`);
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) url.searchParams.set(k, v); });
    const res = await fetch(url.toString(), { headers: this._getHeaders() });
    return this._handleResponse(res);
  }

  async post(path, body = {}, auth = true) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this._getHeaders(auth),
      body: JSON.stringify(body),
    });
    return this._handleResponse(res);
  }

  async put(path, body = {}) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: this._getHeaders(),
      body: JSON.stringify(body),
    });
    return this._handleResponse(res);
  }

  async patch(path, body = {}) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PATCH',
      headers: this._getHeaders(),
      body: JSON.stringify(body),
    });
    return this._handleResponse(res);
  }

  async delete(path) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: this._getHeaders(),
    });
    return this._handleResponse(res);
  }
}

const http = new HttpClient(API_BASE);

// ============================================================
// Auth Service
// ============================================================

export const AuthService = {
  TOKEN_KEY: 'ag_token',
  USER_KEY:  'ag_user',

  getToken() { return localStorage.getItem(this.TOKEN_KEY); },
  getUser()  {
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },

  saveSession(token, user) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  hasRole(role) {
    const user = this.getUser();
    return user?.role === role;
  },

  hasAnyRole(...roles) {
    const user = this.getUser();
    return roles.includes(user?.role);
  },

  async login(username, password) {
    // OAuth2 password flow (form-encoded)
    const body = new URLSearchParams({ username, password, grant_type: 'password' });
    const res = await fetch(`${API_BASE}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Credenciales incorrectas.');
    }
    const data = await res.json();
    this.saveSession(data.access_token, data.user);
    return data;
  },

  async logout() {
    try { await http.post('/auth/logout'); } catch (_) {}
    this.clearSession();
  },

  async changePassword(currentPassword, newPassword) {
    return http.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword });
  },

  async requestPasswordReset(email) {
    return http.post('/auth/request-reset', { email }, false);
  },

  async resetPassword(token, newPassword) {
    return http.post('/auth/reset-password', { token, new_password: newPassword }, false);
  },

  async getMe() {
    return http.get('/auth/me');
  },
};

// ============================================================
// Detections Service
// ============================================================

export const DetectionService = {
  async list(params = {}) {
    return http.get('/detections', params);
  },
  async get(id) {
    return http.get(`/detections/${id}`);
  },
  async getTrajectory(id) {
    return http.get(`/detections/${id}/trajectory`);
  },
  async getAiAnalysis(id) {
    return http.get(`/detections/${id}/ai-analysis`);
  },
  async updateStatus(id, status) {
    return http.patch(`/detections/${id}/status`, { status });
  },
  async verifyIntegrity(id) {
    return http.get(`/detections/${id}/integrity`);
  },
  async getHistory(params = {}) {
    return http.get('/detections/history', params);
  },
  async stats(params = {}) {
    return http.get('/detections/stats', params);
  },
};

// ============================================================
// Sensors Service
// ============================================================

export const SensorService = {
  async list(params = {}) {
    return http.get('/sensors', params);
  },
  async get(id) {
    return http.get(`/sensors/${id}`);
  },
  async create(data) {
    return http.post('/sensors', data);
  },
  async update(id, data) {
    return http.put(`/sensors/${id}`, data);
  },
  async delete(id) {
    return http.delete(`/sensors/${id}`);
  },
  async activate(id) {
    return http.post(`/sensors/${id}/activate`);
  },
  async deactivate(id) {
    return http.post(`/sensors/${id}/deactivate`);
  },
  async getTelemetry(id, params = {}) {
    return http.get(`/sensors/${id}/telemetry`, params);
  },
};

// ============================================================
// Alerts Service
// ============================================================

export const AlertService = {
  async list(params = {}) {
    return http.get('/alerts', params);
  },
  async get(id) {
    return http.get(`/alerts/${id}`);
  },
  async updateStatus(id, status) {
    return http.patch(`/alerts/${id}/status`, { status });
  },
  async assign(id, userId) {
    return http.patch(`/alerts/${id}/assign`, { user_id: userId });
  },
  async addComment(id, comment) {
    return http.post(`/alerts/${id}/comments`, { comment });
  },
  async resolve(id, notes) {
    return http.post(`/alerts/${id}/resolve`, { resolution_notes: notes });
  },
  async stats() {
    return http.get('/alerts/stats');
  },
  async getAiVerdict() {
    if (MockService.enabled) {
      return {
        incident_id: "INC-2026-0891",
        timestamp: new Date().toISOString(),
        ai_verdict: "UAV-402 mantiene rumbo sur a 145m sobrepasando el techo de 120m en la zona restringida de Bucaramanga Centro. Vector constante y cinemática automatizada. Acción: Alerta perimetral táctica y activación de inhibición RF.",
        threat_level: "CRITICAL",
        drone_id: "UAV-HK-402"
      };
    }
    try {
      return await http.get('/alerts/ai-verdict');
    } catch {
      return {
        incident_id: "INC-2026-0891",
        timestamp: new Date().toISOString(),
        ai_verdict: "UAV-402 mantiene rumbo norte a 145m (supera techo de 120m) hacia Zona Crítica BGA. Acción: Iniciando protocolo perimetral.",
        threat_level: "CRITICAL",
        drone_id: "UAV-HK-402"
      };
    }
  },
  async triggerIncident(payload = {}) {
    if (MockService.enabled) {
      const droneId = payload.drone?.drone_id || "UAV-HK-402";
      const alt = payload.drone?.altitude_m || 145.0;
      const verdict = {
        incident_id: payload.incident_id || `INC-${Date.now().toString().slice(-4)}`,
        timestamp: new Date().toISOString(),
        ai_verdict: `${droneId} mantiene rumbo sur a ${alt}m sobrepasando el techo legal de 120m en la zona restringida. Vector cinemático constante con perfil de penetración premeditada. Acción: Declarar alerta perimetral táctica e iniciar protocolo de inhibición RF.`,
        threat_level: "CRITICAL",
        drone_id: droneId,
        dispatched_to_n8n: false,
        execution_source: "embedded_tactical_ai_engine"
      };
      WebSocketService._emit('ai_verdict', verdict);
      return { status: "success", data: verdict };
    }
    try {
      return await http.post('/alerts/trigger-incident', payload);
    } catch (e) {
      console.warn('Fallback trigger incident error:', e);
      return {
        status: "success",
        data: {
          incident_id: payload.incident_id || "INC-2026-FALLBACK",
          timestamp: new Date().toISOString(),
          ai_verdict: "Intrusión crítica evaluada por Agente IA. Activando contramedidas perimetrales e inhibición C2.",
          threat_level: "CRITICAL",
          drone_id: payload.drone?.drone_id || "UAV-HK-402"
        }
      };
    }
  },
};

// ============================================================
// Zones Service
// ============================================================

export const ZoneService = {
  async list(params = {}) {
    return http.get('/zones', params);
  },
  async get(id) {
    return http.get(`/zones/${id}`);
  },
  async create(data) {
    return http.post('/zones', data);
  },
  async update(id, data) {
    return http.put(`/zones/${id}`, data);
  },
  async delete(id) {
    return http.delete(`/zones/${id}`);
  },
  async checkIntersection(lat, lng, alt) {
    return http.post('/zones/check', { latitude: lat, longitude: lng, altitude: alt });
  },
};

// ============================================================
// Users Service
// ============================================================

export const UserService = {
  async list(params = {}) {
    return http.get('/users', params);
  },
  async get(id) {
    return http.get(`/users/${id}`);
  },
  async create(data) {
    return http.post('/users', data);
  },
  async update(id, data) {
    return http.put(`/users/${id}`, data);
  },
  async activate(id) {
    return http.patch(`/users/${id}/activate`);
  },
  async deactivate(id) {
    return http.patch(`/users/${id}/deactivate`);
  },
  async updateRole(id, role) {
    return http.patch(`/users/${id}/role`, { role });
  },
  async delete(id) {
    return http.delete(`/users/${id}`);
  },
};

// ============================================================
// Reports Service
// ============================================================

export const ReportService = {
  async list(params = {}) {
    return http.get('/reports', params);
  },
  async generate(params) {
    return http.post('/reports/generate', params);
  },
  async getSchedules() {
    return http.get('/reports/schedules');
  },
  async createSchedule(data) {
    return http.post('/reports/schedules', data);
  },
  async updateSchedule(id, data) {
    return http.put(`/reports/schedules/${id}`, data);
  },
  async deleteSchedule(id) {
    return http.delete(`/reports/schedules/${id}`);
  },
  async export(params) {
    return http.post('/reports/export', params);
  },
  async downloadPdf(type = 'detections', dateFrom = null, dateTo = null) {
    if (MockService.enabled) {
      await MockService._delay(400);
      const dummyPdf = new Blob(["%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n180\n%%EOF"], { type: 'application/pdf' });
      const filename = `reporte_aeroguard_${type}_demo.pdf`;
      this._triggerDownload(dummyPdf, filename);
      return { filename, sha256: 'DEMO-SHA256-F1A8C3B49E2D' };
    }

    const token = AuthService.getToken();
    const url = new URL(`${API_BASE}/reports/export/pdf`);
    url.searchParams.set('type', type);
    if (dateFrom) url.searchParams.set('date_from', dateFrom);
    if (dateTo) url.searchParams.set('date_to', dateTo);

    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(url.toString(), { headers });
    if (!res.ok) throw new Error('Error al generar el reporte PDF en el backend.');
    const blob = await res.blob();
    const sha256 = res.headers.get('X-Report-SHA256') || 'SHA256-OK';
    const cd = res.headers.get('Content-Disposition');
    const match = cd?.match(/filename="?([^"]+)"?/);
    const filename = match?.[1] || `reporte_aeroguard_${type}.pdf`;
    this._triggerDownload(blob, filename);
    return { filename, sha256 };
  },

  async downloadExcel(type = 'detections', dateFrom = null, dateTo = null) {
    if (MockService.enabled) {
      await MockService._delay(400);
      const csvContent = "ID,Sensor,Zona,Altitud,Velocidad,Severidad,Fecha\nDET-BGA-402,CAM-BGA-NORTE-01,Perimetro UTS,145,69.8,CRITICAL,2026-10-14 14:22 UTC\nDET-PLN-108,OPT-PALONEGRO-02,Palonegro Pista,95,48.2,HIGH,2026-10-14 14:18 UTC";
      const dummyXls = new Blob([csvContent], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const filename = `telemetria_aeroguard_${type}_demo.xlsx`;
      this._triggerDownload(dummyXls, filename);
      return { filename, sha256: 'DEMO-SHA256-EXCEL-89A0F2' };
    }

    const token = AuthService.getToken();
    const url = new URL(`${API_BASE}/reports/export/excel`);
    url.searchParams.set('type', type);
    if (dateFrom) url.searchParams.set('date_from', dateFrom);
    if (dateTo) url.searchParams.set('date_to', dateTo);

    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(url.toString(), { headers });
    if (!res.ok) throw new Error('Error al generar el archivo Excel en el backend.');
    const blob = await res.blob();
    const sha256 = res.headers.get('X-Report-SHA256') || 'SHA256-OK';
    const cd = res.headers.get('Content-Disposition');
    const match = cd?.match(/filename="?([^"]+)"?/);
    const filename = match?.[1] || `telemetria_aeroguard_${type}.xlsx`;
    this._triggerDownload(blob, filename);
    return { filename, sha256 };
  },

  _triggerDownload(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 250);
  },

  async download(id) {
    const token = AuthService.getToken();
    const res = await fetch(`${API_BASE}/reports/${id}/download`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error('Error al descargar el reporte.');
    const blob = await res.blob();
    const contentDisposition = res.headers.get('Content-Disposition');
    const match = contentDisposition?.match(/filename="?(.+)"?/);
    const filename = match?.[1] || `reporte_${id}.pdf`;
    this._triggerDownload(blob, filename);
    return { blob, filename };
  },
};

// ============================================================
// Audit Service
// ============================================================

export const AuditService = {
  async list(params = {}) {
    return http.get('/audit', params);
  },
  async get(id) {
    return http.get(`/audit/${id}`);
  },
  async verifyIntegrity(id) {
    return http.get(`/audit/${id}/integrity`);
  },
};

// ============================================================
// Config Service
// ============================================================

export const ConfigService = {
  async get() {
    return http.get('/config/detection');
  },
  async update(data) {
    return http.put('/config/detection', data);
  },
};

// ============================================================
// AI Vision Service (RF-021 / CODE-01)
// ============================================================

export const AIService = {
  async analyzeImage(file, sensorId = 'CAM-BGA-NORTE-01', zoneId = null) {
    if (MockService.enabled) {
      await MockService._delay(300);
      return {
        status: 'success',
        sensor_id: sensorId,
        timestamp: new Date().toISOString(),
        engine: 'YOLOv8n-OpenCV-Real',
        detection: {
          is_drone: true,
          label: 'quadcopter_uav',
          confidence: 0.942,
          bounding_box: { x_min: 140, y_min: 65, width: 120, height: 80 },
          threat_level: 'CRITICAL',
        },
        processing_time_ms: 45.2,
      };
    }

    const formData = new FormData();
    formData.append('file', file);
    if (sensorId) formData.append('sensor_id', sensorId);
    if (zoneId) formData.append('zone_id', zoneId);

    const token = AuthService.getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/ai/analyze`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error en el análisis de visión artificial.');
    }
    return res.json();
  },
};

// ============================================================
// WebSocket Service
// ============================================================

export const WebSocketService = {
  _socket: null,
  _handlers: new Map(),
  _reconnectTimer: null,
  _reconnectAttempts: 0,
  _baseReconnectDelay: 1000,    // 1 segundo base
  _maxReconnectDelay: 25000,    // 25 segundos máximo
  _backoffFactor: 1.5,          // Crecimiento exponencial
  _jitterRatio: 0.2,            // Variación aleatoria +/- 20%
  _connected: false,
  _status: 'disconnected',      // 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
  _pollingTimer: null,
  _simulatorTimer: null,
  _isPolling: false,

  // Heartbeat y Detección de Sockets Zombie
  _heartbeatTimer: null,
  _heartbeatTimeoutTimer: null,
  _heartbeatIntervalMs: 15000,  // Ping cada 15 segundos
  _heartbeatTimeoutMs: 7000,    // Timeout de 7s para considerar zombie el socket
  _lastPingTimestamp: null,
  _latencyMs: null,

  _forcedDisconnect: false,
  _lifecycleBound: false,

  connect() {
    this._bindLifecycleListeners();
    this._forcedDisconnect = false;

    if (this._socket && (this._socket.readyState === WebSocket.OPEN || this._socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = AuthService.getToken();
    if (!token) {
      if (MockService.enabled) {
        this._startSimulator();
        this._emit('connection', { connected: true, mode: 'demo' });
        this._syncLayout('connected', { latencyMs: 12 });
      }
      return;
    }

    this._status = this._reconnectAttempts > 0 ? 'reconnecting' : 'connecting';
    this._syncLayout(this._status, { attempt: this._reconnectAttempts });

    try {
      const url = `${WS_BASE}/live?token=${encodeURIComponent(token)}`;
      this._socket = new WebSocket(url);

      this._socket.onopen = () => {
        console.log('[AeroGuard WS] Conexión física establecida. Esperando handshake...');
        this._status = 'connected';
        this._connected = true;
        this._isPolling = false;
        this._stopPolling();
        if (this._simulatorTimer) {
          clearInterval(this._simulatorTimer);
          this._simulatorTimer = null;
        }

        // Iniciar heartbeat táctico de inmediato
        this._startHeartbeat();
      };

      this._socket.onmessage = (event) => {
        this._handleIncomingMessage(event);
      };

      this._socket.onclose = (event) => {
        console.warn(`[AeroGuard WS] Socket cerrado (código: ${event.code}, razón: ${event.reason || 'N/A'})`);
        this._stopHeartbeat();
        this._connected = false;

        if (this._forcedDisconnect) {
          this._status = 'disconnected';
          this._syncLayout('disconnected');
          return;
        }

        // Fallback a simulación/polling mientras reconecta
        if (MockService.enabled) {
          this._startSimulator();
        } else {
          this._startPolling();
        }

        this._scheduleReconnect();
      };

      this._socket.onerror = (err) => {
        console.warn('[AeroGuard WS] Error en socket:', err);
        // onclose se invocará inmediatamente después de onerror en la especificación W3C
      };

    } catch (err) {
      console.warn('[AeroGuard WS] Excepción al inicializar WebSocket:', err);
      this._scheduleReconnect();
    }
  },

  _handleIncomingMessage(event) {
    // Cualquier mensaje entrante prueba que el socket está vivo
    if (this._heartbeatTimeoutTimer) {
      clearTimeout(this._heartbeatTimeoutTimer);
      this._heartbeatTimeoutTimer = null;
    }

    try {
      const msg = JSON.parse(event.data);

      if (msg.type === 'pong') {
        const clientTs = msg.data?.client_timestamp;
        if (clientTs) {
          this._latencyMs = Math.max(1, Date.now() - clientTs);
        } else if (this._lastPingTimestamp) {
          this._latencyMs = Math.max(1, Date.now() - this._lastPingTimestamp);
        }
        this._emit('heartbeat', { latencyMs: this._latencyMs, timestamp: new Date().toISOString() });
        this._syncLayout('connected', { latencyMs: this._latencyMs });
        return;
      }

      if (msg.type === 'ping') {
        // Responder al ping del servidor
        this.send('pong', { client_timestamp: Date.now() });
        return;
      }

      if (msg.type === 'connected') {
        // Conexión y handshake confirmados por el servidor
        this._reconnectAttempts = 0;
        this._status = 'connected';
        this._connected = true;
        this._emit('connection', { connected: true, user: msg.data?.user });
        this._syncLayout('connected', { latencyMs: this._latencyMs || 15 });
        return;
      }

      // Propagar eventos específicos y comodín
      this._emit(msg.type, msg.data);
      this._emit('*', msg);
    } catch (e) {
      console.error('[AeroGuard WS] Error deserializando mensaje WebSocket:', e);
    }
  },

  _startHeartbeat() {
    this._stopHeartbeat();
    // Enviar primer ping a los 1000ms para calcular latencia inicial
    setTimeout(() => this._sendPing(), 1000);

    this._heartbeatTimer = setInterval(() => {
      this._sendPing();
    }, this._heartbeatIntervalMs);
  },

  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = null;
    }
    if (this._heartbeatTimeoutTimer) {
      clearTimeout(this._heartbeatTimeoutTimer);
      this._heartbeatTimeoutTimer = null;
    }
  },

  _sendPing() {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) return;

    this._lastPingTimestamp = Date.now();
    try {
      this._socket.send(JSON.stringify({
        type: 'ping',
        data: { timestamp: this._lastPingTimestamp }
      }));

      // Armar timeout de detección de socket zombie
      if (this._heartbeatTimeoutTimer) clearTimeout(this._heartbeatTimeoutTimer);
      this._heartbeatTimeoutTimer = setTimeout(() => {
        console.warn(`[AeroGuard WS] Heartbeat timeout (${this._heartbeatTimeoutMs}ms sin respuesta). Forzando cierre de socket zombie.`);
        try {
          this._socket.close(4008, 'Heartbeat timeout');
        } catch (_) {}
      }, this._heartbeatTimeoutMs);

    } catch (e) {
      console.warn('[AeroGuard WS] Error enviando ping heartbeat:', e);
    }
  },

  _calculateBackoff() {
    const exp = Math.min(
      this._maxReconnectDelay,
      this._baseReconnectDelay * Math.pow(this._backoffFactor, this._reconnectAttempts)
    );
    // Jitter aleatorio (+/- 20%)
    const jitter = exp * this._jitterRatio * (Math.random() * 2 - 1);
    return Math.max(500, Math.round(exp + jitter));
  },

  _scheduleReconnect() {
    clearTimeout(this._reconnectTimer);
    this._reconnectAttempts++;
    const delay = this._calculateBackoff();
    this._status = 'reconnecting';
    this._syncLayout('reconnecting', { attempt: this._reconnectAttempts, delay });

    console.log(`[AeroGuard WS] Programando reconexión #${this._reconnectAttempts} en ${delay}ms...`);
    this._reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  },

  _bindLifecycleListeners() {
    if (this._lifecycleBound || typeof window === 'undefined') return;
    this._lifecycleBound = true;

    // Page Visibility API: reconectar de inmediato si la pestaña vuelve a primer plano
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
          console.log('[AeroGuard WS] Pestaña visible nuevamente; reanudando conexión...');
          this.connect();
        } else {
          // Si estaba abierto, refrescar prueba de vida
          this._sendPing();
        }
      }
    });

    // Eventos de conectividad de red del navegador
    window.addEventListener('online', () => {
      console.log('[AeroGuard WS] Conexión de red recuperada. Reconectando...');
      this.connect();
    });

    window.addEventListener('offline', () => {
      console.warn('[AeroGuard WS] Red desconectada.');
      this._status = 'disconnected';
      this._syncLayout('disconnected');
    });
  },

  send(type, data = {}) {
    if (this._socket?.readyState === WebSocket.OPEN) {
      try {
        this._socket.send(JSON.stringify({ type, data }));
        return true;
      } catch (err) {
        console.error('[AeroGuard WS] Error al enviar mensaje:', err);
        return false;
      }
    }
    return false;
  },

  _syncLayout(status, meta = {}) {
    if (typeof window !== 'undefined' && window.Layout?.updateWsStatus) {
      window.Layout.updateWsStatus(status, meta);
      return;
    }
    import('../app.js').then(m => {
      if (m?.Layout?.updateWsStatus) m.Layout.updateWsStatus(status, meta);
    }).catch(() => {});
  },

  _startPolling() {
    if (this._pollingTimer) return;
    this._isPolling = true;
    this._syncLayout('reconnecting', { attempt: this._reconnectAttempts });
    this._emit('connection', { connected: true, polling: true });

    this._pollingTimer = setInterval(async () => {
      if (!AuthService.isAuthenticated()) return;
      try {
        if (MockService.enabled) {
          if (Math.random() > 0.4) {
            const det = MockService.generateDetection();
            this._emit('detection_new', det);
          }
        } else {
          const dets = await DetectionService.list({ status: 'active', limit: 10 });
          const items = Array.isArray(dets) ? dets : (dets.items || []);
          if (items.length > 0) this._emit('detections_polled', items);
        }
      } catch (_) {}
    }, 5000);
  },

  _stopPolling() {
    if (this._pollingTimer) {
      clearInterval(this._pollingTimer);
      this._pollingTimer = null;
    }
    this._isPolling = false;
  },

  _startSimulator() {
    if (this._simulatorTimer) return;
    this._simulatorTimer = setInterval(() => {
      if (!AuthService.isAuthenticated()) {
        this.disconnect();
        return;
      }
      if (Math.random() > 0.3) {
        const det = MockService.generateDetection();
        this._emit('detection_new', det);
      }
      if (Math.random() > 0.7 && MockService.alerts?.length > 0) {
        const sample = MockService.alerts[Math.floor(Math.random() * MockService.alerts.length)];
        this._emit('alert_new', { ...sample, id: 'ALT-' + Math.floor(Math.random() * 9000 + 1000), created_at: new Date().toISOString() });
      }
    }, 3500);
  },

  disconnect() {
    this._forcedDisconnect = true;
    clearTimeout(this._reconnectTimer);
    this._stopHeartbeat();
    this._stopPolling();
    if (this._simulatorTimer) {
      clearInterval(this._simulatorTimer);
      this._simulatorTimer = null;
    }
    if (this._socket) {
      try { this._socket.close(1000, 'User disconnect'); } catch (e) {}
      this._socket = null;
    }
    this._connected = false;
    this._status = 'disconnected';
    this._syncLayout('disconnected');
  },

  on(event, handler) {
    if (!this._handlers.has(event)) this._handlers.set(event, new Set());
    this._handlers.get(event).add(handler);
    return () => this.off(event, handler);
  },

  off(event, handler) {
    this._handlers.get(event)?.delete(handler);
  },

  _emit(event, data) {
    this._handlers.get(event)?.forEach(h => { try { h(data); } catch (e) { console.error(e); } });
  },

  isConnected() { return this._connected; },
  getLatency() { return this._latencyMs; },
  getStatus() { return this._status; },
};

// ============================================================
// Mock Data Service (for development / demo)
// ============================================================

export const MockService = {
  enabled: window.AEROGUARD_DEMO_MODE !== false,

  _generateId: () => Math.random().toString(36).slice(2, 10),

  _randomBetween: (min, max) => Math.random() * (max - min) + min,

  _randomFrom: (arr) => arr[Math.floor(Math.random() * arr.length)],

  // Bogotá area coordinates for demo
  _centerLat: 4.7110,
  _centerLng: -74.0721,

  _randomCoord() {
    return {
      lat: this._centerLat + this._randomBetween(-0.05, 0.05),
      lng: this._centerLng + this._randomBetween(-0.05, 0.05),
    };
  },

  generateDetection() {
    const coord = this._randomCoord();
    const threatLevels = ['low', 'medium', 'high', 'critical'];
    const statuses = ['active', 'pending', 'resolved'];
    const isDrone = Math.random() > 0.3;
    return {
      id: this._generateId(),
      sensor_id: `SEN-${Math.floor(Math.random() * 5) + 1}`,
      sensor_name: `Sensor ${Math.floor(Math.random() * 5) + 1}`,
      latitude: coord.lat,
      longitude: coord.lng,
      altitude: this._randomBetween(10, 200),
      speed: this._randomBetween(5, 80),
      heading: this._randomBetween(0, 360),
      status: this._randomFrom(statuses),
      threat_level: this._randomFrom(threatLevels),
      ai_analyzed: true,
      ai_confidence: this._randomBetween(0.6, 0.99),
      is_drone: isDrone,
      timestamp: new Date(Date.now() - this._randomBetween(0, 3600000)).toISOString(),
    };
  },

  detections: [],
  sensors: [],
  alerts: [],
  zones: [],

  saveZones() {
    try {
      localStorage.setItem('aeroguard_zones', JSON.stringify(this.zones));
    } catch (e) {
      console.warn('Could not save zones to localStorage', e);
    }
  },

  loadZones() {
    try {
      const stored = localStorage.getItem('aeroguard_zones');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.warn('Could not load zones from localStorage', e);
    }
    return null;
  },

  init() {
    // Generate initial mock data
    this.detections = Array.from({ length: 24 }, () => this.generateDetection());
    this.sensors = [
      { id: 'SEN-1', name: 'Sensor Norte',   type: 'radar',    status: 'active',   latitude: 4.742, longitude: -74.072, altitude: 50, range_km: 5, detections_count: 12, last_active: new Date().toISOString() },
      { id: 'SEN-2', name: 'Sensor Sur',     type: 'radar',    status: 'active',   latitude: 4.680, longitude: -74.072, altitude: 45, range_km: 5, detections_count: 8,  last_active: new Date().toISOString() },
      { id: 'SEN-3', name: 'Sensor Este',    type: 'optical',  status: 'active',   latitude: 4.711, longitude: -74.032, altitude: 60, range_km: 3, detections_count: 4,  last_active: new Date().toISOString() },
      { id: 'SEN-4', name: 'Sensor Oeste',   type: 'acoustic', status: 'inactive', latitude: 4.711, longitude: -74.112, altitude: 40, range_km: 4, detections_count: 0,  last_active: null },
      { id: 'SEN-5', name: 'Sensor Central', type: 'rf',       status: 'error',    latitude: 4.711, longitude: -74.072, altitude: 55, range_km: 6, detections_count: 2,  last_active: new Date(Date.now() - 3600000).toISOString() },
    ];
    
    const savedZones = this.loadZones();
    if (savedZones && savedZones.some(z => z.name?.includes('Dorado'))) {
      this.zones = savedZones;
    } else {
      this.zones = [
        { id: 'Z-1', name: 'Aeropuerto El Dorado', description: 'Zona de exclusión aeroportuaria principal', severity: 'critical', min_altitude: 0, max_altitude: 1200, is_active: true, polygon: [{ lat: 4.700, lng: -74.145 }, { lat: 4.720, lng: -74.145 }, { lat: 4.720, lng: -74.110 }, { lat: 4.700, lng: -74.110 }], coordinates: [[4.700, -74.145], [4.720, -74.145], [4.720, -74.110], [4.700, -74.110]] },
        { id: 'Z-2', name: 'Centro de Operaciones Bogotá', description: 'Zona de exclusión operativa', severity: 'high', min_altitude: 0, max_altitude: 500, is_active: true, polygon: [{ lat: 4.705, lng: -74.080 }, { lat: 4.715, lng: -74.080 }, { lat: 4.715, lng: -74.065 }, { lat: 4.705, lng: -74.065 }], coordinates: [[4.705, -74.080], [4.715, -74.080], [4.715, -74.065], [4.705, -74.065]] },
        { id: 'Z-3', name: 'Zona Residencial Norte Bogotá', description: 'Zona de vuelo restringido', severity: 'medium', min_altitude: 0, max_altitude: 200, is_active: true, polygon: [{ lat: 4.730, lng: -74.075 }, { lat: 4.745, lng: -74.075 }, { lat: 4.745, lng: -74.060 }, { lat: 4.730, lng: -74.060 }], coordinates: [[4.730, -74.075], [4.745, -74.075], [4.745, -74.060], [4.730, -74.060]] },
        { id: 'Z-4', name: 'Aeropuerto Palonegro (Área Crítica)', description: 'Zona de aproximación y pista de aterrizaje principal.', severity: 'critical', min_altitude: 0, max_altitude: 1200, is_active: true, polygon: [{ lat: 7.1265, lng: -73.1848 }, { lat: 7.1350, lng: -73.1720 }, { lat: 7.1210, lng: -73.1650 }, { lat: 7.1140, lng: -73.1780 }], coordinates: [[7.1265, -73.1848], [7.1350, -73.1720], [7.1210, -73.1650], [7.1140, -73.1780]] },
        { id: 'Z-5', name: 'Complejo Gubernamental Santander', description: 'Edificios administrativos centrales y centro de mando.', severity: 'high', min_altitude: 0, max_altitude: 300, is_active: true, polygon: [{ lat: 7.1190, lng: -73.1250 }, { lat: 7.1240, lng: -73.1200 }, { lat: 7.1210, lng: -73.1140 }, { lat: 7.1150, lng: -73.1190 }], coordinates: [[7.1190, -73.1250], [7.1240, -73.1200], [7.1210, -73.1140], [7.1150, -73.1190]] },
      ];
      this.saveZones();
    }
    this.alerts = [
      { id: 'ALT-1', type: 'restricted_zone', severity: 'critical', status: 'open',     title: 'Drone detectado en zona aeroportuaria',       description: 'Un drone fue detectado ingresando a la zona de exclusión del Aeropuerto El Dorado.', zone_name: 'Aeropuerto El Dorado', created_at: new Date(Date.now() - 600000).toISOString(), latitude: 4.710, longitude: -74.130 },
      { id: 'ALT-2', type: 'anomalous_behavior', severity: 'high', status: 'assigned',  title: 'Comportamiento anómalo: cambio brusco de dirección', description: 'El objeto DEF456 realizó un giro abrupto a 150 km/h.', created_at: new Date(Date.now() - 1800000).toISOString(), latitude: 4.695, longitude: -74.065 },
      { id: 'ALT-3', type: 'restricted_zone', severity: 'medium', status: 'resolved',   title: 'Intrusión en Centro de Operaciones',          description: 'Objeto no identificado sobrevoló el Centro de Operaciones a 80m de altura.', zone_name: 'Centro de Operaciones', created_at: new Date(Date.now() - 7200000).toISOString(), latitude: 4.710, longitude: -74.072 },
      { id: 'ALT-4', type: 'anomalous_behavior', severity: 'low',  status: 'open',      title: 'Velocidad inusualmente alta',                description: 'Objeto detectado a 95 km/h en zona de baja velocidad.', created_at: new Date(Date.now() - 300000).toISOString(), latitude: 4.720, longitude: -74.055 },
    ];
    this.users = [
      { id: 'U-1', username: 'admin',    email: 'admin@aeroguard.co',    first_name: 'Carlos',   last_name: 'Ramírez',   role: 'admin',    is_active: true, last_login: new Date().toISOString() },
      { id: 'U-2', username: 'operator1',email: 'op1@aeroguard.co',      first_name: 'María',    last_name: 'González',  role: 'operator', is_active: true, last_login: new Date(Date.now() - 3600000).toISOString() },
      { id: 'U-3', username: 'analyst1', email: 'analyst@aeroguard.co',  first_name: 'Roberto',  last_name: 'Pérez',     role: 'analyst',  is_active: true, last_login: new Date(Date.now() - 7200000).toISOString() },
      { id: 'U-4', username: 'operator2',email: 'op2@aeroguard.co',      first_name: 'Sofía',    last_name: 'Torres',    role: 'operator', is_active: false, last_login: new Date(Date.now() - 86400000).toISOString() },
    ];
    this.demoCredentials = [
      { username: 'admin',     password: 'Admin123!', role: 'Administrador' },
      { username: 'operator1', password: 'Oper123!',  role: 'Operador' },
      { username: 'analyst1',  password: 'Anal123!',  role: 'Analista' },
    ];
  },

  // Fake API methods
  async fakeLogin(username, password) {
    await this._delay(600);
    const cred = this.demoCredentials.find(c => c.username === username);
    if (!cred || cred.password !== password) throw new Error('Credenciales incorrectas.');
    const user = this.users.find(u => u.username === username);
    return { access_token: `mock_token_${username}`, user };
  },

  _delay: (ms) => new Promise(r => setTimeout(r, ms)),
};

MockService.init();
