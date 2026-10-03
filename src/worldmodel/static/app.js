const $ = (id) => document.getElementById(id);
const fmt = (n, d = 3) => Number(n).toFixed(d);
const pct = (n, digits = 0) => `${(Number(n) * 100).toFixed(digits)}%`;
const pretty = (s) => String(s).replaceAll('_', ' ');

function metric(label, value, sub = '') {
  return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub}</div></div>`;
}

function linePoints(seriesA, seriesB, width = 680, height = 250) {
  const all = [...seriesA, ...seriesB];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = Math.max(max - min, 1e-9);
  const n = Math.max(seriesA.length, seriesB.length);
  const points = (values) => values.map((value, i) => {
    const x = (i / Math.max(n - 1, 1)) * width;
    const y = height - ((value - min) / span) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return { a: points(seriesA), b: points(seriesB), min, max };
}

function renderStrategic(data) {
  const eq = data.observational_equivalence;
  const active = data.active_identification;
  const bench = data.identification_benchmark;
  const truth = data.experiment.true_mechanism;
  const truePosterior = active.posterior[truth];
  const entropyGain = (active.entropy_before - active.entropy_after) / Math.max(active.entropy_before, 1e-9);
  const truthAblation = data.belief_ablation.find(x => x.mechanism === truth) || data.belief_ablation[0];

  $('strategic-metrics').innerHTML = [
    metric('Twin-world correlation', pct(eq.mean_return_correlation, 2), 'ordinary returns look the same'),
    metric('True-world posterior', pct(truePosterior, 1), pretty(truth)),
    metric('Entropy removed', pct(entropyGain, 1), 'after one diagnostic reaction'),
    metric('2nd-order uplift', pct(truthAblation.relative_improvement, 1), 'held-out MAE improvement'),
  ].join('');

  $('twin-pill').textContent = `${pct(eq.mean_return_correlation, 2)} correlated`;
  const paths = linePoints(
    data.path_preview.belief_reflexive,
    data.path_preview.liquidity_reflexive
  );
  $('twin-chart').innerHTML = `
    <line x1="0" y1="62.5" x2="680" y2="62.5" class="grid-line"/>
    <line x1="0" y1="125" x2="680" y2="125" class="grid-line"/>
    <line x1="0" y1="187.5" x2="680" y2="187.5" class="grid-line"/>
    <polyline points="${paths.a}" class="world-line belief-line"/>
    <polyline points="${paths.b}" class="world-line liquidity-line"/>
  `;

  $('hidden-mechanics').innerHTML = Object.entries(data.hidden_mechanics).map(([name, m]) => `
    <div class="mechanic-card">
      <span class="mechanic-name">${pretty(name)}</span>
      <strong>${fmt(m.mean_leverage, 2)}×</strong>
      <small>mean leveraged-fund leverage</small>
      <div class="micro-row"><span>dealer hedge</span><b>${fmt(m.dealer_hedge_magnitude, 2)}</b></div>
      <div class="micro-row"><span>margin events</span><b>${m.margin_calls}</b></div>
    </div>
  `).join('');

  const probe = active.selected_probe;
  $('probe-pill').textContent = active.correct ? 'identified' : 'uncertain';
  $('probe-copy').innerHTML = `
    <span class="code-dim">best diagnostic event</span><br>
    <strong>${pretty(probe.event_kind)} ${probe.magnitude >= 0 ? '+' : ''}${fmt(probe.magnitude, 1)}σ</strong>
    <br><span class="code-dim">information score ${fmt(active.information_score, 2)}</span>
  `;

  $('posterior').innerHTML = Object.entries(active.posterior).map(([name, mass]) => `
    <div class="posterior-row">
      <div class="factor-top"><span>${pretty(name)}</span><strong>${pct(mass, 1)}</strong></div>
      <div class="bar"><i style="width:${mass * 100}%"></i></div>
    </div>
  `).join('') + `
    <div class="truth-callout">
      synthetic truth: <strong>${pretty(truth)}</strong> · inferred:
      <strong>${pretty(active.predicted_mechanism)}</strong>
    </div>
  `;

  const maxInfo = Math.max(...active.top_probes.map(p => p.information_score), 1e-9);
  $('probes').innerHTML = active.top_probes.map((p, i) => `
    <div class="probe-row">
      <span class="probe-rank">0${i + 1}</span>
      <span>${pretty(p.label)}</span>
      <div class="probe-meter"><i style="width:${100 * p.information_score / maxInfo}%"></i></div>
      <strong>${fmt(p.information_score, 2)}</strong>
    </div>
  `).join('');

  $('belief-gap-pill').textContent = `gap ${fmt(data.belief_field.mean_higher_order_gap, 2)}`;
  $('belief-factors').innerHTML = data.belief_field.factors.slice(0, 4).map(f => `
    <div class="factor">
      <div class="factor-top">
        <strong>Belief factor ${f.factor}</strong>
        <span>${pct(f.explained_variance, 1)} variance</span>
      </div>
      <div class="bar"><i style="width:${Math.min(100, f.explained_variance * 220)}%"></i></div>
      <div class="muted">
        ${f.dominant_dimensions.slice(0, 3).map(x => `${pretty(x.dimension)} ${fmt(x.loading, 2)}`).join(' · ')}
      </div>
    </div>
  `).join('');

  $('belief-ablation').innerHTML = data.belief_ablation.map(row => `
    <div class="ablation-row">
      <div><strong>${pretty(row.mechanism)}</strong><small>first-order only → + second-order</small></div>
      <span>${fmt(row.first_order_mae)} → ${fmt(row.first_plus_second_order_mae)}</span>
      <b class="${row.relative_improvement >= 0 ? 'safe' : 'flip'}">
        ${row.relative_improvement >= 0 ? '+' : ''}${pct(row.relative_improvement, 1)}
      </b>
    </div>
  `).join('');

  $('identification-benchmark').innerHTML = `
    <div class="benchmark-card">
      <span>Identification accuracy</span>
      <div class="versus"><strong>${pct(bench.active_accuracy, 1)}</strong><em>vs</em><b>${pct(bench.random_accuracy, 1)}</b></div>
      <small>active event · random event</small>
    </div>
    <div class="benchmark-card">
      <span>Posterior on true world</span>
      <div class="versus"><strong>${pct(bench.active_true_posterior, 1)}</strong><em>vs</em><b>${pct(bench.random_true_posterior, 1)}</b></div>
      <small>mean over ${bench.trials} hidden worlds</small>
    </div>
    <div class="benchmark-card">
      <span>Entropy reduction</span>
      <div class="versus"><strong>${fmt(bench.active_entropy_reduction, 2)}</strong><em>vs</em><b>${fmt(bench.random_entropy_reduction, 2)}</b></div>
      <small>information gained from one event</small>
    </div>
  `;

  $('boundary').textContent = data.scientific_boundary;
}


function renderSealed(data) {
  const audit = data.audit;
  const metrics = data.metrics;
  const manifest = data.manifest;
  const ranked = Object.entries(metrics).sort((a, b) => a[1].mae - b[1].mae);
  const best = ranked[0];

  $('sealed-metrics').innerHTML = [
    metric('Leakage violations', audit.leakage_violations, audit.leakage_violations === 0 ? 'fail-closed audit passed' : 'invalid experiment'),
    metric('Forecast seals', audit.all_forecast_seals_valid ? '100%' : 'FAIL', audit.evaluation_events + ' evaluation events'),
    metric('Best frozen MAE', fmt(best[1].mae), pretty(best[0])),
    metric('Evaluation events', audit.evaluation_events, audit.training_events + ' training events'),
  ].join('');

  $('seal-pill').textContent = audit.all_forecast_seals_valid && audit.leakage_violations === 0
    ? 'verified'
    : 'invalid';

  $('manifest-hash').innerHTML = `
    <span class="code-dim">experiment seal</span><br>
    <strong>${manifest.seal.slice(0, 18)}…</strong><br>
    <span class="code-dim">dataset ${manifest.dataset_hash.slice(0, 18)}…</span>
  `;

  $('seal-audit').innerHTML = [
    ['train cutoff', String(audit.last_training_event)],
    ['evaluation starts', String(audit.first_evaluation_event)],
    ['feature leakage', audit.leakage_violations === 0 ? 'none detected' : String(audit.leakage_violations)],
    ['forecast integrity', audit.all_forecast_seals_valid ? 'all seals verify' : 'seal failure'],
  ].map(([label, value]) => `
    <div class="suggestion"><span>${label}</span><code>${value}</code></div>
  `).join('');

  $('sealed-benchmark').innerHTML = ranked.map(([name, row], index) => `
    <tr>
      <td class="${index === 0 ? 'winner' : ''}">${pretty(name)}</td>
      <td>${fmt(row.mae)}</td>
      <td>${fmt(row.rmse)}</td>
      <td>${pct(row.directional_accuracy, 1)}</td>
      <td>${pct(row.interval_coverage_80, 1)}</td>
    </tr>
  `).join('');

  $('sealed-boundary').textContent = data.scientific_boundary;
}

function renderV0(data) {
  const exp = data.experiment;
  const post = data.post_regime;
  const inv = data.prediction_invariant;
  const delta = exp.detected_switch_index == null
    ? null
    : Math.abs(exp.detected_switch_index - exp.true_switch_index);

  $('v0-metrics').innerHTML = [
    metric('Post-regime recovery', pct(post.term_recovery_jaccard, 0), 'symbolic term overlap'),
    metric('Post-regime MAE', fmt(post.mae), 'held-out observations'),
    metric('Break localization', delta == null ? 'miss' : `±${delta}`, 'observations from true break'),
    metric('Model consensus', pct(inv.consensus, 0), inv.robust ? 'invariant survives' : 'models disagree'),
  ].join('');

  $('program').textContent = post.program;
  $('truth').textContent = post.truth_terms.join(' + ');
  $('recovery-pill').textContent = `${pct(post.term_recovery_jaccard, 0)} recovered`;
  $('models').innerHTML = post.top_models.slice(0, 5).map(m => `
    <div class="model-row">
      <span>#${m.rank}</span>
      <code title="${m.program}">${m.program}</code>
      <span>${pct(m.posterior, 0)}</span>
    </div>
  `).join('');

  const n = exp.observations;
  $('true-marker').style.left = `${100 * exp.true_switch_index / n}%`;
  $('detected-marker').style.left = `${100 * (exp.detected_switch_index ?? 0) / n}%`;
  $('detected-marker').style.display = exp.detected_switch_index == null ? 'none' : 'block';
  $('break-copy').textContent = exp.detected_switch_index == null
    ? `The old mechanism did not trigger the detector. Break score ${fmt(exp.break_score, 2)}.`
    : `The hidden world changed at ${exp.true_switch_index}; RMC localized failure around ${exp.detected_switch_index} (score ${fmt(exp.break_score, 2)}).`;

  $('ontology').innerHTML = `<p class="eyebrow">ONTOLOGY BREAK CANDIDATES</p>` +
    data.ontology_break.slice(0, 4).map(s => `
      <div class="suggestion"><code>${s.expression}</code><span>${fmt(s.residual_correlation, 2)} residual corr.</span></div>
    `).join('');

  $('invariant').innerHTML = `
    <div class="invariant-big">${inv.mean >= 0 ? '+' : ''}${fmt(inv.mean, 2)}</div>
    <div class="invariant-range">80% model interval ${fmt(inv.low, 2)} → ${fmt(inv.high, 2)}</div>
    <div class="consensus">
      <div class="factor-top"><span>directional consensus</span><strong>${pct(inv.consensus, 0)}</strong></div>
      <div class="bar"><i style="width:${inv.consensus * 100}%"></i></div>
    </div>
  `;

  $('adversary').innerHTML = data.adversarial_scenarios.map(a => `
    <div class="adv">
      <span>${a.feature} ${a.delta >= 0 ? '+' : ''}${fmt(a.delta, 2)}σ</span>
      <span>${a.prediction >= 0 ? '+' : ''}${fmt(a.prediction, 2)}</span>
      <span class="${a.sign_flipped ? 'flip' : 'safe'}">${a.sign_flipped ? 'SIGN FLIP' : 'holds'}</span>
    </div>
  `).join('');

  $('benchmark').innerHTML = data.sample_efficiency.map(row => {
    const vals = {
      RMC: row.rmc_mae,
      Ridge: row.ridge_mae,
      Poly: row.poly_ridge_mae,
      RF: row.random_forest_mae,
    };
    const best = Object.entries(vals).sort((a, b) => a[1] - b[1])[0][0];
    return `<tr>
      <td>${row.train_size}</td>
      <td>${fmt(row.rmc_mae)}</td>
      <td>${fmt(row.ridge_mae)}</td>
      <td>${fmt(row.poly_ridge_mae)}</td>
      <td>${fmt(row.random_forest_mae)}</td>
      <td class="winner">${best}</td>
    </tr>`;
  }).join('');
}

async function run() {
  const button = $('run');
  button.disabled = true;
  button.textContent = 'Inferring worlds…';
  $('probe-copy').textContent = 'Simulating competing worlds and ranking diagnostic events…';
  $('program').textContent = 'Searching executable mechanisms…';

  try {
    const seed = $('seed').value || '7';
    const target = $('target').value;
    const [strategicResponse, sealedResponse, v0Response] = await Promise.all([
      fetch(`/api/strategic?${new URLSearchParams({ seed, observations: '260' })}`),
      fetch(`/api/sealed?${new URLSearchParams({ seed, observations: '120' })}`),
      fetch(`/api/demo?${new URLSearchParams({ seed, target, observations: '360' })}`),
    ]);

    if (!strategicResponse.ok) throw new Error(`Strategic API HTTP ${strategicResponse.status}`);
    if (!sealedResponse.ok) throw new Error(`Sealed API HTTP ${sealedResponse.status}`);
    if (!v0Response.ok) throw new Error(`Compiler API HTTP ${v0Response.status}`);

    const [strategic, sealed, v0] = await Promise.all([
      strategicResponse.json(),
      sealedResponse.json(),
      v0Response.json(),
    ]);
    renderStrategic(strategic);
    renderSealed(sealed);
    renderV0(v0);
  } catch (err) {
    $('probe-copy').textContent = `Experiment failed: ${err.message}`;
    $('program').textContent = 'Compiler unavailable.';
  } finally {
    button.disabled = false;
    button.textContent = 'Run world experiment';
  }
}

$('run').addEventListener('click', run);
run();
