import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Execute the actual view handlers with isolated service and DOM doubles.
function load(file, className, overrides = {}) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: '', checked: true, disabled: false, handlers: {}, style: {},
      classList: { add() {}, remove() {} }, removed: false,
      addEventListener(name, fn) { this.handlers[name] = fn; },
      remove() { this.removed = true; },
      focus() {},
      querySelector(selector) { return element(selector); },
    });
    return elements.get(id);
  };
  const context = {
    document: {
      getElementById: id => element(id),
      createElement: () => element('overlay'),
      body: { appendChild() {} },
    },
    window: { addEventListener() {} },
    localStorage: { getItem() { return null; } },
    setTimeout: fn => fn(), console,
    escapeHtml: value => value,
    Toast: { info() {}, warn() {}, error() {}, success() {} },
    MockService: { enabled: false },
    SensorType: { RADAR: 'radar' }, SensorStatus: { INACTIVE: 'inactive', ACTIVE: 'active' },
    SensorModel: class { constructor() { this.typeLabel = 'Radar'; } },
    tacticalAudio: { isMuted: () => true },
    ...overrides,
  };
  const source = fs.readFileSync(new URL(`../frontend/src/${file}`, import.meta.url), 'utf8')
    .replace(/^import .*;\r?\n/gm, '').replace(/\bexport /g, '');
  vm.runInNewContext(`${source}\nglobalThis.Subject = ${className};`, context);
  return { subject: typeof context.Subject === 'function' ? new context.Subject() : context.Subject, element, context };
}

test('configuration save and reset use the rendered checkbox', async () => {
  let saved;
  const { subject, element } = load('views/misc.views.js', 'DetectionConfigView', {
    ConfigService: { update: async data => { saved = data; } },
  });
  assert.match(subject._template(), /id="conf-ai-enabled"/);
  subject._bindEvents();
  element('conf-ai-enabled').checked = false;
  element('conf-min-confidence').value = '80';
  await element('config-form').handlers.submit({ preventDefault() {} });
  assert.equal(saved.ai_enabled, false);
  assert.equal(saved.ai_confidence_threshold, 0.8);
  element('reset-config-btn').handlers.click();
  assert.equal(element('conf-ai-enabled').checked, true);
});

test('editing sensor preserves status and refreshes counters', async () => {
  let saved, counters = 0;
  const { subject, element } = load('views/sensors.view.js', 'SensorsViewModel', {
    SensorService: { update: async (id, data) => { saved = data; } },
  });
  subject.load = async () => {};
  subject.renderGrid = () => {};
  subject.renderStats = () => { counters++; };
  subject.showSensorModal({ id: 'sensor', status: 'active', latitude: 0, longitude: 0 });
  element('sensor-lat').value = '0'; element('sensor-lng').value = '0';
  await element('#sensor-form').handlers.submit({ preventDefault() {} });
  assert.equal(Object.hasOwn(saved, 'status'), false);
  assert.equal(saved.latitude, 0);
  assert.equal(counters, 1);
  const html = element('overlay').innerHTML;
  for (const [id, min, max] of [['lat', '-90', '90'], ['lng', '-180', '180'], ['alt', '0', '15000'], ['range', '0.001', '1000']]) {
    assert.match(html, new RegExp(`id="sensor-${id}"[^>]*min="${min}" max="${max}"`));
  }
});

test('failed user save keeps the modal and typed values for correction', async () => {
  const { subject, element } = load('views/users.view.js', 'UsersViewModel', {
    UserService: { create: async () => { throw new Error('Correo duplicado'); } },
  });
  subject.showUserModal();
  element('user-email').value = 'qa@example.test';
  await element('#user-form').handlers.submit({ preventDefault() {} });
  assert.equal(element('overlay').removed, false);
  assert.equal(element('user-email').value, 'qa@example.test');
  assert.equal(element('button[type="submit"]').disabled, false);
});

test('SOAR sends no fabricated event when no detection exists', async () => {
  let calls = 0;
  const { subject, element } = load('viewmodels/dashboard.viewmodel.js', 'DashboardViewModel', {
    AlertService: { triggerIncident: async () => { calls++; } },
  });
  subject.bindTacticalControls();
  await element('btn-trigger-soar').handlers.click();
  assert.equal(calls, 0);
});

test('SOAR preserves zero telemetry and unknown confidence', async () => {
  let saved;
  const { subject, element } = load('viewmodels/dashboard.viewmodel.js', 'DashboardViewModel', {
    AlertService: { triggerIncident: async payload => { saved = payload; return {}; } },
  });
  subject.state.detections = [{ id: 'detection', status: 'active', zoneId: 'zone', altitude: 0, speed: 0, heading: 0, latitude: 0, longitude: 0, aiConfidence: null }];
  subject.state.zones = [{ id: 'zone', isActive: true, name: 'QA zone', maxAltitude: 0 }];
  subject.bindTacticalControls();
  await element('btn-trigger-soar').handlers.click();
  assert.equal(saved.drone.drone_id, 'detection');
  for (const key of ['altitude_m', 'speed_ms', 'heading_deg', 'latitude', 'longitude']) assert.equal(saved.drone[key], 0);
  assert.equal(saved.drone.ai_confidence, null);
  assert.equal(saved.zone.max_allowed_altitude_m, 0);
  assert.equal(saved.zone.name, 'QA zone');
});

test('invalid altitude range keeps the zone form open', async () => {
  let calls = 0;
  const { subject, element } = load('views/zones.view.js', 'ZonesViewModel', {
    ZoneService: { create: async () => { calls++; } },
    AlertSeverity: { HIGH: 'high' },
  });
  subject._showZoneModal();
  element('zone-min-alt').value = '300';
  element('zone-max-alt').value = '100';
  await element('#zone-form').handlers.submit({ preventDefault() {} });
  assert.equal(calls, 0);
  assert.equal(element('overlay').removed, false);
});

test('profile displays only identity fields and closes with Escape', () => {
  const { subject, element } = load('app.js', 'Layout', {
    AuthService: { getUser: () => ({ username: 'qa', email: 'qa@example.test', role: 'analyst', access_token: 'DO-NOT-DISPLAY' }) },
  });
  subject.showUserProfile();
  assert.match(element('overlay').innerHTML, /role="dialog"/);
  assert.match(element('overlay').innerHTML, /qa@example.test/);
  assert.doesNotMatch(element('overlay').innerHTML, /DO-NOT-DISPLAY/);
  element('overlay').handlers.keydown({ key: 'Escape' });
  assert.equal(element('overlay').removed, true);
});

test('trajectory clears an earlier route when the next request fails', async () => {
  let removed = false;
  const { subject, element } = load('views/misc.views.js', 'TrajectoryView', {
    DetectionService: { getTrajectory: async () => { throw new Error('API unavailable'); } },
  });
  subject._map = {};
  subject._layers = [{ remove() { removed = true; } }];
  subject._detections = [{ id: 'current' }];
  element('traj-select').value = 'current';
  await subject._loadTrajectory();
  assert.equal(removed, true);
  assert.match(element('traj-status').textContent, /No se pudo cargar/);
});

test('trajectory handles one sample without inventing a flight path', async () => {
  let position;
  const marker = { bindTooltip() { return this; }, addTo() {}, remove() {} };
  const { subject, element } = load('views/misc.views.js', 'TrajectoryView', {
    window: { L: { circleMarker: () => marker } },
    DetectionService: { getTrajectory: async () => [{ latitude: 0, longitude: 0, altitude: 10, speed: 0, heading: 0, timestamp: '2026-10-29T12:00:00Z' }] },
  });
  subject._map = { setView(point) { position = point; } };
  subject._detections = [{ id: 'current' }];
  element('traj-select').value = 'current';
  await subject._loadTrajectory();
  assert.equal(position[0], 0);
  assert.equal(position[1], 0);
  assert.match(element('traj-status').textContent, /Solo hay una muestra/);
  assert.match(element('traj-points').innerHTML, /10.0/);
});

test('a late trajectory response cannot overwrite a new selection', async () => {
  let finish;
  const { subject, element } = load('views/misc.views.js', 'TrajectoryView', {
    DetectionService: { getTrajectory: () => new Promise(resolve => { finish = resolve; }) },
  });
  subject._map = {};
  subject._detections = [{ id: 'old' }];
  element('traj-select').value = 'old';
  const pending = subject._loadTrajectory();
  subject._clearTrajectory();
  finish([]);
  await pending;
  assert.match(element('traj-status').textContent, /Selecciona/);
});
