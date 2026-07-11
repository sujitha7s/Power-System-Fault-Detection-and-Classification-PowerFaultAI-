/* ============================================================
   PowerFaultAI — Dashboard JS v2
   IBM Cloud integration: risk score, AI insights, WML badge
   ============================================================ */
'use strict';

// ── Colour palette ────────────────────────────────────────────
const PROB_COLORS = ['#24a148','#c09000','#f97316','#da1e28','#a2191f'];
const SEV_MAP = {
  'None':     { badgeCls:'badge-normal',   cardCls:'severity-none',     icon:'check-circle-fill',      bs:'bg-success' },
  'Moderate': { badgeCls:'badge-moderate', cardCls:'severity-moderate', icon:'exclamation-circle-fill',bs:'bg-warning text-dark' },
  'High':     { badgeCls:'badge-high',     cardCls:'severity-high',     icon:'exclamation-triangle-fill',bs:'bg-danger' },
  'Critical': { badgeCls:'badge-critical', cardCls:'severity-critical', icon:'x-octagon-fill',         bs:'bg-danger' },
};
const FAULT_ICONS = {
  'Normal Operation':            'check-circle-fill',
  'Line-to-Ground Fault':        'exclamation-triangle-fill',
  'Line-to-Line Fault':          'exclamation-circle-fill',
  'Double Line-to-Ground Fault': 'exclamation-octagon-fill',
  'Three-Phase Fault':           'x-octagon-fill',
};

// ── Read form ─────────────────────────────────────────────────
function readForm() {
  const fields = ['Va','Vb','Vc','Ia','Ib','Ic',
                  'freq_deviation','thd','power_factor','temperature'];
  const data = {};
  for (const f of fields) {
    const v = parseFloat(document.getElementById(f)?.value);
    if (isNaN(v)) throw new Error('Field "' + f + '" is missing or invalid');
    data[f] = v;
  }
  return data;
}

function fillForm(preset) {
  Object.entries(preset).forEach(function([k, v]) {
    const el = document.getElementById(k);
    if (el) { el.value = v; }
  });
  updateDerived();
}

// ── Derived feature preview ───────────────────────────────────
function updateDerived() {
  const Va = +document.getElementById('Va')?.value || 0;
  const Vb = +document.getElementById('Vb')?.value || 0;
  const Vc = +document.getElementById('Vc')?.value || 0;
  const Ia = +document.getElementById('Ia')?.value || 0;
  const Ib = +document.getElementById('Ib')?.value || 0;
  const Ic = +document.getElementById('Ic')?.value || 0;
  if (!Va && !Vb && !Vc) return;
  const Vavg = (Va+Vb+Vc)/3, Iavg = (Ia+Ib+Ic)/3;
  const Vstd = Math.sqrt(((Va-Vavg)**2+(Vb-Vavg)**2+(Vc-Vavg)**2)/3);
  const Istd = Math.sqrt(((Ia-Iavg)**2+(Ib-Iavg)**2+(Ic-Iavg)**2)/3);
  document.getElementById('dVimb').textContent = (Vstd/(Vavg+1e-9)).toFixed(3);
  document.getElementById('dIimb').textContent = (Istd/(Iavg+1e-9)).toFixed(3);
  document.getElementById('dApS').textContent  = (Vavg*Iavg*1.732).toFixed(3);
  document.getElementById('derivedCard').style.display = '';
}

// ── Render result ─────────────────────────────────────────────
function renderResult(r) {
  const sev  = r.severity || 'None';
  const sevC = SEV_MAP[sev] || SEV_MAP['None'];

  // Show result, hide placeholder
  document.getElementById('resultSection').style.display    = 'block';
  document.getElementById('resultPlaceholder').style.display = 'none';

  // Card class
  const card = document.getElementById('resultCard');
  card.className = 'result-card ' + sevC.cardCls;

  // Fault badge
  const badge = document.getElementById('faultBadge');
  badge.className = 'fault-badge ' + sevC.badgeCls;
  document.getElementById('faultIcon').className  = 'bi bi-' + (FAULT_ICONS[r.predicted_class] || sevC.icon);
  document.getElementById('faultLabel').textContent = r.predicted_class;

  // Severity badge
  const sbadge = document.getElementById('severityBadge');
  sbadge.className = 'badge fs-6 px-3 py-2 rounded-pill ' + sevC.bs;
  sbadge.textContent = sev;

  // Confidence
  const pct = r.confidence ? Math.round(r.confidence * 100) : 0;
  document.getElementById('confValue').textContent = pct + '%';
  const bar = document.getElementById('confBar');
  const barColor = pct >= 80 ? 'var(--success)' : pct >= 60 ? 'var(--warning)' : 'var(--danger)';
  bar.style.background = barColor;
  setTimeout(function(){ bar.style.width = pct + '%'; }, 60);

  // Risk score
  const riskEl = document.getElementById('riskScore');
  if (riskEl) {
    const rs = r.risk_score !== undefined ? r.risk_score : '—';
    riskEl.textContent = rs;
    const rsNum = parseInt(rs);
    riskEl.style.color = rsNum >= 70 ? 'var(--danger)' : rsNum >= 40 ? 'var(--warning)' : 'var(--success)';
  }

  // IBM source badge
  const ibmBadge = document.getElementById('ibmSourceBadge');
  if (ibmBadge) {
    if (r.ibm_source === 'watson_ml') {
      ibmBadge.style.display = '';
      ibmBadge.innerHTML = '<i class="bi bi-cloud-fill me-1"></i>Watson ML';
    } else if (r.ibm_source === 'rule_engine') {
      ibmBadge.style.display = '';
      ibmBadge.innerHTML = '<i class="bi bi-cpu me-1"></i>AI Enhanced';
      ibmBadge.style.background = 'rgba(0,157,154,.1)';
      ibmBadge.style.borderColor = 'rgba(0,157,154,.25)';
      ibmBadge.style.color = 'var(--ibm-teal)';
    } else {
      ibmBadge.style.display = 'none';
    }
  }

  // Cause
  document.getElementById('probCause').textContent = r.probable_cause || '—';

  // Probabilities
  const probList = document.getElementById('probList');
  probList.innerHTML = '';
  if (r.class_probabilities) {
    Object.entries(r.class_probabilities).forEach(function([label, prob], i) {
      const p2 = Math.round(prob * 100);
      probList.innerHTML += '<div class="prob-item">'
        + '<span class="prob-label">' + label + '</span>'
        + '<div class="prob-bar-wrap"><div class="prob-bar" style="width:0%;background:' + (PROB_COLORS[i]||'#888') + '" data-target="' + p2 + '"></div></div>'
        + '<span class="prob-pct">' + p2 + '%</span>'
        + '</div>';
    });
    setTimeout(function(){
      probList.querySelectorAll('.prob-bar').forEach(function(b){
        b.style.width = b.dataset.target + '%';
      });
    }, 80);
  }

  // IBM AI insights panel
  const insightsPanel = document.getElementById('ibmInsightsPanel');
  const insightsList  = document.getElementById('ibmInsightsList');
  const insightSrc    = document.getElementById('ibmInsightSource');
  if (insightsPanel && insightsList && r.ai_insights && r.ai_insights.length) {
    insightsList.innerHTML = r.ai_insights.map(function(txt){
      return '<div class="ibm-insight-item"><i class="bi bi-info-circle-fill"></i><span>' + txt + '</span></div>';
    }).join('');
    if (insightSrc) {
      insightSrc.textContent = r.ibm_source === 'watson_ml' ? 'Watson ML' : 'Rule Engine';
    }
    insightsPanel.style.display = '';
  } else if (insightsPanel) {
    insightsPanel.style.display = 'none';
  }

  // Actions
  const al = document.getElementById('actionList');
  al.innerHTML = (r.recommended_actions || []).map(function(a){
    return '<li><i class="bi bi-arrow-right-circle-fill" style="color:var(--danger)"></i><span>' + a + '</span></li>';
  }).join('');

  // Preventive
  const pl = document.getElementById('preventList');
  pl.innerHTML = (r.preventive_suggestions || []).map(function(a){
    return '<li><i class="bi bi-shield-check-fill" style="color:var(--success)"></i><span>' + a + '</span></li>';
  }).join('');

  // Uncertain warning
  if (r.is_uncertain) {
    showToast('Low confidence — consider collecting more sensor data', 'warning');
  }
}

// ── Form submission ───────────────────────────────────────────
document.getElementById('predForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  let data;
  try { data = readForm(); }
  catch(err) { showToast(err.message, 'danger'); return; }

  setLoading(true, 'Analysing fault signature...');
  try {
    const resp = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await resp.json();
    if (!resp.ok) throw new Error(result.error || 'Prediction failed');
    renderResult(result);
    const cnt = document.getElementById('histCount');
    if (cnt) cnt.textContent = +cnt.textContent + 1;
    showToast('Fault analysis complete', 'success');
  } catch(err) {
    showToast('Error: ' + err.message, 'danger');
  } finally {
    setLoading(false);
  }
});

// ── Quick scenarios ───────────────────────────────────────────
document.querySelectorAll('.scenario-btn').forEach(function(btn) {
  btn.addEventListener('click', async function() {
    const scenario = this.dataset.scenario;
    if (!scenario) return;
    setLoading(true, 'Loading scenario...');
    try {
      const resp = await fetch('/api/quick_predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      });
      const result = await resp.json();
      if (!resp.ok) throw new Error(result.error || 'Failed');
      if (result.input_features) fillForm(result.input_features);
      renderResult(result);
      showToast('Scenario: ' + result.predicted_class, 'success');
    } catch(err) {
      showToast('Error: ' + err.message, 'danger');
    } finally {
      setLoading(false);
    }
  });
});

// ── Reset ─────────────────────────────────────────────────────
const resetBtn = document.getElementById('btnReset');
if (resetBtn) {
  resetBtn.addEventListener('click', function() {
    document.getElementById('derivedCard').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('resultPlaceholder').style.display = '';
  });
}

// ── Retrain ───────────────────────────────────────────────────
const retrainBtn = document.getElementById('btnRetrain');
if (retrainBtn) {
  retrainBtn.addEventListener('click', async function() {
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Training...';
    setLoading(true, 'Training ML models — this may take a minute...');
    try {
      const resp   = await fetch('/api/retrain', { method: 'POST' });
      const result = await resp.json();
      if (result.status === 'success') {
        showToast('Training done! Best: ' + result.best_model, 'success');
        setTimeout(function(){ location.reload(); }, 1800);
      } else {
        showToast('Training error: ' + result.message, 'danger');
        this.disabled = false;
        this.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Train Models Now';
      }
    } catch(err) {
      showToast('Error: ' + err.message, 'danger');
      this.disabled = false;
    } finally {
      setLoading(false);
    }
  });
}

// ── Live derived updates ──────────────────────────────────────
['Va','Vb','Vc','Ia','Ib','Ic'].forEach(function(id) {
  document.getElementById(id)?.addEventListener('input', updateDerived);
});
