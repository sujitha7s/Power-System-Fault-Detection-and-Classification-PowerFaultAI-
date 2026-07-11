/* ── Theme toggle (light ↔ dark) ─────────────────────────── */
(function () {
  'use strict';
  const root   = document.documentElement;
  const btn    = document.getElementById('themeToggle');
  const icon   = document.getElementById('themeIcon');
  const STORED = localStorage.getItem('pf_theme');

  function applyTheme(t) {
    root.setAttribute('data-theme', t);
    if (icon) {
      icon.className = t === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
    localStorage.setItem('pf_theme', t);
  }

  // Initialise from storage or system preference
  const preferred = STORED ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(preferred);

  if (btn) {
    btn.addEventListener('click', function () {
      applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  // Expose globally so pages can react
  window.getCurrentTheme = function () {
    return root.getAttribute('data-theme') || 'light';
  };
})();
