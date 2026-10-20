// TwinForge Connected Graph - Client Router & Navigation
let currentView = 'twin';

function navigatePage(viewName) {
  if (viewName === 'connected-graph') viewName = 'twin';
  const views = ['twin', 'dashboard', 'agents', 'simulator', 'approvals', 'audit', 'control-room', 'integrations'];
  views.forEach(v => {
    const el = document.getElementById('view-' + v);
    const btn = document.getElementById('nav-btn-' + v);
    if (el) el.classList.add('hidden');
    if (btn) {
      btn.className = "group flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-ink-2 hover:bg-surface/70 hover:text-ink transition-colors";
    }
  });

  const activeEl = document.getElementById('view-' + viewName);
  const activeBtn = document.getElementById('nav-btn-' + viewName);
  if (activeEl) activeEl.classList.remove('hidden');
  if (activeBtn) {
    activeBtn.className = "group flex h-9 items-center gap-2.5 rounded-lg px-2.5 bg-surface-2 text-ink shadow-[inset_2px_0_0_var(--color-accent)] transition-colors";
  }
  currentView = viewName;
  window.history.pushState({}, '', '/' + viewName);

  if (viewName === 'agents' && typeof loadSubgraph === 'function') loadSubgraph();
  if (viewName === 'integrations' && typeof checkHealth === 'function') checkHealth();
  if (viewName === 'dashboard' && typeof loadKpis === 'function') loadKpis();
}
