/**
 * AeroGuard — Dashboard ViewModel (MVVM)
 * Gestiona estado, datos y comunicación del Dashboard en tiempo real.
 */

import { DetectionService, AlertService, SensorService, ZoneService, WebSocketService, MockService } from '../services/api.service.js';
import { DetectionModel, AlertModel, SensorModel, RestrictedZoneModel } from '../models/models.js';
import { Toast } from '../app.js';
import { tacticalAudio } from '../services/audio.service.js';

export class DashboardViewModel {
  constructor() {
    this.state = {
      detections:  [],
      alerts:      [],
      sensors:     [],
      zones:       [],
      stats:       { total: 0, active: 0, resolved: 0, alertsOpen: 0 },
      isLoading:   true,
      mapLayers:   { zones: true, sensors: true, trajectories: false },
      wsConnected: false,
      selectedDetection: null,
      lastUpdate: null,
      aiVerdict: null,
      previousAltitudes: new Map(),
    };

    this._wsHandlers = [];
    this._map = null;
    this._markers = new Map();
    this._zonePolygons = [];
    this._trajectoryLines = [];
    this._sensorCircles = [];
    this._simulatorInterval = null;
    this._baseLayers = {};
    this._resizeHandler = () => this.renderAltimetry();
    window.addEventListener('resize', this._resizeHandler);
  }

  // ============================================================
  // Data Loading
  // ============================================================

  async loadData() {
    try {
      if (MockService.enabled) {
        await this._loadMockData();
      } else {
        await Promise.allSettled([
          this._loadDetections(),
          this._loadAlerts(),
          this._loadSensors(),
          this._loadZones(),
          this._loadAiVerdict(),
        ]);
      }
      this._computeStats();
      this.state.lastUpdate = new Date();
    } catch (err) {
      Toast.error('Error al cargar datos del dashboard.');
      console.error('loadData error:', err);
    } finally {
      this.state.isLoading = false;
    }
  }

  async _loadMockData() {
    await new Promise(r => setTimeout(r, 100));
    this.state.detections = (MockService.detections || [])
      .filter(d => d.status === 'active')
      .map(d => new DetectionModel(d));
    this.state.alerts = (MockService.alerts || []).map(a => new AlertModel(a));
    this.state.sensors = (MockService.sensors || []).map(s => new SensorModel(s));
    const zones = MockService.loadZones() || MockService.zones || [];
    this.state.zones = zones.map(z => new RestrictedZoneModel(z));
    this.state.aiVerdict = {
      incident_id: "INC-2026-0891",
      timestamp: new Date().toISOString(),
      ai_verdict: "DEMO: objeto simulado a 145m, umbral de ejemplo de 120m. Verificar visualmente y avisar al responsable de seguridad.",
      threat_level: "CRITICAL",
      drone_id: "UAV-HK-402"
    };
  }

  async _loadAiVerdict() {
    try {
      const data = await AlertService.getAiVerdict();
      if (data) {
        this.state.aiVerdict = data;
      }
    } catch (e) {
      console.warn('Error loading AI verdict:', e);
    }
  }

  async _loadDetections() {
    try {
      const data = await DetectionService.list({ status: 'active', limit: 50 });
      const items = Array.isArray(data) ? data : (data.items || []);
      this.state.detections = items.map(d => new DetectionModel(d));
    } catch (e) {
      console.warn('Error loading detections:', e);
      this.state.detections = [];
    }
  }

  async _loadAlerts() {
    try {
      const data = await AlertService.list({ status: 'open', limit: 20 });
      const items = Array.isArray(data) ? data : (data.items || []);
      this.state.alerts = items.map(a => new AlertModel(a));
    } catch (e) {
      console.warn('Error loading alerts:', e);
      this.state.alerts = [];
    }
  }

  async _loadSensors() {
    try {
      const data = await SensorService.list();
      const items = Array.isArray(data) ? data : (data.items || []);
      this.state.sensors = items.map(s => new SensorModel(s));
    } catch (e) {
      console.warn('Error loading sensors:', e);
      this.state.sensors = [];
    }
  }

  async _loadZones() {
    try {
      let items = [];
      try {
        const data = await ZoneService.list();
        items = Array.isArray(data) ? data : (data.items || []);
      } catch (apiErr) {
        console.warn('Error loading zones from API:', apiErr);
      }

      if (items.length > 0) {
        this.state.zones = items.map(z => new RestrictedZoneModel(z));
        MockService.zones = items;
        MockService.saveZones();
      } else {
        const zones = MockService.loadZones() || MockService.zones || [];
        this.state.zones = zones.map(z => new RestrictedZoneModel(z));
      }
    } catch (e) {
      console.warn('Fallback loading zones from MockService:', e);
      const zones = MockService.loadZones() || MockService.zones || [];
      this.state.zones = zones.map(z => new RestrictedZoneModel(z));
    }
  }

  _computeStats() {
    const dets = this.state.detections;
    const alerts = this.state.alerts;
    this.state.stats = {
      total:      dets.length,
      active:     dets.filter(d => d.status === 'active').length,
      resolved:   dets.filter(d => d.status === 'resolved').length,
      alertsOpen: alerts.filter(a => a.status === 'open').length,
    };
  }

  // ============================================================
  // Map Initialization
  // ============================================================

  initMap(containerId) {
    if (!window.L) {
      console.error('Leaflet not loaded');
      return;
    }

    const L = window.L;
    const container = document.getElementById(containerId);
    if (!container) return;

    // Reset previous instance
    if (this._map) {
      try { this._map.remove(); } catch (e) {}
      this._map = null;
    }
    if (container._leaflet_id) {
      container._leaflet_id = null;
    }

    // Default center around Bucaramanga / Palonegro airport or Bogotá
    let defaultCenter = [7.1265, -73.1848];
    let defaultZoom = 13;

    if (this.state.sensors.length > 0 && this.state.sensors[0].latitude) {
      defaultCenter = [this.state.sensors[0].latitude, this.state.sensors[0].longitude];
    } else if (this.state.detections.length > 0 && this.state.detections[0].latitude) {
      defaultCenter = [this.state.detections[0].latitude, this.state.detections[0].longitude];
    }

    this._map = L.map(containerId, {
      center: defaultCenter,
      zoom: defaultZoom,
      zoomControl: false,
    });

    // 1. CartoDB Dark Matter
    const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
    });

    // 2. Google Maps (Normal)
    const googleRoadLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
      attribution: '&copy; Google Maps',
      maxZoom: 20,
    });

    // 3. Google Maps (Satélite + Calles)
    const googleSatLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
      attribution: '&copy; Google Maps',
      maxZoom: 20,
    });

    // 3. OpenStreetMap Standard
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    });

    // Add default Google layer with fallback to OSM
    let fallbackTriggered = false;
    googleRoadLayer.on('tileerror', () => {
      if (!fallbackTriggered) {
        fallbackTriggered = true;
        console.warn('Google Maps falló. Cambiando a OpenStreetMap (Fallback).');
        if (this._map.hasLayer(googleRoadLayer)) {
          this._map.removeLayer(googleRoadLayer);
          osmLayer.addTo(this._map);
          Toast.warn('Google Maps no disponible. Usando mapa de respaldo.');
        }
      }
    });

    googleSatLayer.on('tileerror', () => {
      if (!fallbackTriggered) {
        fallbackTriggered = true;
        console.warn('Google Maps (Satélite) falló. Cambiando a OpenStreetMap (Fallback).');
        if (this._map.hasLayer(googleSatLayer)) {
          this._map.removeLayer(googleSatLayer);
          osmLayer.addTo(this._map);
          Toast.warn('Google Maps no disponible. Usando mapa de respaldo.');
        }
      }
    });

    googleRoadLayer.addTo(this._map);

    // Layer switcher control (Top Right)
    const baseLayers = {
      '🌙 Modo Oscuro': darkLayer,
      '🛰️ Satélite (Google)': googleSatLayer,
      '🗺️ Calles (Google)': googleRoadLayer,
      '🗺️ OpenStreetMap': osmLayer,
    };
    L.control.layers(baseLayers, null, { position: 'topright' }).addTo(this._map);

    // Zoom control (Bottom Right)
    L.control.zoom({ position: 'bottomright' }).addTo(this._map);

    // Plot initial data
    this._plotDetections();
    this._plotSensors();
    this._plotZones();

    // Auto fit bounds if items exist
    this.fitMapBounds();

    // Invalidate size to ensure full container rendering
    setTimeout(() => { if (this._map) this._map.invalidateSize(); }, 100);
    setTimeout(() => { if (this._map) this._map.invalidateSize(); }, 400);
  }

  fitMapBounds() {
    if (!this._map) return;
    const points = [];
    this.state.detections.forEach(d => {
      if (d.latitude && d.longitude) points.push([d.latitude, d.longitude]);
    });
    this.state.sensors.forEach(s => {
      if (s.latitude && s.longitude) points.push([s.latitude, s.longitude]);
    });
    this.state.zones.forEach(z => {
      if (z.polygon && z.polygon.length) {
        z.polygon.forEach(p => {
          const lat = p.lat ?? p[0];
          const lng = p.lng ?? p[1];
          if (lat && lng) points.push([lat, lng]);
        });
      }
    });

    if (points.length > 1) {
      try {
        this._map.fitBounds(points, { padding: [50, 50], maxZoom: 15 });
      } catch (e) {}
    }
  }

  _makeDetectionIcon(detection) {
    const L = window.L;
    const colors = {
      critical: '#ff1744', high: '#ff6d00', medium: '#ffb300', low: '#00e676'
    };
    const color = colors[detection.threatLevel] || '#00d4ff';
    const size  = detection.threatLevel === 'critical' ? 18 : 14;
    const pulse = detection.status === 'active';

    return L.divIcon({
      className: '',
      html: `
        <div style="
          width:${size}px;height:${size}px;
          background:${color};
          border-radius:50%;
          border:2px solid rgba(255,255,255,0.9);
          box-shadow: 0 0 ${pulse ? '14px' : '6px'} ${color};
          ${pulse ? 'animation:pulse-marker 1.5s infinite' : ''};
          position:relative;
        ">
          ${pulse ? `<div style="position:absolute;inset:-6px;border-radius:50%;border:2px solid ${color};opacity:0.5;animation:pulse-ring 1.5s infinite"></div>` : ''}
        </div>
      `,
      iconSize: [size, size],
      iconAnchor: [size/2, size/2],
    });
  }

  _makeSensorIcon(sensor) {
    const L = window.L;
    const colors = { active: '#00e676', inactive: '#546e7a', error: '#ff1744' };
    const color = colors[sensor.status] || '#546e7a';
    return L.divIcon({
      className: '',
      html: `<div style="font-size:20px;filter:drop-shadow(0 0 6px ${color})" title="${sensor.name}">📡</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
  }

  _plotDetections() {
    const L = window.L;
    if (!this._map) return;

    this._markers.forEach(m => m.remove());
    this._markers.clear();

    this.state.detections.forEach(detection => {
      if (!detection.latitude || !detection.longitude) return;
      const marker = L.marker(
        [detection.latitude, detection.longitude],
        { icon: this._makeDetectionIcon(detection) }
      );

      marker.bindPopup(`
        <div style="background:var(--bg-card,#131b2e);padding:14px;border-radius:10px;min-width:220px;font-family:'Inter',sans-serif;color:#ffffff;box-shadow:0 8px 24px rgba(0,0,0,0.5)">
          <div style="font-weight:700;font-size:14px;margin-bottom:6px;color:#00d4ff;display:flex;align-items:center;gap:6px">
            🎯 Detección de Dron
          </div>
          <div style="font-size:11px;color:#8899bb;margin-bottom:8px">ID: ${detection.id ? String(detection.id).slice(0,8) : 'N/A'}</div>
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#94a3b8">Altitud:</span><strong style="color:#ffffff">${detection.formattedAltitude}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#94a3b8">Velocidad:</span><strong style="color:#ffffff">${detection.formattedSpeed}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#94a3b8">Rumbo:</span><strong style="color:#ffffff">${detection.formattedHeading} (${detection.heading.toFixed(0)}°)</strong>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:8px">
            <span style="color:#94a3b8">IA Confianza:</span><span style="color:${detection.isDrone ? '#ff6d00' : '#00e676'}">${detection.isDrone ? '⚠️ Dron' : '✅ Sensor'} (${detection.confidencePercent})</span>
          </div>
          <a href="#/detections" style="display:inline-block;margin-top:4px;color:#00d4ff;font-size:12px;font-weight:600;text-decoration:none">Ver en lista &rarr;</a>
        </div>
      `, { className: 'aeroguard-popup' });

      marker.addTo(this._map);
      this._markers.set(detection.id, marker);
    });
  }

  _plotSensors() {
    const L = window.L;
    if (!this._map || !this.state.mapLayers.sensors) return;

    this._sensorCircles.forEach(c => c.remove());
    this._sensorCircles = [];

    this.state.sensors.forEach(sensor => {
      if (!sensor.latitude || !sensor.longitude) return;

      const colors = { active: '#00e676', inactive: '#546e7a', error: '#ff1744' };
      const color  = colors[sensor.status] || '#546e7a';

      // Range circle
      const circle = L.circle([sensor.latitude, sensor.longitude], {
        radius: (sensor.rangeKm || 5) * 1000,
        color,
        fillColor: color,
        fillOpacity: 0.05,
        weight: 1.5,
        dashArray: '5, 8',
      }).addTo(this._map);

      // Marker
      const marker = L.marker(
        [sensor.latitude, sensor.longitude],
        { icon: this._makeSensorIcon(sensor) }
      ).bindTooltip(`📡 ${sensor.name} (${sensor.typeLabel} - ${sensor.rangeKm}km)`, { direction: 'top' }).addTo(this._map);

      this._sensorCircles.push(circle, marker);
    });
  }

  _plotZones() {
    const L = window.L;
    if (!this._map || !this.state.mapLayers.zones) return;

    this._zonePolygons.forEach(p => p.remove());
    this._zonePolygons = [];

    const zones = this.state.zones;
    zones.forEach(zone => {
      if (!zone.polygon || !zone.polygon.length) return;
      const colors = { critical: '#ff1744', high: '#ff6d00', medium: '#ffb300', low: '#00e676' };
      const color  = colors[zone.severity] || zone.color || '#ff1744';
      
      const latlngs = zone.polygon.map(p => {
        if (Array.isArray(p)) return [p[0], p[1]];
        return [p.lat ?? p[0], p.lng ?? p[1]];
      });

      const poly = L.polygon(latlngs, {
        color,
        fillColor: color,
        fillOpacity: 0.15,
        weight: 2,
        dashArray: '4, 4',
      }).bindTooltip(`🚫 ${zone.name}`, { sticky: true }).addTo(this._map);
      this._zonePolygons.push(poly);
    });
  }

  // ============================================================
  // Real-time Updates
  // ============================================================

  startRealtime() {
    WebSocketService.connect();
    const h1 = WebSocketService.on('detection_new', (data) => {
      this._onNewDetection(data);
    });
    const h2 = WebSocketService.on('alert_new', (data) => {
      this._onNewAlert(data);
    });
    const h3 = WebSocketService.on('sensor_update', (data) => {
      this._onSensorUpdate(data);
    });
    const h4 = WebSocketService.on('connection', ({ connected }) => {
      this.state.wsConnected = connected;
      if (typeof window !== 'undefined' && window.Layout?.updateWsStatus) {
        window.Layout.updateWsStatus(connected);
      }
    });
    const h5 = WebSocketService.on('ai_verdict', (data) => {
      this._onVerdictUpdate(data);
    });
    this._wsHandlers = [h1, h2, h3, h4, h5];
    this.state.wsConnected = true;
    if (typeof window !== 'undefined' && window.Layout?.updateWsStatus) {
      window.Layout.updateWsStatus(true);
    }
  }

  stopRealtime() {
    this._wsHandlers.forEach(unsub => { if (typeof unsub === 'function') unsub(); });
    this._wsHandlers = [];
  }

  _onNewDetection(data) {
    const det = new DetectionModel(data);
    const idx = this.state.detections.findIndex(d => d.id === det.id);
    if (idx >= 0) {
      this.state.detections[idx] = det;
      this._updateMarker(det);
    } else {
      this.state.detections.unshift(det);
      if (this.state.detections.length > 50) this.state.detections.pop();
      this._plotDetections();
    }
    this._updateStats();
    this._updateLastUpdate();
    this.renderAltimetry();
  }

  _onNewAlert(data) {
    const alert = new AlertModel(data);
    this.state.alerts.unshift(alert);
    if (this.state.alerts.length > 20) this.state.alerts.pop();
    this._renderAlerts();
    this._updateStats();

    // Disparo de sirena táctica para eventos críticos o de alto riesgo
    if (alert.severity === 'critical' || alert.severity === 'high') {
      tacticalAudio.playAlert({ durationMs: 2500, gain: 0.15 });
    }

    Toast.warning(`⚠️ Alerta: ${alert.title}`);
  }

  _onVerdictUpdate(data) {
    const verdict = data?.data || data;
    if (verdict) {
      this.state.aiVerdict = verdict;
      this._renderAiVerdict();
      if (verdict.threat_level === 'CRITICAL') {
        tacticalAudio.playAlert({ durationMs: 2000, gain: 0.12 });
      }
    }
  }

  _onSensorUpdate(data) {
    const idx = this.state.sensors.findIndex(s => s.id === data.id);
    if (idx >= 0) {
      this.state.sensors[idx] = new SensorModel({ ...this.state.sensors[idx], ...data });
      this._renderSensorStatus();
      this._plotSensors();
    }
  }

  _updateMarker(detection) {
    const marker = this._markers.get(detection.id);
    if (marker) {
      marker.setLatLng([detection.latitude, detection.longitude]);
      marker.setIcon(this._makeDetectionIcon(detection));
    }
  }

  _updateStats() {
    this._computeStats();
    const els = {
      'stat-total':    this.state.stats.total,
      'stat-active':   this.state.stats.active,
      'stat-resolved': this.state.stats.resolved,
      'stat-alerts':   this.state.stats.alertsOpen,
    };
    Object.entries(els).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    });

    import('../app.js').then(m => m.Layout.updateAlertBadge(this.state.stats.alertsOpen));
  }

  _updateLastUpdate() {
    const el = document.getElementById('last-update');
    if (el) el.textContent = new Date().toLocaleTimeString('es-CO');
  }

  // ============================================================
  // Render helpers
  // ============================================================

  renderStats() {
    const els = {
      'stat-total':    this.state.stats.total,
      'stat-active':   this.state.stats.active,
      'stat-resolved': this.state.stats.resolved,
      'stat-alerts':   this.state.stats.alertsOpen,
    };
    Object.entries(els).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    });
  }

  _renderAlerts() {
    const container = document.getElementById('alert-list');
    if (!container) return;
    const alerts = this.state.alerts.slice(0, 5);
    if (!alerts.length) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-title" style="font-size:14px">Sin alertas activas</div></div>`;
      return;
    }
    container.innerHTML = alerts.map(a => {
      const am = a instanceof AlertModel ? a : new AlertModel(a);
      return `
        <div class="alert-list-item ${am.severity}" role="listitem">
          <span class="alert-item-icon">${am.severityIcon}</span>
          <div class="alert-item-content">
            <div class="alert-item-title">${am.title}</div>
            <div class="alert-item-desc">${am.description || am.message || ''}</div>
          </div>
          <span class="alert-item-time">${am.formattedTime.split(',')[1]?.trim() || ''}</span>
        </div>
      `;
    }).join('');
  }

  _renderSensorStatus() {
    const container = document.getElementById('sensor-status-list');
    if (!container) return;
    const sensors = this.state.sensors;
    container.innerHTML = sensors.map(s => {
      const dot = s.status === 'active' ? 'status-online' : s.status === 'error' ? 'status-danger' : 'status-offline';
      const statusText = s.status === 'active' ? 'En línea' : s.status === 'error' ? 'Error' : 'Inactivo';
      const textColor  = s.status === 'active' ? 'var(--success)' : s.status === 'error' ? 'var(--danger)' : 'var(--text-muted)';
      return `
        <div class="detector-item">
          <span style="font-size:20px">${s.typeIcon}</span>
          <div class="detector-info">
            <div class="detector-name">${s.name}</div>
            <div class="detector-location">${s.typeLabel} · ${s.rangeKm}km</div>
          </div>
          <span class="status-dot ${dot}"></span>
          <span class="detector-status-text" style="color:${textColor}">${statusText}</span>
        </div>
      `;
    }).join('');
  }

  bindMapControls() {
    document.getElementById('map-layer-zones')?.addEventListener('click', (e) => {
      this.state.mapLayers.zones = !this.state.mapLayers.zones;
      e.currentTarget.classList.toggle('active', this.state.mapLayers.zones);
      if (this.state.mapLayers.zones) this._plotZones();
      else { this._zonePolygons.forEach(p => p.remove()); this._zonePolygons = []; }
    });

    document.getElementById('map-layer-sensors')?.addEventListener('click', (e) => {
      this.state.mapLayers.sensors = !this.state.mapLayers.sensors;
      e.currentTarget.classList.toggle('active', this.state.mapLayers.sensors);
      if (this.state.mapLayers.sensors) this._plotSensors();
      else { this._sensorCircles.forEach(c => c.remove()); this._sensorCircles = []; }
    });

    document.getElementById('map-center-btn')?.addEventListener('click', () => {
      this.fitMapBounds();
    });

    document.getElementById('map-fit-btn')?.addEventListener('click', () => {
      this.fitMapBounds();
    });
  }

  bindTacticalControls() {
    const btnToggle = document.getElementById('btn-toggle-audio');
    const iconSpan = document.getElementById('audio-icon');
    const textSpan = document.getElementById('audio-status-text');

    const updateUI = () => {
      const muted = tacticalAudio.isMuted();
      if (iconSpan) iconSpan.textContent = muted ? '🔇' : '🔊';
      if (textSpan) textSpan.textContent = muted ? 'Sonido: MUTE' : 'Sonido: ON';
      if (btnToggle) {
        btnToggle.style.borderColor = muted ? 'var(--neutral)' : 'var(--text-accent)';
        btnToggle.style.color = muted ? 'var(--text-muted)' : 'var(--text-accent)';
      }
    };

    updateUI();

    btnToggle?.addEventListener('click', () => {
      const muted = tacticalAudio.toggleMute();
      updateUI();
      if (muted) {
        Toast.info('🔇 Sirena táctica silenciada');
      } else {
        Toast.success('🔊 Sirena táctica habilitada');
      }
    });

    document.getElementById('btn-test-siren')?.addEventListener('click', () => {
      tacticalAudio.testSiren();
      Toast.warning('🚨 Ráfaga táctica de prueba (1.5s)');
    });

    document.getElementById('btn-trigger-soar')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-trigger-soar');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Analizando...';
      }
      Toast.info('⚡ Despachando incidente a Pipeline SOAR / Agente IA...');
      try {
        const topDrone = this.state.detections.find(d => d.status === 'active') || {
          id: 'UAV-HK-402',
          altitude: 145.0,
          speed: 70.0,
          heading: 182,
        };
        const payload = {
          incident_id: `INC-${Date.now().toString().slice(-4)}`,
          event_type: 'GEOFENCE_BREACH_CRITICAL',
          drone: {
            drone_id: topDrone.id ? (String(topDrone.id).startsWith('UAV') ? topDrone.id : `UAV-${String(topDrone.id).slice(-3).toUpperCase()}`) : 'UAV-HK-402',
            altitude_m: topDrone.altitude || 145.0,
            speed_ms: (topDrone.speed ? topDrone.speed / 3.6 : 19.4),
            heading_deg: topDrone.heading || 182,
            ai_confidence: 0.96,
            latitude: topDrone.latitude || 7.1193,
            longitude: topDrone.longitude || -73.1227
          },
          zone: {
            name: 'Perímetro Seguridad UTS / Bucaramanga Centro',
            max_allowed_altitude_m: 120.0,
            restriction_type: 'NO_FLY_ZONE'
          }
        };
        const res = await AlertService.triggerIncident(payload);
        if (res?.data) {
          this._onVerdictUpdate(res.data);
          const sourceLabel = res.data.execution_source === 'n8n_soar_pipeline' ? 'n8n SOAR' : 'Agente IA Embebido';
          Toast.success(`🤖 Dictamen táctico generado por ${sourceLabel}`);
        }
      } catch (err) {
        console.error('Error triggering SOAR incident:', err);
        Toast.error('Error al ejecutar análisis SOAR.');
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<span>⚡</span> Disparar SOAR';
        }
      }
    });
  }

  _renderAiVerdict() {
    const verdict = this.state.aiVerdict;
    if (!verdict) return;

    const elText = document.getElementById('ai-verdict-text');
    const elBadge = document.getElementById('ai-verdict-badge');
    const elTarget = document.getElementById('ai-verdict-target');
    const elConf = document.getElementById('ai-verdict-confidence');
    const elTime = document.getElementById('ai-verdict-time');
    const elInc = document.getElementById('ai-verdict-incident');

    if (elText && verdict.ai_verdict) elText.textContent = verdict.ai_verdict;
    if (elTarget && verdict.drone_id) elTarget.textContent = `${verdict.drone_id} (DJI Matrice 300)`;
    if (elInc && verdict.incident_id) elInc.textContent = verdict.incident_id;

    if (elBadge && verdict.threat_level) {
      elBadge.textContent = verdict.threat_level.toUpperCase();
      elBadge.className = verdict.threat_level.toLowerCase() === 'critical' 
        ? 'badge badge-danger' 
        : verdict.threat_level.toLowerCase() === 'high' 
          ? 'badge badge-warning' 
          : 'badge badge-info';
    }

    if (elTime && verdict.timestamp) {
      const d = new Date(verdict.timestamp);
      elTime.textContent = `Actualizado ${d.toLocaleTimeString('es-CO')}`;
    }
    if (elConf) {
      elConf.textContent = '96.4%';
    }
  }

  renderAltimetry() {
    const canvas = document.getElementById('altimetry-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Retina / High-DPI handling
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || 340;
    const height = rect.height || 180;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.resetTransform?.();
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = '#0b1120';
    ctx.fillRect(0, 0, width, height);

    // Padding & dimensions
    const padL = 36;
    const padR = 12;
    const padT = 16;
    const padB = 24;
    const plotW = width - padL - padR;
    const plotH = height - padT - padB;

    const maxAlt = 200; // Eje Y: 0 a 200m AGL
    const getY = (alt) => padT + plotH * (1 - Math.min(maxAlt, Math.max(0, alt)) / maxAlt);

    // Draw gridlines (0m, 50m, 100m, 150m, 200m)
    const gridAltitudes = [0, 50, 100, 150, 200];
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.fillStyle = '#64748b';
    ctx.font = '9px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    gridAltitudes.forEach(alt => {
      const y = getY(alt);
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(width - padR, y);
      ctx.stroke();
      ctx.fillText(`${alt}m`, padL - 5, y);
    });

    // Draw 120m Civil Ceiling line (UAEAC)
    const y120 = getY(120);
    ctx.setLineDash([5, 3]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#ff1744';
    ctx.beginPath();
    ctx.moveTo(padL, y120);
    ctx.lineTo(width - padR, y120);
    ctx.stroke();

    // Ceiling label
    ctx.setLineDash([]);
    ctx.fillStyle = '#ff1744';
    ctx.font = 'bold 9px "Inter", sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('LÍMITE CIVIL 120m', width - padR - 4, y120 - 6);

    // Active drones
    const activeDrones = (this.state.detections || [])
      .filter(d => d.status === 'active' || d.is_drone || d.isDrone)
      .slice(0, 5);

    const countBadge = document.getElementById('altimetry-active-count');
    const statusText = document.getElementById('altimetry-status-text');

    if (countBadge) {
      countBadge.textContent = `${activeDrones.length} Drones`;
    }

    let hasViolation = false;

    if (activeDrones.length === 0) {
      // Empty radar scan placeholder
      ctx.fillStyle = '#475569';
      ctx.font = '11px "Inter", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('RADAR EN BÚSQUEDA · SIN CONTACTOS AÉREOS', padL + plotW / 2, padT + plotH / 2);
      if (statusText) {
        statusText.textContent = 'Espacio aéreo despejado';
        statusText.style.color = 'var(--text-muted)';
      }
      return;
    }

    const slotW = plotW / activeDrones.length;
    const now = Date.now();

    activeDrones.forEach((drone, idx) => {
      const alt = drone.altitude || 45;
      const xCenter = padL + slotW * (idx + 0.5);
      const barW = Math.min(26, slotW * 0.55);
      const yTop = getY(alt);
      const yZero = getY(0);
      const barH = Math.max(4, yZero - yTop);

      // Compute vertical speed
      const prev = this.state.previousAltitudes.get(drone.id);
      let vSpeed = 0;
      let vTrend = '▬';
      if (prev) {
        const dt = Math.max(1, (now - prev.time) / 1000);
        vSpeed = (alt - prev.alt) / dt;
        if (vSpeed > 0.3) vTrend = '▲';
        else if (vSpeed < -0.3) vTrend = '▼';
      }
      this.state.previousAltitudes.set(drone.id, { alt, time: now });

      const isViolation = alt > 120;
      if (isViolation) hasViolation = true;

      // Altitude bar gradient
      const grad = ctx.createLinearGradient(0, yZero, 0, yTop);
      if (isViolation) {
        grad.addColorStop(0, 'rgba(255, 23, 68, 0.3)');
        grad.addColorStop(1, '#ff1744');
      } else if (alt >= 90) {
        grad.addColorStop(0, 'rgba(255, 179, 0, 0.2)');
        grad.addColorStop(1, '#ffb300');
      } else {
        grad.addColorStop(0, 'rgba(0, 102, 255, 0.2)');
        grad.addColorStop(1, '#00d4ff');
      }

      // Bar with glow if violation
      ctx.save();
      if (isViolation) {
        ctx.shadowColor = '#ff1744';
        ctx.shadowBlur = 8;
      }
      ctx.fillStyle = grad;
      ctx.beginPath();
      const radius = 3;
      const xLeft = xCenter - barW / 2;
      ctx.roundRect 
        ? ctx.roundRect(xLeft, yTop, barW, barH, [radius, radius, 0, 0])
        : ctx.rect(xLeft, yTop, barW, barH);
      ctx.fill();
      ctx.restore();

      // Top cap indicator / Drone reticle
      ctx.fillStyle = isViolation ? '#ff5252' : '#ffffff';
      ctx.beginPath();
      ctx.arc(xCenter, yTop, 3.5, 0, Math.PI * 2);
      ctx.fill();

      // Label above bar: Altitude & Trend
      ctx.fillStyle = isViolation ? '#ff5252' : '#00d4ff';
      ctx.font = 'bold 9px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${alt.toFixed(0)}m`, xCenter, Math.max(padT + 4, yTop - 12));

      ctx.fillStyle = vTrend === '▲' ? '#ff5252' : vTrend === '▼' ? '#00e676' : '#94a3b8';
      ctx.font = '8px "JetBrains Mono", monospace';
      const speedStr = `${vTrend} ${Math.abs(vSpeed).toFixed(1)}m/s`;
      ctx.fillText(speedStr, xCenter, Math.max(padT + 12, yTop - 3));

      // Drone identifier below axis
      ctx.fillStyle = '#94a3b8';
      ctx.font = '9px "JetBrains Mono", monospace';
      const droneName = drone.id ? `UAV-${String(drone.id).slice(-3).toUpperCase()}` : `D-${idx + 1}`;
      ctx.fillText(droneName, xCenter, height - 8);
    });

    if (statusText) {
      if (hasViolation) {
        statusText.textContent = '⚠️ ALERTA: INFRACCIÓN DE TECHO (>120m)';
        statusText.style.color = 'var(--danger)';
        statusText.style.fontWeight = 'bold';
      } else {
        statusText.textContent = 'Tráfico nominal (<120m)';
        statusText.style.color = 'var(--success)';
        statusText.style.fontWeight = 'normal';
      }
    }
  }

  destroy() {
    this.stopRealtime();
    tacticalAudio.stop();
    if (this._resizeHandler) {
      window.removeEventListener('resize', this._resizeHandler);
    }
    if (this._map) {
      try { this._map.remove(); } catch (e) {}
      this._map = null;
    }
  }
}
