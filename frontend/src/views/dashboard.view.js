/**
 * AeroGuard — Dashboard View (MVVM - View Layer)
 */

import { DashboardViewModel } from '../viewmodels/dashboard.viewmodel.js';
import { Layout } from '../app.js';

export class DashboardView {
  constructor() {
    this.vm = new DashboardViewModel();
  }

  async render(container) {
    document.title = 'AeroGuard — Dashboard';
    container.innerHTML = Layout.renderShell('#/dashboard', 'Dashboard');
    Layout.bindShellEvents();

    const pageContent = document.getElementById('page-content');
    pageContent.innerHTML = this._template();

    // Load data
    await this.vm.loadData();
    this.vm.renderStats();
    this.vm._renderAlerts();
    this.vm._renderSensorStatus();
    this.vm._renderAiVerdict();

    // Init map and interactive components (after DOM is ready)
    requestAnimationFrame(() => {
      this.vm.initMap('dashboard-map');
      this.vm.bindMapControls();
      this.vm.bindTacticalControls();
      this.vm.renderAltimetry();
      this.vm.startRealtime();
    });
  }

  _template() {
    return `
<div class="dashboard-page fade-in">
  <!-- Tactical Command Bar: Sound toggle, Test siren, System status -->
  <div class="tactical-command-bar" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:var(--spacing-md);margin-bottom:var(--spacing-md);padding:10px 18px;background:rgba(19,28,53,0.75);backdrop-filter:blur(10px);border:1px solid rgba(0,212,255,0.18);border-radius:var(--radius-md);box-shadow:var(--shadow-sm);">
    <div style="display:flex;align-items:center;gap:var(--spacing-md);flex-wrap:wrap;">
      <span style="display:flex;align-items:center;gap:8px;font-family:var(--font-mono);font-size:var(--font-size-xs);font-weight:700;color:var(--text-accent);letter-spacing:1.2px;text-transform:uppercase;">
        <span class="status-dot status-online" style="width:8px;height:8px;box-shadow:0 0 8px #00e676"></span>
        ${window.AEROGUARD_DEMO_MODE !== false ? 'DEMO ACADÉMICA — DATOS SIMULADOS' : 'MONITOREO EXPERIMENTAL'}
      </span>
      <span style="color:var(--text-muted);font-size:var(--font-size-xs);display:flex;align-items:center;gap:6px">
        <span style="opacity:0.4">|</span>
        🛰️ VIGILANCIA C-UAS ACTIVA
        <span style="opacity:0.4">|</span>
        UMBRAL DE EJEMPLO: <b style="color:var(--danger)">120m AGL</b>
      </span>
    </div>
    <div style="display:flex;align-items:center;gap:var(--spacing-sm);">
      <button class="btn btn-secondary btn-sm" id="btn-toggle-audio" style="font-family:var(--font-mono);font-size:12px;display:flex;align-items:center;gap:6px;transition:all 0.2s ease;" title="Activar/Silenciar alarma sonora táctica">
        <span id="audio-icon">🔊</span>
        <span id="audio-status-text">Sonido: ON</span>
      </button>
      <button class="btn btn-danger btn-sm" id="btn-test-siren" style="font-family:var(--font-mono);font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px;box-shadow:0 0 12px rgba(255,23,68,0.25);" title="Disparar ráfaga táctica de prueba (1.5s)">
        <span>🚨</span> Probar Sirena
      </button>
    </div>
  </div>

  <!-- Stats Row -->
  <div class="dashboard-grid" role="region" aria-label="Estadísticas del sistema">
    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(0,212,255,0.1)">🎯</div>
      <div class="stat-card-value text-accent" id="stat-total">—</div>
      <div class="stat-card-label">Detecciones Totales</div>
      <div class="stat-card-change stat-change-neutral" id="stat-total-change">
        📊 Histórico del sistema
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(255,23,68,0.1)">🔴</div>
      <div class="stat-card-value" style="color:var(--danger)" id="stat-active">—</div>
      <div class="stat-card-label">Activas Ahora</div>
      <div class="stat-card-change stat-change-neutral">
        <span class="status-dot status-online" style="width:8px;height:8px"></span>
        En tiempo real
      </div>
    </div>

    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(0,230,118,0.1)">✅</div>
      <div class="stat-card-value" style="color:var(--success)" id="stat-resolved">—</div>
      <div class="stat-card-label">Resueltas</div>
      <div class="stat-card-change stat-change-up">↑ Sin amenaza confirmada</div>
    </div>

    <div class="stat-card">
      <div class="stat-card-icon" style="background:rgba(255,179,0,0.1)">🔔</div>
      <div class="stat-card-value" style="color:var(--warning)" id="stat-alerts">—</div>
      <div class="stat-card-label">Alertas Abiertas</div>
      <div class="stat-card-change stat-change-neutral">Requieren atención</div>
    </div>
  </div>

  <!-- Main content: Map + Side widgets -->
  <div class="dashboard-main-grid">
    <!-- Map Card -->
    <div class="map-card" role="region" aria-label="Mapa de detecciones">
      <!-- Map Controls Overlay -->
      <div class="map-card-header">
        <!-- Layer controls -->
        <div class="map-controls">
          <button class="map-control-btn active" id="map-layer-zones"   title="Mostrar zonas restringidas" aria-label="Zonas">🚫</button>
          <button class="map-control-btn active" id="map-layer-sensors" title="Mostrar sensores"          aria-label="Sensores">📡</button>
          <button class="map-control-btn"        id="map-center-btn"    title="Centrar mapa"              aria-label="Centrar">⊕</button>
          <button class="map-control-btn"        id="map-fit-btn"       title="Ajustar a detecciones"     aria-label="Ajustar">⛶</button>
        </div>

        <!-- Legend -->
        <div class="map-legend" role="note" aria-label="Leyenda del mapa">
          <div class="map-legend-item">
            <div class="map-legend-dot" style="background:#ff1744"></div>
            <span>Crítico</span>
          </div>
          <div class="map-legend-item">
            <div class="map-legend-dot" style="background:#ff6d00"></div>
            <span>Alto</span>
          </div>
          <div class="map-legend-item">
            <div class="map-legend-dot" style="background:#ffb300"></div>
            <span>Medio</span>
          </div>
          <div class="map-legend-item">
            <div class="map-legend-dot" style="background:#00e676"></div>
            <span>Bajo</span>
          </div>
          <div class="map-legend-item">
            <div class="map-legend-dot" style="background:rgba(255,23,68,0.3);border:1px dashed #ff1744"></div>
            <span>Zona Restringida</span>
          </div>
        </div>
      </div>

      <!-- Map -->
      <div id="dashboard-map" class="map-container" aria-label="Mapa interactivo de detecciones" style="height:560px;width:100%;min-height:500px"></div>

      <!-- Map Footer -->
      <div style="position:absolute;bottom:var(--spacing-sm);left:var(--spacing-md);z-index:500;display:flex;align-items:center;gap:var(--spacing-sm)">
        <span style="font-size:var(--font-size-xs);color:var(--text-muted)">
          Última actualización: <span id="last-update">—</span>
        </span>
        <span class="status-dot status-online" id="live-dot" style="width:8px;height:8px"></span>
      </div>
    </div>

    <!-- Side Widgets -->
    <div class="sidebar-widgets">
      <!-- AI Tactical Verdict Widget -->
      <div class="card" style="flex-shrink:0;border:1px solid rgba(0,212,255,0.22);box-shadow:0 0 20px rgba(0,212,255,0.06);" role="region" aria-label="Dictamen Agente IA">
        <div class="card-header" style="padding-bottom:var(--spacing-xs);border-bottom:1px solid rgba(255,255,255,0.06)">
          <div>
            <div class="card-title" style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-accent);">
              <span>🤖</span> DICTAMEN AGENTE IA (C-UAS)
            </div>
            <div class="card-subtitle" style="font-size:11px" id="ai-verdict-time">Evaluación cinemática continua</div>
          </div>
          <span class="badge badge-danger" id="ai-verdict-badge" style="font-size:10px;font-weight:700;letter-spacing:0.5px">CRITICAL</span>
        </div>
        <div style="padding:var(--spacing-sm) var(--spacing-md) var(--spacing-md);display:flex;flex-direction:column;gap:var(--spacing-xs)">
          <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.25);padding:6px 10px;border-radius:var(--radius-sm);border:1px solid rgba(255,255,255,0.04)">
            <div>
              <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Objetivo / Incursión</div>
              <div style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--text-primary)" id="ai-verdict-target">UAV-HK-402 (DJI Matrice 300)</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Confianza</div>
              <div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--success)" id="ai-verdict-confidence">96.4%</div>
            </div>
          </div>
          <div style="font-size:12px;line-height:1.45;color:var(--text-secondary);background:rgba(255,23,68,0.06);border-left:3px solid var(--danger);padding:8px 10px;border-radius:0 var(--radius-sm) var(--radius-sm) 0" id="ai-verdict-text">
            Cargando evaluación táctica del agente...
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--text-muted);padding-top:4px">
            <span id="ai-verdict-incident" style="font-family:var(--font-mono);font-size:10px">INC-2026-0891</span>
            <button class="btn btn-secondary btn-sm" id="btn-trigger-soar" style="font-size:10px;padding:3px 8px;gap:4px;display:flex;align-items:center;" title="Ejecutar análisis de Agente IA SOAR">
              <span>⚡</span> Disparar SOAR
            </button>
          </div>
        </div>
      </div>

      <!-- 2D Altimetry Profile Widget -->
      <div class="card" style="flex-shrink:0" role="region" aria-label="Widget de Altimetría 2D">
        <div class="card-header" style="padding-bottom:var(--spacing-xs)">
          <div>
            <div class="card-title" style="display:flex;align-items:center;gap:6px;font-size:13px">
              <span>📐</span> Perfil de Altitud 2D (AGL)
            </div>
            <div class="card-subtitle" style="font-size:11px">Monitoreo de techo de vuelo civil</div>
          </div>
          <span class="badge badge-info" id="altimetry-active-count" style="font-size:10px">0 Drones</span>
        </div>
        <div style="padding:var(--spacing-xs) var(--spacing-md) var(--spacing-md)">
          <div style="position:relative;width:100%;height:180px;">
            <canvas id="altimetry-canvas" width="340" height="180" style="width:100%;height:180px;display:block;border-radius:var(--radius-sm);background:rgba(10,14,26,0.85);border:1px solid rgba(0,212,255,0.15)"></canvas>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-size:10px;color:var(--text-muted)">
            <span style="display:flex;align-items:center;gap:4px">
              <span style="display:inline-block;width:12px;height:2px;border-top:2px dashed var(--danger)"></span>
              Límite Civil UAEAC: 120m
            </span>
            <span id="altimetry-status-text" style="font-family:var(--font-mono);font-size:10px;color:var(--text-secondary)">Escaneo en curso</span>
          </div>
        </div>
      </div>

      <!-- Active Alerts Widget -->
      <div class="card" style="flex-shrink:0" role="region" aria-label="Alertas activas">
        <div class="card-header">
          <div>
            <div class="card-title">🔔 Alertas Activas</div>
            <div class="card-subtitle">Últimas alertas abiertas</div>
          </div>
          <a href="#/alerts" class="btn btn-secondary btn-sm">Ver todas</a>
        </div>
        <div id="alert-list" role="list" aria-live="polite">
          <!-- Rendered by VM -->
          <div class="flex items-center justify-between" style="padding:var(--spacing-lg)">
            <div class="skeleton" style="width:70%;height:14px;border-radius:4px"></div>
          </div>
        </div>
      </div>

      <!-- Sensor Status Widget -->
      <div class="card" role="region" aria-label="Estado de sensores">
        <div class="card-header">
          <div>
            <div class="card-title">📡 Estado de Sensores</div>
            <div class="card-subtitle">Sistemas de detección</div>
          </div>
          <a href="#/sensors" class="btn btn-secondary btn-sm">Gestionar</a>
        </div>
        <div id="sensor-status-list" class="detector-list" role="list">
          <!-- Rendered by VM -->
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">⚡ Accesos Rápidos</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:var(--spacing-sm)">
          <a href="#/detections" class="btn btn-secondary" style="justify-content:flex-start" aria-label="Ver lista de detecciones">
            🎯 Ver detecciones
          </a>
          <a href="#/zones" class="btn btn-secondary" style="justify-content:flex-start" aria-label="Gestionar zonas restringidas">
            🗺️ Zonas restringidas
          </a>
          <a href="#/reports" class="btn btn-secondary" style="justify-content:flex-start" aria-label="Generar reporte">
            📋 Generar reporte
          </a>
          <a href="#/history" class="btn btn-secondary" style="justify-content:flex-start" aria-label="Ver historial">
            📜 Ver historial
          </a>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  /* Pulse animation for markers */
  @keyframes pulse-marker {
    0%, 100% { box-shadow: 0 0 6px currentColor; }
    50% { box-shadow: 0 0 18px currentColor; }
  }
  @keyframes pulse-ring {
    0% { transform: scale(1); opacity: 0.4; }
    100% { transform: scale(2); opacity: 0; }
  }
  /* Leaflet popup override */
  .aeroguard-popup .leaflet-popup-content-wrapper {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--shadow-lg) !important;
    color: var(--text-primary) !important;
    padding: 0 !important;
  }
  .aeroguard-popup .leaflet-popup-tip { background: var(--bg-card) !important; }
  .aeroguard-popup .leaflet-popup-content { margin: 0 !important; }
</style>
    `;
  }

  destroy() {
    this.vm.destroy();
  }
}
