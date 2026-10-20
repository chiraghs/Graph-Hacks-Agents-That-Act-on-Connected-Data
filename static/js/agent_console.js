// TwinForge Connected Graph - Agent Investigation Console & SSE Streamer
function startInvestigation() {
  const logs = document.getElementById('agent-logs-container');
  const badge = document.getElementById('agent-active-badge');
  const runBtn = document.getElementById('btn-run-agent');

  if (logs) logs.innerHTML = '';
  if (badge) badge.classList.remove('hidden');
  if (runBtn) runBtn.disabled = true;

  const evtSource = new EventSource('/api/investigate');
  evtSource.onmessage = function(event) {
    if (!event.data) return;
    let msg;
    try { msg = JSON.parse(event.data); } catch(e) { return; }

    const evt = msg.event || msg.type || '';
    const d = msg.data || msg;

    const row = document.createElement('div');
    row.className = "p-2.5 rounded-lg border text-xs font-mono transition-all";

    if (evt === 'tool_call') {
      row.className += " border-accent/30 bg-accent/5 text-ink";
      const inputStr = d.input ? JSON.stringify(d.input) : (d.args ? JSON.stringify(d.args) : '');
      row.innerHTML = `
        <div class="flex items-center justify-between text-accent font-semibold mb-1">
          <span class="flex items-center gap-1.5">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
            CYPHER TOOL: ${d.tool || ''}
          </span>
          <span class="text-[10px] text-muted uppercase tracking-wider">MCP CALL</span>
        </div>
        <div class="text-[11.5px] text-ink-2 mb-1">${d.purpose || 'Traversing FalkorDB supply chain topology'}</div>
        <div class="text-[10px] text-muted bg-surface/80 rounded px-1.5 py-0.5 font-mono break-all">${inputStr}</div>
      `;
    } else if (evt === 'tool_result') {
      row.className += " border-healthy/30 bg-healthy/5 text-ink";
      let resultSummary = '';
      if (typeof d.result === 'object' && d.result !== null) {
        if (d.result.error) {
          resultSummary = `<span class="text-critical">Error: ${d.result.error}</span>`;
        } else if (d.result.decision_id) {
          resultSummary = `Decision Committed: <strong class="text-healthy-ink font-bold">${d.result.decision_id}</strong> (${d.result.type}) &bull; Linked Evidence: ${d.result.linked_evidence_count} nodes`;
        } else if (d.result.explanation) {
          resultSummary = `Path Traversed: ${d.result.explanation}`;
        } else if (d.result.shortfall_units !== undefined) {
          resultSummary = `Product: ${d.result.product_id} &bull; Forecast: ${d.result.forecast_30d}u &bull; Shortfall: <strong class="text-critical font-bold">${d.result.shortfall_units}u</strong>`;
        } else if (d.result.affected_customers) {
          resultSummary = `Impact Radius: ${d.result.affected_parts ? d.result.affected_parts.length : 0} parts, ${d.result.affected_products ? d.result.affected_products.length : 0} products, ${d.result.affected_customers.length} enterprise customers`;
        } else if (d.result.available_suppliers_by_lead_time) {
          resultSummary = `Alternate Suppliers: ${d.result.available_suppliers_by_lead_time.map(s => s.name + ' (' + s.lead_time_days + 'd lead)').join(', ')}`;
        } else {
          resultSummary = JSON.stringify(d.result).slice(0, 150) + '...';
        }
      } else {
        resultSummary = String(d.result).slice(0, 150);
      }

      row.innerHTML = `
        <div class="flex items-center justify-between text-healthy font-semibold mb-1">
          <span class="flex items-center gap-1.5">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            FALKORDB RESULT: ${d.tool || ''}
          </span>
          <span class="text-[10px] text-muted font-mono">${d.latency_ms ? d.latency_ms + 'ms' : '<1ms'}</span>
        </div>
        <div class="text-[11.5px] text-ink-2">${resultSummary}</div>
      `;
    } else if (evt === 'agent_thought') {
      row.className += " border-agent/30 bg-agent/5 text-ink";
      row.innerHTML = `
        <div class="text-agent font-semibold text-xs mb-1 flex items-center gap-1.5">
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
          AGENT REASONING
        </div>
        <div class="text-[11.5px] text-ink-2 leading-relaxed">${d.text || ''}</div>
      `;
    } else if (evt === 'agent_report') {
      row.className += " border-warning/40 bg-warning/10 text-ink";
      row.innerHTML = `
        <div class="text-warning font-bold text-xs mb-1.5 flex items-center gap-1.5">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          PRESCRIPTIVE MITIGATION REPORT
        </div>
        <div class="text-[11.5px] text-ink-2 mb-2">${d.summary || 'Completed multi-hop graph analysis. Dispatched mitigation actions.'}</div>
        <div class="text-[10.5px] text-healthy font-semibold">Graph Evidence Generated &bull; Lineage linked in FalkorDB</div>
      `;
      if (typeof loadSubgraph === 'function') loadSubgraph();
    } else if (evt === 'agent_start') {
      row.className += " border-line bg-surface-2/40 text-muted";
      row.innerHTML = `<span class="text-accent font-bold">&bull;</span> <span class="text-ink-2">${d.message || 'Starting agent investigation...'}</span>`;
    } else {
      row.className += " border-line bg-surface-2/40 text-muted";
      row.innerHTML = `<span class="text-ink-2">${JSON.stringify(d)}</span>`;
    }
    logs.appendChild(row);
    logs.scrollTop = logs.scrollHeight;
  };

  evtSource.addEventListener('done', function() {
    evtSource.close();
    if (badge) badge.classList.add('hidden');
    if (runBtn) runBtn.disabled = false;
    if (typeof loadSubgraph === 'function') loadSubgraph();
  });

  evtSource.onerror = function() {
    evtSource.close();
    if (badge) badge.classList.add('hidden');
    if (runBtn) runBtn.disabled = false;
    if (typeof loadSubgraph === 'function') loadSubgraph();
  };
}
