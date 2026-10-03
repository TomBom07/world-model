const $ = (id) => document.getElementById(id);
const fmt = (n, d = 3) => Number(n).toFixed(d);
const pct = (n, d = 0) => `${(Number(n) * 100).toFixed(d)}%`;
const pretty = (value) => String(value ?? '').replaceAll('_', ' ');
const titleCase = (value) => pretty(value).replace(/\b\w/g, (m) => m.toUpperCase());

const CONTEXTS = {
  market: {
    name: 'Market',
    kicker: 'MARKET WORLD',
    title: 'What do you want to understand?',
    copy: 'Two different hidden mechanisms can fit almost the same price history. Rook keeps both alive and looks for evidence that separates them.',
    placeholder: 'Ask about the market world…',
    boundary: 'Controlled market world · identification research, not a trading signal',
    quick: 'Run best test',
    starters: [
      ['What is driving this market?', 'See which hidden mechanism currently has the most posterior mass.'],
      ['Why is normal price history not enough?', 'Understand observational equivalence and why fit is not explanation.'],
      ['What would change your mind?', 'Expose the exact evidence that would falsify the leading view.'],
      ['What if liquidity drops by 2σ?', 'Run a fresh counterfactual through both candidate worlds.'],
    ],
  },
  physics: {
    name: 'Physics',
    kicker: 'PHYSICS WORLD',
    title: 'Which hidden law explains the motion?',
    copy: 'The two resistance laws are built to look nearly identical around normal operation. Rook has to choose a probe that exposes their curvature.',
    placeholder: 'Ask about the hidden physics world…',
    boundary: 'Controlled physics world · system-identification research',
    quick: 'Best experiment',
    starters: [
      ['Which law do you currently believe?', 'See the posterior over linear versus curved resistance.'],
      ['Why do both laws look the same?', 'See how they are constructed to be locally tangent.'],
      ['What experiment distinguishes them?', 'Inspect the force pulse Rook selected before seeing the outcome.'],
      ['How sure are you?', 'See uncertainty, alternatives, and active-versus-random evidence.'],
    ],
  },
  discovery: {
    name: 'Discovery',
    kicker: 'DISCOVERY LAB',
    title: 'What did Rook discover instead of being told?',
    copy: 'This is the open-world layer: discover useful latent variables, reject an incomplete theory family, invent missing structure, and revise concepts.',
    placeholder: 'Ask about theory invention or ontology discovery…',
    boundary: 'Controlled discovery benchmarks · not a claim of unknown real-world laws',
    quick: 'Show discovery',
    starters: [
      ['What did you discover without being told?', 'Summarize the latent variables, regimes, laws, and invented structure.'],
      ['Why did you reject the given theories?', 'Inspect the explicit “none of the above” hypothesis.'],
      ['What new equation did you invent?', 'See the symbolic replacement theory and held-out improvement.'],
      ['What does ontology mean here?', 'Understand splits, merges, and learned internal concepts.'],
    ],
  },
  validation: {
    name: 'Validation',
    kicker: 'VALIDATION',
    title: 'Can we trust this run?',
    copy: 'Rook freezes chronology, redacts unavailable features, seals forecasts before outcomes are read, and scores all models under the same holdout rules.',
    placeholder: 'Ask about leakage, seals, or holdout evaluation…',
    boundary: 'Sealed replay reduces look-ahead risk · it does not prove causality or live alpha',
    quick: 'Inspect seals',
    starters: [
      ['How do I know you did not cheat?', 'Check leakage guards, chronology, and forecast seals.'],
      ['What was sealed before the outcome?', 'Understand the immutable experiment and forecast hashes.'],
      ['Which model did best on the holdout?', 'Compare models under the same frozen evaluation window.'],
      ['What does this still not prove?', 'See the scientific boundary of a historical replay.'],
    ],
  },
  custom: {
    name: 'Your data',
    kicker: 'YOUR DATA',
    title: 'Bring your own world.',
    copy: 'Upload a numeric CSV, choose what you want to explain, and Rook will search for a compact relationship while keeping the final rows untouched for holdout evaluation.',
    placeholder: 'Ask Rook about your uploaded data…',
    boundary: 'Uploaded observational data · predictive structure is not automatically causal',
    quick: 'Analyze data',
    starters: [
      ['Upload a CSV', 'Choose a numeric table and the target you want Rook to explain.'],
      ['What will Rook do with my data?', 'See the train/holdout protocol before uploading anything.'],
      ['What kind of CSV works best?', 'Learn the minimum requirements and current limits.'],
      ['What does Rook refuse to claim?', 'Understand the causality and extrapolation boundary.'],
    ],
  },
};

const STORAGE_KEY = 'rook.threads.v2';

const state = {
  context: 'market',
  strategic: null,
  physics: null,
  frontier: null,
  sealed: null,
  v0: null,
  health: null,
  scenario: null,
  customData: null,
  customFileName: null,
  customUpload: null,
  loading: false,
  threads: [],
  activeThreadId: null,
};

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function escapeHTML(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function toast(message) {
  const node = $('toast');
  node.textContent = message;
  node.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove('show'), 2400);
}

function loadThreads() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    state.threads = Array.isArray(parsed) ? parsed.slice(0, 24) : [];
  } catch {
    state.threads = [];
  }
}

function saveThreads() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.threads.slice(0, 24)));
  } catch {
    // Local persistence is convenience only. The research state still works without it.
  }
}

function createThread(context = state.context) {
  const thread = {
    id: uid(),
    context,
    title: 'New chat',
    createdAt: Date.now(),
    messages: [],
    customAnalysis: context === 'custom' ? state.customData : null,
    customFileName: context === 'custom' ? state.customFileName : null,
  };
  state.threads.unshift(thread);
  state.activeThreadId = thread.id;
  state.context = context;
  saveThreads();
  renderRecent();
  renderContext();
  renderConversation();
  return thread;
}

function activeThread() {
  return state.threads.find((thread) => thread.id === state.activeThreadId) || null;
}

function ensureThread() {
  return activeThread() || createThread(state.context);
}

function saveMessage(role, payload) {
  const thread = ensureThread();
  const message = {
    id: uid(),
    role,
    ...payload,
  };
  thread.messages.push(message);
  if (role === 'user' && thread.title === 'New chat') {
    thread.title = String(payload.text || 'New chat').trim().slice(0, 48) || 'New chat';
  }
  thread.createdAt = Date.now();
  state.threads = [thread, ...state.threads.filter((item) => item.id !== thread.id)];
  saveThreads();
  renderRecent();
  return message;
}

function renderRecent() {
  const node = $('recent-list');
  if (!state.threads.length) {
    node.innerHTML = '<div class="empty-recent">Your conversations stay on this device.</div>';
    return;
  }

  node.innerHTML = state.threads.slice(0, 12).map((thread) => `
    <button class="recent-item ${thread.id === state.activeThreadId ? 'active' : ''}" data-thread="${thread.id}">
      <strong>${escapeHTML(thread.title)}</strong>
      <small>${escapeHTML(CONTEXTS[thread.context]?.name || 'Rook')}</small>
    </button>
  `).join('');
}

function renderContext() {
  const context = CONTEXTS[state.context];
  $('world-name').textContent = context.name;
  $('welcome-kicker').textContent = context.kicker;
  $('welcome-title').textContent = context.title;
  $('welcome-copy').textContent = context.copy;
  $('ask-input').placeholder = context.placeholder;
  $('composer-boundary').textContent = state.context === 'custom' && state.customData
    ? `${state.customFileName || 'Uploaded CSV'} · predictive structure is not automatically causal`
    : context.boundary;
  $('quick-test').textContent = state.context === 'custom' && state.customData ? 'Analyze another' : context.quick;

  document.querySelectorAll('.context-item').forEach((button) => {
    button.classList.toggle('active', button.dataset.context === state.context);
  });

  const starters = state.context === 'custom' && state.customData
    ? [
        ['What did you find?', 'See the best compact equation and untouched holdout score.'],
        ['Which features matter most?', 'Use holdout permutation sensitivity, not causal language.'],
        ['How good is the holdout result?', 'Compare the symbolic model with mean and ridge baselines.'],
        ['Can I call this causal?', 'Keep prediction, mechanism, and causality separate.'],
      ]
    : context.starters;

  $('starter-grid').innerHTML = starters.map(([title, description], index) => `
    <button class="starter-card" data-starter="${escapeHTML(title)}" ${state.context === 'custom' && !state.customData && index === 0 ? 'data-open-custom="true"' : ''}>
      <strong>${escapeHTML(title)}</strong>
      <small>${escapeHTML(description)}</small>
    </button>
  `).join('');
}

function switchContext(context, { newThread = true } = {}) {
  if (!CONTEXTS[context]) return;
  closePopovers();

  const thread = activeThread();
  if (newThread && thread && thread.messages.length > 0 && thread.context !== context) {
    createThread(context);
  } else {
    state.context = context;
    if (thread && thread.messages.length === 0) {
      thread.context = context;
      saveThreads();
    }
    renderContext();
    renderConversation();
    renderRecent();
  }

  if (window.innerWidth <= 900) closeSidebar();
}

function newChat() {
  const thread = activeThread();
  if (thread && thread.messages.length === 0) {
    renderConversation();
    $('ask-input').focus();
    return;
  }
  createThread(state.context);
  $('ask-input').focus();
}

function renderConversation() {
  const thread = activeThread();
  const messages = thread?.messages || [];
  const conversation = $('conversation');
  conversation.innerHTML = '';

  $('welcome').classList.toggle('hidden', messages.length > 0);

  for (const message of messages) {
    appendMessageNode(message);
  }

  if (messages.length) {
    requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' }));
  }
}

function appendMessageNode(message) {
  const wrap = document.createElement('article');
  wrap.className = `message ${message.role}`;
  wrap.dataset.messageId = message.id;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = message.role === 'assistant' ? 'R' : 'You';

  const content = document.createElement('div');
  content.className = 'message-content';

  const role = document.createElement('div');
  role.className = 'message-role';
  role.textContent = message.role === 'assistant' ? 'Rook' : 'You';
  content.appendChild(role);

  const p = document.createElement('p');
  if (message.role === 'assistant') p.innerHTML = message.html || '';
  else p.textContent = message.text || '';
  content.appendChild(p);

  wrap.append(avatar, content);
  $('conversation').appendChild(wrap);
}

function appendThinking() {
  const wrap = document.createElement('article');
  wrap.className = 'message assistant';
  wrap.id = 'thinking-message';
  wrap.innerHTML = `
    <div class="avatar">R</div>
    <div class="message-content">
      <div class="message-role">Rook</div>
      <p class="thinking">Reasoning from the current world…</p>
    </div>
  `;
  $('conversation').appendChild(wrap);
  wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function removeThinking() {
  $('thinking-message')?.remove();
}

function meta(items) {
  return `<span class="answer-meta">${items.map(([label, value]) =>
    `<span class="meta-pill">${escapeHTML(label)} <strong>${escapeHTML(value)}</strong></span>`
  ).join('')}</span>`;
}

function actions(items) {
  return `<span class="answer-actions">${items.map((item) => {
    if (item.action === 'ask') {
      return `<button class="answer-action" data-action="ask" data-question="${escapeHTML(item.question)}">${escapeHTML(item.label)}</button>`;
    }
    return `<button class="answer-action" data-action="${escapeHTML(item.action)}">${escapeHTML(item.label)}</button>`;
  }).join('')}</span>`;
}

async function answerMarket(q) {
  const data = state.strategic;
  if (!data) return loadingAnswer();

  const active = data.active_identification;
  const predicted = active.predicted_mechanism;
  const confidence = active.posterior[predicted] ?? 0;
  const alternative = Object.entries(active.posterior).sort((a, b) => b[1] - a[1]).find(([name]) => name !== predicted);
  const probe = active.selected_probe;
  const entropyRemoved = (active.entropy_before - active.entropy_after) / Math.max(active.entropy_before, 1e-9);

  if (q.includes('what if')) {
    const names = ['growth', 'inflation', 'liquidity', 'policy', 'sentiment'];
    const eventKind = names.find((name) => q.includes(name)) || probe.event_kind;
    const sigmaMatch = q.match(/([+-]?\d+(?:\.\d+)?)\s*(?:σ|sigma)/i);
    let magnitude = sigmaMatch ? Number(sigmaMatch[1]) : (eventKind === 'liquidity' ? -2 : 2);
    magnitude = Math.max(-4, Math.min(4, magnitude));
    const scenario = await fetchScenario(eventKind, magnitude);
    if (!scenario) return '<span class="answer-lead">I could not run that counterfactual.</span>';

    const asset = scenario.most_diagnostic_asset;
    const a = scenario.predictions.belief_reflexive[asset];
    const b = scenario.predictions.liquidity_reflexive[asset];

    return `
      <span class="answer-lead">The two worlds disagree most through ${titleCase(asset)}.</span>
      Under <strong>${titleCase(scenario.event.label)}</strong>, the belief-reflexive world predicts
      <strong>${a >= 0 ? '+' : ''}${fmt(a, 3)}</strong> reaction units while the liquidity-reflexive
      world predicts <strong>${b >= 0 ? '+' : ''}${fmt(b, 3)}</strong>.
      ${meta([
        ['information', fmt(scenario.information_score, 2)],
        ['largest gap', fmt(scenario.absolute_disagreement[asset], 3)],
        ['scope', 'synthetic'],
      ])}
      ${actions([
        { label: 'Open what-if tool', action: 'open-tool' },
        { label: 'Why is this diagnostic?', action: 'ask', question: 'Why is this event diagnostic?' },
      ])}
    `;
  }

  if (q.includes('driving') || q.includes('what do you think') || q.includes('what is happening') || q.includes('leading')) {
    return `
      <span class="answer-lead">My leading explanation is ${titleCase(predicted)}.</span>
      It holds <strong>${pct(confidence, 1)}</strong> posterior mass after the selected diagnostic evidence.
      I still keep <strong>${titleCase(alternative?.[0] || 'alternative')}</strong> alive at
      <strong>${pct(alternative?.[1] || 0, 1)}</strong> rather than pretending the problem is solved.
      ${meta([
        ['belief world', pct(active.posterior.belief_reflexive ?? 0, 1)],
        ['liquidity world', pct(active.posterior.liquidity_reflexive ?? 0, 1)],
        ['path correlation', pct(data.observational_equivalence.mean_return_correlation, 2)],
      ])}
      ${actions([
        { label: 'Why?', action: 'ask', question: 'Why do you believe that?' },
        { label: 'What would change your mind?', action: 'ask', question: 'What would change your mind?' },
        { label: 'Evidence', action: 'open-lab' },
      ])}
    `;
  }

  if (q.includes('normal price') || q.includes('history not enough') || q.includes('observational') || q.includes('fit')) {
    return `
      <span class="answer-lead">Because two different mechanisms can generate almost the same visible history.</span>
      In this controlled run the ordinary paths are <strong>${pct(data.observational_equivalence.mean_return_correlation, 2)}</strong>
      correlated. A forecaster can fit that history without knowing whether belief feedback or liquidity constraints caused it.
      Rook therefore asks where the candidate worlds make different predictions instead of treating fit as explanation.
      ${actions([{ label: 'Show best discriminator', action: 'open-tool' }])}
    `;
  }

  if (q.includes('why') || q.includes('diagnostic')) {
    return `
      <span class="answer-lead">Because passive evidence barely separates the theories, while the selected event does.</span>
      Rook chose <strong>${titleCase(probe.event_kind)} ${probe.magnitude >= 0 ? '+' : ''}${fmt(probe.magnitude, 1)}σ</strong>
      because its predicted reaction fingerprints differ most across the candidate worlds. After observing that reaction,
      uncertainty fell by <strong>${pct(entropyRemoved, 1)}</strong>.
      ${meta([
        ['information score', fmt(active.information_score, 2)],
        ['entropy removed', pct(entropyRemoved, 1)],
        ['leading world', titleCase(predicted)],
      ])}
      ${actions([{ label: 'Run counterfactual', action: 'open-tool' }])}
    `;
  }

  if (q.includes('change your mind') || q.includes('falsif') || q.includes('wrong') || q.includes('disconfirm')) {
    return `
      <span class="answer-lead">A reaction closer to the alternative world would reduce my current belief.</span>
      The highest-information discriminator is <strong>${titleCase(probe.event_kind)}
      ${probe.magnitude >= 0 ? '+' : ''}${fmt(probe.magnitude, 1)}σ</strong>. Before observing it, each candidate
      world produces a different reaction fingerprint. If reality lands nearer the alternative fingerprint, the posterior moves away from
      <strong>${titleCase(predicted)}</strong>.
      ${actions([
        { label: 'Run best test', action: 'open-tool' },
        { label: 'Inspect posterior', action: 'open-lab' },
      ])}
    `;
  }

  if (q.includes('sure') || q.includes('confidence') || q.includes('uncertain') || q.includes('probability')) {
    return `
      <span class="answer-lead">${pct(confidence, 1)} on the leading controlled-world mechanism.</span>
      That number is a posterior inside this synthetic experiment, not a calibrated probability that the real market works this way.
      The alternative remains at <strong>${pct(alternative?.[1] || 0, 1)}</strong>.
      ${actions([{ label: 'What would change your mind?', action: 'ask', question: 'What would change your mind?' }])}
    `;
  }

  return genericAnswer('market');
}

function answerPhysics(q) {
  const data = state.physics;
  if (!data) return loadingAnswer();

  const active = data.active_identification;
  const predicted = active.predicted_mechanism;
  const confidence = active.posterior[predicted] ?? 0;
  const probe = active.selected_probe;
  const bench = data.identification_benchmark;

  if (q.includes('which law') || q.includes('believe') || q.includes('leading')) {
    return `
      <span class="answer-lead">My leading law is ${titleCase(predicted)}.</span>
      The selected force experiment moved its posterior to <strong>${pct(confidence, 1)}</strong>.
      ${meta([
        ['linear', pct(active.posterior.linear_resistance ?? 0, 1)],
        ['curved', pct(active.posterior.curved_resistance ?? 0, 1)],
        ['passive corr.', pct(data.passive_equivalence.velocity_correlation, 3)],
      ])}
      ${actions([
        { label: 'Why?', action: 'ask', question: 'Why do both laws look the same?' },
        { label: 'Best experiment', action: 'open-tool' },
      ])}
    `;
  }

  if (q.includes('why is that') || q.includes('why do you believe')) {
    return `
      <span class="answer-lead">Because the selected probe separates laws that passive motion cannot.</span>
      Ordinary trajectories are <strong>${pct(data.passive_equivalence.velocity_correlation, 3)}</strong> correlated because both laws match at the reference velocity.
      The <strong>${titleCase(probe.name)}</strong> probe deliberately moves the system away from that locally tangent region,
      and the observed reaction lands closer to <strong>${titleCase(predicted)}</strong>.
      ${actions([{ label: 'Open experiment', action: 'open-tool' }, { label: 'Evidence', action: 'open-lab' }])}
    `;
  }

  if (q.includes('look the same') || q.includes('tangent') || q.includes('passive')) {
    const v0 = data.mechanisms.tangent_at_velocity;
    return `
      <span class="answer-lead">The laws were deliberately constructed to match locally.</span>
      At reference velocity <strong>v = ${fmt(v0, 2)}</strong>, they have the same resistance and the same first derivative.
      So ordinary operation near that point hides the curvature difference. Rook must push the system away from the tangent region.
      ${meta([
        ['linear law', data.mechanisms.linear_resistance.equation],
        ['curved law', data.mechanisms.curved_resistance.equation],
      ])}
    `;
  }

  if (q.includes('experiment') || q.includes('distinguish') || q.includes('probe') || q.includes('test')) {
    return `
      <span class="answer-lead">Use the ${titleCase(probe.name)} probe.</span>
      Rook selected a force of <strong>+${fmt(probe.force, 2)}</strong> for <strong>${probe.duration}</strong> steps
      because it maximized expected information gain before the outcome was observed.
      ${meta([
        ['expected info.', fmt(active.expected_information_gain, 3)],
        ['active accuracy', pct(bench.active_accuracy, 1)],
        ['random accuracy', pct(bench.random_accuracy, 1)],
      ])}
      ${actions([
        { label: 'Open experiment', action: 'open-tool' },
        { label: 'Inspect preregistration', action: 'open-lab' },
      ])}
    `;
  }

  if (q.includes('sure') || q.includes('confidence') || q.includes('uncertain')) {
    const other = Object.entries(active.posterior).sort((a, b) => b[1] - a[1]).find(([name]) => name !== predicted);
    return `
      <span class="answer-lead">${pct(confidence, 1)} posterior on ${titleCase(predicted)} in this controlled run.</span>
      The alternative remains at <strong>${pct(other?.[1] || 0, 1)}</strong>. Across the benchmark,
      active probes put <strong>${pct(bench.active_true_posterior, 1)}</strong> mass on the true law on average versus
      <strong>${pct(bench.random_true_posterior, 1)}</strong> for random probes.
      ${actions([{ label: 'Evidence', action: 'open-lab' }])}
    `;
  }

  return genericAnswer('physics');
}

function answerDiscovery(q) {
  const data = state.frontier;
  if (!data) return loadingAnswer();

  const open = data.theory_invention.open_world;
  const invented = data.theory_invention.invented;
  const natural = data.natural_experiments;
  const summary = data.cross_domain_summary;
  const evolution = data.ontology_evolution;

  if (q.includes('why is this') || q.includes('meaningful discovery')) {
    return `
      <span class="answer-lead">Because the benchmark makes Rook recover structure it was not handed, then checks that structure out of sample.</span>
      The system is not rewarded merely for naming something interesting: latent coordinates must beat PCA, regimes must match hidden environments,
      symbolic laws must predict held-out dynamics, and an invented theory must improve holdout error after the known theory family is rejected.
      ${actions([{ label: 'All falsification gates', action: 'open-lab' }])}
    `;
  }

  if (q.includes('what did') || q.includes('discover') || q.includes('without being told')) {
    return `
      <span class="answer-lead">Rook recovered useful latent variables, hidden regimes, symbolic laws, and missing theory structure.</span>
      Across the controlled domains it selected <strong>${summary.selected_dims.join(', ')}</strong> latent dimensions,
      recovered natural-experiment regimes with <strong>ARI ${fmt(natural.adjusted_rand_index, 3)}</strong>,
      and the symbolic latent laws reached mean held-out <strong>R² ${fmt(data.latent_laws.mean_validation_r2, 5)}</strong>.
      ${actions([
        { label: 'Show invented theory', action: 'open-tool' },
        { label: 'All falsification gates', action: 'open-lab' },
      ])}
    `;
  }

  if (q.includes('reject') || q.includes('given theories') || q.includes('none of') || q.includes('unknown')) {
    return `
      <span class="answer-lead">Because the known theory family could not explain the observation well enough.</span>
      Instead of forcing a choice among bad candidates, the open-world layer gave <strong>${pct(open.unknown_probability, 1)}</strong>
      posterior mass to <strong>“none of the above.”</strong> That triggered residual-structure search for a replacement theory.
      ${actions([{ label: 'Show replacement theory', action: 'open-tool' }])}
    `;
  }

  if (q.includes('equation') || q.includes('invent') || q.includes('new theory')) {
    if (!invented?.accepted) return '<span class="answer-lead">No replacement theory was accepted in this run.</span>';
    return `
      <span class="answer-lead">The accepted replacement theory was:</span>
      <span class="code-block" style="display:block;margin:10px 0">${escapeHTML(invented.program)}</span>
      It improved held-out error by <strong>${pct(invented.relative_improvement, 1)}</strong> and recovered the missing
      interaction <strong>x0*x1</strong>.
      ${actions([{ label: 'Technical evidence', action: 'open-lab' }])}
    `;
  }

  if (q.includes('ontology') || q.includes('latent') || q.includes('split') || q.includes('merge')) {
    const split = evolution.splits?.[0];
    const merge = evolution.merges?.[0];
    return `
      <span class="answer-lead">“Ontology” means the internal concepts or variables Rook decides are worth representing.</span>
      The benchmark tests whether it can discover those concepts rather than receiving them by hand.
      ${split ? `It detected that latent dimension <strong>${split.dimension}</strong> should split.` : ''}
      ${merge ? `It also detected that dimensions <strong>${merge.left}</strong> and <strong>${merge.right}</strong> were redundant enough to merge.` : ''}
      ${meta([['min uplift vs PCA', pct(summary.minimum_improvement_over_pca, 1)], ['selected dims', summary.selected_dims.join(' / ')]])}
    `;
  }

  return genericAnswer('discovery');
}

function answerValidation(q) {
  const data = state.sealed;
  if (!data) return loadingAnswer();
  const audit = data.audit;
  const ranked = Object.entries(data.metrics).sort((a, b) => a[1].mae - b[1].mae);
  const [bestName, best] = ranked[0];

  if (q.includes('why should i trust') || q.includes('trust this evaluation')) {
    return `
      <span class="answer-lead">Trust the protocol more than the score.</span>
      The useful evidence is that chronology is frozen, unavailable future features are rejected, every forecast is sealed before the outcome is read,
      and every model gets the same evaluation window. In this run there are <strong>${audit.leakage_violations}</strong> leakage violations and
      <strong>${audit.all_forecast_seals_valid ? 'all seals verify' : 'a seal failure'}</strong>.
      ${actions([{ label: 'Inspect seals', action: 'open-tool' }, { label: 'Full audit', action: 'open-lab' }])}
    `;
  }

  if (q.includes('cheat') || q.includes('leak') || q.includes('trust') || q.includes('look ahead')) {
    return `
      <span class="answer-lead">The replay is designed so forecasts exist before outcomes are read.</span>
      This run reports <strong>${audit.leakage_violations}</strong> leakage violations and
      <strong>${audit.all_forecast_seals_valid ? 'all forecast seals verify' : 'a forecast seal failure'}</strong>.
      Training and evaluation windows are frozen, and every model is scored under the same chronology.
      ${meta([
        ['training events', String(audit.training_events)],
        ['evaluation events', String(audit.evaluation_events)],
        ['seals', audit.all_forecast_seals_valid ? 'valid' : 'failed'],
      ])}
      ${actions([{ label: 'Inspect seals', action: 'open-tool' }, { label: 'Full audit', action: 'open-lab' }])}
    `;
  }

  if (q.includes('sealed') || q.includes('hash') || q.includes('before the outcome')) {
    return `
      <span class="answer-lead">The experiment manifest and every forecast are cryptographically sealed before scoring.</span>
      The manifest seal begins <strong>${escapeHTML(data.manifest.seal.slice(0, 16))}…</strong>.
      The forecast event view contains only features available at that time; the outcome is read only after all model forecasts for that event have been sealed.
      ${actions([{ label: 'Open seal details', action: 'open-tool' }])}
    `;
  }

  if (q.includes('which model') || q.includes('best') || q.includes('holdout')) {
    return `
      <span class="answer-lead">${titleCase(bestName)} had the lowest MAE in this frozen replay.</span>
      Its MAE was <strong>${fmt(best.mae)}</strong> and RMSE <strong>${fmt(best.rmse)}</strong>.
      This is a historical-shaped controlled evaluation, so winning this table is evidence about the protocol and model behavior—not proof of live edge.
      ${actions([{ label: 'Compare all models', action: 'open-tool' }])}
    `;
  }

  if (q.includes('not prove') || q.includes('limit') || q.includes('boundary')) {
    return `
      <span class="answer-lead">It does not prove causality, autonomous science, or live trading alpha.</span>
      Sealing and frozen chronology reduce look-ahead and researcher degrees of freedom. They cannot turn a historical replay into prospective real-world evidence.
      The next scientific step is a prediction made before an untouched future event and scored after that event occurs.
    `;
  }

  return genericAnswer('validation');
}

function loadingAnswer() {
  return '<span class="answer-lead">The world state is still loading.</span>Try again once the status at the top says Ready.';
}

function genericAnswer(context) {
  const prompts = {
    market: ['what I think is driving the market', 'why passive history is insufficient', 'what would change my mind', 'what if liquidity drops by 2σ'],
    physics: ['which hidden law I believe', 'why the laws look identical', 'what experiment distinguishes them', 'how sure I am'],
    discovery: ['what I discovered', 'why I rejected the theory family', 'what equation I invented', 'what ontology means'],
    validation: ['how leakage is prevented', 'what was sealed', 'which model did best', 'what this still does not prove'],
  };
  return `
    <span class="answer-lead">I can answer from this world’s structured experiment state.</span>
    Try asking about ${prompts[context].map((x) => `<strong>${escapeHTML(x)}</strong>`).join(', ')}.
  `;
}

function answerCustom(q) {
  const data = state.customData;

  if (!data) {
    if (q.includes('what will') || q.includes('do with my data') || q.includes('protocol')) {
      return `
        <span class="answer-lead">I keep the final 20% of complete rows untouched, then search only the earlier rows.</span>
        Features are standardized using training statistics only. I search a small symbolic language of linear terms, pairwise interactions, and squares,
        then compare the winning compact model against a mean baseline and ridge regression on the untouched holdout.
        ${actions([{ label: 'Upload CSV', action: 'open-tool' }])}
      `;
    }
    if (q.includes('kind of csv') || q.includes('requirements') || q.includes('works best')) {
      return `
        <span class="answer-lead">Use a CSV with at least 32 complete numeric rows and at least two numeric columns.</span>
        Pick one numeric target and up to eight numeric features. Row order matters because the last rows become the holdout.
        Dates or labels can stay in the file, but the current symbolic engine only models numeric columns.
        ${actions([{ label: 'Upload CSV', action: 'open-tool' }])}
      `;
    }
    if (q.includes('refuse') || q.includes('claim') || q.includes('causal')) {
      return `
        <span class="answer-lead">I will not call an observational relationship causal just because it predicts well.</span>
        A frozen holdout checks generalization inside this dataset. It does not establish intervention invariance, remove confounding,
        or prove the relationship will survive a different population or future regime.
      `;
    }
    return `
      <span class="answer-lead">Upload a numeric CSV first.</span>
      Choose a target and up to eight features. I’ll keep a holdout untouched, search for compact symbolic structure, compare baselines,
      and then you can interrogate the result here.
      ${actions([{ label: 'Upload CSV', action: 'open-tool' }])}
    `;
  }

  const model = data.symbolic_model;
  const holdout = model.holdout;
  const ridge = data.baselines.ridge;
  const mean = data.baselines.mean;
  const top = data.feature_importance.slice(0, 4);

  if (q.includes('what did') || q.includes('find') || q.includes('summary') || q.includes('model')) {
    return `
      <span class="answer-lead">The best compact holdout-tested relationship is:</span>
      <span class="code-block" style="display:block;margin:10px 0">${escapeHTML(model.program)}</span>
      On the untouched final rows it reached <strong>R² ${fmt(holdout.r2, 3)}</strong> and
      <strong>MAE ${fmt(holdout.mae, 3)}</strong>. ${escapeHTML(data.verdict)}
      ${meta([
        ['rows used', String(data.dataset.rows_used)],
        ['holdout rows', String(data.dataset.holdout_rows)],
        ['model posterior', pct(model.posterior, 1)],
      ])}
      ${actions([
        { label: 'Which features matter?', action: 'ask', question: 'Which features matter most?' },
        { label: 'Can I call this causal?', action: 'ask', question: 'Can I call this causal?' },
        { label: 'Evidence', action: 'open-lab' },
      ])}
    `;
  }

  if (q.includes('feature') || q.includes('matter') || q.includes('important')) {
    const readable = top.map((item, index) =>
      `${index + 1}. <strong>${escapeHTML(item.feature)}</strong> (holdout MAE +${fmt(item.mae_increase, 3)} when shuffled)`
    ).join('<br>');
    return `
      <span class="answer-lead">These features matter most to this model’s holdout predictions.</span>
      ${readable || 'No stable feature importance signal was available.'}
      <span class="answer-detail">This is permutation sensitivity, not causal importance.</span>
      ${actions([{ label: 'Inspect all evidence', action: 'open-lab' }])}
    `;
  }

  if (q.includes('good') || q.includes('accurate') || q.includes('holdout') || q.includes('baseline') || q.includes('trust')) {
    return `
      <span class="answer-lead">Judge it by the untouched holdout, not the training fit.</span>
      The symbolic model has <strong>MAE ${fmt(holdout.mae, 3)}</strong>, ridge has
      <strong>${fmt(ridge.mae, 3)}</strong>, and the mean baseline has <strong>${fmt(mean.mae, 3)}</strong>.
      Holdout R² is <strong>${fmt(holdout.r2, 3)}</strong>.
      ${meta([
        ['train rows', String(data.dataset.train_rows)],
        ['holdout rows', String(data.dataset.holdout_rows)],
        ['outside train range', pct(data.extrapolation_fraction, 1)],
      ])}
      ${actions([{ label: 'Evidence', action: 'open-lab' }])}
    `;
  }

  if (q.includes('equation') || q.includes('z(') || q.includes('standard')) {
    return `
      <span class="answer-lead">The equation uses standardized feature values.</span>
      <strong>z(feature)</strong> means the raw value minus that feature’s training mean, divided by its training standard deviation.
      Standardization is learned from training rows only, which keeps the symbolic search numerically stable without leaking holdout information.
      ${actions([{ label: 'Show preprocessing values', action: 'open-lab' }])}
    `;
  }

  if (q.includes('causal') || q.includes('cause') || q.includes('prove')) {
    return `
      <span class="answer-lead">No—this result is predictive, not automatically causal.</span>
      A compact equation that generalizes on held-out rows is evidence of a reproducible association inside this table.
      To argue mechanism or causality, you would need stronger identification: interventions, natural experiments, domain assumptions,
      or prospective evidence designed to separate competing explanations.
    `;
  }

  if (q.includes('weak') || q.includes('limit') || q.includes('extrapolat') || q.includes('risk')) {
    return `
      <span class="answer-lead">The main risks are distribution shift, confounding, and extrapolation.</span>
      <strong>${pct(data.extrapolation_fraction, 1)}</strong> of holdout feature cells lie outside the training min/max range.
      Rook dropped <strong>${data.dataset.rows_dropped}</strong> rows that were incomplete or non-numeric for the selected columns.
      The final slice is a real holdout inside this file, but it is still only one dataset.
      ${actions([{ label: 'Evidence', action: 'open-lab' }])}
    `;
  }

  return `
    <span class="answer-lead">Ask me about the discovered equation, holdout performance, important features, weaknesses, or whether the result is causal.</span>
    ${actions([
      { label: 'What did you find?', action: 'ask', question: 'What did you find?' },
      { label: 'Which features matter?', action: 'ask', question: 'Which features matter most?' },
      { label: 'Evidence', action: 'open-lab' },
    ])}
  `;
}

async function answerQuestion(question) {
  const q = question.trim().toLowerCase();
  if (state.context === 'market') return answerMarket(q);
  if (state.context === 'physics') return answerPhysics(q);
  if (state.context === 'discovery') return answerDiscovery(q);
  if (state.context === 'custom') return answerCustom(q);
  return answerValidation(q);
}

async function askRook(question) {
  const clean = question.trim();
  if (!clean) return;
  if (state.loading && !(state.context === 'custom' && state.customData)) {
    toast('Rook is still preparing the current world.');
    return;
  }

  const thread = ensureThread();
  if (thread.context !== state.context) thread.context = state.context;

  const userMessage = saveMessage('user', { text: clean });
  $('welcome').classList.add('hidden');
  appendMessageNode(userMessage);
  appendThinking();
  $('ask-input').value = '';
  resizeComposer();

  try {
    const html = await answerQuestion(clean);
    removeThinking();
    const reply = saveMessage('assistant', { html });
    appendMessageNode(reply);
    requestAnimationFrame(() => replyNode(reply.id)?.scrollIntoView({ behavior: 'smooth', block: 'end' }));
  } catch (error) {
    removeThinking();
    const html = `<span class="answer-lead">That request failed.</span>${escapeHTML(error.message)}`;
    const reply = saveMessage('assistant', { html });
    appendMessageNode(reply);
  }
}

function replyNode(id) {
  return document.querySelector(`[data-message-id="${CSS.escape(id)}"]`);
}

async function fetchJSON(url, label) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
  return response.json();
}

function setComposerReady(ready) {
  const input = $('ask-input');
  const send = document.querySelector('.send-button');
  input.disabled = !ready;
  if (send) send.disabled = !ready;
  $('ask-form').classList.toggle('loading', !ready);
  if (!ready) input.placeholder = 'Preparing the world…';
  else input.placeholder = CONTEXTS[state.context].placeholder;
}

async function runAnalysis() {
  if (state.loading) return;
  state.loading = true;
  const customAlreadyUsable = state.context === 'custom' && Boolean(state.customData);
  if (!customAlreadyUsable) setComposerReady(false);
  $('run-status').textContent = 'Analyzing…';
  $('runtime-status').textContent = 'Running research stack…';
  $('status-dot').classList.remove('ok');

  const seed = $('seed').value || '7';
  const target = $('target').value || 'growth_equity';

  try {
    const [strategic, physics, frontier, sealed, v0, health] = await Promise.all([
      fetchJSON(`/api/strategic?${new URLSearchParams({ seed, observations: '260' })}`, 'Market world'),
      fetchJSON(`/api/physics?${new URLSearchParams({ seed, observations: '240' })}`, 'Physics world'),
      fetchJSON(`/api/frontier?${new URLSearchParams({ seed })}`, 'Discovery suite'),
      fetchJSON(`/api/sealed?${new URLSearchParams({ seed, observations: '120' })}`, 'Validation replay'),
      fetchJSON(`/api/demo?${new URLSearchParams({ seed, target, observations: '360' })}`, 'Symbolic compiler'),
      fetchJSON('/api/health', 'Health check'),
    ]);

    Object.assign(state, { strategic, physics, frontier, sealed, v0, health });
    $('run-status').textContent = 'Ready';
    $('runtime-status').textContent = 'Research stack healthy';
    $('status-dot').classList.add('ok');
    renderLab();
    toast('Rook is ready.');
  } catch (error) {
    console.error(error);
    $('run-status').textContent = 'Run failed';
    $('runtime-status').textContent = error.message;
    toast(`Run failed: ${error.message}`);
  } finally {
    state.loading = false;
    setComposerReady(true);
  }
}

async function fetchScenario(eventKind, magnitude) {
  const seed = $('seed').value || '7';
  try {
    const data = await fetchJSON(
      `/api/scenario?${new URLSearchParams({
        seed,
        observations: '260',
        event_kind: eventKind,
        magnitude: String(magnitude),
      })}`,
      'Counterfactual'
    );
    state.scenario = data;
    return data;
  } catch (error) {
    toast(error.message);
    return null;
  }
}

function openTool() {
  const context = state.context;
  if (context === 'market') renderMarketTool();
  else if (context === 'physics') renderPhysicsTool();
  else if (context === 'discovery') renderDiscoveryTool();
  else if (context === 'custom') renderCustomTool();
  else renderValidationTool();

  openSheet('tool-sheet');
}

function renderMarketTool() {
  const data = state.strategic;
  const best = data?.active_identification?.selected_probe;
  $('tool-kicker').textContent = 'WHAT-IF LAB';
  $('tool-title').textContent = 'Stress both worlds';

  $('tool-body').innerHTML = `
    <p class="tool-intro">Choose a hypothetical naturally occurring event. Rook recomputes how the belief-driven and liquidity-driven worlds say assets should react.</p>
    <label class="field">
      <span>Event</span>
      <select id="scenario-event">
        <option value="growth">Growth</option>
        <option value="inflation">Inflation</option>
        <option value="liquidity">Liquidity</option>
        <option value="policy">Policy</option>
        <option value="sentiment">Sentiment</option>
      </select>
    </label>
    <label class="field">
      <span>Shock size</span>
      <div class="range-field">
        <input id="scenario-magnitude" type="range" min="-4" max="4" step="0.5" value="${best?.magnitude ?? -2}" />
        <output id="scenario-mag-label">${best?.magnitude >= 0 ? '+' : ''}${fmt(best?.magnitude ?? -2, 1)}σ</output>
      </div>
    </label>
    <button class="tool-primary" id="scenario-run">Run counterfactual</button>
    <div class="tool-result" id="scenario-output"></div>
  `;

  $('scenario-event').value = best?.event_kind || 'liquidity';
  $('scenario-magnitude').addEventListener('input', () => {
    const value = Number($('scenario-magnitude').value);
    $('scenario-mag-label').textContent = `${value >= 0 ? '+' : ''}${fmt(value, 1)}σ`;
  });
  $('scenario-run').addEventListener('click', runToolScenario);

  if (best) runToolScenario();
}

async function runToolScenario() {
  const button = $('scenario-run');
  const eventKind = $('scenario-event').value;
  const magnitude = Number($('scenario-magnitude').value);
  button.disabled = true;
  button.textContent = 'Simulating…';

  const data = await fetchScenario(eventKind, magnitude);
  if (data) {
    const a = data.predictions.belief_reflexive;
    const b = data.predictions.liquidity_reflexive;
    $('scenario-output').innerHTML = `
      <div class="result-summary">
        <strong>${titleCase(data.event.label)}</strong> is most diagnostic through
        <strong>${titleCase(data.most_diagnostic_asset)}</strong>. Information score: <strong>${fmt(data.information_score, 2)}</strong>.
      </div>
      ${data.asset_names.map((asset) => `
        <div class="comparison-row ${asset === data.most_diagnostic_asset ? 'highlight' : ''}">
          <div class="comparison-head"><span>${titleCase(asset)}</span><span>gap ${fmt(data.absolute_disagreement[asset], 3)}</span></div>
          <div class="comparison-values">
            <div><small>belief world</small><strong>${a[asset] >= 0 ? '+' : ''}${fmt(a[asset], 3)}</strong></div>
            <div><small>liquidity world</small><strong>${b[asset] >= 0 ? '+' : ''}${fmt(b[asset], 3)}</strong></div>
          </div>
        </div>
      `).join('')}
      <button class="tool-primary" data-tool-ask="Why is this event diagnostic?">Explain this result in chat</button>
    `;
    $('scenario-output').querySelector('[data-tool-ask]')?.addEventListener('click', (event) => {
      closeSheets();
      askRook(event.currentTarget.dataset.toolAsk);
    });
  }

  button.disabled = false;
  button.textContent = 'Run counterfactual';
}

function renderPhysicsTool() {
  const data = state.physics;
  $('tool-kicker').textContent = 'ACTIVE EXPERIMENT';
  $('tool-title').textContent = 'Expose the hidden law';

  if (!data) {
    $('tool-body').innerHTML = '<p class="tool-intro">Physics world is still loading.</p>';
    return;
  }

  const active = data.active_identification;
  const selected = active.selected_probe;
  $('tool-body').innerHTML = `
    <p class="tool-intro">Rook ranked force probes before observing the synthetic outcome. The selected probe maximizes expected information about which resistance law is true.</p>
    <div class="result-summary">
      <strong>${titleCase(selected.name)}</strong><br>
      Force +${fmt(selected.force, 2)} for ${selected.duration} steps · expected information ${fmt(active.expected_information_gain, 3)}
    </div>
    <div class="tool-result">
      ${active.ranked_probes.slice(0, 5).map((probe, index) => `
        <div class="comparison-row ${index === 0 ? 'highlight' : ''}">
          <div class="comparison-head"><span>${index + 1}. ${titleCase(probe.name)}</span><span>IG ${fmt(probe.expected_information_gain, 3)}</span></div>
          <div class="comparison-values">
            <div><small>force</small><strong>+${fmt(probe.force, 2)}</strong></div>
            <div><small>duration</small><strong>${probe.duration} steps</strong></div>
          </div>
        </div>
      `).join('')}
      <button class="tool-primary" data-tool-ask="Why is this the best experiment?">Explain selection in chat</button>
    </div>
  `;
  $('tool-body').querySelector('[data-tool-ask]').addEventListener('click', (event) => {
    closeSheets();
    askRook(event.currentTarget.dataset.toolAsk);
  });
}

function renderDiscoveryTool() {
  const data = state.frontier;
  $('tool-kicker').textContent = 'THEORY INVENTION';
  $('tool-title').textContent = 'What Rook added';

  if (!data) {
    $('tool-body').innerHTML = '<p class="tool-intro">Discovery suite is still loading.</p>';
    return;
  }

  const open = data.theory_invention.open_world;
  const invented = data.theory_invention.invented;
  const evolution = data.ontology_evolution;

  $('tool-body').innerHTML = `
    <p class="tool-intro">The open-world layer is allowed to say “none of the above,” search residual structure, and change its own representation.</p>
    <div class="lab-grid">
      <div class="lab-metric"><span>Unknown hypothesis</span><strong>${pct(open.unknown_probability, 1)}</strong></div>
      <div class="lab-metric"><span>Holdout improvement</span><strong>${invented ? pct(invented.relative_improvement, 1) : '—'}</strong></div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">INVENTED THEORY</p>
      <div class="code-block">${invented ? escapeHTML(invented.program) : 'No replacement theory accepted.'}</div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">ONTOLOGY EVOLUTION</p>
      <div class="check-list">
        <div class="check-row"><span>Split detected</span><b class="${evolution.splits?.length ? 'pass' : 'fail'}">${evolution.splits?.length ? 'YES' : 'NO'}</b></div>
        <div class="check-row"><span>Merge detected</span><b class="${evolution.merges?.length ? 'pass' : 'fail'}">${evolution.merges?.length ? 'YES' : 'NO'}</b></div>
      </div>
    </div>
    <button class="tool-primary" data-tool-ask="What did you discover without being told?">Explain discovery in chat</button>
  `;
  $('tool-body').querySelector('[data-tool-ask]').addEventListener('click', (event) => {
    closeSheets();
    askRook(event.currentTarget.dataset.toolAsk);
  });
}


function detectDelimiter(text) {
  const firstLine = text.split(/\r?\n/).find((line) => line.trim()) || '';
  const candidates = [',', ';', '\t'];
  const counts = new Map(candidates.map((candidate) => [candidate, 0]));
  let quoted = false;

  for (let i = 0; i < firstLine.length; i += 1) {
    const char = firstLine[i];
    const next = firstLine[i + 1];
    if (char === '"' && quoted && next === '"') {
      i += 1;
      continue;
    }
    if (char === '"') {
      quoted = !quoted;
      continue;
    }
    if (!quoted && counts.has(char)) counts.set(char, counts.get(char) + 1);
  }

  return candidates.sort((a, b) => counts.get(b) - counts.get(a))[0];
}

function parseCSV(text) {
  const delimiter = detectDelimiter(text);
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === delimiter) {
      row.push(field.trim());
      field = '';
    } else if (char === '\n') {
      row.push(field.trim());
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
  }

  row.push(field.trim());
  if (row.some((value) => value !== '') || rows.length === 0) rows.push(row);

  const cleaned = rows.filter((values) => values.some((value) => value !== ''));
  if (cleaned.length < 2) throw new Error('The CSV needs a header row and data rows.');

  const columns = cleaned[0].map((value, index) => {
    const name = String(value || `column_${index + 1}`).replace(/^\uFEFF/, '').trim();
    return name || `column_${index + 1}`;
  });
  if (new Set(columns).size !== columns.length) throw new Error('CSV column names must be unique.');

  const dataRows = cleaned.slice(1).filter((values) => values.length === columns.length);
  if (dataRows.length < 32) throw new Error('Rook needs at least 32 well-formed data rows.');

  return { columns, rows: dataRows, delimiter };
}

function numericValue(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const normalized = text.includes(',') && !text.includes('.') ? text.replace(',', '.') : text;
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
}

function getNumericColumns(upload) {
  return upload.columns.filter((name, index) => {
    let numeric = 0;
    for (const row of upload.rows) {
      if (numericValue(row[index]) !== null) numeric += 1;
    }
    return numeric >= Math.max(24, Math.floor(upload.rows.length * 0.65));
  });
}

async function postJSON(url, payload, label) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = '';
    try {
      const data = await response.json();
      detail = data.detail || '';
    } catch {
      detail = '';
    }
    throw new Error(detail || `${label} returned HTTP ${response.status}`);
  }
  return response.json();
}

function renderCustomTool() {
  $('tool-kicker').textContent = 'YOUR DATA';
  $('tool-title').textContent = state.customData ? 'Analyze another CSV' : 'Bring your own world';

  $('tool-body').innerHTML = `
    <p class="tool-intro">Upload a numeric CSV. Nothing is sent until you press Analyze. Rook keeps the final 20% of complete rows untouched as a holdout.</p>
    <label class="csv-drop" id="csv-drop">
      <input id="custom-file" type="file" accept=".csv,text/csv" />
      <span class="csv-drop-icon">↑</span>
      <strong>${state.customUpload?.fileName ? escapeHTML(state.customUpload.fileName) : 'Choose a CSV'}</strong>
      <small>${state.customUpload ? `${state.customUpload.rows.length} rows · ${state.customUpload.columns.length} columns` : 'Numeric tables work best · CSV stays local until Analyze'}</small>
    </label>
    <div id="custom-setup"></div>
  `;

  const input = $('custom-file');
  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    if (!file) return;
    try {
      const parsed = parseCSV(await file.text());
      const numericColumns = getNumericColumns(parsed);
      if (numericColumns.length < 2) {
        throw new Error('I could not find at least two sufficiently numeric columns.');
      }
      state.customUpload = {
        fileName: file.name,
        columns: parsed.columns,
        rows: parsed.rows,
        numericColumns,
        target: numericColumns[numericColumns.length - 1],
        features: numericColumns.slice(0, Math.min(6, numericColumns.length - 1)),
      };
      renderCustomSetup();
    } catch (error) {
      state.customUpload = null;
      toast(error.message);
      renderCustomTool();
    }
  });

  const drop = $('csv-drop');
  drop.addEventListener('dragover', (event) => {
    event.preventDefault();
    drop.classList.add('dragging');
  });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragging'));
  drop.addEventListener('drop', async (event) => {
    event.preventDefault();
    drop.classList.remove('dragging');
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    try {
      const parsed = parseCSV(await file.text());
      const numericColumns = getNumericColumns(parsed);
      if (numericColumns.length < 2) throw new Error('I could not find at least two sufficiently numeric columns.');
      state.customUpload = {
        fileName: file.name,
        columns: parsed.columns,
        rows: parsed.rows,
        numericColumns,
        target: numericColumns[numericColumns.length - 1],
        features: numericColumns.slice(0, Math.min(6, numericColumns.length - 1)),
      };
      renderCustomTool();
      renderCustomSetup();
    } catch (error) {
      toast(error.message);
    }
  });

  renderCustomSetup();
}

function renderCustomSetup() {
  const node = $('custom-setup');
  const upload = state.customUpload;
  if (!node || !upload) return;

  const available = upload.numericColumns.filter((name) => name !== upload.target);
  upload.features = upload.features.filter((name) => available.includes(name)).slice(0, 8);
  if (!upload.features.length && available.length) upload.features = available.slice(0, Math.min(6, available.length));

  node.innerHTML = `
    <div class="custom-config">
      <label class="field">
        <span>What should Rook explain?</span>
        <select id="custom-target">
          ${upload.numericColumns.map((name) => `<option value="${escapeHTML(name)}" ${name === upload.target ? 'selected' : ''}>${escapeHTML(name)}</option>`).join('')}
        </select>
      </label>

      <div class="field">
        <span>Use these features · max 8</span>
        <div class="feature-list">
          ${available.map((name) => `
            <label class="feature-option">
              <input type="checkbox" value="${escapeHTML(name)}" ${upload.features.includes(name) ? 'checked' : ''} />
              <span>${escapeHTML(name)}</span>
            </label>
          `).join('')}
        </div>
      </div>

      <div class="holdout-note">
        <strong>Frozen holdout</strong>
        <span>Last 20% of complete rows stay unseen during symbolic search.</span>
      </div>

      <button class="tool-primary" id="custom-analyze" ${upload.features.length ? '' : 'disabled'}>Analyze ${escapeHTML(upload.fileName)}</button>
      <div class="tool-result" id="custom-status"></div>
    </div>
  `;

  $('custom-target').addEventListener('change', (event) => {
    upload.target = event.target.value;
    upload.features = upload.numericColumns
      .filter((name) => name !== upload.target)
      .slice(0, Math.min(6, upload.numericColumns.length - 1));
    renderCustomSetup();
  });

  node.querySelectorAll('.feature-option input').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      const checked = [...node.querySelectorAll('.feature-option input:checked')].map((item) => item.value);
      if (checked.length > 8) {
        checkbox.checked = false;
        toast('Choose at most 8 features.');
        return;
      }
      upload.features = checked;
      $('custom-analyze').disabled = checked.length === 0;
    });
  });

  $('custom-analyze').addEventListener('click', analyzeCustomUpload);
}

function customSummaryHTML(data) {
  return `
    <span class="answer-lead">I found a compact relationship and scored it on untouched rows.</span>
    <span class="code-block" style="display:block;margin:10px 0">${escapeHTML(data.symbolic_model.program)}</span>
    Holdout <strong>R² ${fmt(data.symbolic_model.holdout.r2, 3)}</strong> ·
    MAE <strong>${fmt(data.symbolic_model.holdout.mae, 3)}</strong>.
    ${escapeHTML(data.verdict)}
    ${actions([
      { label: 'Which features matter?', action: 'ask', question: 'Which features matter most?' },
      { label: 'Can I call this causal?', action: 'ask', question: 'Can I call this causal?' },
      { label: 'Evidence', action: 'open-lab' },
    ])}
  `;
}

async function analyzeCustomUpload() {
  const upload = state.customUpload;
  const button = $('custom-analyze');
  if (!upload || !button || !upload.features.length) return;

  button.disabled = true;
  button.textContent = 'Analyzing…';
  const status = $('custom-status');
  status.innerHTML = '<div class="result-summary">Searching compact symbolic models and preserving the holdout…</div>';

  try {
    const result = await postJSON('/api/custom/analyze', {
      columns: upload.columns,
      rows: upload.rows,
      target: upload.target,
      features: upload.features,
      holdout_fraction: 0.20,
      seed: Number($('seed').value || 7),
    }, 'Custom world');

    state.customData = result;
    state.customFileName = upload.fileName;

    const thread = ensureThread();
    thread.context = 'custom';
    thread.customAnalysis = result;
    thread.customFileName = upload.fileName;
    if (thread.title === 'New chat') thread.title = `${upload.fileName}: ${upload.target}`.slice(0, 48);
    saveThreads();

    closeSheets();
    renderContext();
    renderLab();

    const reply = saveMessage('assistant', { html: customSummaryHTML(result) });
    renderConversation();
    requestAnimationFrame(() => replyNode(reply.id)?.scrollIntoView({ behavior: 'smooth', block: 'end' }));
    toast('Custom world analyzed.');
  } catch (error) {
    status.innerHTML = `<div class="result-summary"><strong>Could not analyze this CSV.</strong><br>${escapeHTML(error.message)}</div>`;
    button.disabled = false;
    button.textContent = `Analyze ${upload.fileName}`;
  }
}

function renderValidationTool() {
  const data = state.sealed;
  $('tool-kicker').textContent = 'SEALED REPLAY';
  $('tool-title').textContent = 'Inspect experiment integrity';

  if (!data) {
    $('tool-body').innerHTML = '<p class="tool-intro">Validation replay is still loading.</p>';
    return;
  }

  const ranked = Object.entries(data.metrics).sort((a, b) => a[1].mae - b[1].mae);
  $('tool-body').innerHTML = `
    <p class="tool-intro">Every model is evaluated on the same frozen chronology. Forecasts are sealed before the matching outcomes are read.</p>
    <div class="lab-grid">
      <div class="lab-metric"><span>Leakage violations</span><strong>${data.audit.leakage_violations}</strong></div>
      <div class="lab-metric"><span>Forecast seals</span><strong>${data.audit.all_forecast_seals_valid ? 'Valid' : 'Failed'}</strong></div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">FROZEN HOLDOUT</p>
      <div class="check-list">
        ${ranked.map(([name, row], index) => `
          <div class="check-row"><span>${index + 1}. ${titleCase(name)}</span><b class="${index === 0 ? 'pass' : ''}">MAE ${fmt(row.mae)}</b></div>
        `).join('')}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">MANIFEST</p>
      <div class="code-block">${escapeHTML(data.manifest.seal)}</div>
    </div>
    <button class="tool-primary" data-tool-ask="How do I know you did not cheat?">Explain validation in chat</button>
  `;
  $('tool-body').querySelector('[data-tool-ask]').addEventListener('click', (event) => {
    closeSheets();
    askRook(event.currentTarget.dataset.toolAsk);
  });
}

function renderLab() {
  const body = $('lab-body');
  if (!body) return;

  if (state.context === 'market') body.innerHTML = marketLabHTML();
  else if (state.context === 'physics') body.innerHTML = physicsLabHTML();
  else if (state.context === 'discovery') body.innerHTML = discoveryLabHTML();
  else if (state.context === 'custom') body.innerHTML = customLabHTML();
  else body.innerHTML = validationLabHTML();
}

function metricHTML(label, value) {
  return `<div class="lab-metric"><span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong></div>`;
}

function marketLabHTML() {
  const data = state.strategic;
  if (!data) return '<p class="tool-intro">Market world is loading.</p>';
  const active = data.active_identification;
  const bench = data.identification_benchmark;
  return `
    <div class="lab-section">
      <p class="eyebrow">POSTERIOR</p><h3>Current hidden-world belief</h3>
      <div class="lab-grid">
        ${metricHTML('Belief reflexive', pct(active.posterior.belief_reflexive ?? 0, 1))}
        ${metricHTML('Liquidity reflexive', pct(active.posterior.liquidity_reflexive ?? 0, 1))}
        ${metricHTML('Path correlation', pct(data.observational_equivalence.mean_return_correlation, 3))}
        ${metricHTML('Information score', fmt(active.information_score, 3))}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">ACTIVE VS RANDOM</p><h3>Does experiment choice help?</h3>
      <div class="lab-grid">
        ${metricHTML('Active accuracy', pct(bench.active_accuracy, 1))}
        ${metricHTML('Random accuracy', pct(bench.random_accuracy, 1))}
        ${metricHTML('Active true posterior', pct(bench.active_true_posterior, 1))}
        ${metricHTML('Random true posterior', pct(bench.random_true_posterior, 1))}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">SCIENTIFIC BOUNDARY</p>
      <div class="result-summary">${escapeHTML(data.scientific_boundary)}</div>
    </div>
  `;
}

function physicsLabHTML() {
  const data = state.physics;
  if (!data) return '<p class="tool-intro">Physics world is loading.</p>';
  const active = data.active_identification;
  const bench = data.identification_benchmark;
  return `
    <div class="lab-section">
      <p class="eyebrow">CANDIDATE LAWS</p><h3>Controlled hidden physics</h3>
      <div class="code-block">${escapeHTML(data.mechanisms.linear_resistance.equation)}<br>${escapeHTML(data.mechanisms.curved_resistance.equation)}</div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">POSTERIOR</p>
      <div class="lab-grid">
        ${metricHTML('Linear', pct(active.posterior.linear_resistance ?? 0, 1))}
        ${metricHTML('Curved', pct(active.posterior.curved_resistance ?? 0, 1))}
        ${metricHTML('Passive correlation', pct(data.passive_equivalence.velocity_correlation, 3))}
        ${metricHTML('Probe info.', fmt(active.expected_information_gain, 3))}
        ${metricHTML('Active accuracy', pct(bench.active_accuracy, 1))}
        ${metricHTML('Random accuracy', pct(bench.random_accuracy, 1))}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">PREREGISTRATION</p>
      <div class="code-block">${escapeHTML(data.preregistration.seal)}</div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">SCIENTIFIC BOUNDARY</p>
      <div class="result-summary">${escapeHTML(data.scientific_boundary)}</div>
    </div>
  `;
}

function discoveryLabHTML() {
  const data = state.frontier;
  if (!data) return '<p class="tool-intro">Discovery suite is loading.</p>';
  return `
    <div class="lab-section">
      <p class="eyebrow">FALSIFICATION GATES</p><h3>${Object.values(data.checks).filter(Boolean).length}/${Object.keys(data.checks).length} passing</h3>
      <div class="check-list">
        ${Object.entries(data.checks).map(([name, ok]) => `
          <div class="check-row"><span>${escapeHTML(pretty(name))}</span><b class="${ok ? 'pass' : 'fail'}">${ok ? 'PASS' : 'FAIL'}</b></div>
        `).join('')}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">LATENT LAW DISCOVERY</p>
      <div class="lab-grid">
        ${metricHTML('Mean validation R²', fmt(data.latent_laws.mean_validation_r2, 5))}
        ${metricHTML('Natural regime ARI', fmt(data.natural_experiments.adjusted_rand_index, 3))}
        ${metricHTML('Selected dims', data.cross_domain_summary.selected_dims.join(' / '))}
        ${metricHTML('Min uplift vs PCA', pct(data.cross_domain_summary.minimum_improvement_over_pca, 1))}
      </div>
      <div style="height:8px"></div>
      ${data.latent_laws.laws.map((law) => `<div class="code-block" style="margin-top:6px">${escapeHTML(law.target)} · ${escapeHTML(law.program)}</div>`).join('')}
    </div>
    <div class="lab-section">
      <p class="eyebrow">SCIENTIFIC BOUNDARY</p>
      <div class="result-summary">${escapeHTML(data.scientific_boundary)}</div>
    </div>
  `;
}


function customLabHTML() {
  const data = state.customData;
  if (!data) {
    return `
      <div class="lab-section">
        <p class="eyebrow">YOUR DATA</p>
        <h3>No CSV analyzed yet</h3>
        <div class="result-summary">Upload a numeric CSV from the + tool, choose a target and features, then analyze it.</div>
      </div>
    `;
  }

  const model = data.symbolic_model;
  return `
    <div class="lab-section">
      <p class="eyebrow">DATASET</p><h3>${escapeHTML(state.customFileName || 'Uploaded CSV')}</h3>
      <div class="lab-grid">
        ${metricHTML('Rows used', String(data.dataset.rows_used))}
        ${metricHTML('Rows dropped', String(data.dataset.rows_dropped))}
        ${metricHTML('Target', data.dataset.target)}
        ${metricHTML('Holdout', `${data.dataset.holdout_rows} rows`)}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">DISCOVERED MODEL</p>
      <div class="code-block">${escapeHTML(model.program)}</div>
      <div style="height:8px"></div>
      <div class="lab-grid">
        ${metricHTML('Holdout R²', fmt(model.holdout.r2, 4))}
        ${metricHTML('Holdout MAE', fmt(model.holdout.mae, 4))}
        ${metricHTML('Ridge MAE', fmt(data.baselines.ridge.mae, 4))}
        ${metricHTML('Mean MAE', fmt(data.baselines.mean.mae, 4))}
        ${metricHTML('Model posterior', pct(model.posterior, 1))}
        ${metricHTML('Extrapolation', pct(data.extrapolation_fraction, 1))}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">PREDICTIVE FEATURE SENSITIVITY</p>
      <div class="check-list">
        ${data.feature_importance.map((item, index) => `
          <div class="check-row">
            <span>${index + 1}. ${escapeHTML(item.feature)}</span>
            <b class="${item.mae_increase > 0 ? 'pass' : ''}">MAE +${fmt(item.mae_increase, 4)}</b>
          </div>
        `).join('')}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">TOP SYMBOLIC CANDIDATES</p>
      ${model.top_models.map((item) => `
        <div class="code-block" style="margin-top:6px">#${item.rank} · p=${pct(item.posterior, 1)} · ${escapeHTML(item.program)}</div>
      `).join('')}
    </div>
    <div class="lab-section">
      <p class="eyebrow">TRAINING STANDARDIZATION</p>
      <div class="check-list">
        ${data.dataset.features.map((name) => `
          <div class="check-row">
            <span>${escapeHTML(name)}</span>
            <b>μ ${fmt(data.preprocessing.feature_means[name], 3)} · σ ${fmt(data.preprocessing.feature_scales[name], 3)}</b>
          </div>
        `).join('')}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">SCIENTIFIC BOUNDARY</p>
      <div class="result-summary">${escapeHTML(data.scientific_boundary)}</div>
    </div>
  `;
}

function validationLabHTML() {
  const data = state.sealed;
  if (!data) return '<p class="tool-intro">Validation replay is loading.</p>';
  const ranked = Object.entries(data.metrics).sort((a, b) => a[1].mae - b[1].mae);
  return `
    <div class="lab-section">
      <p class="eyebrow">AUDIT</p><h3>Chronology and seal integrity</h3>
      <div class="lab-grid">
        ${metricHTML('Leakage violations', String(data.audit.leakage_violations))}
        ${metricHTML('Forecast seals', data.audit.all_forecast_seals_valid ? 'All valid' : 'Failure')}
        ${metricHTML('Training events', String(data.audit.training_events))}
        ${metricHTML('Evaluation events', String(data.audit.evaluation_events))}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">MODEL COMPARISON</p>
      <div class="check-list">
        ${ranked.map(([name, row], index) => `
          <div class="check-row"><span>${index + 1}. ${titleCase(name)}</span><b class="${index === 0 ? 'pass' : ''}">MAE ${fmt(row.mae)} · RMSE ${fmt(row.rmse)}</b></div>
        `).join('')}
      </div>
    </div>
    <div class="lab-section">
      <p class="eyebrow">SCIENTIFIC BOUNDARY</p>
      <div class="result-summary">${escapeHTML(data.scientific_boundary)}</div>
    </div>
  `;
}

function openSheet(id) {
  closePopovers();
  renderLab();
  $('scrim').classList.add('open');
  $(id).classList.add('open');
  $(id).setAttribute('aria-hidden', 'false');
}

function closeSheets() {
  $('scrim').classList.remove('open');
  document.querySelectorAll('.sheet.open').forEach((sheet) => {
    sheet.classList.remove('open');
    sheet.setAttribute('aria-hidden', 'true');
  });
}

function closePopovers() {
  document.querySelectorAll('.popover.open').forEach((node) => node.classList.remove('open'));
  $('world-switcher').setAttribute('aria-expanded', 'false');
}

function openSidebar() {
  $('sidebar').classList.add('open');
  $('scrim').classList.add('open');
}

function closeSidebar() {
  $('sidebar').classList.remove('open');
  if (!document.querySelector('.sheet.open')) $('scrim').classList.remove('open');
}

function resizeComposer() {
  const input = $('ask-input');
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 170)}px`;
}

function loadThread(id) {
  const thread = state.threads.find((item) => item.id === id);
  if (!thread) return;
  state.activeThreadId = id;
  state.context = thread.context;
  if (thread.context === 'custom') {
    state.customData = thread.customAnalysis || null;
    state.customFileName = thread.customFileName || null;
  }
  renderContext();
  renderConversation();
  renderRecent();
  if (window.innerWidth <= 900) closeSidebar();
}

function bindEvents() {
  $('ask-form').addEventListener('submit', (event) => {
    event.preventDefault();
    askRook($('ask-input').value);
  });

  $('ask-input').addEventListener('input', resizeComposer);
  $('ask-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      askRook($('ask-input').value);
    }
  });

  $('starter-grid').addEventListener('click', (event) => {
    const card = event.target.closest('[data-starter]');
    if (!card) return;
    if (card.dataset.openCustom === 'true') openTool();
    else askRook(card.dataset.starter);
  });

  $('conversation').addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'ask') askRook(button.dataset.question || '');
    if (button.dataset.action === 'open-tool') openTool();
    if (button.dataset.action === 'open-lab') openSheet('lab-sheet');
  });

  $('new-chat').addEventListener('click', newChat);
  $('new-chat-top').addEventListener('click', newChat);
  $('brand-home').addEventListener('click', newChat);

  document.querySelectorAll('.context-item').forEach((button) => {
    button.addEventListener('click', () => switchContext(button.dataset.context));
  });

  $('world-switcher').addEventListener('click', (event) => {
    event.stopPropagation();
    const menu = $('world-menu');
    const open = !menu.classList.contains('open');
    closePopovers();
    menu.classList.toggle('open', open);
    $('world-switcher').setAttribute('aria-expanded', String(open));
  });

  $('world-menu').addEventListener('click', (event) => {
    const button = event.target.closest('[data-context]');
    if (button) switchContext(button.dataset.context);
  });

  $('more-button').addEventListener('click', (event) => {
    event.stopPropagation();
    const menu = $('settings-menu');
    const open = !menu.classList.contains('open');
    closePopovers();
    menu.classList.toggle('open', open);
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.popover') && !event.target.closest('#world-switcher') && !event.target.closest('#more-button')) {
      closePopovers();
    }
  });

  $('rerun-analysis').addEventListener('click', async () => {
    closePopovers();
    const thread = activeThread();
    const hadConversation = Boolean(thread?.messages?.length);
    await runAnalysis();
    if (hadConversation && state.health?.status === 'ok') {
      createThread(state.context);
      toast('World recomputed. Started a fresh chat so old answers are not mixed with the new run.');
    }
  });

  $('recent-list').addEventListener('click', (event) => {
    const button = event.target.closest('[data-thread]');
    if (button) loadThread(button.dataset.thread);
  });

  $('clear-history').addEventListener('click', () => {
    state.threads = [];
    state.activeThreadId = null;
    saveThreads();
    createThread(state.context);
    toast('Local conversation history cleared.');
  });

  $('quick-why').addEventListener('click', () => {
    const question = {
      market: 'Why do you believe that?',
      physics: 'Why is that the best explanation?',
      discovery: 'Why is this a meaningful discovery?',
      validation: 'Why should I trust this evaluation?',
      custom: state.customData ? 'Why should I trust this holdout result?' : 'What will Rook do with my data?',
    }[state.context];
    askRook(question);
  });
  $('quick-test').addEventListener('click', openTool);
  $('tool-button').addEventListener('click', openTool);
  $('open-lab').addEventListener('click', () => openSheet('lab-sheet'));

  $('open-help').addEventListener('click', () => $('help-dialog').showModal());
  $('learn-link').addEventListener('click', () => $('help-dialog').showModal());

  document.querySelectorAll('[data-close-sheet]').forEach((button) => {
    button.addEventListener('click', closeSheets);
  });

  $('scrim').addEventListener('click', () => {
    closeSheets();
    closeSidebar();
  });

  $('menu-button').addEventListener('click', openSidebar);
  $('sidebar-close').addEventListener('click', closeSidebar);

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeSheets();
      closeSidebar();
      closePopovers();
    }
  });
}

async function init() {
  loadThreads();
  if (state.threads.length) {
    state.activeThreadId = state.threads[0].id;
    state.context = state.threads[0].context || 'market';
    if (state.context === 'custom') {
      state.customData = state.threads[0].customAnalysis || null;
      state.customFileName = state.threads[0].customFileName || null;
    }
  } else {
    createThread('market');
  }

  renderContext();
  renderRecent();
  renderConversation();
  bindEvents();
  setComposerReady(state.context === 'custom' && Boolean(state.customData));
  await runAnalysis();
  $('ask-input').focus();
}

init();
