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

test('renderiza respuesta agéntica LangGraph, citas RAG y herramientas sin HTML arbitrario', () => {
  const vm = new DashboardViewModel();
  vm.state.agentLlmOps = {
    total_runs: 4,
    blocked_input_count: 1,
    blocked_output_count: 0,
    avg_latency_ms: 14.2,
    rag_status: { vector_backend: 'qdrant_embedded', indexed_chunks: 8 },
  };
  vm.state.agentResult = {
    engine: 'langgraph',
    provider: 'deterministic',
    vector_backend: 'qdrant_embedded',
    guardrails: { input_passed: true, output_passed: true },
    output: {
      recommended_action: 'NOTIFICAR_Y_VERIFICAR',
      priority: 'CRITICAL',
      summary: 'Contacto sobre 120 m requiere verificación humana.',
    },
    tools_called: ['get_operational_snapshot', 'evaluate_goal_agent'],
    rag_citations: [
      { source: '01_protocolos_operativos_cuas.md', section: 'Escalamiento', score: 0.91 },
      { source: 'xss.md', section: '<script>alert(1)</script>', score: 0.72 },
    ],
    telemetry_trace: { total_latency_ms: 14.2, estimated_tokens: 110 },
  };

  vm._renderAgentMonitor();

  assert.match(element('agent-llmops-summary').textContent, /4 ejecuciones.*1 bloqueos.*qdrant_embedded/);
  assert.equal(element('agent-guardrail-badge').textContent, 'GUARDRAIL OK');
  assert.equal(element('agent-monitor-result').hidden, false);
  assert.equal(element('agent-res-action').textContent, 'NOTIFICAR Y VERIFICAR');
  assert.match(element('agent-res-trace').textContent, /langgraph.*deterministic.*14\.2 ms/);
  assert.equal(element('agent-res-citations').children.length, 2);
  assert.match(element('agent-res-citations').children[1].textContent, /<script>alert\(1\)<\/script>/);
});

test('muestra estado bloqueado cuando el Guardrail rechaza la consulta', () => {
  const vm = new DashboardViewModel();
  vm.state.agentResult = {
    engine: 'langgraph',
    provider: 'guardrail_policy',
    guardrails: { input_passed: false, output_passed: true },
    output: {
      recommended_action: 'BLOQUEADO_POR_GUARDRAIL',
      priority: 'BLOCKED',
      summary: 'Prompt injection detectado.',
    },
    tools_called: [],
    rag_citations: [],
    telemetry_trace: { total_latency_ms: 2.1, estimated_tokens: 0 },
  };

  vm._renderAgentMonitor();

  assert.equal(element('agent-guardrail-badge').textContent, 'BLOQUEADO IN');
  assert.equal(element('agent-res-priority').className, 'badge badge-danger');
});
