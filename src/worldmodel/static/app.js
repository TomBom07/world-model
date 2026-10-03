const $ = (id) => document.getElementById(id);
const fmt = (n, d = 3) => Number(n).toFixed(d);
const pct = (n, d = 0) => `${(Number(n) * 100).toFixed(d)}%`;
const pretty = (value) => String(value ?? '').replaceAll('_', ' ');
const titleCase = (value) => pretty(value).replace(/\b\w/g, (m) => m.toUpperCase());

const state = {
  view: 'home',
  strategic: null,
  physics: null,
  frontier: null,
  sealed: null,
  v0: null,
  health: null,
};

const viewMeta = {
  home: ['OVERVIEW', 'Understand the world, not just the output.'],
  market: ['MARKET WORLD', 'Competing explanations for the same visible history.'],
  physics: ['PHYSICS WORLD', 'Find the intervention that exposes a hidden law.'],
  discoveries: ['DISCOVERIES', 'What Rook inferred, rejected, and invented.'],
  validation: ['VALIDATION', 'Make the research hard to fake.'],
  advanced: ['LAB DETAILS', 'Inspect the machinery and benchmark evidence.'],
};

function toast(message) {
  const node = $('toast');
  node.textContent = message;
  node.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove('show'), 2600);
}

function go(view, focus = null) {
  if (!viewMeta[view]) return;
  state.view = view;

  document.querySelectorAll('.view').forEach((node) => {
    node.classList.toggle('active', node.id === `view-${view}`);
  });
  document.querySelectorAll('.nav-item[data-view]').forEach((node) => {
    node.classList.toggle('active', node.dataset.view === view);
  });

  $('view-label').textContent = viewMeta[view][0];
  $('page-title').textContent = viewMeta[view][1];
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (focus === 'experiment' && view === 'market') {
    setTimeout(() => $('market-experiment')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 260);
  }
}

function linePoints(seriesA, seriesB, width = 760, height = 260) {
  const all = [...seriesA, ...seriesB];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = Math.max(max - min, 1e-9);
  const n = Math.max(seriesA.length, seriesB.length);

  const convert = (values) => values.map((value, index) => {
    const x = (index / Math.max(n - 1, 1)) * width;
    const y = height - ((value - min) / span) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return { a: convert(seriesA), b: convert(seriesB) };
}

function renderTwoLineChart(id, a, b) {
  const points = linePoints(a, b);
  $(id).innerHTML = `
    <line x1="0" y1="65" x2="760" y2="65" class="chart-grid"/>
    <line x1="0" y1="130" x2="760" y2="130" class="chart-grid"/>
    <line x1="0" y1="195" x2="760" y2="195" class="chart-grid"/>
    <polyline points="${points.a}" class="chart-line a"/>
    <polyline points="${points.b}" class="chart-line b"/>
  `;
}

function posteriorHTML(posterior) {
  return Object.entries(posterior)
    .sort((a, b) => b[1] - a[1])
    .map(([name, mass]) => `
      <div class="posterior-item">
        <div class="posterior-top">
          <span>${titleCase(name)}</span>
          <strong>${pct(mass, 1)}</strong>
        </div>
        <div class="posterior-track"><i style="width:${Math.max(1, mass * 100)}%"></i></div>
      </div>
    `).join('');
}

function techItem(label, value) {
  return `<div class="tech-item"><span>${label}</span><strong>${value}</strong></div>`;
}

function auditRow(label, value) {
  return `<div class="audit-row"><span>${label}</span><strong>${value}</strong></div>`;
}

function whyItem(index, copy) {
  return `<div class="why-item"><span>${index}</span><div>${copy}</div></div>`;
}

function renderHome() {
  const s = state.strategic;
  const f = state.frontier;
  if (!s || !f) return;

  const active = s.active_identification;
  const truth = s.experiment.true_mechanism;
  const predicted = active.predicted_mechanism;
  const confidence = active.posterior[predicted] ?? 0;
  const probe = active.selected_probe;
  const invented = f.theory_invention?.invented;
  const unknown = f.theory_invention?.open_world?.unknown_probability ?? 0;

  $('hero-status').textContent = f.all_checks_pass ? 'Research checks passing' : 'Research check failure';
  $('home-world').textContent = titleCase(predicted);
  $('home-world-copy').textContent = predicted === truth
    ? 'After the diagnostic reaction, Rook assigned the most probability to the hidden world that actually generated this controlled run.'
    : 'Rook still has uncertainty about which hidden mechanism generated this run.';
  $('home-world-confidence').textContent = pct(confidence, 1);
  $('home-world-bar').style.width = `${confidence * 100}%`;

  $('home-test').textContent = `${titleCase(probe.event_kind)} ${probe.magnitude >= 0 ? '+' : ''}${fmt(probe.magnitude, 1)}σ`;
  $('home-test-copy').textContent = 'This is the candidate event where the competing market worlds predict the most different reaction fingerprints.';

  if (invented?.accepted) {
    $('home-theory').textContent = 'Current theory family rejected';
    $('home-theory-copy').textContent =
      `Rook put ${pct(unknown, 0)} probability on “none of the above,” then found a new symbolic structure that improved held-out fit by ${pct(invented.relative_improvement, 1)}.`;
  } else {
    $('home-theory').textContent = 'No replacement theory accepted';
    $('home-theory-copy').textContent = 'The open-world test did not accept a new symbolic theory in this run.';
  }
}

function renderMarket() {
  const data = state.strategic;
  if (!data) return;

  const active = data.active_identification;
  const eq = data.observational_equivalence;
  const bench = data.identification_benchmark;
  const truth = data.experiment.true_mechanism;
  const predicted = active.predicted_mechanism;
  const predictedMass = active.posterior[predicted] ?? 0;
  const trueMass = active.posterior[truth] ?? 0;
  const entropyRemoved = (active.entropy_before - active.entropy_after) / Math.max(active.entropy_before, 1e-9);
  const probe = active.selected_probe;

  $('market-verdict').textContent = titleCase(predicted);
  $('market-verdict-sub').textContent = `${pct(predictedMass, 1)} posterior after one diagnostic reaction`;
  $('market-correlation').textContent = `${pct(eq.mean_return_correlation, 2)} path correlation`;
  renderTwoLineChart('market-chart', data.path_preview.belief_reflexive, data.path_preview.liquidity_reflexive);

  $('market-posterior').innerHTML = posteriorHTML(active.posterior);
  $('market-explanation').innerHTML =
    `<strong>Plain English:</strong> ordinary price history barely tells these worlds apart. Rook therefore waits for an event where belief feedback and liquidity constraints predict materially different cross-asset reactions.`;

  $('market-info-score').textContent = `information ${fmt(active.information_score, 2)}`;
  $('market-probe-name').textContent =
    `${titleCase(probe.event_kind)} ${probe.magnitude >= 0 ? '+' : ''}${fmt(probe.magnitude, 1)}σ`;
  $('market-probe-copy').textContent =
    'This is not “the event most likely to move prices.” It is the event most useful for telling the competing explanations apart.';

  $('market-why-test').innerHTML = [
    whyItem('A', 'Both theories already fit the ordinary history, so more ordinary observations have low information value.'),
    whyItem('B', `Under this event the candidate worlds produce the largest expected disagreement score (${fmt(active.information_score, 2)}).`),
    whyItem('C', 'After observing the reaction, Rook updates the probability of each hidden mechanism rather than simply refitting one model.'),
  ].join('');

  $('market-true-posterior').textContent = pct(trueMass, 1);
  $('market-entropy').textContent = pct(entropyRemoved, 1);
  $('market-active-edge').textContent =
    `+${pct(bench.active_true_posterior - bench.random_true_posterior, 1)}`;

  const truthAblation = data.belief_ablation.find((row) => row.mechanism === truth) || data.belief_ablation[0];
  $('market-tech-grid').innerHTML = [
    techItem('Hidden truth', titleCase(truth)),
    techItem('Inferred mechanism', titleCase(predicted)),
    techItem('Mean path correlation', pct(eq.mean_return_correlation, 3)),
    techItem('Active identification accuracy', pct(bench.active_accuracy, 1)),
    techItem('Random-event accuracy', pct(bench.random_accuracy, 1)),
    techItem('Second-order belief uplift', pct(truthAblation.relative_improvement, 1)),
    ...Object.entries(data.hidden_mechanics).flatMap(([name, row]) => [
      techItem(`${titleCase(name)} leverage`, `${fmt(row.mean_leverage, 2)}×`),
      techItem(`${titleCase(name)} margin calls`, row.margin_calls),
    ]),
  ].join('');
}

function renderPhysics() {
  const data = state.physics;
  if (!data) return;

  const active = data.active_identification;
  const eq = data.passive_equivalence;
  const bench = data.identification_benchmark;
  const truth = data.experiment.true_mechanism;
  const predicted = active.predicted_mechanism;
  const mass = active.posterior[predicted] ?? 0;
  const probe = active.selected_probe;

  $('physics-verdict').textContent = titleCase(predicted);
  $('physics-verdict-sub').textContent = `${pct(mass, 1)} posterior after the selected force pulse`;
  $('physics-correlation').textContent = `${pct(eq.velocity_correlation, 3)} correlated`;
  renderTwoLineChart('physics-chart', data.path_preview.linear_resistance, data.path_preview.curved_resistance);
  $('physics-posterior').innerHTML = posteriorHTML(active.posterior);
  $('physics-explanation').innerHTML =
    '<strong>Why passive data fails:</strong> the two drag laws are constructed to have the same value and slope at the normal operating velocity. They only separate when the system is pushed away from that tangent point.';

  $('physics-info-score').textContent = `information ${fmt(active.expected_information_gain, 3)}`;
  $('physics-probe-name').textContent =
    `${titleCase(probe.name)} · force ${probe.force >= 0 ? '+' : ''}${fmt(probe.force, 2)} × ${probe.duration} steps`;
  $('physics-probe-copy').textContent =
    'Rook chose this intervention before seeing the synthetic outcome, then used the observed reaction to update its posterior over the two laws.';

  $('physics-why-test').innerHTML = [
    whyItem('A', 'Near normal operation, linear and curved drag look almost identical.'),
    whyItem('B', 'The selected pulse moves velocity into a region where curvature becomes observable.'),
    whyItem('C', `Across the benchmark, active probes put ${pct(bench.active_true_posterior, 1)} posterior mass on the true law on average versus ${pct(bench.random_true_posterior, 1)} for random probes.`),
  ].join('');

  $('physics-tech-grid').innerHTML = [
    techItem('Hidden truth', titleCase(truth)),
    techItem('Inferred law', titleCase(predicted)),
    techItem('Linear law', data.mechanisms.linear_resistance.equation),
    techItem('Curved law', data.mechanisms.curved_resistance.equation),
    techItem('Tangent velocity', fmt(data.mechanisms.tangent_at_velocity, 3)),
    techItem('Preregistration seal', `${data.preregistration.seal.slice(0, 18)}…`),
    techItem('Seal verifies', data.preregistration.verified ? 'yes' : 'no'),
    techItem('Active identification accuracy', pct(bench.active_accuracy, 1)),
  ].join('');
}

function renderDiscoveries() {
  const data = state.frontier;
  if (!data) return;

  const checks = Object.entries(data.checks);
  const passed = checks.filter(([, ok]) => ok).length;
  const total = checks.length;
  const domains = data.cross_domain_ontology;
  const natural = data.natural_experiments;
  const openWorld = data.theory_invention?.open_world;
  const invented = data.theory_invention?.invented;
  const evolution = data.ontology_evolution;

  $('frontier-score').textContent = `${passed}/${total} gates`;
  $('frontier-score-sub').textContent = data.all_checks_pass ? 'all controlled falsification checks passed' : 'one or more checks failed';

  const domainCopy = Object.entries(domains)
    .map(([name, row]) => `${titleCase(name)} ${row.selected_dim}D / R² ${fmt(row.latent_recovery_r2, 2)}`)
    .join(' · ');
  $('latent-result').textContent =
    `Rook independently selected two intervention-relevant latent coordinates in every tested domain. ${domainCopy}.`;

  $('regime-result').textContent =
    `Recovered ${natural.cluster_count} hidden environments with ARI ${fmt(natural.adjusted_rand_index, 3)} (${fmt(natural.silhouette, 3)} silhouette).`;

  if (invented?.accepted) {
    $('theory-result').textContent =
      `“None of the above” reached ${pct(openWorld.unknown_probability, 0)} probability. The invented theory then cut held-out error by ${pct(invented.relative_improvement, 1)}.`;
    $('invented-equation').textContent = invented.program;
  } else {
    $('theory-result').textContent = 'The current run did not accept a replacement theory.';
    $('invented-equation').textContent = 'No invented theory accepted.';
  }

  const split = evolution.splits?.[0];
  const merge = evolution.merges?.[0];
  $('evolution-result').textContent =
    `${split ? `Split signal on latent dimension ${split.dimension} (variance reduction ${pct(split.variance_reduction, 1)})` : 'No split'} · ${merge ? `merge signal between dimensions ${merge.left} and ${merge.right} (correlation ${fmt(merge.correlation, 4)})` : 'no merge'}.`;

  $('frontier-checks').innerHTML = checks.map(([name, ok]) => `
    <div class="check-item">
      <span>${pretty(name)}</span>
      <b class="${ok ? 'pass' : 'fail'}">${ok ? 'PASS' : 'FAIL'}</b>
    </div>
  `).join('');
}

function renderValidation() {
  const data = state.sealed;
  if (!data) return;

  const audit = data.audit;
  const ranked = Object.entries(data.metrics).sort((a, b) => a[1].mae - b[1].mae);
  const valid = audit.leakage_violations === 0 && audit.all_forecast_seals_valid;

  $('validation-verdict').textContent = valid ? 'Verified' : 'Invalid';
  $('validation-verdict-sub').textContent = valid
    ? 'no leakage violations; all forecast seals verify'
    : 'integrity checks failed';

  $('leakage-answer').textContent = audit.leakage_violations === 0
    ? 'No future leakage detected.'
    : `${audit.leakage_violations} leakage violations.`;

  $('audit-list').innerHTML = [
    auditRow('Training events', audit.training_events),
    auditRow('Evaluation events', audit.evaluation_events),
    auditRow('Last training event', String(audit.last_training_event)),
    auditRow('First evaluation event', String(audit.first_evaluation_event)),
    auditRow('Forecast seals', audit.all_forecast_seals_valid ? 'all valid' : 'failure'),
    auditRow('Manifest', `${data.manifest.seal.slice(0, 16)}…`),
  ].join('');

  $('validation-table').innerHTML = ranked.map(([name, row]) => `
    <tr>
      <td>${titleCase(name)}</td>
      <td>${fmt(row.mae)}</td>
      <td>${pct(row.directional_accuracy, 1)}</td>
      <td>${pct(row.interval_coverage_80, 1)}</td>
    </tr>
  `).join('');

  $('validation-boundary').textContent = data.scientific_boundary;
}

function renderAdvanced() {
  const f = state.frontier;
  const p = state.physics;
  const s = state.sealed;
  const v0 = state.v0;
  if (!f || !p || !s || !v0) return;

  $('diag-api').textContent = state.health?.status === 'ok' ? 'online' : 'unknown';
  $('diag-api').className = state.health?.status === 'ok' ? 'ok' : '';
  $('diag-v4').textContent = f.all_checks_pass ? 'all gates pass' : 'failure';
  $('diag-v4').className = f.all_checks_pass ? 'ok' : '';
  $('diag-physics').textContent = p.active_identification.correct ? 'law identified' : 'uncertain';
  $('diag-physics').className = p.active_identification.correct ? 'ok' : '';
  $('diag-seals').textContent = s.audit.all_forecast_seals_valid ? 'verified' : 'failure';
  $('diag-seals').className = s.audit.all_forecast_seals_valid ? 'ok' : '';

  $('advanced-domains').innerHTML = Object.entries(f.cross_domain_ontology).map(([name, row]) =>
    techItem(titleCase(name), `${row.selected_dim}D · recovery R² ${fmt(row.latent_recovery_r2, 3)} · +${pct(row.improvement_over_pca, 1)} vs PCA`)
  ).join('');

  $('advanced-laws').innerHTML = f.latent_laws.laws.map((law) => `
    <div class="code-row">
      <strong>${law.target}</strong><br>
      ${law.program}<br>
      <span style="color:#777f8b">validation R² ${fmt(law.validation_r2, 5)} · complexity ${law.complexity}</span>
    </div>
  `).join('');

  $('advanced-program').textContent = v0.post_regime.program;
  $('advanced-compiler').innerHTML = [
    auditRow('Term recovery', pct(v0.post_regime.term_recovery_jaccard, 1)),
    auditRow('Held-out MAE', fmt(v0.post_regime.mae)),
    auditRow('True break', v0.experiment.true_switch_index),
    auditRow('Detected break', v0.experiment.detected_switch_index ?? 'miss'),
    auditRow('Model consensus', pct(v0.prediction_invariant.consensus, 1)),
  ].join('');

  $('advanced-objective').innerHTML = [
    auditRow('Compact falsifiable score', fmt(f.unified_objective.compact_falsifiable_score, 4)),
    auditRow('Brittle fit score', fmt(f.unified_objective.brittle_fit_score, 4)),
    auditRow('Preferred', f.unified_objective.prefers_compact_falsifiable ? 'compact falsifiable theory' : 'brittle fit'),
    auditRow('Prospective seal', f.prospective_falsification.seal_valid ? 'valid' : 'invalid'),
    auditRow('Prospective MAE', fmt(f.prospective_falsification.score.mae, 4)),
  ].join('');
}

function renderAll() {
  renderHome();
  renderMarket();
  renderPhysics();
  renderDiscoveries();
  renderValidation();
  renderAdvanced();

  const allGood = state.frontier?.all_checks_pass && state.physics?.active_identification?.correct;
  $('engine-label').textContent = allGood ? 'Rook ready' : 'Check run';
  $('engine-sub').textContent = allGood ? 'controlled research stack healthy' : 'one or more checks need attention';
}

async function fetchJSON(url, label) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
  return response.json();
}

async function run() {
  const button = $('run');
  button.disabled = true;
  button.querySelector('span:first-child').textContent = 'Analyzing…';
  $('engine-label').textContent = 'Rook thinking';
  $('engine-sub').textContent = 'running competing worlds';

  const seed = $('seed').value || '7';
  const target = $('target').value || 'growth_equity';

  try {
    const [strategic, physics, frontier, sealed, v0, health] = await Promise.all([
      fetchJSON(`/api/strategic?${new URLSearchParams({ seed, observations: '260' })}`, 'Strategic world'),
      fetchJSON(`/api/physics?${new URLSearchParams({ seed, observations: '240' })}`, 'Physics world'),
      fetchJSON(`/api/frontier?${new URLSearchParams({ seed })}`, 'Frontier suite'),
      fetchJSON(`/api/sealed?${new URLSearchParams({ seed, observations: '120' })}`, 'Sealed replay'),
      fetchJSON(`/api/demo?${new URLSearchParams({ seed, target, observations: '360' })}`, 'Mechanism compiler'),
      fetchJSON('/api/health', 'Health check'),
    ]);

    Object.assign(state, { strategic, physics, frontier, sealed, v0, health });
    renderAll();
    toast('Analysis complete — start with the Overview.');
  } catch (error) {
    console.error(error);
    $('engine-label').textContent = 'Run failed';
    $('engine-sub').textContent = error.message;
    toast(`Analysis failed: ${error.message}`);
  } finally {
    button.disabled = false;
    button.querySelector('span:first-child').textContent = 'Run analysis';
  }
}

document.querySelectorAll('.nav-item[data-view]').forEach((button) => {
  button.addEventListener('click', () => go(button.dataset.view));
});

document.querySelectorAll('[data-go]').forEach((button) => {
  button.addEventListener('click', () => go(button.dataset.go, button.dataset.focus || null));
});

$('run').addEventListener('click', run);

const dialog = $('guide-dialog');
$('open-guide').addEventListener('click', () => dialog.showModal());

dialog.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});

go('home');
run();
