import { escapeHtml } from './utils/html.js';
/**
 * AeroGuard — Router & App Shell
 * Sistema de routing SPA + gestión de la sesión + toasts
 */

import { AuthService, WebSocketService } from './services/api.service.js';

// ============================================================
// Toast Notifications
// ============================================================

export const Toast = {
  _container: null,

  _getContainer() {
    if (!this._container) {
      this._container = document.getElementById('toast-container');
      if (!this._container) {
        this._container = document.createElement('div');
        this._container.id = 'toast-container';
        document.body.appendChild(this._container);
      }
    }
    return this._container;
  },

  show(message, type = 'info', duration = 4000) {
    const container = this._getContainer();
    const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
      <span class="toast-message">${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('removing');
      toast.addEventListener('animationend', () => toast.remove());
    }, duration);
  },

  success: (msg) => Toast.show(msg, 'success'),
  error:   (msg) => Toast.show(msg, 'danger'),
  warn:    (msg) => Toast.show(msg, 'warning'),
  info:    (msg) => Toast.show(msg, 'info'),
};

// ============================================================
// Confirmation Dialog
// ============================================================

export function confirm(message, title = '¿Confirmar acción?') {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay visible';
    overlay.innerHTML = `
      <div class="modal" style="max-width:420px">
        <div class="modal-header">
          <h3 class="modal-title">⚠️ ${escapeHtml(title)}</h3>
        </div>
        <p style="color:var(--text-secondary)">${escapeHtml(message)}</p>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="confirm-cancel">Cancelar</button>
          <button class="btn btn-danger" id="confirm-ok">Confirmar</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('#confirm-ok').onclick = () => { overlay.remove(); resolve(true); };
    overlay.querySelector('#confirm-cancel').onclick = () => { overlay.remove(); resolve(false); };
    overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
  });
}

// ============================================================
// Router
// ============================================================

export class Router {
  constructor() {
    this._routes = new Map();
    this._currentView = null;
    this._app = document.getElementById('app');
    window.addEventListener('hashchange', () => this._handleRoute());
  }

  register(path, viewFactory, allowedRoles = null) {
    this._routes.set(path, { factory: viewFactory, allowedRoles });
    return this;
  }

  navigate(path) {
    window.location.hash = path;
  }

  start() {
    this._handleRoute();
  }

  async _handleRoute() {
    const hash  = window.location.hash || '#/login';
    const path  = hash.split('?')[0];
    const query = Object.fromEntries(new URLSearchParams(hash.split('?')[1] || ''));

    // Auth guard
    if (path !== '#/login' && path !== '#/reset-password') {
      if (!AuthService.isAuthenticated()) {
        this.navigate('#/login');
        return;
      }
      // Ensure real-time connection is running globally
      WebSocketService.connect();
    } else {
      WebSocketService.disconnect();
    }

    // Redirect to dashboard if already logged in
    if ((path === '#/login') && AuthService.isAuthenticated()) {
      this.navigate('#/dashboard');
      return;
    }

    const route = this._routes.get(path);
    if (!route) {
      console.warn('Route not found:', path);
      this.navigate('#/dashboard');
      return;
    }

    if (route.allowedRoles && path !== '#/login' && path !== '#/reset-password') {
      const role = AuthService.getUser()?.role;
      if (!route.allowedRoles.includes(role)) {
        Toast.error('Acceso denegado: No tienes permisos para ver esta sección.');
        this.navigate('#/dashboard');
        return;
      }
    }

    // Destroy previous view
    if (this._currentView?.destroy) await this._currentView.destroy();

    // Render new view
    const view = route.factory();
    this._currentView = view;
    await view.render(this._app, query);
  }
}

// ============================================================
// Layout Helper
// ============================================================

export const Layout = {
  _sidebarCollapsed: localStorage.getItem('ag_sidebar_collapsed') === 'true',

  renderShell(activePath, pageTitle) {
    const user     = AuthService.getUser();
    const role     = user?.role || 'operator';
    const initials = this._getInitials(user);
    const navItems = this._getNavItems(role);
    const collapsedSidebar = this._sidebarCollapsed ? 'collapsed' : '';
    const collapsedContent = this._sidebarCollapsed ? 'sidebar-collapsed' : '';

    return `
      <!-- Sidebar -->
      <nav class="sidebar ${collapsedSidebar}" id="sidebar" role="navigation" aria-label="Menú principal">
        <a class="sidebar-logo" href="#/dashboard" aria-label="AeroGuard Inicio">
          <div class="sidebar-logo-icon" aria-hidden="true">🛡️</div>
          <div class="sidebar-logo-text">
            <span class="sidebar-logo-name">AEROGUARD</span>
            <span class="sidebar-logo-sub">Sistema de Monitoreo</span>
          </div>
        </a>

        <div class="sidebar-nav" id="sidebar-nav">
          ${navItems.map(section => `
            <div class="nav-section">
              <div class="nav-section-label">${escapeHtml(section.label)}</div>
              ${section.items.map(item => `
                <a class="nav-item ${activePath === item.path ? 'active' : ''}"
                   href="${item.path}"
                   id="nav-${item.id}"
                   aria-label="${escapeHtml(item.label)}"
                   aria-current="${activePath === item.path ? 'page' : 'false'}">
                  <span class="nav-icon" aria-hidden="true">${item.icon}</span>
                  <span class="nav-label">${escapeHtml(item.label)}</span>
                  ${item.badge ? `<span class="nav-badge" id="badge-${item.id}">${item.badge}</span>` : ''}
                </a>
              `).join('')}
            </div>
          `).join('')}
        </div>

        <div class="sidebar-footer">
          <div class="user-profile" id="user-profile-btn" role="button" tabindex="0" aria-label="Perfil de usuario">
            <div class="user-avatar" aria-hidden="true">${escapeHtml(initials)}</div>
            <div class="user-info">
              <div class="user-name">${escapeHtml(user?.first_name || user?.username || 'Usuario')}</div>
              <div class="user-role">${this._getRoleLabel(role)}</div>
            </div>
          </div>
        </div>

        <button class="sidebar-toggle" id="sidebar-toggle-btn" aria-label="Colapsar sidebar">
          ${this._sidebarCollapsed ? '▶' : '◀'}
        </button>
      </nav>

      <!-- Main Content -->
      <div class="main-content ${collapsedContent}" id="main-content">
        <!-- Topbar -->
        <header class="topbar ${collapsedContent}" id="topbar" role="banner">
          <div class="topbar-left">
            <div class="topbar-left">
              <h1 class="page-title" id="page-title">${pageTitle}</h1>
            </div>
          </div>
          <div class="topbar-right">
            <div id="ws-indicator" title="Estado de conexión en tiempo real" style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted)">
              <span class="status-dot ${WebSocketService.isConnected() !== false ? 'status-online' : 'status-offline'}" id="ws-dot"></span>
              <span id="ws-text" style="color:${WebSocketService.isConnected() !== false ? 'var(--success)' : 'var(--text-muted)'}">
                ${WebSocketService.isConnected() !== false ? 'En vivo' : 'Desconectado'}
              </span>
            </div>
            <button class="topbar-btn" id="alerts-btn" aria-label="Ver alertas" title="Alertas activas">
              🔔
              <span class="notification-badge hidden" id="alert-count-badge">0</span>
            </button>
            <button class="topbar-btn" id="logout-btn" aria-label="Cerrar sesión" title="Cerrar sesión">⏻</button>
          </div>
        </header>

        <!-- Page content -->
        <main class="page-content" id="page-content" role="main">
          <!-- Injected by view -->
        </main>
      </div>

      <div id="toast-container"></div>
    `;
  },

  _getInitials(user) {
    if (!user) return 'AG';
    const fn = user.first_name?.[0] || '';
    const ln = user.last_name?.[0]  || '';
    return (fn + ln).toUpperCase() || (user.username?.[0] || 'AG').toUpperCase();
  },

  _getRoleLabel(role) {
    const labels = { admin: 'Administrador', operator: 'Operador', analyst: 'Analista' };
    return labels[role] || role;
  },

  _getNavItems(role) {
    const all = {
      main: [
        { id: 'dashboard',   path: '#/dashboard',   icon: '📊', label: 'Dashboard',    roles: ['admin','operator','analyst'] },
        { id: 'detections',  path: '#/detections',  icon: '🎯', label: 'Detecciones',  roles: ['admin','operator','analyst'] },
        { id: 'alerts',      path: '#/alerts',      icon: '🔔', label: 'Alertas',      roles: ['admin','operator','analyst'], badge: null },
        { id: 'trajectory',  path: '#/trajectory',  icon: '🛤️', label: 'Trayectorias', roles: ['admin','operator','analyst'] },
      ],
      config: [
        { id: 'zones',       path: '#/zones',       icon: '🗺️', label: 'Zonas Restringidas', roles: ['admin','operator','analyst'] },
        { id: 'sensors',     path: '#/sensors',     icon: '📡', label: 'Sensores',            roles: ['admin'] },
        { id: 'detection-config', path: '#/detection-config', icon: '⚙️', label: 'Config. Detección', roles: ['admin'] },
      ],
      reports: [
        { id: 'history',  path: '#/history',  icon: '📜', label: 'Historial',  roles: ['admin','operator','analyst'] },
        { id: 'reports',  path: '#/reports',  icon: '📋', label: 'Reportes',   roles: ['admin','analyst'] },
        { id: 'audit',    path: '#/audit',    icon: '🔍', label: 'Auditoría',  roles: ['admin','analyst'] },
      ],
      admin: [
        { id: 'users', path: '#/users', icon: '👥', label: 'Usuarios', roles: ['admin'] },
      ],
    };

    const sections = [];

    const mainItems = all.main.filter(i => i.roles.includes(role));
    if (mainItems.length) sections.push({ label: 'Principal', items: mainItems });

    const configItems = all.config.filter(i => i.roles.includes(role));
    if (configItems.length) sections.push({ label: 'Configuración', items: configItems });

    const reportItems = all.reports.filter(i => i.roles.includes(role));
    if (reportItems.length) sections.push({ label: 'Reportes & Auditoría', items: reportItems });

    const adminItems = all.admin.filter(i => i.roles.includes(role));
    if (adminItems.length) sections.push({ label: 'Administración', items: adminItems });

    return sections;
  },

  _profilePermissions(role) {
    const byRole = {
      admin: ['Usuarios y roles', 'Detecciones y alertas', 'Zonas restringidas', 'Sensores', 'Reportes', 'Auditoría', 'Configuración'],
      operator: ['Detecciones y alertas', 'Consulta de zonas', 'Consulta de sensores', 'Historial'],
      analyst: ['Consulta de detecciones', 'Consulta de alertas', 'Consulta de zonas', 'Reportes', 'Auditoría', 'Historial'],
    };
    return byRole[role] || [];
  },

  _formatProfileDate(value) {
    if (!value) return 'Sin registro';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Sin registro';
    return date.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
  },

  _profileInitials(user) {
    const parts = [user.first_name, user.last_name].filter(Boolean);
    const letters = parts.length ? parts.map(part => part[0]).join('') : (user.username || 'U').slice(0, 2);
    return letters.slice(0, 2).toUpperCase();
  },

  _profileTemplate(user) {
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'Usuario';
    const isActive = user.is_active !== false;
    const roleLabel = this._getRoleLabel(user.role);
    return `
      <section class="modal profile-modal" role="dialog" aria-modal="true" aria-labelledby="profile-title">
        <button class="modal-close profile-close" id="profile-close" aria-label="Cerrar perfil">✕</button>
        <header class="profile-hero">
          <div class="profile-avatar" aria-hidden="true">${escapeHtml(this._profileInitials(user))}</div>
          <div class="profile-identity">
            <h3 class="profile-name" id="profile-title">${escapeHtml(fullName)}</h3>
            <div class="profile-handle">@${escapeHtml(user.username || '')}</div>
            <div class="profile-badges">
              <span class="badge badge-info">${escapeHtml(roleLabel)}</span>
              <span class="badge ${isActive ? 'badge-success' : 'badge-neutral'}">${isActive ? 'Activo' : 'Inactivo'}</span>
            </div>
          </div>
        </header>

        <div id="profile-view">
          <dl class="profile-grid">
            <div class="profile-field"><dt>Correo</dt><dd>${escapeHtml(user.email || 'Sin correo registrado')}</dd></div>
            <div class="profile-field"><dt>Usuario</dt><dd>${escapeHtml(user.username || '')}</dd></div>
            <div class="profile-field"><dt>Rol</dt><dd>${escapeHtml(roleLabel)}</dd></div>
            <div class="profile-field"><dt>Último acceso</dt><dd id="profile-last-login">${escapeHtml(this._formatProfileDate(user.last_login))}</dd></div>
          </dl>
          <div class="profile-section">
            <div class="profile-section-title">Acceso de tu rol</div>
            <ul class="profile-chips">
              ${this._profilePermissions(user.role).map(item => `<li>${escapeHtml(item)}</li>`).join('')}
            </ul>
          </div>
          <div class="profile-actions">
            <button type="button" class="btn btn-secondary" id="profile-password-toggle">Cambiar contraseña</button>
            <button type="button" class="btn btn-danger" id="profile-logout">Cerrar sesión</button>
          </div>
        </div>

        <form class="profile-password" id="profile-password-form" hidden novalidate>
          <div class="profile-section-title">Cambiar contraseña</div>
          <div class="form-group">
            <label class="form-label" for="profile-current-password">Contraseña actual</label>
            <input class="form-input" type="password" id="profile-current-password" autocomplete="current-password" required>
          </div>
          <div class="form-group">
            <label class="form-label" for="profile-new-password">Nueva contraseña</label>
            <input class="form-input" type="password" id="profile-new-password" autocomplete="new-password" required aria-describedby="profile-password-hint">
            <small class="profile-hint" id="profile-password-hint">Mínimo 8 caracteres, con mayúscula, minúscula, número y símbolo.</small>
          </div>
          <div class="form-group">
            <label class="form-label" for="profile-confirm-password">Confirmar nueva contraseña</label>
            <input class="form-input" type="password" id="profile-confirm-password" autocomplete="new-password" required>
          </div>
          <p class="profile-error" id="profile-password-error" role="alert"></p>
          <div class="profile-actions">
            <button type="button" class="btn btn-secondary" id="profile-password-cancel">Cancelar</button>
            <button type="submit" class="btn btn-primary" id="profile-password-save">Guardar contraseña</button>
          </div>
        </form>
      </section>`;
  },

  showUserProfile() {
    const user = AuthService.getUser();
    if (!user) return;
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay visible';
    overlay.innerHTML = this._profileTemplate(user);

    const find = selector => overlay.querySelector(selector);
    const close = () => {
      overlay.remove();
      document.getElementById('user-profile-btn')?.focus();
    };
    const view = find('#profile-view');
    const form = find('#profile-password-form');
    const errorBox = find('#profile-password-error');
    const showForm = visible => {
      form.hidden = !visible;
      view.hidden = visible;
      errorBox.textContent = '';
      find(visible ? '#profile-current-password' : '#profile-password-toggle').focus();
    };

    find('#profile-close').addEventListener('click', close);
    find('#profile-password-toggle').addEventListener('click', () => showForm(true));
    find('#profile-password-cancel').addEventListener('click', () => { form.reset?.(); showForm(false); });
    find('#profile-logout').addEventListener('click', async () => {
      overlay.remove();
      await AuthService.logout();
      window.location.hash = '#/login';
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const current = find('#profile-current-password').value;
      const next = find('#profile-new-password').value;
      const repeat = find('#profile-confirm-password').value;
      const strong = next.length >= 8 && /[A-Z]/.test(next) && /[a-z]/.test(next) && /\d/.test(next) && /[^A-Za-z0-9]/.test(next);
      let message = '';
      if (!current || !next) message = 'Completa la contraseña actual y la nueva.';
      else if (!strong) message = 'La nueva contraseña no cumple los requisitos.';
      else if (next !== repeat) message = 'La confirmación no coincide con la nueva contraseña.';
      else if (next === current) message = 'La nueva contraseña debe ser diferente de la actual.';
      if (message) { errorBox.textContent = message; return; }

      const save = find('#profile-password-save');
      save.disabled = true;
      try {
        await AuthService.changePassword(current, next);
        overlay.remove();
        Toast.success('Contraseña actualizada. Inicia sesión de nuevo.');
        await AuthService.logout();
        window.location.hash = '#/login';
      } catch (error) {
        errorBox.textContent = error?.message || 'No fue posible cambiar la contraseña.';
        save.disabled = false;
      }
    });

    overlay.addEventListener('click', event => { if (event.target === overlay) close(); });
    overlay.addEventListener('keydown', event => {
      if (event.key === 'Escape') { close(); return; }
      if (event.key !== 'Tab' || !overlay.querySelectorAll) return;
      const focusable = [...overlay.querySelectorAll('button, input')]
        .filter(el => !el.disabled && !el.closest('[hidden]'));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    document.body.appendChild(overlay);
    find('#profile-close').focus();

    // El último acceso viene del servidor; se completa sin bloquear la apertura.
    AuthService.getMe?.().then(me => {
      const target = document.getElementById('profile-last-login');
      if (me && target) target.textContent = this._formatProfileDate(me.last_login);
    }).catch(() => {});
  },

  bindShellEvents() {
    const profile = document.getElementById('user-profile-btn');
    profile?.addEventListener('click', () => this.showUserProfile());
    profile?.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        this.showUserProfile();
      }
    });
    // Sidebar toggle
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._sidebarCollapsed = !this._sidebarCollapsed;
        localStorage.setItem('ag_sidebar_collapsed', this._sidebarCollapsed);
        document.getElementById('sidebar')?.classList.toggle('collapsed', this._sidebarCollapsed);
        document.getElementById('main-content')?.classList.toggle('sidebar-collapsed', this._sidebarCollapsed);
        document.getElementById('topbar')?.classList.toggle('sidebar-collapsed', this._sidebarCollapsed);
        toggleBtn.textContent = this._sidebarCollapsed ? '▶' : '◀';
      });
    }

    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', async () => {
      const ok = await import('./app.js').then(m => m.confirm('¿Cerrar sesión?', 'Cerrar Sesión'));
      if (!ok) return;
      await AuthService.logout();
      window.location.hash = '#/login';
    });

    // Alerts button
    document.getElementById('alerts-btn')?.addEventListener('click', () => {
      window.location.hash = '#/alerts';
    });

    // Synchronize current realtime status immediately on view mount
    this.updateWsStatus(WebSocketService.isConnected() !== false);
  },

  updateWsStatus(statusInfo, meta = {}) {
    let isLive = false;
    let label = 'Desconectado';
    let textColor = 'var(--text-muted)';
    let dotClass = 'status-dot status-offline';

    if (typeof statusInfo === 'boolean') {
      isLive = statusInfo;
      label = isLive ? 'En vivo' : 'Desconectado';
      textColor = isLive ? 'var(--success)' : 'var(--text-muted)';
      dotClass = isLive ? 'status-dot status-online' : 'status-dot status-offline';
    } else if (typeof statusInfo === 'object' && statusInfo !== null) {
      const state = statusInfo.status || (statusInfo.connected ? 'connected' : 'disconnected');
      if (state === 'connected') {
        isLive = true;
        label = statusInfo.latencyMs ? `En vivo (${statusInfo.latencyMs}ms)` : 'En vivo';
        textColor = 'var(--success)';
        dotClass = 'status-dot status-online';
      } else if (state === 'reconnecting') {
        label = statusInfo.attempt ? `Reconectando (${statusInfo.attempt})...` : 'Reconectando...';
        textColor = 'var(--warning)';
        dotClass = 'status-dot status-warning';
      } else if (state === 'connecting') {
        label = 'Conectando...';
        textColor = 'var(--warning)';
        dotClass = 'status-dot status-warning';
      } else {
        label = 'Desconectado';
        textColor = 'var(--text-muted)';
        dotClass = 'status-dot status-offline';
      }
    } else if (typeof statusInfo === 'string') {
      if (statusInfo === 'connected' || statusInfo === 'online') {
        isLive = true;
        label = meta.latencyMs ? `En vivo (${meta.latencyMs}ms)` : 'En vivo';
        textColor = 'var(--success)';
        dotClass = 'status-dot status-online';
      } else if (statusInfo === 'reconnecting') {
        label = meta.attempt ? `Reconectando (${meta.attempt})...` : 'Reconectando...';
        textColor = 'var(--warning)';
        dotClass = 'status-dot status-warning';
      } else if (statusInfo === 'connecting') {
        label = 'Conectando...';
        textColor = 'var(--warning)';
        dotClass = 'status-dot status-warning';
      } else {
        label = 'Desconectado';
        textColor = 'var(--text-muted)';
        dotClass = 'status-dot status-offline';
      }
    }

    const dot  = document.getElementById('ws-dot');
    const text = document.getElementById('ws-text');
    if (dot) dot.className = dotClass;
    if (text) {
      text.textContent = label;
      text.style.color = textColor;
    }

    // Update secondary live indicators across the views
    document.querySelectorAll('#live-dot, .live-dot, .status-live-dot').forEach(el => {
      el.className = dotClass;
    });
    document.querySelectorAll('.live-text, .live-status-text').forEach(el => {
      el.textContent = label;
      el.style.color = textColor;
    });
  },

  updateAlertBadge(count) {
    const badge = document.getElementById('alert-count-badge');
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  },
};

if (typeof window !== 'undefined') {
  window.Layout = Layout;
}
