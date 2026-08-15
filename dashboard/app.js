
const visionStream = document.getElementById('vision-stream');
let selectedVideoUrl = null;

async function startVision() {
  const fileInput = document.getElementById('vision-file');
  const file = fileInput.files[0];
  if (!file) {
    alert('Choose a crowd/CCTV video first.');
    return;
  }
  const profile = document.getElementById('vision-profile').value;
  const threshold = document.getElementById('vision-threshold').value;
  const scale = document.getElementById('vision-scale').value;

  if (selectedVideoUrl) URL.revokeObjectURL(selectedVideoUrl);
  selectedVideoUrl = URL.createObjectURL(file);
  const source = document.getElementById('source-video');
  source.src = selectedVideoUrl;
  source.play().catch(() => {});

  const statusEl = document.getElementById('vision-status');
  statusEl.textContent = 'UPLOADING…';

  try {
    const params = new URLSearchParams({
      profile,
      threshold,
      scale,
      filename: file.name
    });
    const res = await fetch('/api/vision/upload?' + params.toString(), {
      method: 'POST',
      headers: {'Content-Type': 'application/octet-stream'},
      body: file
    });
    const result = await res.json();
    if (!result.ok) throw new Error(result.error || 'Vision start failed');

    visionStream.src = '/api/vision/stream?ts=' + Date.now();
  } catch (err) {
    statusEl.textContent = 'ERROR';
    alert(err.message);
  }
}

async function stopVision() {
  await fetch('/api/vision/stop', {method: 'POST'});
  visionStream.removeAttribute('src');
  document.getElementById('vision-status').textContent = 'OFFLINE';
}

async function pollVision() {
  try {
    const res = await fetch('/api/vision/status');
    const v = await res.json();

    document.getElementById('vision-status').textContent =
      v.error ? 'ERROR' : (v.running ? (v.alert ? 'BOTTLENECK' : 'TRACKING') : 'OFFLINE');

    document.getElementById('vision-count').textContent = v.detected_people ?? 0;
    document.getElementById('vision-occupancy').textContent =
      (v.calibrated_occupancy ?? 0).toLocaleString();
    document.getElementById('vision-fps').textContent = v.fps ?? 0;

    const action = document.getElementById('vision-action');
    if (v.error) {
      action.textContent = v.error;
      action.style.color = '#FF5C52';
    } else if (v.alert) {
      action.textContent = v.recommendation + '  ·  ' + v.direction;
      action.style.color = '#00D4FF';
    } else {
      action.textContent = 'TRACK CLEAR · monitoring ' + (v.profile_label || '');
      action.style.color = '#17C964';
    }
  } catch (_) {}
}

document.getElementById('vision-start').addEventListener('click', startVision);
document.getElementById('vision-stop').addEventListener('click', stopVision);

const POLL_MS = 1000;

const canvas = document.getElementById('venue-canvas');
const ctx = canvas.getContext('2d');
const sparkCanvas = document.getElementById('spark-canvas');
const sparkCtx = sparkCanvas.getContext('2d');

const LOS_COLOR = {
  comfortable: '#17C964',
  busy: '#9FE870',
  congested: '#FF8A1E',
  at_risk: '#FF3B30',
  crush_risk: '#FF3B30',
};

const PHASE_LABEL = {
  0: 'GATES OPEN — FANS ARRIVING',
};

let occHistory = [];
let lastState = null;

function resizeCanvases() {
  for (const c of [canvas, sparkCanvas]) {
    const rect = c.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.max(1, rect.width * dpr);
    c.height = Math.max(1, rect.height * dpr);
  }
  if (lastState) render(lastState);
}
window.addEventListener('resize', resizeCanvases);

function fmtClock(simTimeS) {
  const m = Math.floor(simTimeS / 60).toString().padStart(2, '0');
  const s = Math.floor(simTimeS % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function phaseLabel(phase) {
  if (phase.egress_intensity >= 0.4) return 'CHEQUERED FLAG — MASS EGRESS';
  if (phase.egress_intensity > 0) return 'RACE IN PROGRESS';
  if (phase.gate_inflow_ppl_per_min > 0) return 'GATES OPEN — FANS ARRIVING';
  return 'STEADY STATE';
}

function mapVenueToCanvas(zones, w, h) {
  const xs = zones.map(z => z.x), ys = zones.map(z => z.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 60;
  const sx = (w - pad * 2) / (maxX - minX || 1);
  const sy = (h - pad * 2) / (maxY - minY || 1);
  const s = Math.min(sx, sy);
  return zones.reduce((acc, z) => {
    acc[z.id] = {
      x: pad + (z.x - minX) * s,
      y: pad + (z.y - minY) * s,
    };
    return acc;
  }, {});
}

function render(state) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.scale(dpr, dpr);
  const cw = w / dpr, ch = h / dpr;

  const pos = mapVenueToCanvas(state.zones, cw, ch);
  const zoneById = Object.fromEntries(state.zones.map(z => [z.id, z]));

  // faint track-map background grid, on-theme with a circuit telemetry screen
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 1;
  for (let gx = 0; gx < cw; gx += 40) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, ch); ctx.stroke(); }
  for (let gy = 0; gy < ch; gy += 40) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(cw, gy); ctx.stroke(); }

  // edges
  for (const e of state.edges) {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) continue;
    const util = e.capacity_ppl_per_min > 0 ? e.flow_ppl_per_min / e.capacity_ppl_per_min : 0;
    const boosted = e.steer_bias > 1.05;
    const throttled = e.steer_bias < 0.95;

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    if (boosted) {
      ctx.strokeStyle = '#00D4FF';
      ctx.lineWidth = 2 + Math.min(util, 1) * 4;
      ctx.shadowColor = '#00D4FF'; ctx.shadowBlur = 8;
    } else if (throttled) {
      ctx.strokeStyle = 'rgba(255,59,48,0.35)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.shadowBlur = 0;
    } else {
      ctx.strokeStyle = 'rgba(232,236,239,0.18)';
      ctx.lineWidth = 1 + Math.min(util, 1) * 3;
      ctx.shadowBlur = 0;
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.shadowBlur = 0;
  }

  // zones
  for (const z of state.zones) {
    const p = pos[z.id];
    if (!p) continue;
    const r = 14 + Math.sqrt(z.capacity) * 0.55;
    const color = LOS_COLOR[z.los] || '#666';
    const fillPct = Math.min(1, z.occupancy / z.capacity);

    // base ring
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.04)';
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = color;
    ctx.stroke();

    // fill wedge = occupancy / capacity
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.arc(p.x, p.y, r - 3, -Math.PI / 2, -Math.PI / 2 + fillPct * Math.PI * 2);
    ctx.closePath();
    ctx.fillStyle = color + '55';
    ctx.fill();

    if (z.los === 'at_risk' || z.los === 'crush_risk') {
      ctx.beginPath();
      const pulse = 3 + 2 * Math.sin(Date.now() / 180);
      ctx.arc(p.x, p.y, r + pulse, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,59,48,0.5)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.fillStyle = '#E8ECEF';
    ctx.font = '600 11px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(z.name, p.x, p.y + r + 14);

    ctx.font = '700 11px ui-monospace, monospace';
    ctx.fillStyle = color;
    ctx.fillText(z.occupancy.toLocaleString(), p.x, p.y + 4);
  }

  ctx.restore();
}

function renderSparkline() {
  const dpr = window.devicePixelRatio || 1;
  const w = sparkCanvas.width, h = sparkCanvas.height;
  sparkCtx.clearRect(0, 0, w, h);
  if (occHistory.length < 2) return;
  sparkCtx.save();
  sparkCtx.scale(dpr, dpr);
  const cw = w / dpr, ch = h / dpr;
  const max = Math.max(...occHistory, 1);
  sparkCtx.beginPath();
  occHistory.forEach((v, i) => {
    const x = (i / (occHistory.length - 1)) * cw;
    const y = ch - (v / max) * (ch - 4) - 2;
    i === 0 ? sparkCtx.moveTo(x, y) : sparkCtx.lineTo(x, y);
  });
  sparkCtx.strokeStyle = '#00D4FF';
  sparkCtx.lineWidth = 1.5;
  sparkCtx.stroke();
  sparkCtx.restore();
}


function updateVisionFromState(state) {
  const v = state.vision;
  if (!v) return;
  const statusEl = document.getElementById('vision-status');
  statusEl.textContent = v.error ? 'ERROR' : (v.running ? (v.alert ? 'BOTTLENECK' : 'TRACKING') : 'OFFLINE');
  if (v.alert) {
    const action = document.getElementById('vision-action');
    action.textContent = v.recommendation + ' · ' + v.direction;
    action.style.color = '#00D4FF';
  }
}

function updatePanels(state) {
  document.getElementById('phase-chip').textContent = phaseLabel(state.phase);
  document.getElementById('sim-clock').textContent = fmtClock(state.sim_time_s);
  document.getElementById('occ-current').textContent = state.total_occupancy.toLocaleString();
  const cap = state.zones.reduce((a, z) => a + z.capacity, 0);
  document.getElementById('occ-cap').textContent = cap.toLocaleString();

  const alertsEl = document.getElementById('alerts-list');
  document.getElementById('alert-count').textContent = state.alerts.length;
  alertsEl.innerHTML = '';
  if (state.alerts.length === 0) {
    alertsEl.innerHTML = '<div class="empty-state">No congestion forecasted. Track is clear.</div>';
  } else {
    for (const a of state.alerts) {
      const div = document.createElement('div');
      div.className = 'alert-card' + (a.severity < 1.3 ? ' sev-mid' : '');
      div.innerHTML = `
        <div class="a-zone">${a.zone_name}</div>
        <div class="a-meta">
          <span>${a.los_now} → <b style="color:#FF3B30">${a.los_predicted}</b></span>
          <span class="a-sev">T-${a.lead_time_s}s</span>
        </div>
        <div class="a-meta"><span>density ${a.current_density.toFixed(1)} → ${a.predicted_density.toFixed(1)} ppl/m²</span></div>`;
      alertsEl.appendChild(div);
    }
  }

  const reroutesEl = document.getElementById('reroute-list');
  document.getElementById('reroute-count').textContent = state.reroutes.length;
  reroutesEl.innerHTML = '';
  if (state.reroutes.length === 0) {
    reroutesEl.innerHTML = '<div class="empty-state">No rerouting active.</div>';
  } else {
    for (const r of state.reroutes) {
      const div = document.createElement('div');
      div.className = 'reroute-card';
      div.innerHTML = `<div>Diverting flow away from <b>${r.bottleneck_zone}</b></div>
        <div class="r-path">${r.suggested_via}</div>`;
      reroutesEl.appendChild(div);
    }
  }
}

async function poll() {
  try {
    const res = await fetch('/api/state');
    const state = await res.json();
    lastState = state;
    occHistory.push(state.total_occupancy);
    if (occHistory.length > 120) occHistory.shift();
    render(state);
    renderSparkline();
    updatePanels(state);
    updateVisionFromState(state);
  } catch (err) {
    document.getElementById('phase-chip').textContent = 'DISCONNECTED';
  }
}

document.getElementById('reset-btn').addEventListener('click', async () => {
  await fetch('/api/reset');
  occHistory = [];
});

resizeCanvases();
poll();
setInterval(poll, POLL_MS);
