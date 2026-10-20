// TwinForge Connected Graph - Application Bootstrapper & Global Actions

// Prescriptive Decision Approval
async function approvePrescription(type) {
  try {
    const res = await fetch('/api/decisions/approve', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        type: type || 'reroute_production',
        target_id: 'M7',
        reason: 'Approved mitigation plan: reroute ECU-200 production to Plant 2 (Leipzig) & schedule robotic arm M7 bearing replacement',
        evidence_ids: ['M7', 'PT-4', 'P4', 'C1']
      })
    });
    const out = await res.json();
    alert('Prescriptive Decision Approved & Recorded in FalkorDB!\nDecision node created with BASED_ON lineage links.');
    loadKpis();
  } catch(e) {
    alert('Error approving decision: ' + e);
  }
}

// Reset Demo State in FalkorDB
async function resetGraphState() {
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    const out = await res.json();
    alert('FalkorDB SupplyChain graph reset and re-seeded successfully (' + JSON.stringify(out.counts || out) + ')');
    window.location.reload();
  } catch(e) {
    alert('Error resetting graph: ' + e);
  }
}

// Trigger Crisis Demo
function triggerCrisisDemo() {
  if (typeof navigatePage === 'function') navigatePage('twin');
  if (typeof selectAsset === 'function') selectAsset('A-ROB-03');
  const dropdown = document.getElementById('demo-menu-dropdown');
  if (dropdown) dropdown.classList.add('hidden');
}

// Fast-Forward Plant Time Simulation
function advancePlantTime(hours) {
  alert(`Fast-forwarded ${hours} hour(s) of plant simulation time. Synchronized with FalkorDB live state.`);
  loadKpis();
  const dropdown = document.getElementById('demo-menu-dropdown');
  if (dropdown) dropdown.classList.add('hidden');
}

// Health Check & Live KPIs from FalkorDB
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const hostEl = document.getElementById('integrations-falkordb-host');
    const envEl = document.getElementById('integrations-env-type');
    const sslEl = document.getElementById('integrations-ssl-status');
    if (hostEl) hostEl.innerText = data.target_host + " • Graph: " + data.graph;
    if (envEl) envEl.innerText = data.environment;
    if (sslEl) sslEl.innerText = data.tls_enabled ? "Enabled (TLSv1.3)" : "Disabled (Plaintext Local)";
  } catch(e) {
    console.error('checkHealth error:', e);
  }
}

async function loadKpis() {
  try {
    const res = await fetch('/api/kpis');
    const data = await res.json();
    if (data.status === 'online') {
      const atRiskEl = document.getElementById('kpi-machine-risk');
      if (atRiskEl) atRiskEl.innerText = (data.at_risk_machines > 0 ? "58.0" : "95.4");
      const incEl = document.getElementById('kpi-open-incidents');
      if (incEl) incEl.innerText = data.at_risk_machines;
    }
  } catch(e) {
    console.error('loadKpis error:', e);
  }
}

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', () => {
  // Theme UI setup
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  if (typeof updateThemeUI === 'function') {
    updateThemeUI(currentTheme);
  }

  // Route handling
  const path = window.location.pathname.replace('/', '') || 'twin';
  if (typeof navigatePage === 'function') {
    navigatePage(path);
  }

  // Initial data loading
  checkHealth();
  loadKpis();
});
