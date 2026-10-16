/**
 * AeroGuard — Login ViewModel (MVVM)
 * Gestiona el estado y lógica de la vista de inicio de sesión.
 */

import { AuthService, MockService } from '../services/api.service.js';
import { Toast } from '../app.js';

export class LoginViewModel {
  constructor() {
    // State
    this.state = {
      username: '',
      password: '',
      isLoading: false,
      showPassword: false,
      error: null,
      activeTab: 'login', // 'login' | 'forgot'
      forgotEmail: '',
      forgotSent: false,
    };
  }

  // Validate form fields
  validate() {
    if (!this.state.username.trim()) return 'El nombre de usuario es obligatorio.';
    if (!this.state.password)        return 'La contraseña es obligatoria.';
    if (this.state.password.length < 6) return 'La contraseña debe tener al menos 6 caracteres.';
    return null;
  }

  // Handle login submission
  async submit() {
    const error = this.validate();
    if (error) {
      this.state.error = error;
      this._updateErrorUI(error);
      return false;
    }

    this.state.isLoading = true;
    this.state.error = null;
    this._setLoading(true);

    let data;
    try {
      try {
        data = await MockService.fakeLogin(this.state.username, this.state.password);
      } catch (mockErr) {
        data = await AuthService.login(this.state.username, this.state.password);
      }
      AuthService.saveSession(data.access_token, data.user);
      Toast.success(`Bienvenido, ${data.user?.first_name || data.user?.username}`);
      return true;
    } catch (err) {
      this.state.error = err.message || 'Error al iniciar sesión';
      this._updateErrorUI(this.state.error);
      return false;
    } finally {
      this.state.isLoading = false;
      this._setLoading(false);
    }
  }

  // Handle forgot password
  async submitForgot() {
    if (!this.state.forgotEmail) {
      Toast.warn('Ingresa tu correo electrónico.');
      return;
    }
    this._setForgotLoading(true);
    try {
      if (!MockService.enabled) {
        await AuthService.requestPasswordReset(this.state.forgotEmail);
      } else {
        await new Promise(r => setTimeout(r, 800));
      }
      this.state.forgotSent = true;
      this._renderForgotSuccess();
    } catch (err) {
      Toast.error(err.message);
    } finally {
      this._setForgotLoading(false);
    }
  }

  // --- UI update helpers ---

  _setLoading(loading) {
    const btn = document.getElementById('login-btn');
    const spinner = document.getElementById('login-spinner');
    const btnText = document.getElementById('login-btn-text');
    if (!btn) return;
    btn.disabled = loading;
    spinner?.classList.toggle('hidden', !loading);
    if (btnText) btnText.textContent = loading ? 'Verificando...' : 'Iniciar Sesión';
  }

  _setForgotLoading(loading) {
    const btn = document.getElementById('forgot-btn');
    if (btn) btn.disabled = loading;
  }

  _updateErrorUI(message) {
    const el = document.getElementById('login-error');
    if (!el) return;
    if (message) {
      el.classList.remove('hidden');
      el.querySelector('.alert-message').textContent = message;
    } else {
      el.classList.add('hidden');
    }
  }

  _renderForgotSuccess() {
    const form = document.getElementById('forgot-form');
    if (form) {
      form.innerHTML = `
        <div class="empty-state" style="padding:var(--spacing-xl) 0">
          <div class="empty-state-icon">📧</div>
          <div class="empty-state-title">Correo enviado</div>
          <div class="empty-state-message">
            Revisa tu bandeja de entrada en <strong>${this.state.forgotEmail}</strong>.
            Si el correo existe en el sistema, recibirás las instrucciones.
          </div>
          <button class="btn btn-secondary mt-lg" id="back-to-login-btn">
            ← Volver al inicio de sesión
          </button>
        </div>
      `;
      document.getElementById('back-to-login-btn')?.addEventListener('click', () => {
        this._showTab('login');
      });
    }
  }

  _showTab(tab) {
    this.state.activeTab = tab;
    const loginTab = document.getElementById('login-form-section');
    const forgotTab = document.getElementById('forgot-form-section');
    loginTab?.classList.toggle('hidden', tab !== 'login');
    forgotTab?.classList.toggle('hidden', tab !== 'forgot');
  }

  // Bind all events
  bindEvents() {
    const form = document.getElementById('login-form');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      this.state.username = document.getElementById('username')?.value || '';
      this.state.password = document.getElementById('password')?.value || '';
      const ok = await this.submit();
      if (ok) window.location.hash = '#/dashboard';
    });

    // Show/hide password
    document.getElementById('toggle-password')?.addEventListener('click', () => {
      this.state.showPassword = !this.state.showPassword;
      const input = document.getElementById('password');
      const icon  = document.getElementById('toggle-password-icon');
      if (input) input.type = this.state.showPassword ? 'text' : 'password';
      if (icon)  icon.textContent = this.state.showPassword ? '🙈' : '👁️';
    });

    // Forgot password link
    document.getElementById('forgot-password-link')?.addEventListener('click', (e) => {
      e.preventDefault();
      this._showTab('forgot');
    });

    // Back to login
    document.getElementById('back-to-login')?.addEventListener('click', (e) => {
      e.preventDefault();
      this._showTab('login');
    });

    // Forgot password form
    document.getElementById('forgot-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      this.state.forgotEmail = document.getElementById('forgot-email')?.value || '';
      await this.submitForgot();
    });

    // Username/password live validation
    document.getElementById('username')?.addEventListener('input', (e) => {
      this.state.username = e.target.value;
      if (this.state.error) {
        this.state.error = null;
        this._updateErrorUI(null);
      }
    });

    document.getElementById('password')?.addEventListener('input', (e) => {
      this.state.password = e.target.value;
      if (this.state.error) {
        this.state.error = null;
        this._updateErrorUI(null);
      }
    });

    // Demo credential quick-fill
    document.querySelectorAll('.demo-cred-item').forEach(item => {
      item.addEventListener('click', () => {
        const u = item.dataset.username;
        const p = item.dataset.password;
        const usernameEl = document.getElementById('username');
        const passwordEl = document.getElementById('password');
        if (usernameEl) { usernameEl.value = u; this.state.username = u; }
        if (passwordEl) { passwordEl.value = p; this.state.password = p; }
      });
    });
  }

  destroy() {}
}
