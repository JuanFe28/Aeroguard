/**
 * AeroGuard — Detections View + ViewModel
 * Lista y detalle de detecciones (RF-009, RF-010, RF-011, RF-021)
 */

import { DetectionService, WebSocketService, MockService, AIService } from '../services/api.service.js';
import { DetectionModel } from '../models/models.js';
import { Layout, Toast } from '../app.js';

// ============================================================
// ViewModel
// ============================================================

export class DetectionsViewModel {
  constructor() {
    this.state = {
      detections: [],
      filtered:   [],
      isLoading:  true,
      search:     '',
      filterStatus: '',
      filterThreat: '',
      page: 1,
      perPage: 20,
      total: 0,
      selectedId: null,
    };
    this._unsub = [];
  }

  startRealtime() {
    const unsub1 = WebSocketService.on('detection_new', (raw) => {
      if (!raw) return;
      const d = new DetectionModel(raw);
      const idx = this.state.detections.findIndex(x => x.id === d.id);
      if (idx >= 0) {
        this.state.detections[idx] = d;
      } else {
        this.state.detections.unshift(d);
        this.state.total = (this.state.total || 0) + 1;
      }
      this._applyFilters();
      this.renderTable();
      this.renderCount();
    });
    this._unsub.push(unsub1);

    const unsub2 = WebSocketService.on('detections_polled', (items) => {
      if (!Array.isArray(items)) return;
      let changed = false;
      items.forEach(raw => {
        const d = new DetectionModel(raw);
        const idx = this.state.detections.findIndex(x => x.id === d.id);
        if (idx >= 0) {
          this.state.detections[idx] = d;
          changed = true;
        } else {
          this.state.detections.unshift(d);
          this.state.total = (this.state.total || 0) + 1;
          changed = true;
        }
      });
      if (changed) {
        this._applyFilters();
        this.renderTable();
        this.renderCount();
      }
    });
    this._unsub.push(unsub2);
  }

  async load() {
    this.state.isLoading = true;
    try {
      if (MockService.enabled) {
        await new Promise(r => setTimeout(r, 300));
        this.state.detections = MockService.detections.map(d => new DetectionModel(d));
        this.state.total = this.state.detections.length;
      } else {
        const res = await DetectionService.list({
          status: this.state.filterStatus || undefined,
          threat_level: this.state.filterThreat || undefined,
          search: this.state.search || undefined,
          page: this.state.page,
          per_page: this.state.perPage,
        });
        this.state.detections = (res.items || []).map(d => new DetectionModel(d));
        this.state.total = res.total || 0;
      }
      this._applyFilters();
    } catch (err) {
      Toast.error('Error al cargar detecciones.');
    } finally {
      this.state.isLoading = false;
    }
  }

  _applyFilters() {
    let list = [...this.state.detections];
    if (this.state.search) {
      const q = this.state.search.toLowerCase();
      list = list.filter(d =>
        d.id.toLowerCase().includes(q) ||
        d.sensorName.toLowerCase().includes(q) ||
        d.status.toLowerCase().includes(q)
      );
    }
    if (this.state.filterStatus) list = list.filter(d => d.status === this.state.filterStatus);
    if (this.state.filterThreat) list = list.filter(d => d.threatLevel === this.state.filterThreat);
    this.state.filtered = list;
  }

  renderTable() {
    const tbody = document.getElementById('detections-tbody');
    if (!tbody) return;

    if (this.state.isLoading) {
      tbody.innerHTML = Array(5).fill(0).map(() => `
        <tr>
          ${Array(7).fill(0).map(() => `<td><div class="skeleton" style="height:14px;width:80%;border-radius:4px"></div></td>`).join('')}
        </tr>
      `).join('');
      return;
    }

    if (!this.state.filtered.length) {
      tbody.innerHTML = `
        <tr><td colspan="7">
          <div class="empty-state">
            <div class="empty-state-icon">🎯</div>
            <div class="empty-state-title">Sin detecciones</div>
            <div class="empty-state-message">No hay detecciones con los filtros actuales.</div>
          </div>
        </td></tr>
      `;
      return;
    }

    tbody.innerHTML = this.state.filtered.map(d => `
      <tr style="cursor:pointer" onclick="window.location.hash='#/detections/${d.id}'" role="row" aria-label="Detección ${d.id}">
        <td class="text-primary" style="font-family:var(--font-mono);font-size:12px">${d.id}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="status-dot ${d.status === 'active' ? 'status-danger' : d.status === 'pending' ? 'status-warning' : 'status-online'}"></span>
            ${d.sensorName}
          </div>
        </td>
        <td>
          <div style="font-size:12px">
            <div style="color:var(--text-primary)">${d.latitude.toFixed(5)}, ${d.longitude.toFixed(5)}</div>
            <div style="color:var(--text-muted)">Alt: ${d.formattedAltitude} · ${d.formattedSpeed}</div>
          </div>
        </td>
        <td>
          <span class="badge ${d.threatBadgeClass} badge-dot">${d.threatLevel.toUpperCase()}</span>
        </td>
        <td>
          <div class="confidence-bar">
            <div class="confidence-track">
              <div class="confidence-fill" style="width:${d.aiConfidence ? (d.aiConfidence*100).toFixed(0) : 0}%;background:${d.isDrone ? 'var(--danger)' : 'var(--success)'}"></div>
            </div>
            <span class="confidence-val">${d.confidencePercent}</span>
          </div>
          <div style="font-size:11px;margin-top:2px;color:${d.isDrone ? 'var(--danger)' : 'var(--success)'}">
            ${d.isDrone ? '⚠️ Posible dron' : '✅ No dron'}
          </div>
        </td>
        <td><span class="badge ${d.statusBadgeClass}">${d.status}</span></td>
        <td style="font-size:12px;color:var(--text-muted)">${d.formattedTime}</td>
      </tr>
    `).join('');
  }

  renderCount() {
    const el = document.getElementById('detections-count');
    if (el) el.textContent = `${this.state.filtered.length} detección${this.state.filtered.length !== 1 ? 'es' : ''}`;
  }

  bindEvents() {
    document.getElementById('search-input')?.addEventListener('input', (e) => {
      this.state.search = e.target.value;
      this._applyFilters();
      this.renderTable();
      this.renderCount();
    });

    document.getElementById('filter-status')?.addEventListener('change', (e) => {
      this.state.filterStatus = e.target.value;
      this._applyFilters();
      this.renderTable();
      this.renderCount();
    });

    document.getElementById('filter-threat')?.addEventListener('change', (e) => {
      this.state.filterThreat = e.target.value;
      this._applyFilters();
      this.renderTable();
      this.renderCount();
    });

    document.getElementById('refresh-btn')?.addEventListener('click', () => {
      this.load().then(() => { this.renderTable(); this.renderCount(); });
    });

    document.getElementById('ai-modal-btn')?.addEventListener('click', () => {
      this.openAIModal();
    });
  }

  openAIModal() {
    const existing = document.getElementById('ai-vision-modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'ai-vision-modal-overlay';
    overlay.className = 'modal-overlay visible';
    overlay.innerHTML = `
      <div class="modal" style="max-width:680px;width:95%">
        <div class="modal-header" style="display:flex;justify-content:space-between;align-items:center">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:24px">🤖</span>
            <div>
              <h3 class="modal-title" style="margin:0;color:var(--text-primary)">Visión Artificial C-UAS (RF-021)</h3>
              <p style="margin:0;font-size:12px;color:var(--text-muted)">Inferencia en tiempo real con OpenCV + YOLOv8</p>
            </div>
          </div>
          <button class="btn btn-icon" id="close-ai-modal" style="font-size:18px">✕</button>
        </div>

        <div class="modal-body" style="padding:var(--spacing-md) 0">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--spacing-md);margin-bottom:var(--spacing-md)">
            <div>
              <label class="form-label" for="ai-sensor-select">Sensor Óptico / Cámara</label>
              <select id="ai-sensor-select" class="form-select">
                <option value="CAM-BGA-NORTE-01">CAM-BGA-NORTE-01 (Bucaramanga Norte)</option>
                <option value="OPT-PALONEGRO-02">OPT-PALONEGRO-02 (Aeropuerto Palonegro)</option>
                <option value="CAM-DORADO-01">CAM-DORADO-01 (Aeropuerto El Dorado)</option>
                <option value="CAM-SANTANDER-03">CAM-SANTANDER-03 (Complejo Santander)</option>
              </select>
            </div>
            <div>
              <label class="form-label">Cargar Fotograma (JPEG, PNG, WEBP)</label>
              <input type="file" id="ai-file-input" class="form-input" accept="image/jpeg,image/png,image/webp" style="padding:6px"/>
            </div>
          </div>

          <!-- Canvas Preview -->
          <div style="position:relative;background:#050d18;border:1px dashed var(--glass-border);border-radius:var(--radius-md);overflow:hidden;min-height:240px;display:flex;align-items:center;justify-content:center">
            <canvas id="ai-canvas" width="480" height="270" style="max-width:100%;height:auto;display:block"></canvas>
            <div id="ai-placeholder" style="position:absolute;text-align:center;color:var(--text-muted)">
              <div style="font-size:32px;margin-bottom:8px">📷</div>
              <div>Selecciona una imagen o presiona "Cargar Muestra UAV"</div>
            </div>
          </div>

          <!-- Controls -->
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:var(--spacing-md)">
            <button id="ai-sample-btn" class="btn btn-secondary btn-sm">🎯 Cargar Muestra UAV</button>
            <button id="ai-run-infer-btn" class="btn btn-primary btn-sm">⚡ Ejecutar Inferencia Real</button>
          </div>

          <!-- Results Box -->
          <div id="ai-results-panel" style="display:none;margin-top:var(--spacing-md);padding:var(--spacing-md);background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius-md)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span id="ai-res-badge" class="badge badge-critical badge-dot">DRON DETECTADO</span>
              <span id="ai-res-time" style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted)">0.0 ms</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:8px;font-size:12px">
              <div><strong style="color:var(--text-secondary)">Motor:</strong> <span id="ai-res-engine" style="color:var(--text-primary)">—</span></div>
              <div><strong style="color:var(--text-secondary)">Confianza:</strong> <span id="ai-res-conf" style="color:var(--accent)">—</span></div>
              <div><strong style="color:var(--text-secondary)">Bounding Box:</strong> <span id="ai-res-box" style="font-family:var(--font-mono);color:var(--text-primary)">—</span></div>
            </div>
          </div>
        </div>

        <div class="modal-footer" style="display:flex;justify-content:flex-end">
          <button class="btn btn-secondary" id="close-ai-modal-btn">Cerrar</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const canvas = overlay.querySelector('#ai-canvas');
    const ctx = canvas.getContext('2d');
    const placeholder = overlay.querySelector('#ai-placeholder');
    const fileInput = overlay.querySelector('#ai-file-input');
    const sampleBtn = overlay.querySelector('#ai-sample-btn');
    const runBtn = overlay.querySelector('#ai-run-infer-btn');
    const resultsPanel = overlay.querySelector('#ai-results-panel');

    let currentFile = null;

    const drawSample = () => {
      canvas.width = 480;
      canvas.height = 270;
      const grad = ctx.createLinearGradient(0, 0, 0, 270);
      grad.addColorStop(0, '#4a7c9f');
      grad.addColorStop(0.7, '#7fa3c1');
      grad.addColorStop(1, '#536858');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 480, 270);

      // Dron
      ctx.fillStyle = '#10151c';
      ctx.fillRect(195, 75, 90, 30);
      ctx.lineWidth = 4;
      ctx.strokeStyle = '#10151c';
      ctx.beginPath();
      ctx.moveTo(160, 55); ctx.lineTo(320, 125);
      ctx.moveTo(160, 125); ctx.lineTo(320, 55);
      ctx.stroke();
      ctx.fillStyle = '#222933';
      ctx.fillRect(150, 48, 26, 6);
      ctx.fillRect(304, 48, 26, 6);
      ctx.fillRect(150, 126, 26, 6);
      ctx.fillRect(304, 126, 26, 6);

      placeholder.style.display = 'none';
      resultsPanel.style.display = 'none';

      canvas.toBlob((blob) => {
        currentFile = new File([blob], 'uav_frame_sample.jpg', { type: 'image/jpeg' });
      }, 'image/jpeg');
    };

    sampleBtn.onclick = () => drawSample();

    fileInput.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      currentFile = file;
      const reader = new FileReader();
      reader.onload = (evt) => {
        const img = new Image();
        img.onload = () => {
          canvas.width = 480;
          canvas.height = Math.round((img.height / img.width) * 480);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          placeholder.style.display = 'none';
          resultsPanel.style.display = 'none';
        };
        img.src = evt.target.result;
      };
      reader.readAsDataURL(file);
    };

    runBtn.onclick = async () => {
      if (!currentFile) {
        Toast.warn('Por favor carga una imagen o genera la muestra.');
        return;
      }
      runBtn.disabled = true;
      runBtn.textContent = '⏳ Analizando...';
      const sensorId = overlay.querySelector('#ai-sensor-select').value;

      try {
        const res = await AIService.analyzeImage(currentFile, sensorId);
        resultsPanel.style.display = 'block';

        const isDrone = res.detection?.is_drone;
        const conf = res.detection?.confidence || 0;
        const bb = res.detection?.bounding_box || { x_min: 0, y_min: 0, width: 0, height: 0 };

        const badge = overlay.querySelector('#ai-res-badge');
        badge.className = `badge ${isDrone ? 'badge-critical' : 'badge-success'} badge-dot`;
        badge.textContent = isDrone ? '⚠️ DRON DETECTADO' : '✅ SIN AMENAZA';

        overlay.querySelector('#ai-res-time').textContent = `${res.processing_time_ms} ms`;
        overlay.querySelector('#ai-res-engine').textContent = res.engine || 'YOLOv8n-OpenCV';
        overlay.querySelector('#ai-res-conf').textContent = `${(conf * 100).toFixed(1)}%`;
        overlay.querySelector('#ai-res-box').textContent = isDrone ? `[x:${bb.x_min}, y:${bb.y_min}, ${bb.width}x${bb.height}]` : 'N/A';

        if (isDrone && bb.width > 0 && bb.height > 0) {
          const bx = bb.x_min;
          const by = bb.y_min;
          const bw = bb.width;
          const bh = bb.height;

          ctx.strokeStyle = '#ff1744';
          ctx.lineWidth = 2;
          ctx.strokeRect(bx, by, bw, bh);

          ctx.fillStyle = '#ff1744';
          const corner = 8;
          ctx.fillRect(bx - 2, by - 2, corner, 3);
          ctx.fillRect(bx - 2, by - 2, 3, corner);
          ctx.fillRect(bx + bw - corner + 2, by - 2, corner, 3);
          ctx.fillRect(bx + bw - 1, by - 2, 3, corner);

          ctx.font = 'bold 11px monospace';
          ctx.fillStyle = 'rgba(255, 23, 68, 0.9)';
          ctx.fillRect(bx, Math.max(0, by - 18), 130, 16);
          ctx.fillStyle = '#ffffff';
          ctx.fillText(`UAV ${(conf * 100).toFixed(0)}% [${res.detection?.label || 'drone'}]`, bx + 4, Math.max(12, by - 6));
        }

        Toast.success(`Inferencia completada en ${res.processing_time_ms} ms (${res.engine}).`);
      } catch (err) {
        Toast.error(err.message || 'Error en inferencia de IA.');
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = '⚡ Ejecutar Inferencia Real';
      }
    };

    const close = () => overlay.remove();
    overlay.querySelector('#close-ai-modal').onclick = close;
    overlay.querySelector('#close-ai-modal-btn').onclick = close;
    overlay.onclick = (e) => { if (e.target === overlay) close(); };
  }

  destroy() {
    this._unsub.forEach(u => u && u());
    this._unsub = [];
  }
}

// ============================================================
// View
// ============================================================

export class DetectionsView {
  constructor() {
    this.vm = new DetectionsViewModel();
  }

  async render(container) {
    document.title = 'AeroGuard — Detecciones';
    container.innerHTML = Layout.renderShell('#/detections', 'Detecciones');
    Layout.bindShellEvents();

    document.getElementById('page-content').innerHTML = this._template();
    this.vm.bindEvents();
    this.vm.startRealtime();
    await this.vm.load();
    this.vm.renderTable();
    this.vm.renderCount();
  }

  _template() {
    return `
<div class="detections-page fade-in">
  <!-- Header -->
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Lista de Detecciones</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">
        Objetos detectados por los sensores del sistema
      </p>
    </div>
    <div style="display:flex;gap:var(--spacing-sm)">
      <button id="ai-modal-btn" class="btn btn-primary" aria-label="Analizar Fotograma IA">📷 Analizar con IA</button>
      <button id="refresh-btn" class="btn btn-secondary" aria-label="Actualizar lista">🔄 Actualizar</button>
      <a href="#/history" class="btn btn-secondary" aria-label="Ver historial">📜 Historial</a>
    </div>
  </div>

  <!-- Filters -->
  <div class="card mb-lg">
    <div class="filter-bar">
      <div class="input-group" style="flex:1;min-width:220px">
        <span class="input-icon">🔍</span>
        <input id="search-input" type="search" class="form-input" placeholder="Buscar por ID, sensor..." aria-label="Buscar detecciones"/>
      </div>
      <select id="filter-status" class="form-select" style="width:180px" aria-label="Filtrar por estado">
        <option value="">Todos los estados</option>
        <option value="active">Activo</option>
        <option value="pending">Pendiente</option>
        <option value="resolved">Resuelto</option>
        <option value="discarded">Descartado</option>
      </select>
      <select id="filter-threat" class="form-select" style="width:180px" aria-label="Filtrar por amenaza">
        <option value="">Todos los niveles</option>
        <option value="critical">Crítico</option>
        <option value="high">Alto</option>
        <option value="medium">Medio</option>
        <option value="low">Bajo</option>
      </select>
      <span id="detections-count" style="font-size:var(--font-size-sm);color:var(--text-muted);white-space:nowrap;padding:10px 0"></span>
    </div>
  </div>

  <!-- Table -->
  <div class="card" style="padding:0">
    <div class="table-container">
      <table class="table" role="grid" aria-label="Tabla de detecciones">
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Sensor</th>
            <th scope="col">Ubicación</th>
            <th scope="col">Amenaza</th>
            <th scope="col">IA / Confianza</th>
            <th scope="col">Estado</th>
            <th scope="col">Hora</th>
          </tr>
        </thead>
        <tbody id="detections-tbody" aria-live="polite">
          <!-- Rendered by VM -->
        </tbody>
      </table>
    </div>
  </div>
</div>
    `;
  }

  destroy() { this.vm.destroy(); }
}
