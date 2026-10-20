// TwinForge Connected Graph - Vis.js Interactive Evidence Graph Network
let visNetworkInstance = null;

async function loadSubgraph() {
  const container = document.getElementById('subgraph-vis-container');
  if (!container) return;

  try {
    const res = await fetch('/api/subgraph');
    const data = await res.json();
    if (!data.nodes || !data.nodes.length) {
      container.innerHTML = '<div class="h-full flex items-center justify-center text-muted font-mono text-xs">Run agent investigation to generate evidence nodes.</div>';
      return;
    }

    if (typeof vis === 'undefined') {
      console.warn('Vis.js library is not loaded');
      return;
    }

    const nodes = new vis.DataSet(data.nodes);
    const edges = new vis.DataSet(data.edges);
    const options = {
      nodes: { borderWidth: 1.5, shadow: true },
      edges: { smooth: { type: 'cubicBezier' }, font: { color: '#94a3b8', size: 10 } },
      physics: { stabilization: true, barnesHut: { gravitationalConstant: -3500 } }
    };
    visNetworkInstance = new vis.Network(container, { nodes, edges }, options);
  } catch (e) {
    console.error('Error loading Vis.js evidence subgraph:', e);
  }
}
