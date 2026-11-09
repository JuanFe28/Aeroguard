import { escapeHtml } from '../utils/html.js';
/**
 * AeroGuard — Reports, History & Audit Views (RF-023 to RF-029)
 */
import { ReportService, AuditService, DetectionService, ConfigService, MockService } from '../services/api.service.js';
import { AuditLogModel } from '../models/models.js';
import { Layout, Toast } from '../app.js';

// ============================================================
// REPORTS VIEW
// ============================================================

export class ReportsView {
  async render(container) {
    document.title = 'AeroGuard — Reportes';
    container.innerHTML = Layout.renderShell('#/reports', 'Reportes y Exportación');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this._bindEvents();
    await this._loadSchedules();
  }

  _template() {
    return `
<div class="fade-in">
  <div class="mb-lg">
    <h2 style="color:var(--text-primary)">Reportes y Exportación</h2>
    <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Genera reportes en PDF, exporta datos históricos y programa reportes automáticos</p>
  </div>

  <!-- Quick Generate -->
  <div class="grid-2 mb-lg">
    <!-- Report Card: Detections -->
    <div class="card">
      <div class="card-header">
        <div style="display:flex;align-items:center;gap:var(--spacing-md)">
          <div style="width:48px;height:48px;background:rgba(0,212,255,0.1);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:24px">🎯</div>
          <div>
            <div class="card-title">Reporte de Detecciones</div>
            <div class="card-subtitle">Estadísticas, gráficas y mapa de calor</div>
          </div>
        </div>
      </div>
      <div class="grid-2 mb-md">
        <div class="form-group" style="margin:0">
          <label class="form-label" for="det-date-from">Desde</label>
          <input id="det-date-from" type="date" class="form-input" aria-label="Fecha inicial del reporte de detecciones"/>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label" for="det-date-to">Hasta</label>
          <input id="det-date-to" type="date" class="form-input" aria-label="Fecha final del reporte de detecciones"/>
        </div>
      </div>
      <div style="display:flex;gap:var(--spacing-sm)">
        <button class="btn btn-primary btn-sm" id="gen-det-pdf" aria-label="Generar PDF de detecciones">📄 Generar PDF</button>
        <button class="btn btn-secondary btn-sm" id="gen-det-csv" aria-label="Exportar CSV de detecciones">📊 Exportar CSV</button>
        <button class="btn btn-secondary btn-sm" id="gen-det-excel" aria-label="Exportar Excel de detecciones">📗 Exportar Excel</button>
      </div>
    </div>

    <!-- Report Card: Alerts -->
    <div class="card">
      <div class="card-header">
        <div style="display:flex;align-items:center;gap:var(--spacing-md)">
          <div style="width:48px;height:48px;background:rgba(255,23,68,0.1);border-radius:var(--radius-md);display:flex;align-items:center;justify-content:center;font-size:24px">🔔</div>
          <div>
            <div class="card-title">Reporte de Alertas</div>
            <div class="card-subtitle">Historial y análisis de alertas</div>
          </div>
        </div>
      </div>
      <div class="grid-2 mb-md">
        <div class="form-group" style="margin:0">
          <label class="form-label" for="alt-date-from">Desde</label>
          <input id="alt-date-from" type="date" class="form-input" aria-label="Fecha inicial del reporte de alertas"/>
        </div>
        <div class="form-group" style="margin:0">
          <label class="form-label" for="alt-date-to">Hasta</label>
          <input id="alt-date-to" type="date" class="form-input" aria-label="Fecha final del reporte de alertas"/>
        </div>
      </div>
      <div style="display:flex;gap:var(--spacing-sm)">
        <button class="btn btn-primary btn-sm" id="gen-alt-pdf" aria-label="Generar PDF de alertas">📄 Generar PDF</button>
        <button class="btn btn-secondary btn-sm" id="gen-alt-csv" aria-label="Exportar CSV de alertas">📊 Exportar CSV</button>
      </div>
    </div>
  </div>

  <!-- Scheduled Reports -->
  <div class="card mb-lg">
    <div class="card-header">
      <div>
        <div class="card-title">⏰ Reportes Programados</div>
        <div class="card-subtitle">Generación automática periódica</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="new-schedule-btn" aria-label="Programar nuevo reporte">➕ Programar</button>
    </div>
    <form id="schedule-form" class="hidden">
      <label>Nombre <input class="form-input" name="name" required maxlength="128"></label>
      <label>Cron (UTC) <input class="form-input" name="cron" value="0 8 * * *" required></label>
      <label>Formato <select class="form-input" name="format"><option>pdf</option><option>csv</option><option>excel</option></select></label>
      <button class="btn btn-primary" type="submit">Guardar programación</button>
    </form>
    <div id="schedules-list" aria-live="polite">Consultando programaciones...</div>
  </div>

  <!-- Status / Progress -->
  <div id="report-status" class="hidden">
    <div class="alert alert-info">
      <span class="alert-icon"><span class="loading-spinner" style="width:20px;height:20px;border-width:2px;vertical-align:middle"></span></span>
      <div class="alert-content">
        <div class="alert-title">Generando reporte...</div>
        <div class="alert-message">Este proceso puede tomar hasta 30 segundos. El archivo se descargará automáticamente.</div>
      </div>
    </div>
  </div>
</div>`;
  }

  _bindEvents() {
    const handleDownload = async (type, format) => {
      const statusEl = document.getElementById('report-status');
      if (statusEl) statusEl.classList.remove('hidden');

      try {
        let res;
        const dateFrom = type === 'detections'
          ? document.getElementById('det-date-from')?.value
          : document.getElementById('alt-date-from')?.value;
        const dateTo = type === 'detections'
          ? document.getElementById('det-date-to')?.value
          : document.getElementById('alt-date-to')?.value;

        if (format === 'pdf') {
          res = await ReportService.downloadPdf(type, dateFrom, dateTo);
        } else if (format === 'csv') {
          res = await ReportService.downloadCsv(type, dateFrom, dateTo);
        } else {
          res = await ReportService.downloadExcel(type, dateFrom, dateTo);
        }

        const shaShort = res?.sha256 ? `${res.sha256.substring(0, 16)}...` : 'VERIFICADO';
        Toast.success(`Archivo "${res?.filename || 'reporte'}" descargado exitosamente. Sello SHA-256: [${shaShort}]`);
      } catch (err) {
        Toast.error(err.message || 'Error al generar el reporte.');
      } finally {
        if (statusEl) statusEl.classList.add('hidden');
      }
    };

    document.getElementById('gen-det-pdf')?.addEventListener('click',   () => handleDownload('detections', 'pdf'));
    document.getElementById('gen-det-csv')?.addEventListener('click',   () => handleDownload('detections', 'csv'));
    document.getElementById('gen-det-excel')?.addEventListener('click', () => handleDownload('detections', 'excel'));
    document.getElementById('gen-alt-pdf')?.addEventListener('click',   () => handleDownload('alerts', 'pdf'));
    document.getElementById('gen-alt-csv')?.addEventListener('click',   () => handleDownload('alerts', 'csv'));

    document.getElementById('new-schedule-btn')?.addEventListener('click', () => {
      document.getElementById('schedule-form')?.classList.toggle('hidden');
    });
  }
  async _loadSchedules() {
    const target = document.getElementById('schedules-list');
    if (!target) return;
    try {
      const items = await ReportService.getSchedules();
      target.innerHTML = items.length ? items.map(item => `<div class="card"><strong>${escapeHtml(item.name)}</strong> · ${escapeHtml(item.cron_expr)} UTC · ${escapeHtml(item.format)} · ${item.is_active ? 'Activo' : 'Inactivo'} <button class="btn btn-secondary" data-delete-schedule="${escapeHtml(item.id)}">Eliminar</button></div>`).join('') : '<p>No hay reportes programados.</p>';
      target.querySelectorAll('[data-delete-schedule]').forEach(button => button.addEventListener('click', async () => {
        try { await ReportService.deleteSchedule(button.dataset.deleteSchedule); await this._loadSchedules(); }
        catch (error) { Toast.error(error.message); }
      }));
    } catch (error) { target.textContent = error.message; }
    const form = document.getElementById('schedule-form');
    if (form && !form.dataset.bound) {
      form.dataset.bound = 'true';
      form.addEventListener('submit', async event => {
        event.preventDefault();
        try {
          await ReportService.createSchedule({name: form.elements.name.value, cron_expr: form.elements.cron.value, format: form.elements.format.value, report_type: 'detections'});
          form.classList.add('hidden'); await this._loadSchedules(); Toast.success('Programación guardada.');
        } catch (error) { Toast.error(error.message); }
      });
    }
  }


  destroy() {}
}

// ============================================================
// HISTORY VIEW
// ============================================================

export class HistoryView {
  async render(container) {
    document.title = 'AeroGuard — Historial';
    container.innerHTML = Layout.renderShell('#/history', 'Historial de Detecciones');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this._loadHistory();
    this._bindEvents();
  }

  async _loadHistory() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    await new Promise(r => setTimeout(r, 300));
    let items;
    try { items = MockService.enabled ? MockService.detections.slice().reverse() : await DetectionService.list(); }
    catch (error) { Toast.error(error.message); return; }
    tbody.innerHTML = items.map(d => {
      const dm = { ...d };
      return `
        <tr>
          <td style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted)">${dm.id}</td>
          <td style="color:var(--text-secondary)">${escapeHtml(dm.sensor_name)}</td>
          <td style="font-size:12px">
            <div style="color:var(--text-primary)">${(dm.latitude||0).toFixed(5)}, ${(dm.longitude||0).toFixed(5)}</div>
            <div style="color:var(--text-muted)">Alt ${(dm.altitude||0).toFixed(0)}m · ${(dm.speed||0).toFixed(1)} km/h</div>
          </td>
          <td><span class="badge badge-${dm.threat_level === 'critical' ? 'critical' : dm.threat_level === 'high' ? 'high' : dm.threat_level === 'medium' ? 'medium' : 'low'}">${(dm.threat_level||'low').toUpperCase()}</span></td>
          <td style="font-size:12px;color:${dm.is_drone ? 'var(--danger)' : 'var(--success)'}">${dm.is_drone ? '⚠️ Posible dron' : '✅ No dron'} (${((dm.ai_confidence||0)*100).toFixed(0)}%)</td>
          <td><span class="badge ${dm.status === 'active' ? 'badge-danger' : dm.status === 'resolved' ? 'badge-success' : 'badge-neutral'}">${dm.status}</span></td>
          <td style="font-size:12px;color:var(--text-muted)">${dm.timestamp ? new Date(dm.timestamp).toLocaleString('es-CO', {dateStyle:'short', timeStyle:'medium'}) : '—'}</td>
        </tr>
      `;
    }).join('');
  }

  _bindEvents() {
    document.getElementById('export-history-csv')?.addEventListener('click', () => {
      ReportService.downloadCsv().catch(error => Toast.error(error.message));
    });
    document.getElementById('export-history-excel')?.addEventListener('click', () => {
      ReportService.downloadExcel().catch(error => Toast.error(error.message));
    });
  }

  _template() {
    return `
<div class="fade-in">
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Historial de Detecciones</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Registro histórico completo de todas las detecciones procesadas</p>
    </div>
    <div style="display:flex;gap:var(--spacing-sm)">
      <button id="export-history-csv"   class="btn btn-secondary" aria-label="Exportar historial CSV">📊 Exportar CSV</button>
      <button id="export-history-excel" class="btn btn-secondary" aria-label="Exportar historial Excel">📗 Exportar Excel</button>
    </div>
  </div>
  <div class="card" style="padding:0">
    <div class="table-container">
      <table class="table" role="grid" aria-label="Historial de detecciones">
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Sensor</th>
            <th scope="col">Ubicación</th>
            <th scope="col">Amenaza</th>
            <th scope="col">IA</th>
            <th scope="col">Estado</th>
            <th scope="col">Timestamp</th>
          </tr>
        </thead>
        <tbody id="history-tbody" aria-live="polite">
          ${Array(5).fill(0).map(() => `<tr>${Array(7).fill(0).map(() => `<td><div class="skeleton" style="height:12px;width:75%;border-radius:4px"></div></td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>
</div>`;
  }

  destroy() {}
}

// ============================================================
// AUDIT VIEW
// ============================================================

export class AuditView {
  async render(container) {
    document.title = 'AeroGuard — Auditoría';
    container.innerHTML = Layout.renderShell('#/audit', 'Auditoría del Sistema');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this._loadAudit();
  }

  async _loadAudit() {
    const tbody = document.getElementById('audit-tbody');
    if (!tbody) return;
    await new Promise(r => setTimeout(r, 400));

    // Mock audit logs
    let logs = MockService.enabled ? [
      { id:'AUD-1', username:'admin',     action:'LOGIN',          resource:'auth',        ip:'192.168.1.10', timestamp: new Date(Date.now()-3600000).toISOString(),  integrity_ok: true },
      { id:'AUD-2', username:'operator1', action:'VIEW_DETECTION', resource:'detection',   ip:'192.168.1.20', timestamp: new Date(Date.now()-3200000).toISOString(),  integrity_ok: true },
      { id:'AUD-3', username:'admin',     action:'CREATE_ZONE',    resource:'zone',        ip:'192.168.1.10', timestamp: new Date(Date.now()-2800000).toISOString(),  integrity_ok: true },
      { id:'AUD-4', username:'analyst1',  action:'EXPORT_DATA',    resource:'history',     ip:'192.168.1.30', timestamp: new Date(Date.now()-2400000).toISOString(),  integrity_ok: true },
      { id:'AUD-5', username:'admin',     action:'RESOLVE_ALERT',  resource:'alert',       ip:'192.168.1.10', timestamp: new Date(Date.now()-1800000).toISOString(),  integrity_ok: true },
      { id:'AUD-6', username:'operator1', action:'VIEW_DASHBOARD', resource:'dashboard',   ip:'192.168.1.20', timestamp: new Date(Date.now()-1200000).toISOString(),  integrity_ok: true },
      { id:'AUD-7', username:'admin',     action:'UPDATE_CONFIG',  resource:'config',      ip:'192.168.1.10', timestamp: new Date(Date.now()-600000).toISOString(),   integrity_ok: true },
      { id:'AUD-8', username:'analyst1',  action:'GENERATE_REPORT',resource:'report',      ip:'192.168.1.30', timestamp: new Date(Date.now()-300000).toISOString(),   integrity_ok: true },
    ] : [];
    if (!MockService.enabled) {
      try { const verification = await AuditService.verifyIntegrity(); logs = (await AuditService.list()).map(log => ({...log, integrity_ok: verification.valid})); } catch (error) { Toast.error(error.message); return; }
    }
    logs = logs.map(l => new AuditLogModel(l));

    tbody.innerHTML = logs.map(log => `
      <tr>
        <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">${log.id}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="user-avatar" style="width:28px;height:28px;font-size:10px">${escapeHtml((log.username?.[0] || '?').toUpperCase())}</div>
            <span style="font-size:var(--font-size-sm);color:var(--text-primary)">${escapeHtml(log.username)}</span>
          </div>
        </td>
        <td><span class="badge badge-info" style="font-family:var(--font-mono)">${escapeHtml(log.action)}</span></td>
        <td style="color:var(--text-secondary);font-size:var(--font-size-sm)">${escapeHtml(log.resource)}</td>
        <td style="font-size:12px;color:var(--text-muted);font-family:var(--font-mono)">${escapeHtml(log.ip)}</td>
        <td>
          <span class="badge ${log.integrityOk ? 'badge-success' : 'badge-danger'}">
            ${log.integrityOk === null ? 'Sin verificación completa' : log.integrityOk ? '✅ Íntegro' : '⚠️ Alterado'}
          </span>
        </td>
        <td style="font-size:12px;color:var(--text-muted)">${log.formattedTime}</td>
      </tr>
    `).join('');
  }

  _template() {
    return `
<div class="fade-in">
  <div class="mb-lg">
    <h2 style="color:var(--text-primary)">Auditoría del Sistema</h2>
    <p style="color:var(--text-muted);font-size:var(--font-size-sm)">
      Registro de operaciones críticas con verificación de integridad mediante hashes.
    </p>
  </div>
  <div class="alert alert-info mb-lg">
    <span class="alert-icon">🔒</span>
    <div class="alert-content">
      <div class="alert-title">Registros de Solo Lectura</div>
      <div class="alert-message">La API expone los registros en modo de solo lectura. La integridad se verifica mediante hashes criptográficos SHA-256 encadenados.</div>
    </div>
  </div>
  <div class="card" style="padding:0">
    <div class="table-container">
      <table class="table" role="grid" aria-label="Registros de auditoría">
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Usuario</th>
            <th scope="col">Acción</th>
            <th scope="col">Recurso</th>
            <th scope="col">IP</th>
            <th scope="col">Integridad</th>
            <th scope="col">Timestamp</th>
          </tr>
        </thead>
        <tbody id="audit-tbody" aria-live="polite">
          ${Array(5).fill(0).map(() => `<tr>${Array(7).fill(0).map(() => `<td><div class="skeleton" style="height:12px;width:75%;border-radius:4px"></div></td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>
</div>`;
  }

  destroy() {}
}

// ============================================================
// DETECTION CONFIG VIEW (RF-018)
// ============================================================

export class DetectionConfigView {
  async render(container) {
    document.title = 'AeroGuard — Configuración de Detección';
    container.innerHTML = Layout.renderShell('#/detection-config', 'Configuración de Detección');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this._bindEvents();
    try {
      const config = await ConfigService.get();
      const fields = {'conf-max-altitude':'detection_max_altitude', 'conf-min-speed':'detection_min_speed', 'conf-max-speed':'detection_max_speed', 'conf-anomaly-threshold':'anomaly_threshold'};
      for (const [id, key] of Object.entries(fields)) document.getElementById(id).value = config[key];
      document.getElementById('conf-min-confidence').value = config.ai_confidence_threshold * 100;
      document.getElementById('conf-min-confidence-val').textContent = `${config.ai_confidence_threshold * 100}%`;
      document.getElementById('conf-ai-enabled').checked = config.ai_enabled;
      document.getElementById('conf-alerts-enabled').checked = config.alerts_enabled;
    } catch (error) { Toast.error(error.message); }
  }

  _template() {
    return `
<div class="fade-in" style="max-width:700px">
  <div class="mb-lg">
    <h2 style="color:var(--text-primary)">Parámetros de Detección</h2>
    <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Configura los umbrales y parámetros del sistema de detección y IA</p>
  </div>

  <form id="config-form">
    <div class="card mb-lg">
      <div class="card-header"><div class="card-title">🤖 Parámetros de IA</div></div>
      <div class="form-group">
        <label class="form-label" for="conf-min-confidence">Confianza mínima para clasificar como posible dron (%)</label>
        <input id="conf-min-confidence" type="range" min="50" max="99" value="70" class="form-input" style="padding:6px 0" aria-label="Confianza mínima"/>
        <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted)">
          <span>50%</span>
          <span id="conf-min-confidence-val" style="color:var(--brand-primary);font-weight:700">70%</span>
          <span>99%</span>
        </div>
      </div>

    </div>

    <div class="card mb-lg">
      <div class="card-header"><div class="card-title">✈️ Filtros de Telemetría</div></div>
      <div class="grid-2">
        <div class="form-group">
          <label class="form-label" for="conf-max-altitude">Altitud máxima (m)</label>
          <input id="conf-max-altitude" type="number" class="form-input" value="1000" min="50" max="5000" aria-label="Altitud máxima"/>
        </div>
        <div class="form-group">
          <label class="form-label" for="conf-anomaly-threshold">Umbral de anomalía (σ)</label>
          <input id="conf-anomaly-threshold" type="number" step="0.1" class="form-input" value="2.5" min="1" max="5" aria-label="Umbral de detección de anomalías"/>
        </div>
        <div class="form-group">
          <label class="form-label" for="conf-min-speed">Velocidad mínima (km/h)</label>
          <input id="conf-min-speed" type="number" class="form-input" value="0" min="0" aria-label="Velocidad mínima"/>
        </div>
        <div class="form-group" style="margin-bottom:0">
          <label class="form-label" for="conf-max-speed">Velocidad máxima (km/h)</label>
          <input id="conf-max-speed" type="number" class="form-input" value="300" min="10" aria-label="Velocidad máxima"/>
        </div>
      </div>
    </div>

    <div class="card mb-lg">
      <div class="card-header"><div class="card-title">🔔 Alertas</div></div>
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:var(--spacing-sm);cursor:pointer">
          <input type="checkbox" id="conf-alerts-enabled" checked style="accent-color:var(--brand-primary);width:18px;height:18px" aria-label="Habilitar alertas automáticas"/>
          <span style="color:var(--text-secondary)">Alertas automáticas habilitadas</span>
        </label>
      </div>
      <div class="form-group" style="margin-bottom:0">
        <label style="display:flex;align-items:center;gap:var(--spacing-sm);cursor:pointer">
          <input type="checkbox" id="conf-ai-enabled" checked style="accent-color:var(--brand-primary);width:18px;height:18px" aria-label="Habilitar análisis experimental de IA"/>
          <span style="color:var(--text-secondary)">Análisis experimental de IA habilitado</span>
        </label>
      </div>
    </div>

    <div style="display:flex;gap:var(--spacing-md)">
      <button type="submit" class="btn btn-primary" id="save-config-btn" aria-label="Guardar configuración">💾 Guardar Configuración</button>
      <button type="button" class="btn btn-secondary" id="reset-config-btn" aria-label="Restablecer configuración predeterminada">↩️ Restablecer</button>
    </div>
  </form>
</div>`;
  }

  _bindEvents() {
    // Live slider value
    const slider = document.getElementById('conf-min-confidence');
    const valEl  = document.getElementById('conf-min-confidence-val');
    slider?.addEventListener('input', () => {
      if (valEl) valEl.textContent = `${slider.value}%`;
    });

    document.getElementById('config-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('save-config-btn');
      if (btn) btn.textContent = 'Guardando...';
      try {
        await ConfigService.update({
          detection_max_altitude: Number(document.getElementById('conf-max-altitude').value),
          detection_min_speed: Number(document.getElementById('conf-min-speed').value),
          detection_max_speed: Number(document.getElementById('conf-max-speed').value),
          anomaly_threshold: Number(document.getElementById('conf-anomaly-threshold').value),
          ai_confidence_threshold: Number(slider.value) / 100,
          ai_enabled: document.getElementById('conf-ai-enabled').checked,
          alerts_enabled: document.getElementById('conf-alerts-enabled').checked
        });
        Toast.success('Configuración persistida correctamente.');
      } catch (error) { Toast.error(error.message); }
      if (btn) btn.textContent = '💾 Guardar Configuración';
    });

    document.getElementById('reset-config-btn')?.addEventListener('click', () => {
      if (slider) slider.value = 70;
      if (valEl) valEl.textContent = '70%';
      document.getElementById('conf-max-altitude').value = 1000;
      document.getElementById('conf-anomaly-threshold').value = 2.5;
      document.getElementById('conf-min-speed').value = 0;
      document.getElementById('conf-max-speed').value = 300;
      document.getElementById('conf-ai-enabled').checked = true;
      document.getElementById('conf-alerts-enabled').checked = true;

      Toast.info('Configuración restablecida a valores predeterminados.');
    });
  }

  destroy() {}
}

// ============================================================
// TRAJECTORY VIEW (RF-011)
// ============================================================

export class TrajectoryView {
  constructor() { this._map = null; this._layers = []; this._request = 0; }

  async render(container, query = {}) {
    document.title = 'AeroGuard — Trayectorias';
    container.innerHTML = Layout.renderShell('#/trajectory', 'Consulta de Trayectorias');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this._populateSelect(query.detection);
    document.getElementById('load-trajectory-btn')?.addEventListener('click', () => this._loadTrajectory());
    document.getElementById('refresh-trajectories-btn')?.addEventListener('click', () => this._populateSelect());
    document.getElementById('traj-select')?.addEventListener('change', () => this._clearTrajectory());
    requestAnimationFrame(() => this._initMap());
  }

  _template() {
    return `
<div class="fade-in">
  <div class="mb-lg">
    <h2 style="color:var(--text-primary)">Trayectorias de Vuelo</h2>
    <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Recorrido histórico 2D y registros de telemetría. La línea une muestras recibidas; no predice el vuelo ni acredita una infracción.</p>
  </div>
  <div class="card mb-lg">
    <div style="display:flex;gap:var(--spacing-md);align-items:flex-end;flex-wrap:wrap">
      <div class="form-group" style="flex:1;min-width:200px;margin:0">
        <label class="form-label" for="traj-select">Seleccionar Detección</label>
        <select id="traj-select" class="form-select" aria-label="Seleccionar detección para visualizar trayectoria">
          <option value="">-- Selecciona una detección --</option>
        </select>
      </div>
      <button id="load-trajectory-btn" class="btn btn-primary" aria-label="Cargar trayectoria">🛤️ Cargar Trayectoria</button>
      <button id="refresh-trajectories-btn" class="btn btn-secondary">Actualizar detecciones</button>
    </div>
  </div>
  <p id="traj-status" role="status" aria-live="polite">Cargando detecciones…</p>
  <div class="map-card" style="min-height:500px" role="region" aria-label="Mapa de trayectoria">
    <div id="trajectory-map" style="width:100%;min-height:500px;border-radius:var(--radius-lg)"></div>
  </div>
  <div id="traj-stats" class="hidden">
    <div class="grid-4 mt-lg" id="traj-stats-grid"></div>
  </div>
  <div id="traj-detail" class="card mt-lg hidden">
    <h3>Registro de puntos</h3>
    <p>Fecha/hora local del navegador · coordenadas WGS84 · distancia horizontal aproximada · velocidad media de las muestras.</p>
    <div class="table-container"><table aria-label="Puntos de trayectoria"><thead><tr><th>Punto</th><th>Fecha y hora</th><th>Latitud</th><th>Longitud</th><th>Altitud (m)</th><th>Velocidad (km/h)</th><th>Rumbo (°)</th></tr></thead><tbody id="traj-points"></tbody></table></div>
  </div>
</div>`;
  }

  async _populateSelect(selectedId = null) {
    this._clearTrajectory();
    const sel = document.getElementById('traj-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Selecciona una detección --</option>';
    let detections;
    try { detections = MockService.enabled ? MockService.detections : await DetectionService.list(); }
    catch (error) { this._setStatus('No se pudieron consultar las detecciones. Intenta actualizar.'); Toast.error(error.message); return; }
    detections = Array.isArray(detections) ? detections : (detections.items || []);
    this._detections = detections;
    document.getElementById('load-trajectory-btn').disabled = !detections.length;
    this._setStatus(detections.length ? 'Selecciona una detección para consultar sus muestras. Se muestran hasta 50 detecciones recientes.' : 'No hay detecciones registradas. La trayectoria se forma al recibir telemetría del mismo objeto y sensor; no se generan rutas de ejemplo automáticamente.');
    detections.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = `ID: ${d.id} · ${d.sensor_name || d.sensor_id || 'Sin sensor'} · ${new Date(d.timestamp || d.created_at).toLocaleString('es-CO', {dateStyle:'short', timeStyle:'short'})}`;
      sel.appendChild(opt);
    });
    if (selectedId && detections.some(d => d.id === selectedId)) sel.value = selectedId;
  }

  _initMap() {
    if (!window.L) return;
    const L = window.L;
    this._map = L.map('trajectory-map', { center: [4.7110, -74.0721], zoom: 13, zoomControl: false, zoomAnimation: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(this._map);
    L.control.zoom({ position: 'bottomright' }).addTo(this._map);
  }

  async _loadTrajectory() {
    const id = document.getElementById('traj-select')?.value;
    if (!id) { Toast.warn('Selecciona una detección primero.'); return; }
    if (!this._map) return;
    this._clearTrajectory();
    const request = this._request;
    this._setStatus('Consultando puntos de trayectoria…');

    const det = this._detections?.find(d => d.id === id);
    if (!det) return;
    const L = window.L;
    let samples;
    try { samples = await DetectionService.getTrajectory(id); }
    catch (error) { if (request === this._request) { this._setStatus('No se pudo cargar la trayectoria. No hay una ruta visible válida para esta consulta.'); Toast.error(error.message); } return; }
    if (request !== this._request) return;
    const points = samples.map(point => [point.latitude, point.longitude]);
    if (!points.length) { this._setStatus('Esta detección no tiene muestras de trayectoria.'); return; }
    const distanceKm = points.slice(1).reduce((total, point, index) => total + L.latLng(points[index]).distanceTo(L.latLng(point)) / 1000, 0);
    const averageSpeed = samples.reduce((total, point) => total + point.speed, 0) / samples.length;
    const maxAltitude = Math.max(...samples.map(point => point.altitude));

    // Clear previous
    const add = layer => { this._layers.push(layer); return layer.addTo(this._map); };

    // Draw polyline
    if (points.length > 1) add(L.polyline(points, { color: '#00d4ff', weight: 3, opacity: 0.8, dashArray: '8, 4' }));

    // Start/end markers
    add(L.circleMarker(points[0],  { radius: 10, color: '#00e676', fillColor: '#00e676', fillOpacity: 1 }).bindTooltip(points.length === 1 ? 'Única muestra recibida' : 'Inicio'));
    if (points.length > 1) add(L.circleMarker(points[points.length-1], { radius: 10, color: '#ff1744', fillColor: '#ff1744', fillOpacity: 1 }).bindTooltip('Último punto'));

    // Intermediate points
    points.forEach((p, i) => {
      if (i > 0 && i < points.length - 1) {
        add(L.circleMarker(p, { radius: 4, color: '#00d4ff', fillColor: '#00d4ff', fillOpacity: 0.6 }));
      }
    });

    if (points.length === 1) this._map.setView(points[0], 15);
    else this._map.fitBounds(L.polyline(points).getBounds(), { padding: [40, 40], maxZoom: 17 });
    this._setStatus(points.length === 1 ? 'Solo hay una muestra: aún no permite reconstruir un recorrido.' : `${points.length} muestras recibidas. Inicio en verde; último punto en rojo. No se interpolan muestras faltantes.`);
    document.getElementById('traj-detail').classList.remove('hidden');
    document.getElementById('traj-points').innerHTML = samples.map((p, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(new Date(p.timestamp).toLocaleString('es-CO'))}</td><td>${Number(p.latitude).toFixed(6)}</td><td>${Number(p.longitude).toFixed(6)}</td><td>${Number(p.altitude).toFixed(1)}</td><td>${Number(p.speed).toFixed(1)}</td><td>${Number(p.heading).toFixed(1)}</td></tr>`).join('');

    // Show stats
    const stats = document.getElementById('traj-stats');
    const grid  = document.getElementById('traj-stats-grid');
    if (stats && grid) {
      stats.classList.remove('hidden');
      grid.innerHTML = `
        <div class="stat-card"><div class="stat-card-icon" style="background:rgba(0,212,255,0.1)">📍</div><div class="stat-card-value text-accent">${points.length}</div><div class="stat-card-label">Puntos</div></div>
        <div class="stat-card"><div class="stat-card-icon" style="background:rgba(0,230,118,0.1)">📏</div><div class="stat-card-value" style="color:var(--success)">${distanceKm.toFixed(2)} km</div><div class="stat-card-label">Distancia</div></div>
        <div class="stat-card"><div class="stat-card-icon" style="background:rgba(255,179,0,0.1)">⚡</div><div class="stat-card-value" style="color:var(--warning)">${averageSpeed.toFixed(1)} km/h</div><div class="stat-card-label">Vel. Promedio</div></div>
        <div class="stat-card"><div class="stat-card-icon" style="background:rgba(0,102,255,0.1)">⬆️</div><div class="stat-card-value" style="color:var(--brand-secondary)">${maxAltitude.toFixed(0)} m</div><div class="stat-card-label">Alt. Máxima</div></div>
      `;
    }

    Toast.success('Trayectoria cargada correctamente.');
  }

  _setStatus(message) {
    const element = document.getElementById('traj-status');
    if (element) element.textContent = message;
  }

  _clearTrajectory() {
    this._request++;
    this._layers.forEach(layer => layer.remove());
    this._layers = [];
    document.getElementById('traj-stats')?.classList.add('hidden');
    document.getElementById('traj-detail')?.classList.add('hidden');
    this._setStatus('Selecciona una detección y carga su trayectoria.');
  }

  destroy() {
    this._request++;
    if (this._map) { this._map.stop(); this._map.remove(); this._map = null; }
  }
}
