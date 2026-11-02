import { escapeHtml } from '../utils/html.js';
/**
 * AeroGuard — Users View + ViewModel (RF-004 to RF-007)
 */
import { UserService, MockService } from '../services/api.service.js';
import { UserModel } from '../models/models.js';
import { Layout, Toast, confirm } from '../app.js';

class UsersViewModel {
  constructor() {
    this.state = { users: [], filtered: [], isLoading: true, search: '' };
  }

  async load() {
    this.state.isLoading = true;
    try {
      if (MockService.enabled) {
        await new Promise(r => setTimeout(r, 300));
        this.state.users = MockService.users.map(u => new UserModel(u));
      } else {
        const res = await UserService.list();
        this.state.users = (Array.isArray(res) ? res : (res.items || [])).map(u => new UserModel(u));
      }
      this._applyFilters();
    } catch (err) { Toast.error('Error al cargar usuarios.'); }
    finally { this.state.isLoading = false; }
  }

  _applyFilters() {
    const q = this.state.search.toLowerCase();
    this.state.filtered = q
      ? this.state.users.filter(u => u.fullName.toLowerCase().includes(q) || u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
      : [...this.state.users];
  }

  showUserModal(user = null) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">${user ? '✏️ Editar Usuario' : '➕ Nuevo Usuario'}</h3>
          <button class="modal-close" id="close-user-modal" aria-label="Cerrar">✕</button>
        </div>
        <form id="user-form">
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="user-fname">Nombre *</label>
              <input id="user-fname" type="text" class="form-input" required value="${escapeHtml(user?.firstName || '')}" aria-required="true"/>
            </div>
            <div class="form-group">
              <label class="form-label" for="user-lname">Apellido *</label>
              <input id="user-lname" type="text" class="form-input" required value="${escapeHtml(user?.lastName || '')}" aria-required="true"/>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label" for="user-username">Usuario *</label>
            <input id="user-username" type="text" class="form-input" required value="${escapeHtml(user?.username || '')}" ${user ? 'readonly style="opacity:0.6"' : ''} aria-required="true"/>
          </div>
          <div class="form-group">
            <label class="form-label" for="user-email">Correo Electrónico *</label>
            <input id="user-email" type="email" class="form-input" required value="${escapeHtml(user?.email || '')}" aria-required="true"/>
          </div>
          <div class="form-group">
            <label class="form-label" for="user-role">Rol *</label>
            <select id="user-role" class="form-select" required aria-required="true">
              <option value="operator" ${user?.role === 'operator' ? 'selected' : ''}>Operador de Seguridad</option>
              <option value="analyst"  ${user?.role === 'analyst'  ? 'selected' : ''}>Analista/Auditor</option>
              <option value="admin"    ${user?.role === 'admin'    ? 'selected' : ''}>Administrador</option>
            </select>
          </div>
          ${!user ? `
          <div class="form-group">
            <label class="form-label" for="user-password">Contraseña Inicial *</label>
            <input id="user-password" type="password" class="form-input" required minlength="8" placeholder="Mínimo 8 caracteres" aria-required="true"/>
          </div>
          ` : ''}
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="cancel-user">Cancelar</button>
            <button type="submit" class="btn btn-primary">${user ? '💾 Guardar' : '✅ Crear Usuario'}</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.classList.add('visible'), 10);
    overlay.querySelector('#close-user-modal')?.addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-user')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector('#user-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const button = overlay.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        if (await this._saveUser(user?.id)) overlay.remove();
      } finally {
        button.disabled = false;
      }
    });
  }

  async _saveUser(id = null) {
    const data = {
      first_name: document.getElementById('user-fname')?.value,
      last_name:  document.getElementById('user-lname')?.value,
      username:   document.getElementById('user-username')?.value,
      email:      document.getElementById('user-email')?.value,
      role:       document.getElementById('user-role')?.value,
      password:   document.getElementById('user-password')?.value,
    };
    try {
      if (MockService.enabled) {
        if (id) {
          const idx = MockService.users.findIndex(u => u.id === id);
          if (idx >= 0) Object.assign(MockService.users[idx], data);
        } else {
          MockService.users.push({ ...data, id: `U-${Date.now()}`, is_active: true, last_login: null });
        }
      } else {
        if (id) await UserService.update(id, data);
        else await UserService.create(data);
      }
      Toast.success(id ? 'Usuario actualizado.' : 'Usuario creado correctamente.');
      await this.load();
      this.renderTable();
      return true;
    } catch (err) { Toast.error(err.message); return false; }
  }

  async toggleUser(id, isActive) {
    const ok = await confirm(`¿${isActive ? 'Desactivar' : 'Activar'} este usuario?`);
    if (!ok) return;
    try {
      if (MockService.enabled) {
        const u = MockService.users.find(u => u.id === id);
        if (u) u.is_active = !u.is_active;
      } else {
        if (isActive) await UserService.deactivate(id);
        else await UserService.activate(id);
      }
      Toast.success(`Usuario ${isActive ? 'desactivado' : 'activado'}.`);
      await this.load(); this.renderTable();
    } catch (err) { Toast.error(err.message); }
  }

  renderTable() {
    const tbody = document.getElementById('users-tbody');
    if (!tbody) return;
    if (!this.state.filtered.length) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="empty-state-icon">👥</div><div class="empty-state-title">Sin usuarios</div></div></td></tr>`;
      return;
    }
    tbody.innerHTML = this.state.filtered.map(u => `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:var(--spacing-md)">
            <div class="user-avatar" style="width:36px;height:36px;font-size:13px">${u.initials}</div>
            <div>
              <div style="font-weight:600;color:var(--text-primary)">${escapeHtml(u.fullName)}</div>
              <div style="font-size:var(--font-size-xs);color:var(--text-muted)">@${escapeHtml(u.username)}</div>
            </div>
          </div>
        </td>
        <td style="color:var(--text-secondary)">${escapeHtml(u.email)}</td>
        <td><span class="badge badge-info">${u.roleLabel}</span></td>
        <td><span class="badge ${u.isActive ? 'badge-success badge-dot' : 'badge-neutral'}">${u.isActive ? 'Activo' : 'Inactivo'}</span></td>
        <td style="font-size:12px;color:var(--text-muted)">${u.lastLogin ? new Date(u.lastLogin).toLocaleString('es-CO', { dateStyle:'short', timeStyle:'short' }) : 'Nunca'}</td>
        <td>
          <div style="display:flex;gap:var(--spacing-sm)">
            <button class="btn btn-icon" onclick="usersVM.showUserModal(usersVM.state.users.find(u=>u.id==='${u.id}'))" title="Editar" aria-label="Editar usuario ${escapeHtml(u.fullName)}">✏️</button>
            <button class="btn btn-icon" onclick="usersVM.toggleUser('${u.id}', ${u.isActive})" title="${u.isActive ? 'Desactivar' : 'Activar'}" aria-label="${u.isActive ? 'Desactivar' : 'Activar'} usuario ${escapeHtml(u.fullName)}">
              ${u.isActive ? '⏸️' : '▶️'}
            </button>
          </div>
        </td>
      </tr>
    `).join('');
    window.usersVM = this;
  }

  bindEvents() {
    document.getElementById('new-user-btn')?.addEventListener('click', () => this.showUserModal());
    document.getElementById('user-search')?.addEventListener('input', e => {
      this.state.search = e.target.value;
      this._applyFilters();
      this.renderTable();
    });
  }
  destroy() {}
}

export class UsersView {
  constructor() { this.vm = new UsersViewModel(); }
  async render(container) {
    document.title = 'AeroGuard — Usuarios';
    container.innerHTML = Layout.renderShell('#/users', 'Gestión de Usuarios');
    Layout.bindShellEvents();
    document.getElementById('page-content').innerHTML = this._template();
    this.vm.bindEvents();
    await this.vm.load();
    this.vm.renderTable();
  }
  _template() {
    return `
<div class="fade-in">
  <div class="flex justify-between items-center mb-lg">
    <div>
      <h2 style="color:var(--text-primary)">Gestión de Usuarios</h2>
      <p style="color:var(--text-muted);font-size:var(--font-size-sm)">Administración de accesos y roles del sistema</p>
    </div>
    <button id="new-user-btn" class="btn btn-primary" aria-label="Crear nuevo usuario">➕ Nuevo Usuario</button>
  </div>
  <div class="card mb-lg">
    <div class="input-group" style="max-width:360px">
      <span class="input-icon">🔍</span>
      <input id="user-search" type="search" class="form-input" placeholder="Buscar usuario..." aria-label="Buscar usuarios"/>
    </div>
  </div>
  <div class="card" style="padding:0">
    <div class="table-container">
      <table class="table" role="grid" aria-label="Tabla de usuarios">
        <thead>
          <tr>
            <th scope="col">Usuario</th>
            <th scope="col">Correo</th>
            <th scope="col">Rol</th>
            <th scope="col">Estado</th>
            <th scope="col">Último Acceso</th>
            <th scope="col">Acciones</th>
          </tr>
        </thead>
        <tbody id="users-tbody" aria-live="polite"><!-- Rendered by VM --></tbody>
      </table>
    </div>
  </div>
</div>`;
  }
  destroy() { this.vm.destroy(); }
}
