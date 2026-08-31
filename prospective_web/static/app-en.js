"use strict";

const state = { dashboard: null, region: "all", points: [] };
const canvas = document.getElementById("score-chart");
const context = canvas.getContext("2d");
const stage = document.getElementById("chart-stage");
const tooltip = document.getElementById("chart-tooltip");

async function loadDashboard() {
  const refresh = document.getElementById("refresh-button");
  refresh.classList.add("loading");
  hideError();
  try {
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.dashboard = await response.json();
    renderAll();
  } catch (error) {
    showError(`Dashboard data could not be loaded: ${error.message}`);
    setText("status-label", "Data unavailable");
    document.getElementById("status-dot").className = "attention";
  } finally {
    refresh.classList.remove("loading");
  }
}

function renderAll() {
  renderStatus();
  renderDryRun();
  renderFilters();
  renderMetrics();
  renderChart();
  renderRegions();
  renderScores();
  renderProtocol();
}

function renderDryRun() {
  const progress = state.dashboard.dry_run;
  const notice = document.getElementById("run-notice");
  const copy = {
    awaiting_scores: ["Dry run started", "Waiting for the first completed target-day score."],
    running: ["Dry run in progress", `${progress.provisional_days}/${progress.planned_days} common target days scored.`],
    settling: ["14-day dry run completed", `Waiting for final score settlement: ${progress.final_days}/${progress.planned_days} days.`],
    complete: ["Dry run complete", `${progress.final_days}/${progress.planned_days} final daily scores are ready for review.`],
  }[progress.phase];
  const shownDays = progress.phase === "settling" || progress.phase === "complete" ? progress.final_days : progress.provisional_days;
  notice.className = `run-notice ${progress.phase.replace("_", "-")}`;
  setText("run-eyebrow", progress.phase === "complete" ? "COMPLETE" : progress.phase === "settling" ? "SETTLEMENT" : "DRY RUN");
  setText("run-title", copy[0]);
  setText("run-detail", copy[1]);
  setText("run-progress-label", `${shownDays}/${progress.planned_days} days`);
  document.getElementById("run-progress-bar").style.width = `${Math.min(100, shownDays / progress.planned_days * 100)}%`;
}

function renderStatus() {
  const ok = state.dashboard.pipeline_status === "ok";
  const invalid = state.dashboard.pooled_primary_claim_status === "inconclusive";
  setText("status-label", invalid ? "Primary claim inconclusive" : ok ? "Pipeline operational" : "Review required");
  setText("updated-label", `${formatDateTime(state.dashboard.generated_at)} UTC`);
  document.getElementById("status-dot").className = ok ? "ok" : "attention";
}

function selectedScores(revision = "provisional") {
  return state.dashboard.daily_scores.filter((score) =>
    score.revision === revision && (state.region === "all" || score.region_id === state.region)
  );
}

function aggregate(scores) {
  const events = scores.reduce((sum, score) => sum + score.event_count, 0);
  const gain = scores.reduce((sum, score) => sum + score.total_gain, 0);
  const mean = events ? gain / events : null;
  return { days: new Set(scores.map((score) => score.target_date)).size, events, gain, mean };
}

function renderFilters() {
  const labels = [["all", "All"], ...state.dashboard.regions.map((region) => [region.region_id, shortRegion(region.name)])];
  const control = document.getElementById("region-filter");
  control.replaceChildren();
  labels.forEach(([id, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `segment${state.region === id ? " active" : ""}`;
    button.textContent = label;
    button.addEventListener("click", () => { state.region = id; renderAll(); });
    control.appendChild(button);
  });
}

function renderMetrics() {
  const provisional = aggregate(selectedScores());
  setText("metric-target", state.dashboard.latest_target_start ? formatDate(state.dashboard.latest_target_start) : "Pending");
  setText("metric-regions", `${state.dashboard.published_regions}/3`);
  setText("metric-igpe", formatGain(provisional.mean));
  setText("metric-factor", provisional.mean === null ? "relative to ETAS" : `${formatFactor(Math.exp(provisional.mean))} relative factor`);
  setText("metric-events", formatInteger(provisional.events));
  setText("metric-days", `${state.dashboard.dry_run.provisional_days}/${state.dashboard.dry_run.planned_days} common days`);
  renderSummary("provisional", aggregate(selectedScores("provisional")));
  renderSummary("final", aggregate(selectedScores("final")));
  setText("incident-count", formatInteger(state.dashboard.open_incidents));
  setText("incident-detail", state.dashboard.open_incidents ? "Open records require review" : "No open warnings");
}

function renderSummary(id, value) {
  setText(`${id}-score`, formatGain(value.mean));
  setText(`${id}-detail`, value.days ? `${value.events} events · ${formatSigned(value.gain)} total` : (id === "final" ? "7-day settlement window" : "No score yet"));
}

function renderChart() {
  const scores = selectedScores().sort((a, b) => a.target_date.localeCompare(b.target_date));
  document.getElementById("chart-empty").classList.toggle("hidden", scores.length > 0);
  const total = aggregate(scores);
  setText("chart-total", total.mean === null ? "—" : `${formatSigned(total.mean)} IGPE`);
  setText("chart-subtitle", `${state.region === "all" ? "All regions" : regionName(state.region)} · provisional`);
  resizeCanvas();
}

function resizeCanvas() {
  const rect = stage.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  drawChart(rect.width, rect.height);
}

function drawChart(width, height) {
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#fbfcfb";
  context.fillRect(0, 0, width, height);
  const scores = selectedScores().sort((a, b) => a.target_date.localeCompare(b.target_date));
  state.points = [];
  if (!scores.length) return;
  const padding = { left: 48, right: 18, top: 22, bottom: 35 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const values = scores.map((score) => score.mean_igpe || 0);
  const extent = Math.max(0.002, ...values.map(Math.abs)) * 1.2;
  const y = (value) => padding.top + (extent - value) / (extent * 2) * innerHeight;
  const zero = y(0);
  context.strokeStyle = "#d6dedb";
  context.lineWidth = 1;
  [-extent, 0, extent].forEach((value) => {
    context.beginPath(); context.moveTo(padding.left, y(value)); context.lineTo(width - padding.right, y(value)); context.stroke();
    context.fillStyle = "#68736f"; context.font = "9px system-ui"; context.textAlign = "right"; context.fillText(value.toFixed(3), padding.left - 7, y(value) + 3);
  });
  const slot = innerWidth / scores.length;
  const barWidth = Math.max(4, Math.min(28, slot * 0.58));
  scores.forEach((score, index) => {
    const value = score.mean_igpe || 0;
    const x = padding.left + slot * index + slot / 2;
    const top = Math.min(zero, y(value));
    const barHeight = Math.max(1, Math.abs(y(value) - zero));
    context.fillStyle = value >= 0 ? "#087f7a" : "#cf5b4c";
    context.fillRect(x - barWidth / 2, top, barWidth, barHeight);
    state.points.push({ x, y: top, width: barWidth, height: barHeight, score });
    if (scores.length <= 14 || index % Math.ceil(scores.length / 10) === 0) {
      context.save(); context.translate(x, height - 9); context.rotate(-0.45); context.fillStyle = "#68736f"; context.font = "9px system-ui"; context.textAlign = "right"; context.fillText(formatShortDate(score.target_date), 0, 0); context.restore();
    }
  });
}

function renderRegions() {
  const body = document.getElementById("regions-body");
  body.replaceChildren();
  state.dashboard.regions.forEach((region) => {
    const row = document.createElement("tr");
    const forecast = region.latest_forecast;
    row.append(
      cell(primary(region.name, `M≥${region.minimum_magnitude.toFixed(1)} · ${region.catalog_source}`)),
      cell(status(forecast, region.operations)),
      cell(forecast ? formatDate(forecast.target_start) : "—"),
      cell(primary(region.latest_catalog ? formatDateTime(region.latest_catalog.cutoff) : "—", region.latest_catalog ? `${region.latest_catalog.window_events} events / 30 days` : "No snapshot")),
      cell(scoreValue(region.provisional)),
      cell(scoreValue(region.final)),
    );
    body.appendChild(row);
  });
}

function renderScores() {
  const body = document.getElementById("scores-body");
  const scores = [...state.dashboard.daily_scores].sort((a, b) => b.target_date.localeCompare(a.target_date) || a.region_id.localeCompare(b.region_id));
  body.replaceChildren();
  document.getElementById("scores-empty").classList.toggle("hidden", scores.length > 0);
  scores.forEach((score) => {
    const row = document.createElement("tr");
    row.append(
      cell(formatDate(score.target_date)), cell(regionName(score.region_id)), cell(score.revision === "final" ? "Final" : "Provisional"),
      cell(formatInteger(score.event_count)), cell(formatSigned(score.total_gain)), cell(formatGain(score.mean_igpe)), cell(resultLabel(score.mean_igpe)),
    );
    body.appendChild(row);
  });
}

function renderProtocol() {
  const protocol = state.dashboard.protocol;
  const facts = document.getElementById("protocol-facts");
  facts.replaceChildren();
  [["Identifier", protocol.protocol_id], ["Mode", "14-day dry run"], ["Prospective claim", protocol.counts_toward_prospective_claim ? "Included" : "Not included"], ["Regions", "3"], ["Final delay", `${protocol.settled_score_delay_days} days`]].forEach(([label, value]) => {
    const div = document.createElement("div"); const dt = document.createElement("dt"); const dd = document.createElement("dd"); dt.textContent = label; dd.textContent = value; div.append(dt, dd); facts.appendChild(div);
  });
  const regions = document.getElementById("protocol-regions");
  regions.replaceChildren();
  state.dashboard.regions.forEach((region) => {
    const item = document.createElement("div"); item.className = "protocol-region";
    const copy = document.createElement("div"); const title = document.createElement("strong"); const detail = document.createElement("small");
    title.textContent = region.name; detail.textContent = depthLabel(region); copy.append(title, detail);
    const magnitude = document.createElement("span"); magnitude.textContent = `M≥${region.minimum_magnitude.toFixed(1)}`;
    item.append(copy, magnitude); regions.appendChild(item);
  });
}

function handleChartPointer(event) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const point = state.points.find((item) => Math.abs(item.x - x) <= Math.max(9, item.width));
  if (!point) { tooltip.classList.remove("visible"); return; }
  tooltip.innerHTML = `<strong>${formatDate(point.score.target_date)}</strong><br>${regionName(point.score.region_id)} · ${formatGain(point.score.mean_igpe)} IGPE<br>${point.score.event_count} events`;
  tooltip.style.left = `${Math.min(point.x + 10, rect.width - 150)}px`;
  tooltip.style.top = `${Math.max(point.y - 50, 8)}px`;
  tooltip.classList.add("visible");
}

function primary(titleText, detailText) { const wrap = document.createElement("div"); wrap.className = "primary-cell"; const title = document.createElement("strong"); const detail = document.createElement("small"); title.textContent = titleText; detail.textContent = detailText; wrap.append(title, detail); return wrap; }
function status(forecast, operations) { const span = document.createElement("span"); const invalid = operations && !operations.primary_eligible; span.className = `status-pill${forecast && forecast.status === "published" && !invalid ? "" : " waiting"}`; span.textContent = invalid ? "Primary ineligible" : forecast && forecast.status === "published" ? "Published" : "Pending"; return span; }
function scoreValue(summary) { if (!summary.days) return "Pending"; const span = document.createElement("span"); span.className = gainClass(summary.mean_igpe); span.textContent = `${formatGain(summary.mean_igpe)} · ${summary.events} events`; return span; }
function resultLabel(value) { if (value === null) return "No events"; const span = document.createElement("span"); span.className = gainClass(value); span.textContent = value > 0 ? "CH-008" : value < 0 ? "ETAS" : "Tie"; return span; }
function cell(content) { const td = document.createElement("td"); if (content instanceof Node) td.appendChild(content); else td.textContent = content; return td; }
function gainClass(value) { return value > 0 ? "gain-positive" : value < 0 ? "gain-negative" : "gain-neutral"; }
function regionName(id) { return state.dashboard.regions.find((region) => region.region_id === id)?.name || id; }
function shortRegion(name) { return name.includes("California") ? "California" : name.includes("Zealand") ? "New Zealand" : "Chile"; }
function depthLabel(region) { const min = region.minimum_depth_km ?? 0; return region.maximum_depth_km === null ? `${min}+ km depth` : `${min}–${region.maximum_depth_km} km depth`; }
function formatGain(value) { return value === null || value === undefined ? "—" : formatSigned(value, 4); }
function formatSigned(value, digits = 3) { return `${value > 0 ? "+" : ""}${Number(value).toFixed(digits)}`; }
function formatFactor(value) { return `${Number(value).toFixed(4)}×`; }
function formatInteger(value) { return new Intl.NumberFormat("en-GB").format(value); }
function formatDate(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(value)); }
function formatShortDate(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" }).format(new Date(value)); }
function formatDateTime(value) { return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hour12: false }).format(new Date(value)); }
function setText(id, value) { document.getElementById(id).textContent = value; }
function showError(message) { const banner = document.getElementById("error-banner"); banner.textContent = message; banner.classList.add("visible"); }
function hideError() { document.getElementById("error-banner").classList.remove("visible"); }

document.querySelectorAll(".tab").forEach((button) => {
  if (!button.dataset.view) return;
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab[data-view]").forEach((item) => { const active = item === button; item.classList.toggle("active", active); item.setAttribute("aria-selected", String(active)); });
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    document.getElementById(`${button.dataset.view}-view`).classList.add("active");
    if (button.dataset.view === "overview") requestAnimationFrame(resizeCanvas);
  });
});
document.getElementById("refresh-button").addEventListener("click", loadDashboard);
canvas.addEventListener("pointermove", handleChartPointer);
canvas.addEventListener("pointerleave", () => tooltip.classList.remove("visible"));
new ResizeObserver(resizeCanvas).observe(stage);
loadDashboard();
