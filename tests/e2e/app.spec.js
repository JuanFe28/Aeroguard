import { test as base, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { randomBytes } from 'node:crypto';

const routes = {
  dashboard: 'Dashboard', detections: 'Detecciones', alerts: 'Alertas',
  zones: 'Zonas', users: 'Usuarios', sensors: 'Sensores', reports: 'Reportes',
  history: 'Historial', audit: 'Auditoría', 'detection-config': 'Configuración',
  trajectory: 'Trayectorias',
};
const palette = { '--bg-primary': '#0a0e1a', '--brand-primary': '#00d4ff', '--danger': '#ff1744' };

const test = base.extend({
  qa: [async ({ playwright }, use) => {
    const baseURL = process.env.AEROGUARD_QA_URL || 'http://127.0.0.1:18082';
    if (process.env.AEROGUARD_QA_CONFIRM !== 'isolated') throw new Error('Solo QA aislado: falta AEROGUARD_QA_CONFIRM=isolated.');
    const target = new URL(baseURL);
    if (!['http:', 'https:'].includes(target.protocol) || !['frontend', 'localhost', '127.0.0.1', '[::1]'].includes(target.hostname) || target.username || target.password || target.pathname !== '/' || target.search || target.hash) throw new Error('Se requiere una URL privada de QA sin credenciales ni parámetros.');
    const api = await playwright.request.newContext({ baseURL, maxRedirects: 0 });
    const health = await api.get('/health');
    expect(health.status()).toBe(200);
    const info = await health.json();
    if (!String(info.version).includes('-qa.')) throw new Error('El destino no está identificado como QA; no se crearán datos.');
    const secret = process.env.AEROGUARD_QA_ADMIN_PASSWORD;
    if (!secret) throw new Error('Falta la contraseña privada de bootstrap de QA.');
    const login = await api.post('/api/v1/auth/token', { form: { username: 'admin', password: secret } });
    expect(login.status()).toBe(200);
    const bootstrap = (await login.json()).access_token;
    const prefix = 'qa_' + randomBytes(5).toString('hex');
    const password = 'Qa@' + randomBytes(18).toString('hex');
    const roles = {};
    for (const role of ['admin', 'operator', 'analyst']) {
      const username = `${prefix}_${role}`;
      const created = await api.post('/api/v1/users', {
        headers: { Authorization: `Bearer ${bootstrap}` },
        data: { username, email: `${username}@example.com`, password, first_name: 'QA', last_name: role, role },
      });
      expect(created.status(), `Crear usuario sintético ${role}`).toBe(201);
      const session = await api.post('/api/v1/auth/token', { form: { username, password } });
      expect(session.status()).toBe(200);
      roles[role] = { username, password, token: (await session.json()).access_token, user: await created.json() };
    }
    const admin = await playwright.request.newContext({ baseURL, extraHTTPHeaders: { Authorization: `Bearer ${roles.admin.token}` }, maxRedirects: 0 });
    const zoneRes = await admin.post('/api/v1/zones', { data: {
      name: `${prefix}_zona_sintetica`, min_altitude: 0, max_altitude: 200, is_active: true,
      coordinates: [[7, -73], [7, -72.99], [7.01, -72.99], [7.01, -73]], threat_level: 'high',
    } });
    expect(zoneRes.status()).toBe(201);
    const zone = await zoneRes.json();
    const sensorRes = await admin.post('/api/v1/sensors', { data: { name: `${prefix}_sensor`, latitude: 7.005, longitude: -72.995, altitude: 0, range_km: 5, status: 'active' } });
    expect(sensorRes.status()).toBe(201);
    const sensor = await sensorRes.json();
    let detection;
    for (const latitude of [7.004, 7.005, 7.006]) {
      const packet = await admin.post('/api/v1/sensors/telemetry', { data: { sensor_id: sensor.id, object_id: `${prefix}_objeto`, latitude, longitude: -72.995, altitude: 60, speed: 10, heading: 45 } });
      expect(packet.status()).toBe(202);
      detection = (await packet.json()).detection_id;
    }
    const alerts = await (await admin.get('/api/v1/alerts?limit=500')).json();
    const alert = alerts.find(a => a.detection_id === detection);
    expect(alert).toBeTruthy();
    await use({ api: admin, roles, prefix, zone, sensor, detection, alert, health: info });
    // No se borra la evidencia sintética al terminar. Otra ejecución usa un prefijo nuevo.
    await admin.dispose(); await api.dispose();
  }, { scope: 'worker' }],
});

const runtimeErrors = new WeakMap();
test.beforeEach(async ({ page }) => {
  const errors = [];
  runtimeErrors.set(page, errors);
  page.on('pageerror', error => errors.push({ message: error.message, stack: error.stack }));
});
test.afterEach(async ({ page }, info) => {
  const errors = runtimeErrors.get(page) || [];
  await attachJSON(info, 'errores-javascript', errors);
  expect.soft(errors, 'No deben ocurrir excepciones JavaScript sin manejar').toEqual([]);
});

async function login(page, account) {
  await page.goto('/#/login');
  await page.locator('#username').fill(account.username);
  await page.locator('#password').fill(account.password);
  await page.locator('#login-btn').click();
  await expect(page).toHaveURL(/#\/dashboard$/);
  await expect(page.locator('#page-title')).toBeVisible();
}
async function goto(page, route) {
  await page.goto(`/#/${route}`);
  await expect(page.locator('#page-title')).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`#/${route}$`));
  await expect(page.locator('.skeleton')).toHaveCount(0);
}
async function attachJSON(info, name, value) {
  await info.attach(name, { body: Buffer.from(JSON.stringify(value, null, 2)), contentType: 'application/json' });
}
async function inspect(page, info, label) {
  // Inventario: nunca guardar valores introducidos ni almacenamiento/tokens.
  const inventory = await page.evaluate(() => ({
    title: document.title,
    text: document.querySelector('#page-content')?.innerText || document.querySelector('#login-form-section')?.innerText,
    controls: [...document.querySelectorAll('button,a,input,select,textarea,[role="button"]')].filter(e => e.getClientRects().length).map(e => ({
      tag: e.tagName, id: e.id, name: e.getAttribute('name'), type: e.getAttribute('type'),
      label: e.getAttribute('aria-label') || e.labels?.[0]?.innerText || e.innerText?.trim(),
      required: !!e.required, min: e.min, max: e.max, maxLength: e.maxLength, disabled: !!e.disabled,
      color: getComputedStyle(e).color, background: getComputedStyle(e).backgroundColor,
      font: getComputedStyle(e).fontFamily, fontSize: getComputedStyle(e).fontSize,
    })),
    overflow: document.documentElement.scrollWidth > innerWidth + 2,
    contentOverflow: !!document.querySelector('#page-content') && document.querySelector('#page-content').scrollWidth > document.querySelector('#page-content').clientWidth + 2,
    palette: Object.fromEntries(['--bg-primary', '--brand-primary', '--danger'].map(k => [k, getComputedStyle(document.documentElement).getPropertyValue(k).trim()])),
  }));
  await attachJSON(info, `inventario-${label}`, inventory);
  const screenshot = await page.screenshot({ fullPage: true, animations: 'disabled', caret: 'hide', mask: [page.locator('input[type="password"]')] });
  await info.attach(`pantalla-${label}`, { body: screenshot, contentType: 'image/png' });
  expect.soft(inventory.text || '').not.toMatch(/\uFFFD|undefined|\[object Object\]|API KEY REQUIRED/);
  expect.soft(inventory.palette).toEqual(palette);
  expect.soft(inventory.overflow, `Desbordamiento horizontal ${label}`).toBe(false);
  expect.soft(inventory.contentOverflow, `Contenido recortado dentro de la página ${label}`).toBe(false);
}

test('Acceso: obligatorios, contraseña visible, recuperación y retorno', async ({ page, qa }, info) => {
  await page.goto('/#/login');
  await page.locator('#login-btn').click();
  await expect(page.locator('#login-error')).toContainText('obligatorio');
  await page.locator('#username').fill(qa.roles.admin.username);
  await page.locator('#password').fill('x');
  await page.locator('#login-btn').click();
  await expect(page.locator('#login-error')).toContainText('6 caracteres');
  await page.locator('#toggle-password').click();
  await expect(page.locator('#password')).toHaveAttribute('type', 'text');
  await page.locator('#toggle-password').click();
  await page.locator('#password').fill('');
  await page.locator('#forgot-password-link').click();
  await expect(page.locator('#forgot-email')).toBeVisible();
  await page.locator('#forgot-btn').click();
  await expect(page.locator('.toast-message')).toContainText('correo');
  await page.locator('#forgot-email').fill('correo-invalido');
  await page.locator('#forgot-btn').click();
  await expect(page.locator('.toast-danger')).toBeVisible();
  await page.locator('#back-to-login').click();
  await expect(page.locator('#username')).toBeVisible();
  await inspect(page, info, 'login');
});

test('Recuperación: enlace sin token no cambia ninguna contraseña', async ({ page, qa }) => {
  await page.goto('/#/reset-password');
  await page.locator('#new-pass').fill('NuevaSoloQA@12345');
  await page.locator('#confirm-pass').fill('OtraSoloQA@12345');
  await page.locator('#reset-submit-btn').click();
  await expect(page.locator('#reset-error')).toBeVisible();
  await page.locator('#confirm-pass').fill('NuevaSoloQA@12345');
  await page.locator('#reset-submit-btn').click();
  await expect(page.locator('#reset-error')).toBeVisible();
});

for (const [route, title] of Object.entries(routes)) {
  for (const [width, height] of [[1440, 1000], [768, 1024], [390, 844]]) {
    test(`Pantalla ${title}: ${width}px, texto, colores y diseño`, async ({ page, qa }, info) => {
      await page.setViewportSize({ width, height });
      await login(page, qa.roles.admin);
      await goto(page, route);
      await expect(page).toHaveTitle(new RegExp(title));
      await inspect(page, info, `${route}-${width}`);
      if (width === 1440) {
        const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
        const violations = scan.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, helpUrl: v.helpUrl, nodes: v.nodes.map(n => ({ target: n.target, failureSummary: n.failureSummary })) }));
        await attachJSON(info, `accesibilidad-${route}`, violations);
        expect.soft(violations.filter(v => ['serious', 'critical'].includes(v.impact)), 'Contraste, etiquetas y accesibilidad').toEqual([]);
      }
    });
  }
}

test('Shell: todos los enlaces, perfil por teclado, sidebar, alertas y salida', async ({ page, qa }) => {
  await login(page, qa.roles.admin);
  for (const route of Object.keys(routes)) {
    await page.locator(`.sidebar a.nav-item[href="#/${route}"]`).click();
    await expect(page).toHaveURL(new RegExp(`#/${route}$`));
  }
  await page.locator('#user-profile-btn').focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toContainText(qa.roles.admin.username);
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.locator('#sidebar-toggle-btn').click(); await expect(page.locator('#sidebar')).toHaveClass(/collapsed/);
  await page.locator('#sidebar-toggle-btn').click(); await expect(page.locator('#sidebar')).not.toHaveClass(/collapsed/);
  await page.locator('#alerts-btn').click(); await expect(page).toHaveURL(/#\/alerts$/);
  await page.locator('#logout-btn').click(); await page.locator('#confirm-cancel').click();
  await expect(page.locator('#page-title')).toBeVisible();
  // La salida revoca sesiones del usuario; usar una cuenta descartable propia.
  const disposable = { username: `${qa.prefix}_logout`, password: 'SoloLogoutQA@12345' };
  expect((await qa.api.post('/api/v1/users', { data: { ...disposable, email: `${disposable.username}@example.com`, first_name: 'QA', last_name: 'logout', role: 'operator' } })).status()).toBe(201);
  await page.evaluate(() => localStorage.clear()); await login(page, disposable);
  await page.locator('#logout-btn').click(); await page.locator('#confirm-ok').click();
  await expect(page).toHaveURL(/#\/login$/);
});

test('Sensores: todos los campos, límites, cancelar, crear, activar y editar', async ({ page, qa }, info) => {
  await login(page, qa.roles.admin); await goto(page, 'sensors');
  await page.locator('#refresh-sensors-btn').click();
  await page.locator('#new-sensor-btn').click(); await page.locator('#cancel-sensor').click();
  await page.locator('#new-sensor-btn').click(); await page.locator('#close-sensor-modal').click();
  await page.locator('#new-sensor-btn').click();
  await page.locator('#sensor-form button[type="submit"]').click();
  await expect(page.locator('#sensor-form')).toBeVisible();
  await page.locator('#sensor-name').fill(`${qa.prefix}_UI_sensor`);
  await page.locator('#sensor-type').selectOption({ index: 0 });
  for (const [id, value] of Object.entries({ 'sensor-lat': '91', 'sensor-lng': '0', 'sensor-alt': '0', 'sensor-range': '5' })) await page.locator(`#${id}`).fill(value);
  expect(await page.locator('#sensor-lat').evaluate(e => e.validity.rangeOverflow)).toBe(true);
  await page.locator('#sensor-lat').fill('0');
  await inspect(page, info, 'sensor-formulario');
  await page.locator('#sensor-form button[type="submit"]').click(); await expect(page.locator('#sensor-form')).toHaveCount(0);
  const card = page.getByRole('article', { name: `Sensor: ${qa.prefix}_UI_sensor`, exact: true });
  await expect(card).toContainText('Inactivo');
  await card.getByRole('button', { name: /^Activar sensor/ }).click(); await page.locator('#confirm-cancel').click();
  await card.getByRole('button', { name: /^Activar sensor/ }).click(); await page.locator('#confirm-ok').click();
  await expect(card).toContainText('En línea');
  await card.getByRole('button', { name: /^Editar sensor/ }).click();
  await expect(page.locator('#sensor-lat')).toHaveValue('0');
  await page.locator('#sensor-alt').fill('10'); await page.locator('#sensor-form button[type="submit"]').click();
  await expect(page.locator('#sensor-form')).toHaveCount(0); await expect(card).toContainText('En línea');
  await card.getByRole('button', { name: /^Desactivar sensor/ }).click(); await page.locator('#confirm-ok').click();
  await expect(card).toContainText('Inactivo');
});

test('Usuarios: todos los campos, crear, buscar, editar y estados', async ({ page, qa }, info) => {
  await login(page, qa.roles.admin); await goto(page, 'users');
  await page.locator('#new-user-btn').click(); await page.locator('#cancel-user').click();
  await page.locator('#new-user-btn').click(); await page.locator('#close-user-modal').click();
  await page.locator('#new-user-btn').click();
  const username = `${qa.prefix}_UI`;
  for (const [id, value] of Object.entries({ 'user-fname': 'Prueba ñá', 'user-lname': 'Interfaz', 'user-username': username, 'user-email': `${username}@example.com`, 'user-password': 'SoloDatosQA@12345' })) await page.locator(`#${id}`).fill(value);
  await page.locator('#user-role').selectOption('operator');
  await inspect(page, info, 'usuario-formulario');
  await page.locator('#user-form button[type="submit"]').click(); await expect(page.locator('#user-form')).toHaveCount(0);
  await page.locator('#user-search').fill(username);
  const row = page.locator('#users-tbody tr').filter({ hasText: username });
  await expect(row).toHaveCount(1);
  await row.getByRole('button', { name: /^Editar usuario/ }).click();
  await expect(page.locator('#user-username')).toHaveAttribute('readonly', '');
  await page.locator('#user-fname').fill('Editado ñá'); await page.locator('#user-role').selectOption('analyst');
  await page.locator('#user-form button[type="submit"]').click(); await expect(row).toContainText('Editado ñá');
  await row.getByRole('button', { name: /^Desactivar usuario/ }).click(); await page.locator('#confirm-ok').click();
  await expect(row).toContainText('Inactivo');
  await row.getByRole('button', { name: /^Activar usuario/ }).click(); await page.locator('#confirm-ok').click();
  await expect(row).toContainText('Activo');
});

test('Zonas: campos, altitudes, dibujo, mapa, edición, estado y eliminación', async ({ page, qa }, info) => {
  await login(page, qa.roles.admin); await goto(page, 'zones');
  for (const id of ['btn-jump-bogota', 'btn-jump-buca', 'btn-fit-all']) await page.locator(`#${id}`).click();
  await page.locator('#new-zone-btn').click(); await page.locator('#cancel-zone').click();
  await page.locator('#new-zone-btn').click(); await page.locator('#close-zone-modal').click();
  await page.locator('#new-zone-btn').click();
  const name = `${qa.prefix}_UI_zona`;
  await page.locator('#zone-name').fill(name); await page.locator('#zone-description').fill('QA sintético, ñá y texto de prueba.');
  await page.locator('#zone-severity').selectOption('high');
  await page.locator('#zone-min-alt').fill('300'); await page.locator('#zone-max-alt').fill('100');
  await page.locator('#save-zone-btn').click(); await expect(page.locator('#zone-form')).toBeVisible();
  await page.locator('#zone-min-alt').fill('0'); await page.locator('#zone-max-alt').fill('200');
  await inspect(page, info, 'zona-formulario');
  await page.locator('#save-zone-btn').click(); await expect(page.locator('#zone-form')).toHaveCount(0);
  await expect(page.locator('#zone-detail-panel')).toContainText(name);
  await page.getByRole('button', { name: 'Dibujar Polígono', exact: true }).click();
  const map = page.locator('#zones-map');
  for (const position of [{ x: 180, y: 180 }, { x: 320, y: 180 }, { x: 280, y: 320 }]) await map.click({ position });
  await page.getByRole('button', { name: 'Guardar Polígono', exact: true }).click();
  await expect(page.locator('.toast-message').filter({ hasText: 'Polígono delimitado' })).toBeVisible();
  await page.getByRole('button', { name: `Editar zona ${name}`, exact: true }).click();
  await page.locator('#zone-description').fill('QA editado'); await page.locator('#save-zone-btn').click();
  await expect(page.locator('#zone-form')).toHaveCount(0);
  await page.locator('#zone-detail-panel').getByRole('button', { name: /Desactivar/ }).click();
  await page.locator('#zone-detail-panel').getByRole('button', { name: /Activar/ }).click();
  await page.getByRole('button', { name: `Eliminar zona ${name}`, exact: true }).click(); await page.locator('#confirm-cancel').click();
  await page.getByRole('button', { name: `Eliminar zona ${name}`, exact: true }).click(); await page.locator('#confirm-ok').click();
  await expect(page.locator('#zones-list')).not.toContainText(name);
});

test('Configuración: cada campo, guardar, persistir y restablecer', async ({ page, qa }) => {
  await login(page, qa.roles.admin); await goto(page, 'detection-config');
  await page.locator('#conf-min-confidence').fill('75');
  for (const [id, value] of Object.entries({ 'conf-max-altitude': '900', 'conf-anomaly-threshold': '2.8', 'conf-min-speed': '0', 'conf-max-speed': '250' })) await page.locator(`#${id}`).fill(value);
  await page.locator('#conf-ai-enabled').uncheck(); await page.locator('#conf-alerts-enabled').check();
  await page.locator('#save-config-btn').click();
  await expect(page.locator('.toast-message').filter({ hasText: 'persistida' })).toBeVisible();
  await page.reload(); await expect(page.locator('#conf-max-altitude')).toHaveValue('900');
  await expect(page.locator('#conf-ai-enabled')).not.toBeChecked();
  await page.locator('#reset-config-btn').click(); await expect(page.locator('#conf-max-altitude')).toHaveValue('1000');
  await page.locator('#save-config-btn').click();
  await expect(page.locator('.toast-message').filter({ hasText: 'persistida' })).toBeVisible();
});

test('Detecciones: filtros, actualizar, análisis de muestra y acceso a trayectoria', async ({ page, qa }, info) => {
  await login(page, qa.roles.admin); await goto(page, 'detections');
  await page.locator('#search-input').fill('sin-coincidencias-qa'); await expect(page.locator('#detections-tbody')).toContainText('Sin detecciones');
  await page.locator('#search-input').fill('');
  await page.locator('#filter-status').selectOption('active'); await page.locator('#filter-threat').selectOption('high');
  await page.locator('#refresh-btn').click();
  await page.locator('#filter-status').selectOption(''); await page.locator('#filter-threat').selectOption('');
  await page.locator('#ai-modal-btn').click();
  await page.locator('#ai-sensor-select').selectOption(qa.sensor.id);
  await page.locator('#ai-sample-btn').click();
  // El input de archivo usa una imagen sintética generada en el propio canvas.
  const image = await page.locator('#ai-canvas').evaluate(canvas => canvas.toDataURL('image/png').split(',')[1]);
  await page.locator('#ai-file-input').setInputFiles({ name: 'QA-sintetico.png', mimeType: 'image/png', buffer: Buffer.from(image, 'base64') });
  await inspect(page, info, 'analisis-muestra');
  await page.locator('#ai-run-infer-btn').click(); await expect(page.locator('#ai-results-panel')).toBeVisible();
  await page.locator('#close-ai-modal-btn').click();
  await page.locator('#ai-modal-btn').click(); await page.locator('#close-ai-modal').click();
  await page.locator('#detections-tbody tr').filter({ hasText: qa.detection }).click();
  await expect(page).toHaveURL(/#\/trajectory\?detection=/);
  await expect(page.locator('#traj-select')).toHaveValue(qa.detection);
  await page.locator('#load-trajectory-btn').click(); await expect(page.locator('#traj-points tr')).toHaveCount(3);
});

test('Trayectorias: actualizar, selección, tres puntos y cambio de selección', async ({ page, qa }) => {
  await login(page, qa.roles.admin); await goto(page, 'trajectory');
  await page.locator('#refresh-trajectories-btn').click();
  await page.locator('#traj-select').selectOption(qa.detection);
  await page.locator('#load-trajectory-btn').click(); await expect(page.locator('#traj-points tr')).toHaveCount(3);
  await expect(page.locator('#traj-detail')).toBeVisible();
  await page.locator('#traj-select').selectOption(''); await expect(page.locator('#traj-detail')).toBeHidden();
});

test('Dashboard: capas, centrar, ajustar, sonido, sirena y análisis experimental', async ({ page, qa }) => {
  await login(page, qa.roles.admin);
  await expect(page.locator('#ws-text')).toContainText('En vivo');
  await expect(page.locator('#dashboard-map .leaflet-pane')).not.toHaveCount(0);
  for (const id of ['map-layer-zones', 'map-layer-sensors']) {
    await page.locator(`#${id}`).click(); await expect(page.locator(`#${id}`)).not.toHaveClass(/active/);
    await page.locator(`#${id}`).click(); await expect(page.locator(`#${id}`)).toHaveClass(/active/);
  }
  for (const id of ['map-center-btn', 'map-fit-btn', 'btn-toggle-audio', 'btn-test-siren', 'btn-toggle-audio']) await page.locator(`#${id}`).click();
  await page.locator('#btn-trigger-soar').click();
  await expect(page.locator('#btn-trigger-soar')).toBeEnabled();
  await expect(page.locator('#ai-verdict-text')).not.toBeEmpty();
  await page.getByRole('link', { name: 'Ver historial', exact: true }).click(); await expect(page).toHaveURL(/#\/history$/);
});

test('Alertas: filtros, asignación, resolución y mapa', async ({ page, qa }) => {
  await login(page, qa.roles.operator); await goto(page, 'alerts');
  await page.locator('#filter-alert-status').selectOption('open'); await page.locator('#filter-alert-severity').selectOption('high');
  await page.locator('#refresh-alerts-btn').click();
  await page.locator('#filter-alert-status').selectOption(''); await page.locator('#filter-alert-severity').selectOption('');
  const alert = page.locator(`[data-alert-id="${qa.alert.id}"]`);
  await expect(alert).toHaveCount(1);
  await alert.getByRole('button', { name: /^Asignar alerta/ }).click();
  await expect(alert).toContainText('assigned');
  await alert.getByRole('link', { name: 'Ver detección relacionada' }).click();
  await expect(page).toHaveURL(/#\/trajectory\?detection=/);
  await goto(page, 'alerts');
  await alert.getByRole('button', { name: /^Resolver alerta/ }).click(); await page.locator('#confirm-cancel').click();
  await alert.getByRole('button', { name: /^Resolver alerta/ }).click(); await page.locator('#confirm-ok').click();
  await expect(page.locator('#alerts-list')).toContainText('resolved');
});

test('Reportes: todas las descargas, fechas, programación y eliminación', async ({ page, qa }) => {
  await login(page, qa.roles.analyst); await goto(page, 'reports');
  for (const id of ['det-date-from', 'alt-date-from']) await page.locator(`#${id}`).fill('2020-01-01');
  for (const id of ['det-date-to', 'alt-date-to']) await page.locator(`#${id}`).fill('2099-12-31');
  for (const id of ['gen-det-pdf', 'gen-det-csv', 'gen-det-excel', 'gen-alt-pdf', 'gen-alt-csv']) {
    const download = page.waitForEvent('download'); await page.locator(`#${id}`).click();
    expect((await download).suggestedFilename()).toMatch(/\.(pdf|csv|xlsx)$/);
  }
  await page.locator('#new-schedule-btn').click();
  await page.locator('#schedule-form [name="name"]').fill(`${qa.prefix}_programacion`);
  await page.locator('#schedule-form [name="cron"]').fill('0 0 1 1 *');
  await page.locator('#schedule-form [name="format"]').selectOption('csv');
  await page.locator('#schedule-form button[type="submit"]').click();
  const schedule = page.locator('#schedules-list .card').filter({ hasText: `${qa.prefix}_programacion` });
  await expect(schedule).toBeVisible(); await schedule.getByRole('button', { name: 'Eliminar' }).click(); await expect(schedule).toHaveCount(0);
});

test('Historial: CSV y Excel; auditoría verifica cadena desde API real', async ({ page, qa }) => {
  await login(page, qa.roles.analyst); await goto(page, 'history');
  for (const id of ['export-history-csv', 'export-history-excel']) {
    const download = page.waitForEvent('download'); await page.locator(`#${id}`).click(); expect((await download).suggestedFilename()).toMatch(/\.(csv|xlsx)$/);
  }
  await goto(page, 'audit'); await expect(page.locator('#audit-tbody')).toContainText('LOGIN');
  const audit = await qa.api.get('/api/v1/audit/verify?limit=500'); expect(audit.status()).toBe(200); expect((await audit.json()).valid).toBe(true);
});

for (const role of ['operator', 'analyst']) {
  test(`Permisos ${role}: navegación y API restringidas`, async ({ page, qa, playwright, baseURL }) => {
    await login(page, qa.roles[role]);
    for (const route of ['users', 'sensors', 'detection-config', ...(role === 'operator' ? ['reports', 'audit'] : [])]) {
      await expect(page.locator(`.sidebar a[href="#/${route}"]`)).toHaveCount(0);
      await page.goto(`/#/${route}`); await expect(page).toHaveURL(/#\/dashboard$/);
    }
    const api = await playwright.request.newContext({ baseURL, extraHTTPHeaders: { Authorization: `Bearer ${qa.roles[role].token}` } });
    expect((await api.get('/api/v1/users')).status()).toBe(403); await api.dispose();
  });
}

test('Sesión anónima: rutas protegidas y API bloqueadas', async ({ page, request, qa }) => {
  await page.goto('/#/users'); await expect(page).toHaveURL(/#\/login$/);
  expect((await request.get('/api/v1/users')).status()).toBe(401);
  expect((await request.get('/metrics')).status()).toBe(401);
});

test('Móvil: menú accesible, perfil y formularios alcanzables sin recorte', async ({ page, qa }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, qa.roles.admin);
  for (const route of Object.keys(routes)) {
    await page.locator(`.sidebar a.nav-item[href="#/${route}"]`).click();
    await expect(page).toHaveURL(new RegExp(`#/${route}$`));
  }
  await page.locator('#user-profile-btn').click(); await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await goto(page, 'sensors'); await page.locator('#new-sensor-btn').click();
  await expect(page.locator('#sensor-name')).toBeVisible(); await page.locator('#cancel-sensor').click();
  await goto(page, 'users'); await page.locator('#new-user-btn').click(); await page.locator('#cancel-user').click();
});

test('Mapas: teselas reales disponibles y atribución visible', async ({ page, qa }) => {
  await login(page, qa.roles.admin);
  for (const [route, id] of [['dashboard', 'dashboard-map'], ['zones', 'zones-map'], ['trajectory', 'trajectory-map']]) {
    await goto(page, route);
    await expect.poll(() => page.locator(`#${id} img.leaflet-tile`).evaluateAll(images => images.some(img => img.complete && img.naturalWidth > 0)), { timeout: 15000, message: `Teselas no disponibles en ${route}; revisar Internet/proveedor` }).toBe(true);
    await expect(page.locator(`#${id} .leaflet-control-attribution`)).toContainText('OpenStreetMap');
  }
});
