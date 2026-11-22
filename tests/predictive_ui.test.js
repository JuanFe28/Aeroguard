import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.window = {
  addEventListener: () => {},
  removeEventListener: () => {},
  location: { hash: '#/dashboard' },
};
globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };

const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      id,
      hidden: true,
      textContent: '',
      className: '',
      children: [],
      appendChild(child) {
        this.children.push(child);
      },
      replaceChildren() {
        this.children = [];
      },
    });
  }
  return elements.get(id);
}

globalThis.document = {
  getElementById: id => element(id),
  createElement: type => ({ type, textContent: '' }),
  querySelectorAll: () => [],
};

const { DashboardViewModel } = await import('../frontend/src/viewmodels/dashboard.viewmodel.js');

test('renderiza resultados predictivos ML sin interpretar HTML arbitrario', () => {
  const vm = new DashboardViewModel();
  vm.state.predictiveSummary = {
    models: {
      random_forest: { runtime_compact_accuracy: 0.9508 },
      regresion_lineal: { test_r2: 0.9356 },
      regresion_logistica: { test_roc_auc: 0.9689 },
    },
  };
  vm.state.predictiveForecast = {
    model: 'ARIMA(1, 1, 1)',
    peak_forecast_14d: { date: '2026-11-01', predicted_high_risk: 151.77, lower_95: 128.02, upper_95: 175.51 },
  };
  vm.state.predictiveResult = {
    threat_level: 'CRITICAL',
    risk_score: 88.4,
    geofence_breach_probability: 0.92,
    high_risk_threshold: 0.4,
    flight_profile: 'Aproximación Cercana',
    key_factors: ['Distancia 60 m', '<img src=x onerror=alert(1)>'],
  };

  vm._renderPredictivePanel();

  assert.equal(element('ml-active-model-badge').textContent, 'RF 95.1%');
  assert.match(element('arima-peak-summary').textContent, /ARIMA\(1, 1, 1\).*2026-11-01/);
  assert.equal(element('ml-prediction-result').hidden, false);
  assert.equal(element('ml-pred-threat').textContent, 'Amenaza RF: CRITICAL');
  assert.equal(element('ml-pred-risk').textContent, 'Risk Score: 88.4/100');
  assert.equal(element('ml-pred-factors').children.length, 2);
  assert.equal(element('ml-pred-factors').children[1].textContent, '<img src=x onerror=alert(1)>');
});

test('oculta resultados ML cuando no existe evaluación activa', () => {
  const vm = new DashboardViewModel();
  vm.state.predictiveResult = null;
  vm._renderPredictivePanel();
  assert.equal(element('ml-prediction-result').hidden, true);
});
