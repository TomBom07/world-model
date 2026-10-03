const $ = (id) => document.getElementById(id);

const state = {
  projects: [],
  projectId: null,
  snapshot: null,
  tab: 'overview',
  ollama: { available: false, models: [], model: null },
};

function escapeHTML(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function fmt(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return number.toFixed(digits);
}

function pct(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${(number * 100).toFixed(digits)}%`;
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(number);
}

function toast(message) {
  const node = $('toast');
  node.textContent = message;
  node.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove('show'), 2400);
}

async function api(url, options = {}) {
  const request = { ...options };
  request.headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (request.body && typeof request.body !== 'string') {
    request.body = JSON.stringify(request.body);
  }
  const response = await fetch(url, request);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // keep HTTP fallback
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function titleCase(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll('#tabs button').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tab);
  });
  render();
}

async function refreshOllama() {
  try {
    const result = await api('/api/ai/status');
    state.ollama.available = Boolean(result.available);
    state.ollama.models = result.models || [];
    const names = state.ollama.models.map((item) => item.name);
    const saved = localStorage.getItem('rook.worlds.ollamaModel');
    state.ollama.model = names.includes(saved) ? saved : names[0] || null;

    const select = $('ollama-model');
    if (names.length) {
      select.innerHTML = state.ollama.models.map((item) => {
        const detail = [item.parameter_size, item.quantization].filter(Boolean).join(' · ');
        return `<option value="${escapeHTML(item.name)}">${escapeHTML(item.name)}${detail ? ` · ${escapeHTML(detail)}` : ''}</option>`;
      }).join('');
      select.value = state.ollama.model;
      select.disabled = false;
    } else {
      select.innerHTML = '<option value="">No local models</option>';
      select.disabled = true;
    }

    $('ai-chip').textContent = state.ollama.model ? `Local AI · ${state.ollama.model}` : 'Local AI offline';
    $('ai-chip').classList.toggle('online', Boolean(state.ollama.model));
    $('ollama-note').textContent = state.ollama.model
      ? 'Ollama is available on this computer. Reports can use the selected model.'
      : 'Ollama is unavailable or has no installed models. Structured Rook features still work.';
  } catch (error) {
    $('ai-chip').textContent = 'Local AI offline';
    $('ai-chip').classList.remove('online');
    $('ollama-model').innerHTML = '<option value="">Ollama unavailable</option>';
    $('ollama-note').textContent = error.message;
  }
}

async function loadProjects({ preserve = true } = {}) {
  const result = await api('/api/worlds');
  state.projects = result.projects || [];
  if (!preserve || !state.projects.some((item) => item.id === state.projectId)) {
    state.projectId = state.projects[0]?.id || null;
  }
  renderWorldList();
  if (state.projectId) await loadSnapshot(state.projectId);
  else {
    state.snapshot = null;
    render();
  }
}

async function loadSnapshot(projectId) {
  state.projectId = projectId;
  state.snapshot = await api(`/api/worlds/${encodeURIComponent(projectId)}`);
  localStorage.setItem('rook.worlds.activeProject', projectId);
  renderWorldList();
  render();
}

function renderWorldList() {
  const node = $('world-list');
  if (!state.projects.length) {
    node.innerHTML = '<div style="padding:8px;color:#69717c;font-size:8px">No worlds yet.</div>';
    return;
  }
  node.innerHTML = state.projects.map((project) => `
    <button class="world-item ${project.id === state.projectId ? 'active' : ''}" data-world-id="${project.id}">
      <strong>${escapeHTML(project.name)}</strong>
      <small>${escapeHTML(titleCase(project.kind))}</small>
    </button>
  `).join('');
}

function pageHead(kicker, title, description, action = '') {
  return `
    <div class="page-head">
      <div>
        <p class="eyebrow">${escapeHTML(kicker)}</p>
        <h2>${escapeHTML(title)}</h2>
        <p>${escapeHTML(description)}</p>
      </div>
      ${action}
    </div>
  `;
}

function emptySection(text) {
  return `<div class="card"><p style="margin:0">${escapeHTML(text)}</p></div>`;
}

function render() {
  const content = $('content');
  const snapshot = state.snapshot;

  if (!snapshot) {
    $('project-kind').textContent = 'WORLD';
    $('project-name').textContent = 'Choose a world';
    content.innerHTML = `
      <div class="empty-state">
        <span class="empty-mark">R</span>
        <h2>Build a living model of something you care about.</h2>
        <p>Create a world for a company, market, technology, business, research question, or anything else you want to understand over time.</p>
        <button class="primary-button" id="empty-new-world">Create your first world</button>
      </div>
    `;
    $('empty-new-world')?.addEventListener('click', openNewWorldDialog);
    return;
  }

  $('project-kind').textContent = titleCase(snapshot.project.kind);
  $('project-name').textContent = snapshot.project.name;

  if (state.tab === 'overview') renderOverview();
  else if (state.tab === 'world') renderWorld();
  else if (state.tab === 'forecasts') renderForecasts();
  else if (state.tab === 'simulate') renderSimulate();
  else if (state.tab === 'report') renderReport();
  else if (state.tab === 'business') renderBusiness();
  else if (state.tab === 'paper') renderPaper();
}

function renderOverview() {
  const s = state.snapshot;
  const health = s.health || {};
  const calibration = s.forecast_calibration || {};
  const latestReport = s.reports?.[0];

  $('content').innerHTML = `
    ${pageHead(
      'LIVING WORLD',
      s.project.name,
      s.project.goal || 'A persistent world model that becomes more useful as evidence, forecasts, and outcomes accumulate.',
      '<button class="secondary-button" id="overview-refresh">Refresh world</button>'
    )}

    <div class="grid grid-4">
      <div class="card metric-card"><span>Entities</span><strong>${health.entities || 0}</strong><small>things Rook models</small></div>
      <div class="card metric-card"><span>Claims</span><strong>${health.claims || 0}</strong><small>${health.unresolved_claims || 0} still unresolved</small></div>
      <div class="card metric-card"><span>Open forecasts</span><strong>${health.open_forecasts || 0}</strong><small>${calibration.resolved || 0} resolved so far</small></div>
      <div class="card metric-card"><span>Brier score</span><strong>${calibration.mean_brier_score == null ? '—' : fmt(calibration.mean_brier_score, 3)}</strong><small>lower is better</small></div>
    </div>

    <div class="section grid grid-2">
      <div class="card">
        <div class="section-head"><h3>Leading claims</h3><button class="secondary-button" data-jump="world">Open world</button></div>
        <div class="list">
          ${s.claims?.slice(0, 5).map((claim) => `
            <div class="list-row">
              <div><strong>${escapeHTML(claim.text)}</strong><small>${escapeHTML(titleCase(claim.status))}</small></div>
              <span class="tag ${claim.confidence >= .7 ? 'good' : claim.confidence < .4 ? 'bad' : 'warn'}">${pct(claim.confidence)}</span>
            </div>
          `).join('') || '<p style="color:#69717c;font-size:8px">No claims yet.</p>'}
        </div>
      </div>

      <div class="card">
        <div class="section-head"><h3>Outstanding forecasts</h3><button class="secondary-button" data-jump="forecasts">Forecasts</button></div>
        <div class="list">
          ${s.forecasts?.filter((item) => item.status === 'open').slice(0, 5).map((forecast) => `
            <div class="list-row">
              <div><strong>${escapeHTML(forecast.question)}</strong><small>${escapeHTML(forecast.horizon || 'No horizon')}</small></div>
              <span class="tag">${pct(forecast.probability)}</span>
            </div>
          `).join('') || '<p style="color:#69717c;font-size:8px">No open forecasts yet.</p>'}
        </div>
      </div>
    </div>

    <div class="section card">
      <div class="section-head">
        <h3>Latest living report</h3>
        <button class="secondary-button" data-jump="report">${latestReport ? 'Open report' : 'Generate report'}</button>
      </div>
      <p>${latestReport ? escapeHTML(latestReport.content?.executive_summary || latestReport.title) : 'Reports are generated from the World itself: claims, forecasts, simulations, business metrics, evidence, and paper positions.'}</p>
    </div>
  `;

  $('overview-refresh')?.addEventListener('click', () => loadSnapshot(state.projectId));
  document.querySelectorAll('[data-jump]').forEach((button) => {
    button.addEventListener('click', () => setTab(button.dataset.jump));
  });
}

function renderGraphSVG() {
  const entities = state.snapshot.entities || [];
  const relations = state.snapshot.relations || [];
  if (!entities.length) return '<div style="padding:80px 20px;text-align:center;color:#69717c;font-size:9px">Add entities to begin building the world graph.</div>';

  const width = 760;
  const height = 480;
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * .34;
  const positions = new Map();

  entities.forEach((entity, index) => {
    const angle = (Math.PI * 2 * index / entities.length) - Math.PI / 2;
    const ring = entities.length <= 3 ? radius * .62 : radius;
    positions.set(entity.id, {
      x: cx + Math.cos(angle) * ring,
      y: cy + Math.sin(angle) * ring,
    });
  });

  const edges = relations.map((relation) => {
    const a = positions.get(relation.source_id);
    const b = positions.get(relation.target_id);
    if (!a || !b) return '';
    const klass = relation.weight > 0 ? 'positive' : relation.weight < 0 ? 'negative' : '';
    return `<line class="graph-edge ${klass}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" />`;
  }).join('');

  const nodes = entities.map((entity) => {
    const p = positions.get(entity.id);
    const label = entity.name.length > 22 ? `${entity.name.slice(0, 20)}…` : entity.name;
    return `
      <g class="graph-node" transform="translate(${p.x},${p.y})">
        <circle r="36"></circle>
        <text y="-1">${escapeHTML(label)}</text>
        <text y="13" class="kind">${escapeHTML(titleCase(entity.kind))}</text>
      </g>
    `;
  }).join('');

  return `<svg class="graph-stage" viewBox="0 0 ${width} ${height}" role="img" aria-label="World graph">${edges}${nodes}</svg>`;
}

function renderWorld() {
  const s = state.snapshot;
  const entities = s.entities || [];

  $('content').innerHTML = `
    ${pageHead('EPISTEMIC WORLD GRAPH', 'What exists, what Rook believes, and why', 'Entities and relationships form the structural world. Claims remain explicit hypotheses with confidence rather than being silently promoted to facts.')}

    <div class="world-layout">
      <div class="card graph-card">
        <div class="section-head"><h3>World graph</h3><span class="tag">${entities.length} nodes · ${s.relations.length} edges</span></div>
        ${renderGraphSVG()}
      </div>

      <div class="grid">
        <form class="stack-form" id="entity-form">
          <h3>Add entity</h3>
          <div class="field"><span>Name</span><input id="entity-name" required placeholder="GPU demand" /></div>
          <div class="mini-grid">
            <div class="field"><span>Type</span><input id="entity-kind" placeholder="metric / company / event" value="concept" /></div>
            <div class="field"><span>Baseline value</span><input id="entity-value" type="number" step="any" value="0" /></div>
          </div>
          <button class="primary-button">Add to world</button>
        </form>

        <form class="stack-form" id="relation-form">
          <h3>Add relationship</h3>
          <div class="field"><span>From</span><select id="relation-source">${entityOptions(entities)}</select></div>
          <div class="field"><span>To</span><select id="relation-target">${entityOptions(entities)}</select></div>
          <div class="field"><span>Relationship</span><input id="relation-name" placeholder="increases / constrains / depends on" /></div>
          <div class="mini-grid">
            <div class="field"><span>Weight</span><input id="relation-weight" type="number" min="-5" max="5" step=".1" value=".5" /></div>
            <div class="field"><span>Confidence</span><input id="relation-confidence" type="number" min="0" max="1" step=".05" value=".5" /></div>
          </div>
          <button class="primary-button" ${entities.length < 2 ? 'disabled' : ''}>Connect</button>
        </form>
      </div>
    </div>

    <div class="section grid grid-2">
      <form class="stack-form" id="claim-form">
        <h3>Add competing claim</h3>
        <div class="field"><span>Claim / hypothesis</span><textarea id="claim-text" required placeholder="Power availability becomes more binding than GPU supply by 2029."></textarea></div>
        <div class="mini-grid">
          <div class="field"><span>Status</span><select id="claim-status"><option value="hypothesis">Hypothesis</option><option value="supported">Supported</option><option value="uncertain">Uncertain</option><option value="rejected">Rejected</option></select></div>
          <div class="field"><span>Confidence</span><input id="claim-confidence" type="number" min="0" max="1" step=".05" value=".5" /></div>
        </div>
        <button class="primary-button">Store claim</button>
      </form>

      <form class="stack-form" id="source-form">
        <h3>Add evidence / source</h3>
        <div class="field"><span>Title</span><input id="source-title" required placeholder="Industry report / observation / note" /></div>
        <div class="field"><span>URL (optional)</span><input id="source-url" placeholder="https://…" /></div>
        <div class="field"><span>Excerpt / evidence</span><textarea id="source-excerpt" placeholder="What does this source actually support?"></textarea></div>
        <button class="primary-button">Add evidence</button>
      </form>
    </div>

    <div class="section grid grid-2">
      <div class="card">
        <div class="section-head"><h3>Claims</h3><span class="tag">${s.claims.length}</span></div>
        <div class="list">
          ${s.claims.map((claim) => `
            <div class="list-row">
              <div><strong>${escapeHTML(claim.text)}</strong><small>${escapeHTML(titleCase(claim.status))}</small></div>
              <span class="tag">${pct(claim.confidence)}</span>
            </div>
          `).join('') || '<p style="color:#69717c;font-size:8px">No claims yet.</p>'}
        </div>
      </div>
      <div class="card">
        <div class="section-head"><h3>Evidence</h3><span class="tag">${s.sources.length}</span></div>
        <div class="list">
          ${s.sources.map((source) => `
            <div class="list-row">
              <div><strong>${escapeHTML(source.title)}</strong><small>${escapeHTML(source.excerpt || source.url || source.source_type)}</small></div>
              <span class="tag">${escapeHTML(titleCase(source.source_type))}</span>
            </div>
          `).join('') || '<p style="color:#69717c;font-size:8px">No evidence yet.</p>'}
        </div>
      </div>
    </div>
  `;

  $('entity-form').addEventListener('submit', createEntity);
  $('relation-form').addEventListener('submit', createRelation);
  $('claim-form').addEventListener('submit', createClaim);
  $('source-form').addEventListener('submit', createSource);
}

function entityOptions(entities) {
  return entities.map((entity) => `<option value="${entity.id}">${escapeHTML(entity.name)}</option>`).join('');
}

async function createEntity(event) {
  event.preventDefault();
  const body = {
    name: $('entity-name').value.trim(),
    kind: $('entity-kind').value.trim() || 'concept',
    attributes: { value: Number($('entity-value').value || 0) },
  };
  await api(`/api/worlds/${state.projectId}/entities`, { method: 'POST', body });
  toast('Entity added.');
  await loadSnapshot(state.projectId);
}

async function createRelation(event) {
  event.preventDefault();
  const body = {
    source_id: $('relation-source').value,
    target_id: $('relation-target').value,
    relation: $('relation-name').value.trim() || 'influences',
    weight: Number($('relation-weight').value || 0),
    confidence: Number($('relation-confidence').value || .5),
  };
  await api(`/api/worlds/${state.projectId}/relations`, { method: 'POST', body });
  toast('Relationship added.');
  await loadSnapshot(state.projectId);
}

async function createClaim(event) {
  event.preventDefault();
  const body = {
    text: $('claim-text').value.trim(),
    status: $('claim-status').value,
    confidence: Number($('claim-confidence').value || .5),
  };
  await api(`/api/worlds/${state.projectId}/claims`, { method: 'POST', body });
  toast('Claim stored.');
  await loadSnapshot(state.projectId);
}

async function createSource(event) {
  event.preventDefault();
  const body = {
    title: $('source-title').value.trim(),
    url: $('source-url').value.trim() || null,
    source_type: 'source',
    excerpt: $('source-excerpt').value.trim(),
  };
  await api(`/api/worlds/${state.projectId}/sources`, { method: 'POST', body });
  toast('Evidence added.');
  await loadSnapshot(state.projectId);
}

function renderForecasts() {
  const s = state.snapshot;
  const calibration = s.forecast_calibration || {};
  const resolved = s.forecasts.filter((item) => item.status === 'resolved');

  $('content').innerHTML = `
    ${pageHead('FORECAST LEDGER', 'Make the future explicit', 'Every forecast is timestamped with an evidence cutoff. Resolve it later and Rook scores the prediction instead of rewriting history.')}

    <div class="grid grid-3">
      <div class="card metric-card"><span>Open</span><strong>${s.forecasts.filter((item) => item.status === 'open').length}</strong><small>awaiting outcomes</small></div>
      <div class="card metric-card"><span>Resolved</span><strong>${resolved.length}</strong><small>scored predictions</small></div>
      <div class="card metric-card"><span>Mean Brier</span><strong>${calibration.mean_brier_score == null ? '—' : fmt(calibration.mean_brier_score, 3)}</strong><small>0 is perfect · lower is better</small></div>
    </div>

    <form class="inline-form section" id="forecast-form">
      <div class="field" style="grid-column:span 2"><span>Forecast</span><input id="forecast-question" required placeholder="Will X occur before date Y?" /></div>
      <div class="field"><span>Probability %</span><input id="forecast-probability" type="number" min="0" max="100" step="1" value="50" /></div>
      <div class="field"><span>Horizon</span><input id="forecast-horizon" placeholder="3 months" /></div>
      <button class="primary-button">Seal forecast</button>
    </form>

    <div class="section">
      <div class="section-head"><h3>Ledger</h3><span class="tag">${s.forecasts.length} forecasts</span></div>
      <div class="grid grid-2">
        ${s.forecasts.map((forecast) => `
          <div class="card forecast-card">
            <div class="section-head">
              <span class="tag ${forecast.status === 'resolved' ? 'good' : 'warn'}">${escapeHTML(titleCase(forecast.status))}</span>
              <span class="tag">${escapeHTML(forecast.horizon || 'No horizon')}</span>
            </div>
            <strong style="font-size:11px;line-height:1.5">${escapeHTML(forecast.question)}</strong>
            <div class="probability">${pct(forecast.probability)}</div>
            <div class="calibration-track"><i style="width:${Math.max(0, Math.min(100, Number(forecast.probability) * 100))}%"></i></div>
            <small style="color:#69717c;font-size:8px">Evidence cutoff ${escapeHTML(forecast.evidence_cutoff)}</small>
            ${forecast.status === 'open' ? `
              <div style="display:flex;gap:7px">
                <button class="secondary-button" data-resolve="${forecast.id}" data-outcome="true">Occurred</button>
                <button class="secondary-button" data-resolve="${forecast.id}" data-outcome="false">Did not occur</button>
              </div>
            ` : `
              <small style="color:#9aa1ab;font-size:8px">Outcome: <strong>${forecast.outcome ? 'YES' : 'NO'}</strong> · Brier ${fmt(forecast.brier_score, 3)}</small>
            `}
          </div>
        `).join('') || emptySection('No forecasts yet.')}
      </div>
    </div>
  `;

  $('forecast-form').addEventListener('submit', createForecast);
  document.querySelectorAll('[data-resolve]').forEach((button) => {
    button.addEventListener('click', () => resolveForecast(button.dataset.resolve, button.dataset.outcome === 'true'));
  });
}

async function createForecast(event) {
  event.preventDefault();
  const body = {
    question: $('forecast-question').value.trim(),
    probability: Number($('forecast-probability').value || 50) / 100,
    horizon: $('forecast-horizon').value.trim(),
  };
  await api(`/api/worlds/${state.projectId}/forecasts`, { method: 'POST', body });
  toast('Forecast sealed.');
  await loadSnapshot(state.projectId);
}

async function resolveForecast(id, outcome) {
  await api(`/api/worlds/${state.projectId}/forecasts/${id}/resolve`, {
    method: 'POST',
    body: { outcome },
  });
  toast('Forecast resolved and scored.');
  await loadSnapshot(state.projectId);
}

function renderSimulate() {
  const s = state.snapshot;
  $('content').innerHTML = `
    ${pageHead('SIMULATION STUDIO', 'Fork the world', 'Apply shocks to entities and propagate them through the stored relationship graph. This is structural sensitivity analysis unless the graph has been empirically calibrated.')}

    <div class="grid grid-2">
      <form class="stack-form" id="simulate-form">
        <h3>Scenario</h3>
        <div class="field"><span>Name</span><input id="simulation-name" value="Counterfactual scenario" /></div>
        <div class="field">
          <span>Shocks</span>
          <div class="list">
            ${s.entities.map((entity) => `
              <div class="list-row">
                <div><strong>${escapeHTML(entity.name)}</strong><small>baseline ${fmt(entity.attributes?.value || 0)}</small></div>
                <input class="shock-input" data-entity-id="${entity.id}" type="number" step=".1" value="0" style="width:90px;min-height:30px;border:1px solid var(--line);border-radius:7px;background:#0d0f12;color:white;padding:0 7px" />
              </div>
            `).join('') || '<p style="color:#69717c;font-size:8px">Add entities in the World tab first.</p>'}
          </div>
        </div>
        <div class="mini-grid">
          <div class="field"><span>Monte Carlo runs</span><input id="simulation-runs" type="number" min="100" max="20000" value="2000" /></div>
          <div class="field"><span>Propagation steps</span><input id="simulation-steps" type="number" min="1" max="12" value="4" /></div>
        </div>
        <div class="field"><span>Unmodeled noise</span><input id="simulation-noise" type="number" min="0" max=".5" step=".01" value=".04" /></div>
        <button class="primary-button" ${s.entities.length ? '' : 'disabled'}>Run simulation</button>
      </form>

      <div class="card">
        <div class="section-head"><h3>Latest result</h3><span class="tag">${s.simulations.length} saved</span></div>
        <div id="simulation-output">
          ${s.simulations[0] ? simulationResultHTML(s.simulations[0]) : '<p style="color:#69717c;font-size:8px">Run a scenario to see propagated distributions.</p>'}
        </div>
      </div>
    </div>
  `;

  $('simulate-form').addEventListener('submit', runSimulation);
}

function simulationResultHTML(simulation) {
  const result = simulation.result || {};
  const outcomes = result.outcomes || [];
  const max = Math.max(1e-9, ...outcomes.map((item) => Math.abs(Number(item.mean_change || 0))));
  return `
    <div class="paper-warning">${escapeHTML(result.boundary || '')}</div>
    <div class="sim-result">
      ${outcomes.slice(0, 12).map((item) => {
        const change = Number(item.mean_change || 0);
        const width = Math.min(50, Math.abs(change) / max * 50);
        return `
          <div class="sim-row">
            <span>${escapeHTML(item.name)}</span>
            <div class="sim-bar"><i class="${change < 0 ? 'neg' : ''}" style="width:${width}%"></i></div>
            <strong style="text-align:right">${change >= 0 ? '+' : ''}${fmt(change, 2)}</strong>
          </div>
        `;
      }).join('')}
    </div>
    <div class="section code-card">runs=${result.runs} · steps=${result.steps} · noise=${result.noise}<br>shocks=${escapeHTML(JSON.stringify(result.shocks || {}))}</div>
  `;
}

async function runSimulation(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button[type="submit"],button.primary-button');
  button.disabled = true;
  button.textContent = 'Simulating…';

  const shocks = {};
  document.querySelectorAll('.shock-input').forEach((input) => {
    const value = Number(input.value || 0);
    if (value !== 0) shocks[input.dataset.entityId] = value;
  });

  try {
    const result = await api(`/api/worlds/${state.projectId}/simulate`, {
      method: 'POST',
      body: {
        name: $('simulation-name').value.trim(),
        shocks,
        runs: Number($('simulation-runs').value),
        steps: Number($('simulation-steps').value),
        noise: Number($('simulation-noise').value),
      },
    });
    $('simulation-output').innerHTML = simulationResultHTML(result);
    toast('Simulation complete.');
    state.snapshot = await api(`/api/worlds/${state.projectId}`);
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Run simulation';
  }
}

function renderReport() {
  const s = state.snapshot;
  const report = s.reports?.[0];
  $('content').innerHTML = `
    ${pageHead(
      'LIVING REPORT',
      'A report that stays attached to the world',
      'The report is generated from explicit claims, forecasts, simulations, evidence, business observations, and paper positions—not from an empty prompt.',
      '<button class="primary-button" id="generate-report">Generate deep report</button>'
    )}

    ${report ? reportHTML(report) : `
      <div class="empty-state" style="min-height:55vh">
        <span class="empty-mark">R</span>
        <h2 style="font-size:28px">No report yet.</h2>
        <p>Build the World, add forecasts or evidence, then generate a living report. If Ollama is available, Rook will also write a grounded narrative.</p>
      </div>
    `}
  `;

  $('generate-report')?.addEventListener('click', generateReport);
}

function reportHTML(report) {
  const content = report.content || {};
  const claims = content.competing_claims || [];
  const forecasts = content.forecasts || {};
  const sims = content.recent_simulations || [];
  const sources = content.evidence || [];
  return `
    <article class="report-shell">
      <div class="report-cover">
        <p class="eyebrow">${escapeHTML(report.title)}</p>
        <h2>${escapeHTML(content.project?.name || report.title)}</h2>
        <p style="color:#9aa1ab;font-size:10px;line-height:1.65">${escapeHTML(content.executive_summary || '')}</p>
      </div>
      <div class="report-body">
        ${content.narrative ? `
          <h3>Deep analysis</h3>
          <div class="report-quote">${escapeHTML(content.narrative)}</div>
        ` : content.narrative_error ? `
          <div class="paper-warning">Structured report generated. Ollama narrative unavailable: ${escapeHTML(content.narrative_error)}</div>
        ` : ''}

        <h3>Competing claims</h3>
        <ul>${claims.map((claim) => `<li><strong>${pct(claim.confidence)}</strong> · ${escapeHTML(claim.text)} <em>(${escapeHTML(titleCase(claim.status))})</em></li>`).join('') || '<li>No claims stored.</li>'}</ul>

        <h3>Outstanding forecasts</h3>
        <ul>${(forecasts.open || []).map((item) => `<li><strong>${pct(item.probability)}</strong> · ${escapeHTML(item.question)}</li>`).join('') || '<li>No open forecasts.</li>'}</ul>

        <h3>Recent simulations</h3>
        <ul>${sims.map((item) => `<li>${escapeHTML(item.name)} · ${item.result?.runs || 0} simulated worlds</li>`).join('') || '<li>No simulations yet.</li>'}</ul>

        <h3>Evidence</h3>
        <ul>${sources.map((item) => `<li>${escapeHTML(item.title)}${item.url ? ` · ${escapeHTML(item.url)}` : ''}</li>`).join('') || '<li>No evidence attached.</li>'}</ul>

        <h3>Scientific boundary</h3>
        <ul>${(content.limitations || []).map((item) => `<li>${escapeHTML(item)}</li>`).join('')}</ul>
      </div>
    </article>
  `;
}

async function generateReport() {
  const button = $('generate-report');
  button.disabled = true;
  button.textContent = state.ollama.model ? 'Rook is writing…' : 'Building report…';
  try {
    await api(`/api/worlds/${state.projectId}/reports`, {
      method: 'POST',
      body: {
        title: `${state.snapshot.project.name} · Living Report`,
        ollama_model: state.ollama.model || null,
      },
    });
    toast('Living report generated.');
    await loadSnapshot(state.projectId);
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Generate deep report';
  }
}

function renderBusiness() {
  const s = state.snapshot;
  const metrics = s.business?.metrics || [];
  $('content').innerHTML = `
    ${pageHead('BUSINESS WORLD', 'Turn operating data into a model', 'Store business observations over time. Rook summarizes trends here; the same metrics can also become entities in the World and inputs into simulations.')}

    <form class="inline-form" id="observation-form">
      <div class="field"><span>Metric</span><input id="metric-name" required placeholder="Revenue" /></div>
      <div class="field"><span>Value</span><input id="metric-value" type="number" step="any" required /></div>
      <div class="field"><span>Unit</span><input id="metric-unit" placeholder="EUR / orders / %" /></div>
      <div class="field"><span>Date</span><input id="metric-date" type="date" required /></div>
      <button class="primary-button">Add observation</button>
    </form>

    <div class="section grid grid-3">
      ${metrics.map((metric) => `
        <div class="card metric-card">
          <span>${escapeHTML(metric.metric)}</span>
          <strong>${fmt(metric.latest, 2)} ${escapeHTML(metric.unit)}</strong>
          <small>${metric.pct_change == null ? 'First observation' : `${metric.pct_change >= 0 ? '+' : ''}${pct(metric.pct_change, 1)} vs previous`} · ${metric.observations} points</small>
        </div>
      `).join('') || emptySection('Add business metrics to start building an operating history.')}
    </div>

    <div class="section table-wrap">
      <table>
        <thead><tr><th>Metric</th><th>Latest</th><th>Previous</th><th>Change</th><th>Trend / observation</th><th>Last observed</th></tr></thead>
        <tbody>
          ${metrics.map((metric) => `
            <tr>
              <td>${escapeHTML(metric.metric)}</td>
              <td>${fmt(metric.latest, 2)} ${escapeHTML(metric.unit)}</td>
              <td>${metric.previous == null ? '—' : fmt(metric.previous, 2)}</td>
              <td>${metric.change == null ? '—' : fmt(metric.change, 2)}</td>
              <td>${fmt(metric.trend_per_observation, 3)}</td>
              <td>${escapeHTML(metric.last_observed_at)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  $('metric-date').value = new Date().toISOString().slice(0, 10);
  $('observation-form').addEventListener('submit', createObservation);
}

async function createObservation(event) {
  event.preventDefault();
  await api(`/api/worlds/${state.projectId}/observations`, {
    method: 'POST',
    body: {
      metric: $('metric-name').value.trim(),
      value: Number($('metric-value').value),
      unit: $('metric-unit').value.trim(),
      observed_at: $('metric-date').value,
    },
  });
  toast('Business observation added.');
  await loadSnapshot(state.projectId);
}

function renderPaper() {
  const s = state.snapshot;
  const paper = s.paper || {};
  const account = paper.account || { cash: 0, initial_cash: 0 };
  const trades = paper.trades || [];

  $('content').innerHTML = `
    ${pageHead('PAPER TRADING', 'Test the thesis before money moves', 'Paper trades attach a thesis and falsifier to each simulated position. This workspace does not place live broker orders.')}

    <div class="paper-warning">Paper mode only. Rook does not place live orders here. Treat simulated P&L as a research record, not evidence of future profitability.</div>

    <div class="grid grid-3 section">
      <div class="card metric-card"><span>Paper cash</span><strong>${money(account.cash)}</strong><small>initial ${money(account.initial_cash)}</small></div>
      <div class="card metric-card"><span>Realized P&L</span><strong>${money(paper.realized_pnl || 0)}</strong><small>closed paper trades</small></div>
      <div class="card metric-card"><span>Open trades</span><strong>${trades.filter((item) => item.status === 'open').length}</strong><small>${trades.length} total</small></div>
    </div>

    <form class="inline-form section" id="paper-trade-form">
      <div class="field"><span>Symbol</span><input id="trade-symbol" required placeholder="NVDA" /></div>
      <div class="field"><span>Side</span><select id="trade-side"><option value="buy">Buy</option><option value="sell">Sell / short</option></select></div>
      <div class="field"><span>Quantity</span><input id="trade-quantity" type="number" min=".0001" step="any" required /></div>
      <div class="field"><span>Entry price</span><input id="trade-price" type="number" min=".0001" step="any" required /></div>
      <button class="primary-button">Open paper trade</button>
      <div class="field" style="grid-column:span 2"><span>Thesis</span><input id="trade-thesis" placeholder="Why should this position work?" /></div>
      <div class="field" style="grid-column:span 2"><span>Falsifier</span><input id="trade-falsifier" placeholder="What evidence would make you exit?" /></div>
    </form>

    <div class="section table-wrap">
      <table>
        <thead><tr><th>Status</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Thesis</th><th></th></tr></thead>
        <tbody>
          ${trades.map((trade) => `
            <tr>
              <td><span class="tag ${trade.status === 'closed' ? 'good' : 'warn'}">${escapeHTML(titleCase(trade.status))}</span></td>
              <td><strong>${escapeHTML(trade.symbol)}</strong></td>
              <td>${escapeHTML(titleCase(trade.side))}</td>
              <td>${fmt(trade.quantity, 3)}</td>
              <td>${money(trade.entry_price)}</td>
              <td>${trade.exit_price == null ? '—' : money(trade.exit_price)}</td>
              <td>${trade.realized_pnl == null ? '—' : money(trade.realized_pnl)}</td>
              <td>${escapeHTML(trade.thesis || '—')}</td>
              <td>${trade.status === 'open' ? `<button class="secondary-button" data-close-trade="${trade.id}">Close</button>` : ''}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  $('paper-trade-form').addEventListener('submit', createPaperTrade);
  document.querySelectorAll('[data-close-trade]').forEach((button) => {
    button.addEventListener('click', () => closePaperTrade(button.dataset.closeTrade));
  });
}

async function createPaperTrade(event) {
  event.preventDefault();
  try {
    await api(`/api/worlds/${state.projectId}/paper/trades`, {
      method: 'POST',
      body: {
        symbol: $('trade-symbol').value.trim(),
        side: $('trade-side').value,
        quantity: Number($('trade-quantity').value),
        entry_price: Number($('trade-price').value),
        thesis: $('trade-thesis').value.trim(),
        falsifier: $('trade-falsifier').value.trim(),
      },
    });
    toast('Paper trade opened.');
    await loadSnapshot(state.projectId);
  } catch (error) {
    toast(error.message);
  }
}

async function closePaperTrade(id) {
  const raw = window.prompt('Paper exit price');
  if (raw == null) return;
  const exitPrice = Number(raw);
  if (!Number.isFinite(exitPrice) || exitPrice <= 0) {
    toast('Enter a valid positive exit price.');
    return;
  }
  await api(`/api/worlds/${state.projectId}/paper/trades/${id}/close`, {
    method: 'POST',
    body: { exit_price: exitPrice },
  });
  toast('Paper trade closed.');
  await loadSnapshot(state.projectId);
}

function openNewWorldDialog() {
  $('new-world-dialog').showModal();
  setTimeout(() => $('new-world-name').focus(), 50);
}

async function createWorld(event) {
  event.preventDefault();
  const name = $('new-world-name').value.trim();
  if (!name) return;
  const button = $('create-world');
  button.disabled = true;
  button.textContent = 'Creating…';
  try {
    const project = await api('/api/worlds', {
      method: 'POST',
      body: {
        name,
        kind: $('new-world-kind').value,
        goal: $('new-world-goal').value.trim(),
      },
    });
    $('new-world-dialog').close();
    $('new-world-form').reset();
    state.projectId = project.id;
    await loadProjects({ preserve: true });
    toast('World created.');
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Create world';
  }
}

function openSettings() {
  $('settings-sheet').classList.add('open');
  $('scrim').classList.add('open');
}

function closeSettings() {
  $('settings-sheet').classList.remove('open');
  $('scrim').classList.remove('open');
  $('rail').classList.remove('open');
}

function bindEvents() {
  $('new-world').addEventListener('click', openNewWorldDialog);
  $('new-world-form').addEventListener('submit', createWorld);
  $('refresh-worlds').addEventListener('click', () => loadProjects());
  $('world-list').addEventListener('click', (event) => {
    const button = event.target.closest('[data-world-id]');
    if (button) loadSnapshot(button.dataset.worldId);
  });

  $('tabs').addEventListener('click', (event) => {
    const button = event.target.closest('[data-tab]');
    if (button) setTab(button.dataset.tab);
  });

  $('open-settings').addEventListener('click', openSettings);
  $('close-settings').addEventListener('click', closeSettings);
  $('scrim').addEventListener('click', closeSettings);

  $('ollama-model').addEventListener('change', (event) => {
    state.ollama.model = event.target.value || null;
    if (state.ollama.model) localStorage.setItem('rook.worlds.ollamaModel', state.ollama.model);
    $('ai-chip').textContent = state.ollama.model ? `Local AI · ${state.ollama.model}` : 'Local AI offline';
  });

  $('open-rail').addEventListener('click', () => {
    $('rail').classList.add('open');
    $('scrim').classList.add('open');
  });
  $('close-rail').addEventListener('click', closeSettings);

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeSettings();
  });
}

async function init() {
  bindEvents();
  try {
    const health = await api('/api/health');
    $('local-dot').classList.toggle('ok', health.status === 'ok');
    $('local-status').textContent = `Local Rook ${health.version}`;
  } catch {
    $('local-status').textContent = 'Rook backend offline';
  }

  await Promise.all([refreshOllama(), loadProjects({ preserve: false })]);
  const remembered = localStorage.getItem('rook.worlds.activeProject');
  if (remembered && state.projects.some((item) => item.id === remembered) && remembered !== state.projectId) {
    await loadSnapshot(remembered);
  }
}

init();
