import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.window = {
  addEventListener: () => {},
  removeEventListener: () => {},
  location: { hash: '#/dashboard' },
};
globalThis.localStorage = {getItem: () => null, setItem:()=>{}, removeItem:()=>{}};

const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    id,
    hidden:false,
    textContent:'',
    className:'',
    children:[],
    appendChild(child){this.children.push(child)},
    replaceChildren(){this.children=[]},
  });
  return elements.get(id);
}
globalThis.document = {
  getElementById: (id) => element(id),
  createElement: (type) => ({type, textContent:''}),
  querySelectorAll:()=>[],
};

const {DashboardViewModel}=await import('../frontend/src/viewmodels/dashboard.viewmodel.js');

test('renderiza acción, evidencia y explicación sin HTML arbitrario',()=>{
  const vm = new DashboardViewModel();
  vm.state.aiVerdict = {
    incident_id:'TEST-1', ai_verdict:'Revisión', threat_level:'MEDIUM',
    goal_decision:{ action:'VERIFICAR_DETECCION',priority:'REVIEW',
      explanation:'Confirmar con operador',evidence:['Altitud 135 m','<script>no ejecutar</script>'],
      human_review_required:true },
  };
  vm._renderAiVerdict();
  assert.equal(element('ai-goal-decision').hidden,false);
  assert.equal(element('ai-goal-action').textContent,'VERIFICAR DETECCION');
  assert.equal(element('ai-goal-evidence').children.length,2);
  assert.equal(element('ai-goal-evidence').children[1].textContent,'<script>no ejecutar</script>');
  assert.match(element('ai-goal-review').textContent,/Requiere revisión humana/);
});

test('oculta la sección de objetivos si el dictamen no trae decisión',()=>{
  const vm=new DashboardViewModel();
  vm.state.aiVerdict={ai_verdict:'Dictamen externo',threat_level:'LOW'};
  vm._renderAiVerdict();
  assert.equal(element('ai-goal-decision').hidden,true);
});
