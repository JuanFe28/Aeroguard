/**
 * AeroGuard — Login View (MVVM - View Layer)
 * Renderiza la pantalla de inicio de sesión.
 */

import { LoginViewModel } from '../viewmodels/login.viewmodel.js';
import { MockService } from '../services/api.service.js';

export class LoginView {
  constructor() {
    this.vm = new LoginViewModel();
  }

  async render(container) {
    document.title = 'AeroGuard — Iniciar Sesión';
    container.innerHTML = this._template();
    this.vm.bindEvents();
  }

  _template() {
    const creds = MockService.enabled ? MockService.demoCredentials : [];
    return `
<div class="login-page" role="main">
  <!-- Left Panel: Branding -->
  <div class="login-left" aria-hidden="true">
    <div class="login-left-content">
      <!-- Logo -->
      <div class="login-logo">
        <div class="login-logo-icon">🛡️</div>
        <div class="login-logo-text">
          <span class="login-logo-name">AEROGUARD</span>
          <span class="login-logo-sub">Sistema de Monitoreo</span>
        </div>
      </div>

      <!-- Headline -->
      <h1 class="login-headline">
        Protección del<br><span>espacio aéreo</span><br>en tiempo real
      </h1>
      <p class="login-description">
        Sistema inteligente para la detección, clasificación y monitoreo de
        drones no autorizados. Vigilancia 24/7 con visión artificial e
        inteligencia de datos.
      </p>

      <!-- Feature highlights -->
      <div class="login-features">
        <div class="login-feature">
          <div class="login-feature-icon" style="background:rgba(0,212,255,0.1)">📡</div>
          <div class="login-feature-text">
            <div class="login-feature-title">Sensores Multi-tipo</div>
            <div class="login-feature-desc">Radar, óptico, acústico y RF integrados</div>
          </div>
        </div>
        <div class="login-feature">
          <div class="login-feature-icon" style="background:rgba(0,102,255,0.1)">🤖</div>
          <div class="login-feature-text">
            <div class="login-feature-title">IA con YOLO</div>
            <div class="login-feature-desc">Clasificación automática: posible dron / no dron</div>
          </div>
        </div>
        <div class="login-feature">
          <div class="login-feature-icon" style="background:rgba(255,23,68,0.1)">🔴</div>
          <div class="login-feature-text">
            <div class="login-feature-title">Alertas Automáticas</div>
            <div class="login-feature-desc">Zonas restringidas y comportamiento anómalo</div>
          </div>
        </div>
        <div class="login-feature">
          <div class="login-feature-icon" style="background:rgba(0,230,118,0.1)">🔒</div>
          <div class="login-feature-text">
            <div class="login-feature-title">Seguridad OAuth 2.0 + JWT</div>
            <div class="login-feature-desc">Control de acceso por roles, OWASP Top 10</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Decorative radar animation -->
    <div class="login-radar" aria-hidden="true">
      <div class="radar-ring"></div>
      <div class="radar-ring"></div>
      <div class="radar-ring"></div>
    </div>
  </div>

  <!-- Right Panel: Login Form -->
  <div class="login-right">
    <div class="login-form-container">
      <!-- Tab: Login -->
      <div id="login-form-section">
        <h2 class="login-form-title">Iniciar Sesión</h2>
        <p class="login-form-subtitle">Accede con tus credenciales institucionales</p>

        <!-- Error Alert -->
        <div id="login-error" class="alert alert-danger hidden" role="alert" aria-live="assertive">
          <span class="alert-icon">⚠️</span>
          <div class="alert-content">
            <div class="alert-message"></div>
          </div>
        </div>

        <!-- Login Form -->
        <form id="login-form" novalidate>
          <div class="form-group">
            <label for="username" class="form-label">Usuario</label>
            <div class="input-group">
              <span class="input-icon" aria-hidden="true">👤</span>
              <input
                id="username"
                type="text"
                class="form-input"
                placeholder="Nombre de usuario"
                autocomplete="username"
                required
                aria-required="true"
                aria-describedby="username-hint"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="password" class="form-label">Contraseña</label>
            <div class="input-group" style="position:relative">
              <span class="input-icon" aria-hidden="true">🔑</span>
              <input
                id="password"
                type="password"
                class="form-input"
                placeholder="••••••••"
                autocomplete="current-password"
                required
                aria-required="true"
                style="padding-right:48px"
              />
              <button
                type="button"
                id="toggle-password"
                aria-label="Mostrar u ocultar contraseña"
                style="position:absolute;right:12px;background:none;border:none;cursor:pointer;color:var(--text-muted);font-size:18px;line-height:1"
              >
                <span id="toggle-password-icon">👁️</span>
              </button>
            </div>
          </div>

          <div class="flex justify-between items-center mb-lg">
            <a href="#" id="forgot-password-link" class="text-accent" style="font-size:var(--font-size-sm)">
              ¿Olvidaste tu contraseña?
            </a>
          </div>

          <button type="submit" id="login-btn" class="btn btn-primary btn-block btn-lg" aria-live="polite">
            <span class="loading-spinner hidden" id="login-spinner" aria-hidden="true" style="width:18px;height:18px;border-width:2px"></span>
            <span id="login-btn-text">Iniciar Sesión</span>
          </button>
        </form>

        ${creds.length ? `
        <div class="demo-credentials" role="region" aria-label="Credenciales de demostración">
          <div class="demo-credentials-title">🧪 Demo — Haz clic para rellenar</div>
          ${creds.map(c => `
            <div class="demo-cred-item" data-username="${c.username}" data-password="${c.password}" role="button" tabindex="0" aria-label="Usar credenciales de ${c.role}">
              <span><strong>${c.username}</strong> / ${c.password}</span>
              <span class="demo-cred-role">${c.role}</span>
            </div>
          `).join('')}
        </div>
        ` : ''}
      </div>

      <!-- Tab: Forgot Password -->
      <div id="forgot-form-section" class="hidden">
        <h2 class="login-form-title">Recuperar Contraseña</h2>
        <p class="login-form-subtitle">Te enviaremos un enlace a tu correo</p>

        <form id="forgot-form" novalidate>
          <div class="form-group">
            <label for="forgot-email" class="form-label">Correo Electrónico</label>
            <div class="input-group">
              <span class="input-icon" aria-hidden="true">📧</span>
              <input
                id="forgot-email"
                type="email"
                class="form-input"
                placeholder="tu@correo.com"
                autocomplete="email"
                required
                aria-required="true"
              />
            </div>
          </div>

          <button type="submit" id="forgot-btn" class="btn btn-primary btn-block mt-md">
            Enviar Enlace de Recuperación
          </button>
          <button type="button" id="back-to-login" class="btn btn-secondary btn-block mt-md">
            ← Volver al inicio de sesión
          </button>
        </form>
      </div>

      <div class="login-footer">
        AeroGuard v1.0 — Prototipo Académico · UTS<br>
        <span style="opacity:0.5">© 2026 — Solo para uso educativo</span>
      </div>
    </div>
  </div>
</div>
    `;
  }

  destroy() {
    this.vm.destroy();
  }
}

// ============================================================
// RESET PASSWORD VIEW (RF-003)
// ============================================================

export class ResetPasswordView {
  async render(container, query = {}) {
    document.title = 'AeroGuard — Restablecer Contraseña';
    const token = query.token || '';
    container.innerHTML = this._template(token);
    this._bindEvents(token);
  }

  _template(token) {
    return `
<div class="login-page" role="main">
  <div class="login-left" aria-hidden="true">
    <div class="login-left-content">
      <div class="login-logo">
        <div class="login-logo-icon">🛡️</div>
        <div class="login-logo-text">
          <span class="login-logo-name">AEROGUARD</span>
          <span class="login-logo-sub">Sistema de Monitoreo</span>
        </div>
      </div>
      <h1 class="login-headline">Restablece tu<br><span>contraseña</span></h1>
      <p class="login-description">
        Ingresa una nueva contraseña segura para recuperar el acceso a tu cuenta operativa en AeroGuard.
      </p>
    </div>
  </div>

  <div class="login-right">
    <div class="login-form-container">
      <h2 class="login-form-title">Nueva Contraseña</h2>
      <p class="login-form-subtitle">Mínimo 8 caracteres, incluye mayúsculas y números</p>

      <div id="reset-error" class="alert alert-danger hidden" role="alert">
        <span class="alert-icon">⚠️</span>
        <div class="alert-content"><div class="alert-message"></div></div>
      </div>

      <form id="reset-password-form" novalidate>
        <div class="form-group">
          <label for="new-pass" class="form-label">Nueva Contraseña</label>
          <input id="new-pass" type="password" class="form-input" placeholder="••••••••" required />
        </div>

        <div class="form-group">
          <label for="confirm-pass" class="form-label">Confirmar Contraseña</label>
          <input id="confirm-pass" type="password" class="form-input" placeholder="••••••••" required />
        </div>

        <button type="submit" id="reset-submit-btn" class="btn btn-primary btn-block btn-lg mt-md">
          Actualizar Contraseña
        </button>
        <a href="#/login" class="btn btn-secondary btn-block mt-md text-center" style="display:block">
          ← Cancelar y volver al Login
        </a>
      </form>
    </div>
  </div>
</div>
    `;
  }

  _bindEvents(token) {
    const form = document.getElementById('reset-password-form');
    const errEl = document.getElementById('reset-error');
    const btn = document.getElementById('reset-submit-btn');

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const p1 = document.getElementById('new-pass')?.value || '';
      const p2 = document.getElementById('confirm-pass')?.value || '';

      const showError = (msg) => {
        if (!errEl) return;
        errEl.classList.remove('hidden');
        errEl.querySelector('.alert-message').textContent = msg;
      };

      if (!p1 || p1.length < 8) {
        showError('La contraseña debe contener al menos 8 caracteres.');
        return;
      }
      if (p1 !== p2) {
        showError('Las contraseñas no coinciden.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Actualizando...';

      try {
        const { AuthService, MockService } = await import('../services/api.service.js');
        const { Toast } = await import('../app.js');

        if (MockService.enabled) {
          await new Promise(r => setTimeout(r, 600));
        } else {
          await AuthService.resetPassword(token, p1);
        }

        Toast.success('Contraseña actualizada con éxito. Inicia sesión ahora.');
        window.location.hash = '#/login';
      } catch (err) {
        showError(err.message || 'Error al restablecer la contraseña.');
        btn.disabled = false;
        btn.textContent = 'Actualizar Contraseña';
      }
    });
  }

  destroy() {}
}

