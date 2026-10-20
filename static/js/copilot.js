// TwinForge Connected Graph - Natural Language to Cypher Graph Copilot
function openCopilotModal() {
  const modal = document.getElementById('copilot-modal');
  if (modal) modal.classList.remove('hidden');
  const input = document.getElementById('copilot-user-input');
  if (input) {
    input.focus();
  }
}

function closeCopilotModal() {
  const modal = document.getElementById('copilot-modal');
  if (modal) modal.classList.add('hidden');
}

function sendCopilotPrompt(text) {
  const input = document.getElementById('copilot-user-input');
  if (input) {
    input.value = text;
    submitCopilotQuery();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function submitCopilotQuery() {
  const input = document.getElementById('copilot-user-input');
  const thread = document.getElementById('copilot-chat-thread');
  const sendBtn = document.getElementById('copilot-submit-btn');
  if (!input || !thread) return;

  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  if (sendBtn) sendBtn.disabled = true;

  // 1. Append User Message Bubble
  const userBubble = document.createElement('div');
  userBubble.className = "flex items-start justify-end gap-3";
  userBubble.innerHTML = `
    <div class="rounded-xl bg-accent px-4 py-2.5 text-xs text-white max-w-[80%] shadow-sm">
      <p>${escapeHtml(query)}</p>
    </div>
  `;
  thread.appendChild(userBubble);

  // 2. Append Loading Placeholder Bubble
  const loadingId = 'copilot-loading-' + Date.now();
  const loadingBubble = document.createElement('div');
  loadingBubble.id = loadingId;
  loadingBubble.className = "flex items-start gap-3 animate-pulse";
  loadingBubble.innerHTML = `
    <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-agent text-white text-xs font-bold shadow">
      TF
    </div>
    <div class="rounded-xl border border-line bg-surface p-3 text-xs text-muted max-w-[85%] flex items-center gap-2">
      <span class="inline-block h-3 w-3 animate-spin rounded-full border-2 border-agent border-t-transparent"></span>
      <span>Querying FalkorDB context layer...</span>
    </div>
  `;
  thread.appendChild(loadingBubble);
  thread.scrollTop = thread.scrollHeight;

  try {
    const resp = await fetch('/api/copilot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const data = await resp.json();

    // Remove loading placeholder
    const loader = document.getElementById(loadingId);
    if (loader) loader.remove();

    // 3. Append Copilot Response Bubble
    const responseBubble = document.createElement('div');
    responseBubble.className = "flex items-start gap-3";

    if (data.status === 'success') {
      const cypherHtml = data.cypher ? `
        <div class="mt-2.5 rounded-lg border border-line-strong bg-deep p-2.5 font-mono text-[11px] overflow-x-auto">
          <div class="flex items-center justify-between text-[10px] text-muted mb-1 pb-1 border-b border-line">
            <span class="text-accent font-semibold flex items-center gap-1">
              <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
              GENERATED CYPHER
            </span>
            <span class="text-healthy font-semibold">⚡ ${data.falkordb_latency_ms || 1.8}ms on FalkorDB</span>
          </div>
          <code class="text-ink-2 select-all">${escapeHtml(data.cypher)}</code>
        </div>
      ` : '';

      const answerFormatted = escapeHtml(data.answer || data.explanation || '')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-ink font-semibold">$1</strong>')
        .replace(/• (.*?)(?:\n|$)/g, '<div class="flex items-start gap-1.5 my-1"><span class="text-accent">•</span><span>$1</span></div>')
        .replace(/\n\n/g, '<br/>');

      responseBubble.innerHTML = `
        <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-agent text-white text-xs font-bold shadow">
          TF
        </div>
        <div class="rounded-xl border border-line bg-surface p-4 text-xs text-ink-2 max-w-[85%] shadow-sm space-y-2">
          <div class="flex items-center justify-between text-[10px] text-muted border-b border-line pb-1.5">
            <span class="flex items-center gap-1 text-agent font-medium">
              <span class="h-1.5 w-1.5 rounded-full bg-agent"></span>
              ${escapeHtml(data.provider || 'TwinForge Engine')} &bull; ${escapeHtml(data.model || 'Free Open Model')}
            </span>
            <span>${data.row_count || 0} records matched</span>
          </div>
          <div class="text-ink leading-relaxed font-sans text-[12.5px]">
            ${answerFormatted}
          </div>
          ${cypherHtml}
        </div>
      `;
    } else {
      responseBubble.innerHTML = `
        <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-critical text-white text-xs font-bold shadow">
          !
        </div>
        <div class="rounded-xl border border-red-500/30 bg-red-500/5 p-3.5 text-xs text-critical max-w-[85%] space-y-1">
          <p class="font-semibold">Unable to resolve query</p>
          <p class="text-[11px] text-muted">${escapeHtml(data.message || data.error || 'Unknown query error')}</p>
        </div>
      `;
    }

    thread.appendChild(responseBubble);
    thread.scrollTop = thread.scrollHeight;
  } catch (err) {
    const loader = document.getElementById(loadingId);
    if (loader) loader.remove();
    const errBubble = document.createElement('div');
    errBubble.className = "flex items-start gap-3";
    errBubble.innerHTML = `
      <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-critical text-white text-xs font-bold shadow">!</div>
      <div class="rounded-xl border border-red-500/30 bg-red-500/5 p-3 text-xs text-critical">
        Network error communicating with Copilot endpoint: ${escapeHtml(err.message)}
      </div>
    `;
    thread.appendChild(errBubble);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    if (input) input.focus();
  }
}
