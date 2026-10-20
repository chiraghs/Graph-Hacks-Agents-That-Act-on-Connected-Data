// TwinForge Connected Graph - Digital Twin Canvas & Drawer Controls
let currentTwinMode = 'topology';
let canvasZoom = 0.80;
let canvasPanX = 10;
let canvasPanY = 15;
let isDraggingCanvas = false;
let dragStartX = 0;
let dragStartY = 0;

function setTwinView(mode) {
  currentTwinMode = mode;
  const modes = ['topology', 'floor'];
  modes.forEach(m => {
    const btn = document.getElementById('tab-twin-' + m);
    const st = document.getElementById('stage-' + m);
    if (btn) btn.className = "flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[12.5px] text-muted hover:text-ink transition-colors";
    if (st) st.classList.add('hidden');
  });

  const activeBtn = document.getElementById('tab-twin-' + mode);
  const activeStage = document.getElementById('stage-' + mode);
  if (activeBtn) activeBtn.className = "flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[12.5px] bg-surface-3 text-ink font-medium transition-colors";
  if (activeStage) activeStage.classList.remove('hidden');
}

function zoomCanvas(factor) {
  canvasZoom = Math.min(2.5, Math.max(0.4, canvasZoom * factor));
  updateCanvasTransform();
}

function resetCanvasTransform() {
  canvasZoom = 0.96;
  canvasPanX = 20;
  canvasPanY = 20;
  updateCanvasTransform();
}

function updateCanvasTransform() {
  const stageTopology = document.getElementById('stage-topology');
  if (stageTopology) {
    stageTopology.style.transform = `translate(${canvasPanX}px, ${canvasPanY}px) scale(${canvasZoom})`;
  }
}

// Watchlist Dropdown
function toggleWatchlist() {
  const el = document.getElementById('watchlist-dropdown-content');
  const ch = document.getElementById('watchlist-chevron');
  if (el) {
    el.classList.toggle('hidden');
    if (ch) ch.classList.toggle('rotate-180');
  }
}

// Demo Controls Dropdown
function toggleDemoMenu() {
  const el = document.getElementById('demo-menu-dropdown');
  if (el) el.classList.toggle('hidden');
}

// Asset Panel Drawer
function selectAsset(assetId) {
  const drawer = document.getElementById('drawer-asset-panel');
  const nameEl = document.getElementById('drawer-asset-name');
  const idEl = document.getElementById('drawer-asset-id');
  const subEl = document.getElementById('drawer-asset-sub');
  const healthEl = document.getElementById('drawer-metric-health');
  const healthBar = document.getElementById('drawer-bar-health');
  const vibEl = document.getElementById('drawer-metric-vibration');
  const tempEl = document.getElementById('drawer-metric-temp');

  if (assetId === 'A-ROB-03' || assetId === 'M7') {
    if (idEl) idEl.innerText = "A-ROB-03 (M7)";
    if (nameEl) nameEl.innerText = "Assembly Robot A3";
    if (subEl) subEl.innerText = "Six-Axis Articulated Robot \u2022 KUKA KR-16 \u2022 Assembly Line A";
    if (healthEl) healthEl.innerText = "58";
    if (healthBar) { healthBar.style.width = "58%"; healthBar.className = "h-full bg-warning rounded-full"; }
    if (vibEl) vibEl.innerText = "6.22 mm/s";
    if (tempEl) tempEl.innerText = "69.0 \u00B0C";
  } else if (assetId === 'B-ROB-03' || assetId === 'M12') {
    if (idEl) idEl.innerText = "B-ROB-03 (M12)";
    if (nameEl) nameEl.innerText = "Assembly Robot B3";
    if (subEl) subEl.innerText = "Articulated Robot \u2022 Redundant Backup M13 Online \u2022 Assembly Line B";
    if (healthEl) healthEl.innerText = "100";
    if (healthBar) { healthBar.style.width = "100%"; healthBar.className = "h-full bg-healthy rounded-full"; }
    if (vibEl) vibEl.innerText = "2.60 mm/s";
    if (tempEl) tempEl.innerText = "56.0 \u00B0C";
  } else {
    if (idEl) idEl.innerText = assetId;
    if (nameEl) nameEl.innerText = assetId;
    if (subEl) subEl.innerText = "Automated Equipment \u2022 Nominal Operation";
    if (healthEl) healthEl.innerText = "100";
    if (healthBar) { healthBar.style.width = "100%"; healthBar.className = "h-full bg-healthy rounded-full"; }
    if (vibEl) vibEl.innerText = "1.60 mm/s";
  }

  if (drawer) drawer.classList.remove('hidden');

  // Query live FalkorDB graph impact & blast radius
  const targetMachineId = (assetId.includes('A-ROB-03') || assetId === 'M7') ? 'M7' : ((assetId.includes('B-ROB-03') || assetId === 'M12') ? 'M12' : null);
  if (targetMachineId) {
    fetch('/api/simulate/' + targetMachineId)
      .then(r => r.json())
      .then(data => {
        if (data && data.machine) {
          const m = data.machine;
          if (healthEl && m.health_score !== undefined) {
            healthEl.innerText = m.health_score;
            if (healthBar) healthBar.style.width = m.health_score + '%';
          }
          const linksEl = document.getElementById('drawer-links-content');
          if (linksEl && data.impact) {
            const parts = (data.impact.affected_parts || []).map(p => p.name).join(', ') || 'P-ROTOR-X (PT-4)';
            const prods = (data.impact.downstream_products || []).map(p => `${p.name} [Shortfall: ${p.shortfall}u]`).join(', ') || 'ECU-200 (P4)';
            const custs = (data.impact.affected_customers || []).map(c => c.name).join(', ') || 'ORD-1042 (Kestrel Robotics)';
            linksEl.innerHTML = `
              <p class="text-ink flex items-center gap-2">
                <span class="text-accent">&rarr;</span> Machine <span class="font-bold text-warning">${m.id} (${m.name})</span> [Risk: ${Math.round(m.failure_risk * 100)}%]
              </p>
              <p class="text-ink-2 pl-4 flex items-center gap-2">
                <span class="text-accent">&rarr;</span> Part <span class="font-bold text-accent">${parts}</span> [Single Point of Failure]
              </p>
              <p class="text-ink-2 pl-8 flex items-center gap-2">
                <span class="text-accent">&rarr;</span> Product <span class="font-bold text-critical">${prods}</span>
              </p>
              <p class="text-ink-2 pl-12 flex items-center gap-2">
                <span class="text-accent">&rarr;</span> Impacted Customer <span class="font-bold text-critical-ink">${custs}</span>
              </p>
            `;
          }
        }
      })
      .catch(e => console.log('FalkorDB simulation fetch:', e));
  }
}

function selectOtherNode(nodeId) {
  selectAsset(nodeId);
}

function closeAssetPanel() {
  const drawer = document.getElementById('drawer-asset-panel');
  if (drawer) drawer.classList.add('hidden');
}

function switchDrawerTab(tabName) {
  const tabs = ['overview', 'telemetry', 'links', 'history'];
  tabs.forEach(t => {
    const btn = document.getElementById('tab-drawer-' + t);
    const content = document.getElementById('drawer-tab-' + t);
    if (btn) btn.className = "border-b-2 border-transparent hover:text-ink pb-2";
    if (content) content.classList.add('hidden');
  });

  const activeBtn = document.getElementById('tab-drawer-' + tabName);
  const activeContent = document.getElementById('drawer-tab-' + tabName);
  if (activeBtn) activeBtn.className = "border-b-2 border-accent text-ink pb-2 font-semibold";
  if (activeContent) activeContent.classList.remove('hidden');
}

// Camera Modal
function openCameraModal(camId) {
  const modal = document.getElementById('camera-modal');
  const title = document.getElementById('camera-modal-title');
  if (title) title.innerText = "CAMERA STREAM: " + camId.toUpperCase();
  if (modal) modal.classList.remove('hidden');
}

function closeCameraModal() {
  const modal = document.getElementById('camera-modal');
  if (modal) modal.classList.add('hidden');
}

// Attach Pan & Zoom Event Listeners on DOM load
document.addEventListener('DOMContentLoaded', () => {
  const canvasViewport = document.getElementById('twin-canvas-viewport');
  if (!canvasViewport) return;

  canvasViewport.addEventListener('mousedown', (e) => {
    if (e.target.closest('#drawer-asset-panel') || e.target.closest('#risk-watchlist-box') || e.target.closest('.cursor-pointer')) return;
    isDraggingCanvas = true;
    dragStartX = e.clientX - canvasPanX;
    dragStartY = e.clientY - canvasPanY;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDraggingCanvas) return;
    canvasPanX = e.clientX - dragStartX;
    canvasPanY = e.clientY - dragStartY;
    updateCanvasTransform();
  });

  window.addEventListener('mouseup', () => {
    isDraggingCanvas = false;
  });

  canvasViewport.addEventListener('wheel', (e) => {
    if (currentTwinMode !== 'topology') return;
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    canvasZoom = Math.min(2.5, Math.max(0.4, canvasZoom * zoomFactor));
    updateCanvasTransform();
  }, { passive: false });
});
