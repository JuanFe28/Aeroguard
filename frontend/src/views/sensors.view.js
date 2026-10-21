import { escapeHtml } from '../utils/html.js';
/**
 * AeroGuard — Sensors View + ViewModel (RF-019, RF-020)
 */
import { SensorService, WebSocketService, MockService } from '../services/api.service.js';
import { SensorModel, SensorStatus, SensorType } from '../models/models.js';
import { Layout, Toast, confirm } from '../app.js';

class SensorsViewModel {
  constructor() {
    this.state = { sensors: [], isLoading: true };
    this._unsub = [];
  }

  startRealtime() {
    const unsub = WebSocketService.on('sensor_update', (raw) => {
      if (!raw) return;
      const s = new SensorModel(raw);
      const idx = this.state.sensors.findIndex(x => x.id === s.id);
      if (idx >= 0) {
        this.state.sensors[idx] = s;
      } else {
        this.state.sensors.push(s);
      }
      this.renderGrid();
      this.renderStats();
    });
    this._unsub.push(unsub);
  }

  async load() {
    this.state.isLoading = true;
    try {
      if (MockService.enabled) {
        await new Promise(r => setTimeout(r, 300));
        this.state.sensors = MockService.sensors.map(s => new SensorModel(s));
      } else {
        const res = await SensorService.list();
        this.state.sensors = (Array.isArray(res) ? res : (res.items || [])).map(s => new SensorModel(s));
      }
    } catch (err) { Toast.error('Error al cargar sensores.'); }
    finally { this.state.isLoading = false; }
  }

  async toggleSensor(id, status) {
    const isActive = status === SensorStatus.ACTIVE;
    const ok = await confirm(`¿${isActive ? 'Desactivar' : 'Activar'} este sensor?`, `${isActive ? 'Desactivar' : 'Activar'} Sensor`);
    if (!ok) return;
    try {
      if (MockService.enabled) {
        const s = MockService.sensors.find(s => s.id === id);
        if (s) s.status = isActive ? SensorStatus.INACTIVE : SensorStatus.ACTIVE;
      } else {
        if (isActive) await SensorService.deactivate(id);
        else await SensorService.activate(id);
      }
      Toast.success(`Sensor ${isActive ? 'desactivado' : 'activado'}.`);
      await this.load(); this.renderGrid();
    } catch (err) { Toast.error(err.message); }
  }

  showSensorModal(sensor = null) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">${sensor ? '✏️ Editar Sensor' : '➕ Nuevo Sensor'}</h3>
          <button class="modal-close" id="close-sensor-modal" aria-label="Cerrar">✕</button>
        </div>
        <form id="sensor-form">
          <div class="form-group">
            <label class="form-label" for="sensor-name">Nombre *</label>
            <input id="sensor-name" type="text" class="form-input" required value="${escapeHtml(sensor?.name || '')}" aria-required="true"/>
          </div>
          <div class="form-group">
            <label class="form-label" for="sensor-type">Tipo *</label>
            <select id="sensor-type" class="form-select" required>
              ${Object.values(SensorType).map(t => `<option value="${t}" ${sensor?.type === t ? 'selected' : ''}>${new SensorModel({type:t}).typeLabel}</option>`).join('')}
            </select>
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="sensor-lat">Latitud *</label>
              <input id="sensor-lat" type="number" step="any" class="form-input" required value="${sensor?.latitude || ''}" placeholder="4.7110"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="sensor-lng">Longitud *</label>
              <input id="sensor-lng" type="number" step="any" class="form-input" required value="${sensor?.longitude || ''}" placeholder="-74.0721"/>
            </div>
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="sensor-alt">Altitud (m)</label>
              <input id="sensor-alt" type="number" class="form-input" value="${sensor?.altitude || 0}"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="sensor-range">Rango (km)</label>
              <input id="sensor-range" type="number" step="0.5" class="form-input" value="${sensor?.rangeKm || 5}"/>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="cancel-sensor">Cancelar</button>
            <button type="submit" class="btn btn-primary">${sensor ? '💾 Guardar' : '✅ Agregar Sensor'}</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.classList.add('visible'), 10);
    overlay.querySelector('#close-sensor-modal')?.addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-sensor')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector('#sensor-form')?.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        name: document.getElementById('sensor-name')?.value,
        type: document.getElementById('sensor-type')?.value,
        latitude: parseFloat(document.getElementById('sensor-lat')?.value),
        longitude: parseFloat(document.getElementById('sensor-lng')?.value),
        altitude: parseFloat(document.getElementById('sensor-alt')?.value || 0),
        range_km: parseFloat(document.getElementById('sensor-range')?.value || 5),
        status: SensorStatus.INACTIVE,
      };
      try {
        if (MockService.enabled) {
          if (sensor) Object.assign(MockService.sensors.find(s => s.id === sensor.id), data);
          else MockService.sensors.push({ ...data, id: `SEN-${Date.now()}`, detections_count: 0, last_active: null });
        } else {
          if (sensor) await SensorService.update(sensor.id, data);
          else await SensorService.create(data);
        }
        Toast.success(sensor ? 'Sensor actualizado.' : 'Sensor agregado.');
        overlay.remove();
        await this.load(); this.renderGrid();
      } catch (err) { Toast.error(err.message); }
    });
  }

  renderGrid() {
    const container = document.getElementById('sensors-grid');
    if (!container) return;
    if (!this.state.sensors.length) {
      container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-state-icon">📡</div><div class="empty-state-title">Sin sensores configurados</div></div>`;
      return;
    }
    container.innerHTML = this.state.sensors.map(s => {
      const statusColors = { active: 'var(--success)', inactive: 'var(--neutral)', error: 'var(--danger)' };
      const statusLabels = { active: 'En línea', inactive: 'Inactivo', error: 'Error' };
      const dotClass     = s.status === 'active' ? 'status-online' : s.status === 'error' ? 'status-danger' : 'status-offline';
      return `
        <div class="card" style="position:relative;overflow:hidden" role="article" aria-label="Sensor: ${escapeHtml(s.name)}">
          <div style="position:absolute;top:0;left:0;right:0;height:3px;background:${statusColors[s.status] || 'var(--neutral)'}"></div>
          <div style="display:flex;align-items:center;gap:var(--spacing-md);margin-bottom:var(--spacing-md)">
            <div style="font-size:32px">${s.typeIcon}</div>
            <div style="flex:1;min-width:0">
              <div style="font-weight:700;color:var(--text-primary);font-size:var(--font-size-md)">${escapeHtml(s.name)}</div>
              <div style="font-size:var(--font-size-sm);color:var(--text-muted)">${escapeHtml(s.typeLabel)}</div>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <span class="status-dot ${dotClass}"></span>
              <span style="font-size:var(--font-size-xs);color:${statusColors[s.status]};font-weight:600">${statusLabels[s.status]}</span>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--spacing-sm);margin-bottom:var(--spacing-md)">
            <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius-sm);padding:8px 12px">
              <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase">Detecciones</div>
              <div style="font-size:20px;font-weight:700;color:var(--brand-primary)">${s.detectionsCount}</div>
            </div>
            <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius-sm);padding:8px 12px">
              <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase">Rango</div>
              <div style="font-size:20px;font-weight:700;color:var(--brand-primary)">${s.rangeKm} km</div>
            </div>
          </div>
          <div style="font-size:var(--font-size-xs);color:var(--text-muted);margin-bottom:var(--spacing-md)">
            📍 ${s.latitude?.toFixed(4)}, ${s.longitude?.toFixed(4)} · ${s.altitude}m
            ${s.lastActive ? `· Último: ${new Date(s.lastActive).toLocaleTimeString('es-CO')}` : ''}
          </div>
          <div style="display:flex;gap:var(--spacing-sm)">
            <button class="btn btn-${s.status === 'active' ? 'warning' : 'success'} btn-sm flex-1"
              onclick="sensorsVM.toggleSensor('${s.id}', '${s.status}')"
              aria-label="${s.status === 'active' ? 'Desactivar' : 'Activar'} sensor ${escapeHtml(s.name)}">
              ${s.status === 'active' ? '⏸️ Desactivar' : '▶️ Activar'}
            </button>
            <button class="btn btn-icon" onclick="sensorsVM.showSensorModal(sensorsVM.state.sensors.find(s=>s.id==='${s.id}'))" aria-label="Editar sensor ${escapeHtml(s.name)}" title="Editar">✏️</button>
          </div>
        </div>
      `;
    }).join('');
    window.sensorsVM = this;
  }

  renderStats() {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('stat-sensors-active',   this.state.sensors.filter(s => s.status === 'active').length);
    setEl('stat-sensors-inactive', this.state.sensors.filter(s => s.status === 'inactive').length);
    setEl('stat-sensors-error',    this.state.sensors.filter(s => s.status === 'error').length);
    setEl('stat-sensors-total',    this.state.sensors.length);
  }

  bindEvents() {
    document.getElementById('new-sensor-btn')?.addEventListener('click', () => this.showSensorModal());
    document.getElementById('refresh-sensors-btn')?.addEventListener('click', () => {
      this.load().then(() => { this.renderGrid(); this.renderStats(); });
    });
  }
  destroy() {
    this._unsub.forEach(u => u && u());
    this._unsub = [];
  }
}

export class SensorsView {
  constructor() { this.vm = new SensorsViewModel(); }
  async render(container) {
    document.title = 'AeroGuard — Sensores';
    container.innerHTML = Layout.renderShell('#/sensors', 'Gestión de Sensores');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this.vm.bindEvents();
    this.vm.startRealtime();
    await this.vm.load();
    this.vm.renderStats();
    this.vm.renderGrid();
  }
  _template() {
    return `
<div class="fade-in">
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Gestión de Sensores</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Activación y monitoreo de sensores simulados</p>
    </div>
    <div style="display:flex;gap:var(--spacing-sm)">
      <button id="refresh-sensors-btn" class="btn btn-secondary" aria-label="Actualizar">🔄 Actualizar</button>
      <button id="new-sensor-btn" class="btn btn-primary" aria-label="Agregar sensor">➕ Agregar Sensor</button>
    </div>
  </div>
  <div class="grid-4 mb-lg">
    <div class="stat-card"><div class="stat-card-icon" style="background:rgba(0,230,118,0.1)">📡</div><div class="stat-card-value" style="color:var(--success)" id="stat-sensors-active">—</div><div class="stat-card-label">Activos</div></div>
    <div class="stat-card"><div class="stat-card-icon" style="background:rgba(84,110,122,0.1)">📡</div><div class="stat-card-value" style="color:var(--neutral)" id="stat-sensors-inactive">—</div><div class="stat-card-label">Inactivos</div></div>
    <div class="stat-card"><div class="stat-card-icon" style="background:rgba(255,23,68,0.1)">⚠️</div><div class="stat-card-value" style="color:var(--danger)" id="stat-sensors-error">—</div><div class="stat-card-label">Con Error</div></div>
    <div class="stat-card"><div class="stat-card-icon" style="background:rgba(0,212,255,0.1)">🔢</div><div class="stat-card-value" id="stat-sensors-total">—</div><div class="stat-card-label">Total</div></div>
  </div>
  <div class="grid-auto" id="sensors-grid" role="list" aria-label="Lista de sensores" aria-live="polite">
    <!-- Rendered by VM -->
  </div>
</div>`;
  }
  destroy() { this.vm.destroy(); }
}
