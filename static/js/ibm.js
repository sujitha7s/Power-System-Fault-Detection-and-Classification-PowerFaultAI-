/* ============================================================
   PowerFaultAI — IBM Cloud integration + shared utilities
   Handles: IBM status polling, toast helper, loading overlay
   ============================================================ */
'use strict';

// ── Shared toast helper ──────────────────────────────────────
window.showToast = function(msg, type) {
  type = type || 'success';
  const id  = 'toast_' + Date.now();
  const cls = type === 'success' ? 'bg-success'
            : type === 'warning' ? 'bg-warning text-dark'
            : type === 'info'    ? 'bg-primary'
            : 'bg-danger';
  const el = document.createElement('div');
  el.id = id;
  el.className = 'toast align-items-center text-white ' + cls + ' border-0';
  el.setAttribute('role','alert');
  el.setAttribute('aria-live','assertive');
  el.innerHTML = '<div class="d-flex"><div class="toast-body fw-600">' + msg + '</div>'
    + '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
  const container = document.getElementById('toastContainer');
  if (container) container.appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 4000 });
  t.show();
  el.addEventListener('hidden.bs.toast', function(){ el.remove(); });
};

// ── Loading overlay helpers ──────────────────────────────────
window.setLoading = function(on, msg) {
  const ov = document.getElementById('loadingOverlay');
  const lm = document.getElementById('loadingMsg');
  if (lm) lm.textContent = msg || 'Processing...';
  if (ov) ov.classList.toggle('active', !!on);
};

// ── IBM Cloud status pill ────────────────────────────────────
(function pollIBMStatus() {
  const pill    = document.getElementById('ibmStatusPill');
  const dot     = document.getElementById('ibmDot');
  const txtSpan = document.getElementById('ibmStatusText');
  if (!pill) return;

  function applyStatus(data) {
    dot.classList.remove('pulse');
    if (!data) {
      // network error
      pill.className = 'ibm-status-pill ibm-pill-offline';
      if (txtSpan) txtSpan.textContent = 'IBM Cloud';
      return;
    }
    if (data.configured && data.token_ok) {
      pill.className = 'ibm-status-pill ibm-pill-connected';
      if (txtSpan) txtSpan.textContent = 'IBM Connected';
      pill.title = 'IBM Cloud API authenticated. WML:' +
        (data.wml_configured ? 'on' : 'off') +
        ' EN:' + (data.en_configured ? 'on' : 'off');
    } else if (data.configured && !data.token_ok) {
      pill.className = 'ibm-status-pill ibm-pill-checking';
      dot.classList.add('pulse');
      if (txtSpan) txtSpan.textContent = 'IBM Auth Failed';
      pill.title = 'IBM_API_KEY set but IAM token request failed';
    } else {
      pill.className = 'ibm-status-pill ibm-pill-offline';
      if (txtSpan) txtSpan.textContent = 'IBM Offline';
      pill.title = 'IBM Cloud not configured — set IBM_API_KEY in .env';
    }
  }

  // Initial check
  fetch('/api/ibm-status')
    .then(function(r){ return r.json(); })
    .then(applyStatus)
    .catch(function(){ applyStatus(null); });

  // Re-check every 5 minutes
  setInterval(function(){
    fetch('/api/ibm-status')
      .then(function(r){ return r.json(); })
      .then(applyStatus)
      .catch(function(){ applyStatus(null); });
  }, 300000);
})();
