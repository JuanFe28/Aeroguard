import { escapeHtml } from '../utils/html.js';
/**
 * AeroGuard — Zones View + ViewModel (RF-015, RF-016, RF-017)
 * Gestión de zonas restringidas con mapa interactivo y editor de polígonos.
 */

import { ZoneService, MockService, AuthService } from '../services/api.service.js';
import { RestrictedZoneModel, AlertSeverity } from '../models/models.js';
import { Layout, Toast, confirm } from '../app.js';

// ============================================================
// ViewModel
// ============================================================

export class ZonesViewModel {
  constructor() {
    this.state = {
      zones: [],
      isLoading: true,
      selectedZone: null,
      isDrawing: false,
      drawPoints: [],
      showForm: false,
      editingZone: null,
    };
    this._map = null;
    this._polygons = new Map();
    this._drawLayer = null;
    this._tempMarkers = [];
    this._tempLine = null;
  }

  async load() {
    this.state.isLoading = true;
    try {
      let items = [];
      try {
        const res = await ZoneService.list();
        items = Array.isArray(res) ? res : (Array.isArray(res) ? res : (res.items || []));
      } catch (apiErr) {
        if (!MockService.enabled) throw apiErr;
      }

      if (items.length > 0) {
        this.state.zones = items.map(z => new RestrictedZoneModel(z));
        MockService.zones = items;
        MockService.saveZones();
      } else {
        this.state.zones = (MockService.enabled ? MockService.zones || [] : []).map(z => new RestrictedZoneModel(z));
      }
    } catch (err) {
      console.error('Error al cargar zonas:', err);
      this.state.zones = (MockService.enabled ? MockService.zones || [] : []).map(z => new RestrictedZoneModel(z));
      Toast.error('Error al cargar zonas.');
    } finally {
      this.state.isLoading = false;
    }
  }

  initMap(containerId) {
    if (!window.L) { console.error('Leaflet not loaded'); return; }
    const L = window.L;
    const container = document.getElementById(containerId);
    if (!container) return;

    if (this._map) {
      try { this._map.remove(); } catch (e) {}
      this._map = null;
    }
    if (container._leaflet_id) {
      container._leaflet_id = null;
    }

    this._map = L.map(containerId, {
      center: [4.7110, -74.0721],
      zoom: 12,
      zoomControl: false,
    });

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this._map);

    L.control.zoom({ position: 'bottomright' }).addTo(this._map);
    this._plotZones();

    if (this.state.zones.length > 0) {
      const first = this.state.zones[0];
      this._selectZone(first);
    }

    setTimeout(() => { if (this._map) this._map.invalidateSize(); }, 150);
    setTimeout(() => { if (this._map) this._map.invalidateSize(); }, 500);
  }

  fitAllZones() {
    if (!this._map || !this.state.zones.length) return;
    const allPts = [];
    this.state.zones.forEach(z => {
      if (z.polygon?.length) {
        z.polygon.forEach(p => {
          const lat = p.lat ?? p[0];
          const lng = p.lng ?? p[1];
          if (lat != null && lng != null) allPts.push([lat, lng]);
        });
      }
    });
    if (allPts.length) {
      this._map.fitBounds(allPts, { padding: [50, 50] });
    }
  }

  _plotZones() {
    const L = window.L;
    if (!this._map) return;

    // Clear existing
    this._polygons.forEach(p => { if (Array.isArray(p)) p.forEach(x => x.remove()); else p.remove(); });
    this._polygons.clear();

    this.state.zones.forEach(zone => {
      if (!zone.polygon?.length) return;
      const color = zone.severityColor;
      const latlngs = zone.polygon.map(p => [p.lat ?? p[0], p.lng ?? p[1]]);

      const poly = L.polygon(latlngs, {
        color,
        fillColor: color,
        fillOpacity: zone.id === this.state.selectedZone?.id ? 0.25 : 0.12,
        weight: zone.id === this.state.selectedZone?.id ? 3 : 2,
      });

      poly.bindTooltip(`<strong>${escapeHtml(zone.name)}</strong><br>${escapeHtml(zone.description)}`, { sticky: true });
      poly.on('click', () => this._selectZone(zone));
      poly.addTo(this._map);

      // Label in center
      if (zone.center) {
        const label = L.marker(zone.center, {
          icon: L.divIcon({
            className: '',
            html: `<div style="background:${color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.5)">${escapeHtml(zone.name)}</div>`,
            iconAnchor: [0, 0],
          }),
        }).addTo(this._map);
        this._polygons.set(zone.id, [poly, label]);
      } else {
        this._polygons.set(zone.id, [poly]);
      }
    });
  }

  _selectZone(zone) {
    // Si cambia de zona, limpiar dibujo activo
    if (this.state.isDrawing) {
      this.state.isDrawing = false;
      this._cleanupDrawing(true);
      if (this._map && this._onMapClickBound) this._map.off('click', this._onMapClickBound);
      const mapElement = document.getElementById('zones-map');
      if (mapElement) mapElement.style.cursor = '';
    }
    
    this.state.selectedZone = zone;
    this._plotZones();
    this._renderZoneDetail();
    document.querySelectorAll('.zone-card').forEach(el => {
      el.classList.toggle('active', el.dataset.zoneId === zone.id);
    });
    if (zone.center && this._map) {
      this._map.setView([zone.center.lat, zone.center.lng], 14);
    }
  }

  _renderZoneDetail() {
    const panel = document.getElementById('zone-detail-panel');
    if (!panel) return;
    const zone = this.state.selectedZone;
    if (!zone) {
      panel.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🗺️</div><div class="empty-state-title">Selecciona una zona</div></div>`;
      return;
    }

    panel.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:var(--spacing-md)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <h3 style="color:var(--text-primary)">${escapeHtml(zone.name)}</h3>
            <p style="font-size:var(--font-size-sm);color:var(--text-muted)">${escapeHtml(zone.description || 'Sin descripción')}</p>
          </div>
          <span class="badge badge-${zone.severity}">${zone.severity.toUpperCase()}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--spacing-md)">
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:var(--spacing-md)">
            <div style="font-size:var(--font-size-xs);color:var(--text-muted);text-transform:uppercase;letter-spacing:1px">Alt. Mínima</div>
            <div style="font-size:var(--font-size-xl);font-weight:700;color:var(--brand-primary)">${zone.minAltitude} m</div>
          </div>
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:var(--spacing-md)">
            <div style="font-size:var(--font-size-xs);color:var(--text-muted);text-transform:uppercase;letter-spacing:1px">Alt. Máxima</div>
            <div style="font-size:var(--font-size-xl);font-weight:700;color:var(--brand-primary)">${zone.maxAltitude} m</div>
          </div>
        </div>

        <div style="display:flex;align-items:center;gap:var(--spacing-sm)">
          <span class="status-dot ${zone.isActive ? 'status-online' : 'status-offline'}"></span>
          <span style="font-size:var(--font-size-sm);color:${zone.isActive ? 'var(--success)' : 'var(--text-muted)'}">
            ${zone.isActive ? 'Zona activa' : 'Zona inactiva'}
          </span>
        </div>

        <div style="display:flex;gap:var(--spacing-sm);flex-wrap:wrap">
          ${AuthService.getUser()?.role === 'admin' ? `
          <button class="btn btn-${this.state.isDrawing ? 'success' : 'primary'} btn-sm" onclick="zonesVM.toggleDrawingMode()" aria-label="${this.state.isDrawing ? 'Guardar Polígono' : 'Dibujar Polígono'}">
            ${this.state.isDrawing ? '✅ Guardar Polígono' : '🖌️ Dibujar Polígono'}
          </button>
          <button class="btn btn-secondary btn-sm" onclick="zonesVM.openEditForm()" aria-label="Editar zona ${escapeHtml(zone.name)}">✏️ Editar</button>
          <button class="btn btn-danger btn-sm" onclick="zonesVM.deleteZone('${zone.id}')" aria-label="Eliminar zona ${escapeHtml(zone.name)}">🗑️ Eliminar</button>
          <button class="btn btn-${zone.isActive ? 'warning' : 'success'} btn-sm"
            onclick="zonesVM.toggleZone('${zone.id}')"
            aria-label="${zone.isActive ? 'Desactivar' : 'Activar'} zona ${escapeHtml(zone.name)}">
            ${zone.isActive ? '⏸️ Desactivar' : '▶️ Activar'}
          </button>
          ` : ''}
        </div>
      </div>
    `;

    window.zonesVM = this;
  }

  openCreateForm() {
    this.state.editingZone = null;
    this._showZoneModal();
  }

  openEditForm() {
    this.state.editingZone = this.state.selectedZone;
    this._showZoneModal(this.state.editingZone);
  }

  _showZoneModal(zone = null) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'zone-modal';
    overlay.innerHTML = `
      <div class="modal modal-lg">
        <div class="modal-header">
          <h3 class="modal-title">${zone ? '✏️ Editar Zona' : '➕ Nueva Zona Restringida'}</h3>
          <button class="modal-close" id="close-zone-modal" aria-label="Cerrar modal">✕</button>
        </div>
        <form id="zone-form">
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="zone-name">Nombre *</label>
              <input id="zone-name" type="text" class="form-input" required value="${escapeHtml(zone?.name || '')}" placeholder="Nombre de la zona" aria-required="true"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="zone-severity">Severidad *</label>
              <select id="zone-severity" class="form-select" required aria-required="true">
                <option value="low"      ${zone?.severity === 'low'      ? 'selected' : ''}>Baja</option>
                <option value="medium"   ${zone?.severity === 'medium'   ? 'selected' : ''}>Media</option>
                <option value="high"     ${(!zone || zone?.severity === 'high') ? 'selected' : ''}>Alta</option>
                <option value="critical" ${zone?.severity === 'critical' ? 'selected' : ''}>Crítica</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label" for="zone-description">Descripción</label>
            <textarea id="zone-description" class="form-textarea" rows="2" placeholder="Descripción de la zona...">${escapeHtml(zone?.description || '')}</textarea>
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="zone-min-alt">Altitud Mínima (m)</label>
              <input id="zone-min-alt" type="number" class="form-input" value="${zone?.minAltitude ?? 0}" min="0"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="zone-max-alt">Altitud Máxima (m)</label>
              <input id="zone-max-alt" type="number" class="form-input" value="${zone?.maxAltitude ?? 500}" min="0"/>
            </div>
          </div>
          <div class="alert alert-info">
            <span class="alert-icon">ℹ️</span>
            <div class="alert-content">
              <div class="alert-title">Polígono de la zona</div>
              <div class="alert-message">
                ${zone ? `La zona tiene ${zone.polygon?.length || 0} puntos definidos.` : 'La zona se crea inactiva. Selecciónala y usa "Dibujar Zona" para delimitar el polígono y activarla.'}
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="cancel-zone">Cancelar</button>
            <button type="submit" class="btn btn-primary" id="save-zone-btn">
              ${zone ? '💾 Guardar Cambios' : '✅ Crear Zona'}
            </button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.classList.add('visible'), 10);

    overlay.querySelector('#close-zone-modal')?.addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-zone')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    overlay.querySelector('#zone-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (await this._saveZone(zone?.id)) overlay.remove();
    });
  }

  async _saveZone(id = null) {
    const minAlt = parseFloat(document.getElementById('zone-min-alt')?.value || 0);
    const maxAlt = parseFloat(document.getElementById('zone-max-alt')?.value || 500);
    if (!Number.isFinite(minAlt) || !Number.isFinite(maxAlt) || minAlt < 0 || minAlt > maxAlt || maxAlt > 15000) {
      Toast.error('La altitud mínima debe ser menor o igual a la máxima, entre 0 y 15000 m.');
      return false;
    }
    const severity = document.getElementById('zone-severity')?.value || 'high';
    const name = document.getElementById('zone-name')?.value;
    const description = document.getElementById('zone-description')?.value;

    const existing = id ? this.state.zones.find(z => z.id === id) : null;
    const polygon = existing?.polygon || [];
    const coordinates = polygon.map(p => Array.isArray(p) ? [p[0], p[1]] : [p.lat ?? p[0], p.lng ?? p[1]]);

    const data = {
      name,
      description,
      severity,
      threat_level: severity,
      min_altitude: minAlt,
      max_altitude: maxAlt,
      polygon,
      coordinates,
      is_active: existing?.isActive ?? false,
    };

    try {
      let savedZone = null;
      try {
        if (!MockService.enabled && id) savedZone = await ZoneService.update(id, data);
        else if (!MockService.enabled) savedZone = await ZoneService.create(data);
      } catch (apiErr) {
        if (!MockService.enabled) throw apiErr;
      }

      const finalId = savedZone?.id || id || `Z-${Date.now()}`;
      const finalData = savedZone ? { ...data, ...savedZone, id: finalId } : { ...data, id: finalId };

      if (id) {
        const idx = MockService.zones.findIndex(z => z.id === id);
        if (idx >= 0) Object.assign(MockService.zones[idx], finalData);
      } else {
        MockService.zones.push(finalData);
      }
      MockService.saveZones();

      Toast.success(id ? 'Zona actualizada correctamente.' : 'Zona creada correctamente.');
      await this.load();
      this.renderZoneList();
      this._plotZones();
      const updated = this.state.zones.find(z => z.id === finalId);
      if (updated) {
        this.state.selectedZone = updated;
        this._renderZoneDetail();
      }
      return true;
    } catch (err) {
      Toast.error(err.message || 'Error al guardar la zona');
      return false;
    }
  }

  toggleDrawingMode() {
    this.state.isDrawing = !this.state.isDrawing;
    const mapElement = document.getElementById('zones-map');
    
    if (this.state.isDrawing) {
      this.state.drawPoints = [];
      this._cleanupDrawing();
      
      // Activar cursor de crosshair
      if (mapElement) mapElement.style.cursor = 'crosshair';
      
      // Bind click event
      this._onMapClickBound = this._onMapClick.bind(this);
      this._map.on('click', this._onMapClickBound);
      
      Toast.info('Modo dibujo activo: Haz clic en el mapa para trazar los vértices.');
    } else {
      // Finalizar dibujo
      this._cleanupDrawing(false);
      if (mapElement) mapElement.style.cursor = '';
      this._map.off('click', this._onMapClickBound);
      
      if (this.state.drawPoints.length >= 3) {
        this._saveDrawnPolygon();
      } else if (this.state.drawPoints.length > 0) {
        Toast.error('El polígono debe tener al menos 3 vértices.');
      }
      this.state.drawPoints = [];
    }
    
    this._renderZoneDetail();
  }

  _onMapClick(e) {
    if (!this.state.isDrawing) return;
    const L = window.L;
    this.state.drawPoints.push({ lat: e.latlng.lat, lng: e.latlng.lng });
    
    const marker = L.circleMarker(e.latlng, { radius: 5, color: '#ffeb3b', fillColor: '#ffeb3b', fillOpacity: 1 }).addTo(this._map);
    this._tempMarkers.push(marker);
    
    if (this._tempLine) {
      this._tempLine.remove();
    }
    
    this._tempLine = L.polyline(this.state.drawPoints, { color: '#ffeb3b', weight: 3, dashArray: '5, 5' }).addTo(this._map);
  }

  _cleanupDrawing(removePoints = true) {
    this._tempMarkers.forEach(m => m.remove());
    this._tempMarkers = [];
    if (this._tempLine) {
      this._tempLine.remove();
      this._tempLine = null;
    }
    if (removePoints) {
      this.state.drawPoints = [];
    }
  }

  async _saveDrawnPolygon() {
    if (!this.state.selectedZone) return;
    const z = this.state.selectedZone;
    const coords = this.state.drawPoints.map(p => [p.lat, p.lng]);
    const data = {
      name: z.name,
      description: z.description,
      severity: z.severity,
      threat_level: z.severity,
      min_altitude: z.minAltitude,
      max_altitude: z.maxAltitude,
      polygon: this.state.drawPoints,
      coordinates: coords,
      is_active: true,
    };

    try {
      let savedZone = null;
      try {
        savedZone = await ZoneService.update(z.id, data);
      } catch (apiErr) {
        if (!MockService.enabled) throw apiErr;
      }

      // Sync with MockService / localStorage
      const mz = MockService.zones.find(zone => zone.id === z.id);
      if (mz) {
        mz.polygon = this.state.drawPoints;
        mz.coordinates = coords;
      }
      MockService.saveZones();

      Toast.success('Polígono delimitado y guardado correctamente.');
      await this.load();
      this.renderZoneList();
      this._plotZones();
      const updated = this.state.zones.find(zone => zone.id === z.id);
      if (updated) {
        this.state.selectedZone = updated;
        this._renderZoneDetail();
      }
    } catch (err) {
      Toast.error('Error al guardar el polígono: ' + err.message);
    }
  }

  async deleteZone(id) {
    const ok = await confirm('¿Eliminar esta zona restringida? Esta acción no se puede deshacer.', 'Eliminar Zona');
    if (!ok) return;
    try {
      try {
        await ZoneService.delete(id);
      } catch (apiErr) {
        if (!MockService.enabled) throw apiErr;
      }
      const idx = MockService.zones.findIndex(z => z.id === id);
      if (idx >= 0) MockService.zones.splice(idx, 1);
      MockService.saveZones();

      this.state.selectedZone = null;
      Toast.success('Zona eliminada correctamente.');
      await this.load();
      this.renderZoneList();
      this._plotZones();
      document.getElementById('zone-detail-panel').innerHTML = `<div class="empty-state"><div class="empty-state-icon">🗺️</div><div class="empty-state-title">Selecciona una zona</div></div>`;
    } catch (err) {
      Toast.error(err.message);
    }
  }

  async toggleZone(id) {
    const zone = this.state.zones.find(z => z.id === id);
    if (!zone) return;
    const newActive = !zone.isActive;
    try {
      try {
        await ZoneService.update(id, { is_active: newActive });
      } catch (apiErr) {
        if (!MockService.enabled) throw apiErr;
      }
      const mz = MockService.zones.find(z => z.id === id);
      if (mz) mz.is_active = newActive;
      MockService.saveZones();

      Toast.success(`Zona ${newActive ? 'activada' : 'desactivada'}.`);
      await this.load();
      this.renderZoneList();
      this._plotZones();
      const updated = this.state.zones.find(z => z.id === id);
      if (updated) {
        this.state.selectedZone = updated;
        this._renderZoneDetail();
      }
    } catch (err) {
      Toast.error(err.message);
    }
  }

  renderZoneList() {
    const container = document.getElementById('zones-list');
    if (!container) return;

    if (!this.state.zones.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🗺️</div>
          <div class="empty-state-title">Sin zonas configuradas</div>
          <div class="empty-state-message">Crea la primera zona restringida con el botón "Nueva Zona".</div>
        </div>
      `;
      return;
    }

    container.innerHTML = this.state.zones.map(zone => `
      <div class="zone-card ${this.state.selectedZone?.id === zone.id ? 'active' : ''}"
           data-zone-id="${zone.id}"
           onclick="zonesVM._selectZone(zonesVM.state.zones.find(z=>z.id==='${zone.id}'))"
           role="button"
           tabindex="0"
           aria-label="Zona: ${escapeHtml(zone.name)}"
           aria-selected="${this.state.selectedZone?.id === zone.id}">
        <div class="zone-card-header">
          <div>
            <div class="zone-card-name">${escapeHtml(zone.name)}</div>
            <div class="zone-card-id">${zone.id}</div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
            <span class="badge badge-${zone.severity}">${zone.severity}</span>
            <span class="status-dot ${zone.isActive ? 'status-online' : 'status-offline'}" style="width:8px;height:8px;margin-right:4px" title="${zone.isActive ? 'Activa' : 'Inactiva'}"></span>
          </div>
        </div>
        <div class="zone-card-info">
          <span class="zone-info-item">📐 ${zone.polygon?.length || 0} puntos</span>
          <span class="zone-info-item">⬇️ ${zone.minAltitude}m</span>
          <span class="zone-info-item">⬆️ ${zone.maxAltitude}m</span>
        </div>
      </div>
    `).join('');

    window.zonesVM = this;
  }

  bindEvents() {
    document.getElementById('new-zone-btn')?.addEventListener('click', () => this.openCreateForm());
    document.getElementById('btn-jump-bogota')?.addEventListener('click', () => {
      if (this._map) this._map.flyTo([4.7110, -74.0721], 12);
    });
    document.getElementById('btn-jump-buca')?.addEventListener('click', () => {
      if (this._map) this._map.flyTo([7.1265, -73.1848], 13);
    });
    document.getElementById('btn-fit-all')?.addEventListener('click', () => {
      this.fitAllZones();
    });
  }

  destroy() {
    if (this._map) { this._map.remove(); this._map = null; }
  }
}

// ============================================================
// View
// ============================================================

export class ZonesView {
  constructor() { this.vm = new ZonesViewModel(); }

  async render(container) {
    document.title = 'AeroGuard — Zonas Restringidas';
    container.innerHTML = Layout.renderShell('#/zones', 'Zonas Restringidas');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this.vm.bindEvents();
    await this.vm.load();
    this.vm.renderZoneList();
    requestAnimationFrame(() => {
      this.vm.initMap('zones-map');
    });
  }

  _template() {
    return `
<div class="fade-in">
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Zonas Restringidas</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Configuración de polígonos de exclusión aérea</p>
    </div>
    ${AuthService.getUser()?.role === 'admin' ? `
    <button id="new-zone-btn" class="btn btn-primary" aria-label="Crear nueva zona restringida">
      ➕ Nueva Zona
    </button>
    ` : ''}
  </div>

  <div class="zones-split">
    <!-- Map -->
    <div class="map-card" style="min-height:520px;position:relative" role="region" aria-label="Mapa de zonas restringidas">
      <div style="position:absolute;top:12px;left:12px;z-index:500;display:flex;gap:6px;background:rgba(10,14,26,0.88);padding:6px 10px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);box-shadow:0 4px 12px rgba(0,0,0,0.4)">
        <button type="button" id="btn-jump-bogota" class="btn btn-sm btn-secondary" style="font-size:12px;padding:4px 10px">📍 Bogotá</button>
        <button type="button" id="btn-jump-buca" class="btn btn-sm btn-secondary" style="font-size:12px;padding:4px 10px">📍 Bucaramanga</button>
        <button type="button" id="btn-fit-all" class="btn btn-sm btn-secondary" style="font-size:12px;padding:4px 10px">⛶ Ver Todas</button>
      </div>
      <div id="zones-map" class="map-container" style="min-height:520px"></div>
    </div>

    <!-- Zone list + detail -->
    <div style="display:flex;flex-direction:column;gap:var(--spacing-md);overflow-y:auto;max-height:calc(100vh - 200px)">
      <!-- Zone List -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">📍 Zonas Configuradas</div>
        </div>
        <div id="zones-list" style="display:flex;flex-direction:column;gap:var(--spacing-sm)" role="list" aria-label="Lista de zonas restringidas">
          <!-- Rendered by VM -->
        </div>
      </div>

      <!-- Zone Detail -->
      <div class="card" id="zone-detail-panel" role="region" aria-label="Detalle de zona seleccionada">
        <div class="empty-state" style="padding:var(--spacing-xl) 0">
          <div class="empty-state-icon">🗺️</div>
          <div class="empty-state-title">Selecciona una zona</div>
          <div class="empty-state-message">Haz clic en una zona de la lista o del mapa para ver sus detalles.</div>
        </div>
      </div>
    </div>
  </div>
</div>
    `;
  }

  destroy() { this.vm.destroy(); }
}
