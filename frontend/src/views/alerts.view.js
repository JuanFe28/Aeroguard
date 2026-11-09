import { escapeHtml } from '../utils/html.js';
/**
 * AeroGuard — Alerts View + ViewModel (RF-012 to RF-014)
 */

import { AlertService, WebSocketService, MockService } from '../services/api.service.js';
import { AlertModel } from '../models/models.js';
import { Layout, Toast, confirm } from '../app.js';

// ============================================================
// ViewModel
// ============================================================

export class AlertsViewModel {
  constructor() {
    this.state = {
      alerts: [],
      filtered: [],
      isLoading: true,
      filterStatus: '',
      filterSeverity: '',
    };
    this._unsub = [];
  }

  startRealtime() {
    const unsub = WebSocketService.on('alert_new', (raw) => {
      if (!raw) return;
      const a = new AlertModel(raw);
      const idx = this.state.alerts.findIndex(x => x.id === a.id);
      if (idx >= 0) {
        this.state.alerts[idx] = a;
      } else {
        this.state.alerts.unshift(a);
      }
      this._applyFilters();
      this.renderStats();
      this.renderList();
    });
    this._unsub.push(unsub);
  }

  async load() {
    this.state.isLoading = true;
    try {
      if (MockService.enabled) {
        await new Promise(r => setTimeout(r, 300));
        this.state.alerts = MockService.alerts.map(a => new AlertModel(a));
      } else {
        const res = await AlertService.list({
          status: this.state.filterStatus || undefined,
          severity: this.state.filterSeverity || undefined,
        });
        this.state.alerts = (Array.isArray(res) ? res : (res.items || [])).map(a => new AlertModel(a));
      }
      this._applyFilters();
    } catch (err) {
      Toast.error('Error al cargar alertas.');
    } finally {
      this.state.isLoading = false;
    }
  }

  _applyFilters() {
    let list = [...this.state.alerts];
    if (this.state.filterStatus)   list = list.filter(a => a.status === this.state.filterStatus);
    if (this.state.filterSeverity) list = list.filter(a => a.severity === this.state.filterSeverity);
    this.state.filtered = list;
  }

  async resolveAlert(id) {
    const ok = await confirm('¿Marcar esta alerta como resuelta?', 'Resolver Alerta');
    if (!ok) return;
    try {
      if (MockService.enabled) {
        const alert = MockService.alerts.find(a => a.id === id);
        if (alert) alert.status = 'resolved';
      } else {
        await AlertService.resolve(id, 'Resuelta desde el panel');
      }
      Toast.success('Alerta marcada como resuelta.');
      await this.load();
      this.renderList();
    } catch (err) {
      Toast.error(err.message);
    }
  }

  async assignAlert(id, userId) {
    try {
      if (!MockService.enabled) await AlertService.assign(id, userId);
      const alert = this.state.alerts.find(a => a.id === id);
      if (alert) alert.status = 'assigned';
      Toast.success('Alerta asignada correctamente.');
      await this.load();
      this.renderList();
    } catch (err) {
      Toast.error(err.message);
    }
  }

  renderList() {
    const container = document.getElementById('alerts-list');
    if (!container) return;

    if (this.state.isLoading) {
      container.innerHTML = Array(4).fill(0).map(() => `
        <div class="card" style="padding:var(--spacing-lg)">
          <div class="skeleton" style="height:16px;width:60%;border-radius:4px;margin-bottom:8px"></div>
          <div class="skeleton" style="height:12px;width:85%;border-radius:4px"></div>
        </div>
      `).join('');
      return;
    }

    if (!this.state.filtered.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">✅</div>
          <div class="empty-state-title">Sin alertas</div>
          <div class="empty-state-message">No hay alertas con los filtros seleccionados.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = this.state.filtered.map(a => `
      <div class="card" data-alert-id="${escapeHtml(a.id)}" style="border-left:4px solid var(--severity-${a.severity})" role="article" aria-label="Alerta: ${escapeHtml(a.title)}">
        <div class="card-header" style="margin-bottom:var(--spacing-sm)">
          <div style="display:flex;align-items:center;gap:var(--spacing-sm)">
            <span style="font-size:20px">${a.severityIcon}</span>
            <div>
              <div style="font-weight:600;color:var(--text-primary)">${escapeHtml(a.title)}</div>
              <div style="display:flex;gap:var(--spacing-sm);margin-top:4px">
                <span class="badge badge-${a.severity}">${a.severity.toUpperCase()}</span>
                <span class="badge ${a.status === 'open' ? 'badge-danger' : a.status === 'assigned' ? 'badge-warning' : 'badge-success'}">${a.status}</span>
                <span class="badge badge-info">${escapeHtml(a.typeLabel)}</span>
              </div>
            </div>
          </div>
          <div style="text-align:right">
            <div style="font-size:var(--font-size-xs);color:var(--text-muted)">${a.formattedTime}</div>
            ${a.zoneName ? `<div style="font-size:var(--font-size-xs);color:var(--brand-primary)">📍 ${escapeHtml(a.zoneName)}</div>` : ''}
          </div>
        </div>
        <p style="color:var(--text-secondary);font-size:var(--font-size-sm);margin-bottom:var(--spacing-md)">${escapeHtml(a.description)}</p>
        <div style="display:flex;gap:var(--spacing-sm);flex-wrap:wrap">
          ${a.status !== 'resolved' ? `
            <button class="btn btn-success btn-sm" onclick="alertsVM.resolveAlert('${a.id}')" aria-label="Resolver alerta ${escapeHtml(a.title)}">
              ✅ Resolver
            </button>
            <button class="btn btn-warning btn-sm" onclick="alertsVM.assignAlert('${a.id}', null)" aria-label="Asignar alerta ${escapeHtml(a.title)}">
              👤 Asignar
            </button>
          ` : ''}
          ${a.latitude && a.longitude ? `
            <button class="btn btn-secondary btn-sm" onclick="window.location.hash='#/dashboard'" aria-label="Ver en mapa">
              🗺️ Ver en mapa
            </button>
          ` : ''}
          ${a.detectionId ? `
            <a href="#/trajectory?detection=${encodeURIComponent(a.detectionId)}" class="btn btn-secondary btn-sm" aria-label="Ver detección relacionada">
              🎯 Ver detección
            </a>
          ` : ''}
        </div>
      </div>
    `).join('');

    // Expose VM globally for inline handlers
    window.alertsVM = this;
  }

  renderStats() {
    const open     = this.state.alerts.filter(a => a.status === 'open').length;
    const assigned = this.state.alerts.filter(a => a.status === 'assigned').length;
    const resolved = this.state.alerts.filter(a => a.status === 'resolved').length;
    const critical = this.state.alerts.filter(a => a.severity === 'critical').length;

    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('stat-alerts-open', open);
    setEl('stat-alerts-assigned', assigned);
    setEl('stat-alerts-resolved', resolved);
    setEl('stat-alerts-critical', critical);
  }

  bindEvents() {
    document.getElementById('filter-alert-status')?.addEventListener('change', (e) => {
      this.state.filterStatus = e.target.value;
      this._applyFilters();
      this.renderList();
    });
    document.getElementById('filter-alert-severity')?.addEventListener('change', (e) => {
      this.state.filterSeverity = e.target.value;
      this._applyFilters();
      this.renderList();
    });
    document.getElementById('refresh-alerts-btn')?.addEventListener('click', () => {
      this.load().then(() => { this.renderList(); this.renderStats(); });
    });
  }

  destroy() {
    this._unsub.forEach(u => u && u());
    this._unsub = [];
  }
}

// ============================================================
// View
// ============================================================

export class AlertsView {
  constructor() { this.vm = new AlertsViewModel(); }

  async render(container) {
    document.title = 'AeroGuard — Alertas';
    container.innerHTML = Layout.renderShell('#/alerts', 'Gestión de Alertas');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this.vm.bindEvents();
    this.vm.startRealtime();
    await this.vm.load();
    this.vm.renderStats();
    this.vm.renderList();
  }

  _template() {
    return `
<div class="fade-in">
  <!-- Header -->
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Gestión de Alertas</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Monitoreo y resolución de alertas del sistema</p>
    </div>
    <button id="refresh-alerts-btn" class="btn btn-secondary">🔄 Actualizar</button>
  </div>

  <!-- Stats -->
  <div class="grid-4 mb-lg">
    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(255,23,68,0.1)">🔴</div>
      <div class="stat-card-value" style="color:var(--danger)" id="stat-alerts-open">—</div>
      <div class="stat-card-label">Abiertas</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(255,179,0,0.1)">🟡</div>
      <div class="stat-card-value" style="color:var(--warning)" id="stat-alerts-assigned">—</div>
      <div class="stat-card-label">Asignadas</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(0,230,118,0.1)">✅</div>
      <div class="stat-card-value" style="color:var(--success)" id="stat-alerts-resolved">—</div>
      <div class="stat-card-label">Resueltas</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(255,23,68,0.15)">🚨</div>
      <div class="stat-card-value" style="color:var(--severity-critical)" id="stat-alerts-critical">—</div>
      <div class="stat-card-label">Críticas</div>
    </div>
  </div>

  <!-- Filters -->
  <div class="card mb-lg">
    <div class="filter-bar">
      <select id="filter-alert-status" class="form-select" style="width:180px" aria-label="Filtrar por estado">
        <option value="">Todos los estados</option>
        <option value="open">Abiertas</option>
        <option value="assigned">Asignadas</option>
        <option value="resolved">Resueltas</option>
        <option value="closed">Cerradas</option>
      </select>
      <select id="filter-alert-severity" class="form-select" style="width:180px" aria-label="Filtrar por severidad">
        <option value="">Todas las severidades</option>
        <option value="critical">Crítica</option>
        <option value="high">Alta</option>
        <option value="medium">Media</option>
        <option value="low">Baja</option>
      </select>
    </div>
  </div>

  <!-- Alert List -->
  <div id="alerts-list" style="display:flex;flex-direction:column;gap:var(--spacing-md)" role="region" aria-live="polite" aria-label="Lista de alertas">
    <!-- Rendered by VM -->
  </div>
</div>
    `;
  }

  destroy() { this.vm.destroy(); }
}
