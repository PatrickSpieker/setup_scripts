'use strict';
const report = JSON.parse(document.getElementById('report-data').textContent);
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const nodeModels = [], edgeModels = [];
let scale = 1, offsetX = 0, offsetY = 0, width = 1, height = 1, results = [], resultIndex = -1;
function el(tag, text, className) {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  if (className) item.className = className;
  return item;
}
function svg(tag, attributes) {
  const item = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) item.setAttribute(key, value);
  return item;
}
function details(title, entries) {
  const content = $('detail-content');
  content.replaceChildren(el('h2', title));
  for (const [heading, value] of entries) {
    if (value === undefined || value === '') continue;
    content.append(el('h3', heading), el('p', String(value)));
  }
  $('details').hidden = false;
}
function coverage() {
  details('Coverage', [
    ['Status', report.status === 'exhausted' ? 'Discovered frontier exhausted within scope' : 'Partial report — ' + report.status],
    ['Summary', report.summary],
    ['Scope', Object.entries(report.scope).map(([k, v]) => k + ': ' + (v || 'all discovered')).join(' · ')],
    ['Counts', `${report.states.length} captured states · ${report.actions.filter(a => a.status === 'observed').length} observed interactions · ${report.actions.filter(a => a.status !== 'observed').length} unexplored interactions`],
    ['Coverage boundary', report.remaining_unknown ? 'Additional undiscovered interactions may remain. Pending and uncertain branches are marked on the graph.' : 'Coverage is limited to discovered interactions in the recorded scope, not every theoretical app state.'],
    ['Limits', `States: ${report.limits.states ?? 'none'}; elapsed seconds: ${report.limits.seconds ?? 'none'}`],
    ...report.actions.filter(a => a.status !== 'observed').map(a => [a.label, `${a.reason || 'exploration limit'}: ${a.explanation || (a.status === 'in_flight' ? 'Outcome uncertain; inspect before retrying.' : 'Pending at checkpoint.')}`]),
    ['Test-data restoration', report.changes.length ? 'Changes and restoration outcomes follow.' : 'No test-data changes recorded.'],
    ...report.changes.map(c => [c.description, `${c.status === 'pending' ? 'Not yet restored' : c.status}: ${c.explanation}`])
  ]);
}
function openState(state) {
  details(state.title, [['State ID', state.id], ['URL', state.url], ['Prerequisites', state.prerequisites], ['Observations', state.observations], ['Navigation evidence', state.evidence]]);
}
function openAction(action) {
  details(action.label, [['Action ID', action.id], ['Status', action.status], ['Effect', action.effect], ['Prerequisites', action.prerequisites], ['Discovery', action.provenance], ['Evidence', action.evidence], ['Reason', action.reason], ['Explanation', action.explanation]]);
}
function transform() { $('world').style.transform = `translate(${offsetX}px,${offsetY}px) scale(${scale})`; }
function fit() {
  scale = Math.min(1, ($('viewport').clientWidth - 60) / width, ($('viewport').clientHeight - 60) / height);
  scale = Math.max(0.005, scale);
  offsetX = ($('viewport').clientWidth - width * scale) / 2;
  offsetY = 25;
  transform();
}
function zoom(factor, x = $('viewport').clientWidth / 2, y = $('viewport').clientHeight / 2) {
  const next = Math.max(0.005, Math.min(3, scale * factor));
  offsetX = x - (x - offsetX) * next / scale;
  offsetY = y - (y - offsetY) * next / scale;
  scale = next;
  transform();
}
function focusResult(delta) {
  if (!results.length) return;
  resultIndex = (resultIndex + delta + results.length) % results.length;
  const result = results[resultIndex];
  scale = 0.9;
  offsetX = $('viewport').clientWidth / 2 - result.x * scale;
  offsetY = $('viewport').clientHeight / 2 - result.y * scale;
  transform();
  $('matches').textContent = `${resultIndex + 1}/${results.length}`;
}
function search() {
  const query = $('search').value.trim().toLocaleLowerCase();
  results = [];
  for (const node of nodeModels) {
    const match = Boolean(query) && (node.title + ' ' + node.id).toLocaleLowerCase().includes(query);
    node.element.classList.toggle('match', match);
    if (match) results.push({x: node.x + 140, y: node.y + node.h / 2});
  }
  for (const edge of edgeModels) {
    const match = Boolean(query) && edge.action.label.toLocaleLowerCase().includes(query);
    edge.path.classList.toggle('match', match);
    edge.label.classList.toggle('match', match);
    if (match) results.push({x: edge.labelX + 130, y: edge.labelY + edge.labelH / 2});
  }
  resultIndex = -1;
  $('matches').textContent = query ? `${results.length} matches` : '';
  if (results.length) focusResult(1);
}
async function build() {
  $('title').textContent = report.title;
  document.title = report.title;
  $('scope').textContent = `${report.scope.mode} · ${report.scope.platform} · ${report.scope.role} · ${report.scope.device} · ${report.scope.theme}${report.scope.workflow ? ' · ' + report.scope.workflow : ''} · ${report.status}`;
  $('empty').hidden = Boolean(report.states.length);
  const byId = new Map();
  for (const state of report.states) {
    const article = el('article', undefined, 'node');
    const heading = el('button', undefined, 'heading');
    heading.append(el('h2', state.title), el('small', state.id));
    heading.onclick = () => openState(state);
    const shot = el('button', undefined, 'shot');
    shot.setAttribute('aria-label', 'Enlarge ' + state.title);
    const img = el('img'); img.src = state.image; img.alt = state.title;
    shot.append(img);
    shot.onclick = () => { $('large-image').src = state.image; $('large-image').alt = state.title; $('lightbox').showModal(); };
    article.append(heading, shot); $('nodes').append(article);
    const model = {id: state.id, title: state.title, element: article, rank: null, x: 0, y: 0};
    nodeModels.push(model); byId.set(state.id, model);
  }
  for (const action of report.actions) {
    let destination = action.to;
    if (action.status !== 'observed') {
      destination = 'stub:' + action.id;
      const article = el('article', undefined, 'node stub');
      const reason = action.reason || 'exploration limit';
      const explanation = action.explanation || (action.status === 'in_flight' ? 'Outcome uncertain; inspect before retrying.' : 'Pending when this checkpoint was saved.');
      article.append(el('h2', reason), el('p', explanation), el('small', action.id));
      $('nodes').append(article);
      const model = {id: destination, title: reason, element: article, rank: null, x: 0, y: 0};
      nodeModels.push(model); byId.set(destination, model);
    }
    const source = byId.get(action.from), target = byId.get(destination);
    if (!source || !target) throw new Error('Invalid action endpoint: ' + action.id);
    edgeModels.push({action, source, target});
  }
  await Promise.all([...document.querySelectorAll('.shot img')].map(img => img.decode()));
  // Assign discovery depth, preserving disconnected roots and cycles.
  for (const root of nodeModels) {
    if (root.rank !== null) continue;
    root.rank = 0;
    const queue = [root];
    for (let i = 0; i < queue.length; i++) {
      for (const edge of edgeModels.filter(e => e.source === queue[i])) {
        if (edge.target.rank === null) { edge.target.rank = queue[i].rank + 1; queue.push(edge.target); }
      }
    }
  }
  const rows = [];
  for (const node of nodeModels) { (rows[node.rank] ||= []).push(node); node.h = node.element.offsetHeight; }
  const maxColumns = Math.max(1, ...rows.map(row => row.length));
  const coreWidth = maxColumns * 400;
  const measure = el('div'); measure.id = 'measure'; document.body.append(measure);
  for (const edge of edgeModels) {
    edge.label = el('button', edge.action.label, 'edge-label');
    edge.label.onclick = () => openAction(edge.action);
    measure.append(edge.label); edge.labelH = edge.label.offsetHeight;
    edge.outer = edge.target.rank !== edge.source.rank + 1;
  }
  let y = 45, lane = 0;
  for (let rank = 0; rank < rows.length; rank++) {
    const incoming = edgeModels.filter(e => e.outer && e.target.rank === rank);
    for (const edge of incoming) { edge.entryY = y; y += 30; }
    y += 30;
    const row = rows[rank];
    row.forEach((node, i) => { node.x = (coreWidth - row.length * 400) / 2 + i * 400 + 60; node.y = y; node.element.style.left = node.x + 'px'; node.element.style.top = y + 'px'; });
    y += Math.max(...row.map(node => node.h)) + 35;
    for (const edge of edgeModels.filter(e => e.source.rank === rank)) {
      edge.labelX = edge.source.x + 10; edge.labelY = y;
      edge.routeY = y + edge.labelH / 2;
      if (edge.outer) edge.laneX = coreWidth + 60 + lane++ * 36;
      y += edge.labelH + 30;
    }
    y += 45;
  }
  width = coreWidth + (lane ? 100 + lane * 36 : 0); height = y;
  $('world').style.width = width + 'px'; $('world').style.height = height + 'px';
  $('edges').setAttribute('width', width); $('edges').setAttribute('height', height);
  const defs = svg('defs', {}), marker = svg('marker', {id:'arrow', viewBox:'0 0 10 10', refX:9, refY:5, markerWidth:7, markerHeight:7, orient:'auto-start-reverse'});
  marker.append(svg('path', {d:'M 0 0 L 10 5 L 0 10 z', fill:'#7b90a7'})); defs.append(marker); $('edges').append(defs);
  // Paths first, labels last so every label stays legible above crossing lines.
  for (const edge of edgeModels) {
    const sx = edge.source.x + 140, sy = edge.source.y + edge.source.h;
    const tx = edge.target.x + 140, ty = edge.target.y - 4;
    let d = `M ${sx} ${sy} V ${edge.routeY}`;
    d += edge.outer ? ` H ${edge.laneX} V ${edge.entryY} H ${tx} V ${ty}` : ` H ${tx} V ${ty}`;
    edge.path = svg('path', {d, class:'edge' + (edge.action.status !== 'observed' ? ' pending' : ''), 'marker-end':'url(#arrow)'});
    $('edges').append(edge.path);
  }
  for (const edge of edgeModels) {
    const foreign = svg('foreignObject', {x:edge.labelX, y:edge.labelY, width:260, height:edge.labelH + 2});
    foreign.append(edge.label); $('edges').append(foreign);
  }
  measure.remove();
  scale = Math.max(0.005, Math.min(1, ($('viewport').clientWidth - 60) / width));
  offsetX = ($('viewport').clientWidth - width * scale) / 2; offsetY = 25; transform();
}
$('coverage').onclick = coverage;
$('close-details').onclick = () => { $('details').hidden = true; };
$('close-image').onclick = () => $('lightbox').close();
$('fit').onclick = fit; $('in').onclick = () => zoom(1.3); $('out').onclick = () => zoom(1 / 1.3);
$('search').oninput = search; $('next').onclick = () => focusResult(1); $('previous').onclick = () => focusResult(-1);
$('search').onkeydown = e => { if (e.key === 'Enter') focusResult(e.shiftKey ? -1 : 1); };
let drag = null;
$('viewport').addEventListener('pointerdown', e => {
  if (e.target.closest('button')) return;
  drag = {x:e.clientX, y:e.clientY, ox:offsetX, oy:offsetY};
  $('viewport').setPointerCapture(e.pointerId); $('viewport').classList.add('dragging');
});
$('viewport').addEventListener('pointermove', e => { if (drag) { offsetX = drag.ox + e.clientX - drag.x; offsetY = drag.oy + e.clientY - drag.y; transform(); } });
for (const event of ['pointerup', 'pointercancel']) $('viewport').addEventListener(event, () => { drag = null; $('viewport').classList.remove('dragging'); });
$('viewport').addEventListener('wheel', e => { e.preventDefault(); const r = $('viewport').getBoundingClientRect(); zoom(Math.exp(-e.deltaY * 0.001), e.clientX - r.left, e.clientY - r.top); }, {passive:false});
$('viewport').addEventListener('keydown', e => {
  if (e.target !== $('viewport')) return;
  if (e.key === '+' || e.key === '=') zoom(1.3);
  else if (e.key === '-') zoom(1 / 1.3);
  else if (e.key === '0') fit();
  else if (e.key.startsWith('Arrow')) { e.preventDefault(); offsetX += e.key === 'ArrowLeft' ? 50 : e.key === 'ArrowRight' ? -50 : 0; offsetY += e.key === 'ArrowUp' ? 50 : e.key === 'ArrowDown' ? -50 : 0; transform(); }
});
function resizeViewport() { $('viewport').style.height = Math.max(120, innerHeight - document.querySelector('header').offsetHeight) + 'px'; }
window.addEventListener('resize', resizeViewport);
new ResizeObserver(resizeViewport).observe(document.querySelector('header'));
resizeViewport();
build().catch(error => details('Report could not render', [['Error', error.message]]));
