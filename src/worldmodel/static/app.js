const $ = (id) => document.getElementById(id);
const fmt = (n, d=3) => Number(n).toFixed(d);
const pct = (n) => `${Math.round(Number(n) * 100)}%`;

function metric(label, value, sub='') {
  return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${sub}</div></div>`;
}

function render(data) {
  const exp = data.experiment;
  const post = data.post_regime;
  const pre = data.pre_regime;
  const inv = data.prediction_invariant;
  const delta = exp.detected_switch_index == null ? null : Math.abs(exp.detected_switch_index - exp.true_switch_index);

  $('metrics').innerHTML = [
    metric('Post-regime recovery', pct(post.term_recovery_jaccard), 'symbolic term overlap'),
    metric('Post-regime MAE', fmt(post.mae), 'held world, refit mechanism'),
    metric('Break localization', delta == null ? 'miss' : `±${delta}`, 'observations from true break'),
    metric('Model consensus', pct(inv.consensus), inv.robust ? 'invariant survives' : 'fragile / disagreeing'),
  ].join('');

  $('program').textContent = post.program;
  $('truth').textContent = post.truth_terms.join(' + ');
  $('recovery-pill').textContent = `${pct(post.term_recovery_jaccard)} recovered`;
  $('models').innerHTML = post.top_models.slice(0,5).map(m => `
    <div class="model-row"><span>#${m.rank}</span><code title="${m.program}">${m.program}</code><span>${pct(m.posterior)}</span></div>
  `).join('');

  const n = exp.observations;
  $('true-marker').style.left = `${100 * exp.true_switch_index / n}%`;
  $('detected-marker').style.left = `${100 * (exp.detected_switch_index ?? 0) / n}%`;
  $('detected-marker').style.display = exp.detected_switch_index == null ? 'none' : 'block';
  $('break-copy').textContent = exp.detected_switch_index == null
    ? `The old mechanism did not trigger the break detector. Break score ${fmt(exp.break_score,2)}.`
    : `The hidden world changed at observation ${exp.true_switch_index}. RMC detected model failure around ${exp.detected_switch_index} with break score ${fmt(exp.break_score,2)}.`;
  $('ontology').innerHTML = `<p class="eyebrow">ONTOLOGY BREAK CANDIDATES</p>` + data.ontology_break.slice(0,4).map(s => `
    <div class="suggestion"><code>${s.expression}</code><span>${fmt(s.residual_correlation,2)} residual corr.</span></div>
  `).join('');

  $('tomography').innerHTML = data.tomography.map(f => `
    <div class="factor">
      <div class="factor-top"><strong>Latent factor ${f.factor}</strong><span>${pct(f.explained_variance)} variance</span></div>
      <div class="bar"><i style="width:${Math.min(100, f.explained_variance*180)}%"></i></div>
      <div class="muted">${f.dominant_loadings.map(x => `${x.asset} ${fmt(x.loading,2)}`).join(' · ')}</div>
    </div>
  `).join('');

  $('invariant').innerHTML = `
    <div class="invariant-big">${inv.mean >= 0 ? '+' : ''}${fmt(inv.mean,2)}</div>
    <div class="invariant-range">80% model interval ${fmt(inv.low,2)} → ${fmt(inv.high,2)}</div>
    <div class="consensus"><div class="factor-top"><span>directional consensus</span><strong>${pct(inv.consensus)}</strong></div><div class="bar"><i style="width:${inv.consensus*100}%"></i></div></div>
  `;
  $('adversary').innerHTML = data.adversarial_scenarios.map(a => `
    <div class="adv"><span>${a.feature} ${a.delta >= 0 ? '+' : ''}${fmt(a.delta,2)}σ</span><span>${a.prediction >= 0 ? '+' : ''}${fmt(a.prediction,2)}</span><span class="${a.sign_flipped ? 'flip':'safe'}">${a.sign_flipped ? 'SIGN FLIP':'holds'}</span></div>
  `).join('');

  $('benchmark').innerHTML = data.sample_efficiency.map(r => {
    const vals = {RMC:r.rmc_mae, Ridge:r.ridge_mae, 'Poly Ridge':r.poly_ridge_mae, 'Random forest':r.random_forest_mae};
    const best = Object.entries(vals).sort((a,b)=>a[1]-b[1])[0][0];
    return `<tr><td>${r.train_size}</td><td>${fmt(r.rmc_mae)}</td><td>${fmt(r.ridge_mae)}</td><td>${fmt(r.poly_ridge_mae)}</td><td>${fmt(r.random_forest_mae)}</td><td class="winner">${best}</td></tr>`;
  }).join('');
}

async function run() {
  const button = $('run');
  button.disabled = true;
  button.textContent = 'Compiling…';
  $('program').textContent = 'Searching compact executable mechanisms…';
  try {
    const params = new URLSearchParams({seed:$('seed').value || '7', target:$('target').value, observations:'360'});
    const response = await fetch(`/api/demo?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (err) {
    $('program').textContent = `Experiment failed: ${err.message}`;
  } finally {
    button.disabled = false;
    button.textContent = 'Compile world';
  }
}

$('run').addEventListener('click', run);
run();
