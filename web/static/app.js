"use strict";

const state = {
  snapshot: null,
  thresholdIndex: 0,
  metric: "probability",
  showEvents: true,
  hoveredCell: null,
};

const canvas = document.getElementById("forecast-map");
const context = canvas.getContext("2d");
const tooltip = document.getElementById("map-tooltip");
const stage = document.getElementById("map-stage");

const testNames = {
  number: ["Number test", "Gözlenen olay sayısı"],
  spatial: ["Spatial test", "Uzamsal rate dağılımı"],
  pseudolikelihood: ["Pseudolikelihood", "Hücre bazlı likelihood"],
  magnitude: ["Magnitude test", "Frekans–magnitude dağılımı"],
};

async function loadSnapshot() {
  hideError();
  document.getElementById("map-loading").classList.remove("hidden");
  try {
    const response = await fetch("/api/forecast", { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.snapshot = await response.json();
    state.thresholdIndex = 0;
    renderAll();
    document.getElementById("map-loading").classList.add("hidden");
  } catch (error) {
    showError(`Forecast snapshot yüklenemedi: ${error.message}`);
    document.getElementById("map-loading").textContent = "Snapshot kullanılamıyor";
  }
}

function renderAll() {
  renderThresholdControl();
  renderSummary();
  renderFacts();
  renderHotspots();
  renderValidation();
  renderParameters();
  resizeAndDraw();
}

function renderThresholdControl() {
  const control = document.getElementById("threshold-control");
  control.replaceChildren();
  state.snapshot.grid.thresholds.forEach((threshold, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `segment${index === state.thresholdIndex ? " active" : ""}`;
    button.textContent = `M≥${formatMagnitude(threshold)}`;
    button.addEventListener("click", () => {
      state.thresholdIndex = index;
      renderThresholdControl();
      renderSummary();
      renderHotspots();
      drawMap();
    });
    control.appendChild(button);
  });
}

function renderSummary() {
  const summary = state.snapshot.grid.summaries[state.thresholdIndex];
  const m4 = state.snapshot.grid.summaries.find((item) => item.threshold === 4);
  setText("mean-count", summary.mean_count.toFixed(2));
  setText("mean-threshold", `M≥${formatMagnitude(summary.threshold)} / 24 saat`);
  setText("any-probability", formatPercent(summary.probability_at_least_one));
  setText("count-range", `${formatCount(summary.count_quantiles["2.5"])}–${formatCount(summary.count_quantiles["97.5"])}`);
  setText("m4-probability", formatPercent(m4.probability_at_least_one));
}

function renderFacts() {
  const { forecast, catalog } = state.snapshot;
  setText("issue-label", `${formatDate(forecast.issue_time)} · 24 saat`);
  setText("window-label", `${formatDateTime(forecast.issue_time)} → ${formatDateTime(forecast.window_end_exclusive)}`);
  setText("fact-issue", formatDateTime(forecast.issue_time));
  setText("fact-simulations", formatInteger(forecast.n_simulations));
  setText("fact-history", formatInteger(catalog.history_events));
  setText("fact-last-event", formatDateTime(catalog.last_history_event));
}

function renderHotspots() {
  const list = document.getElementById("hotspot-list");
  const index = state.thresholdIndex;
  const metric = state.metric;
  const sorted = [...state.snapshot.grid.cells]
    .sort((a, b) => b[metric][index] - a[metric][index])
    .slice(0, 6);
  list.replaceChildren();
  sorted.forEach((cell) => {
    const item = document.createElement("li");
    const location = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = coordinateLabel(cell);
    const detail = document.createElement("small");
    detail.textContent = `${cell.latitude.toFixed(2)}°N · ${Math.abs(cell.longitude).toFixed(2)}°W`;
    location.append(title, detail);
    const value = document.createElement("span");
    value.className = "hotspot-value";
    value.textContent = formatMetric(cell[metric][index]);
    item.append(location, value);
    list.appendChild(item);
  });
  setText("hotspot-unit", metric === "probability" ? "Olasılık" : "Beklenen sayı");
}

function renderValidation() {
  const grid = document.getElementById("validation-grid");
  grid.replaceChildren();
  Object.entries(state.snapshot.evaluation.pycsep).forEach(([key, result]) => {
    const item = document.createElement("article");
    item.className = "validation-item";
    const icon = document.createElement("span");
    icon.className = "validation-icon";
    icon.innerHTML = "&#10003;";
    const copy = document.createElement("div");
    const heading = document.createElement("h3");
    heading.textContent = testNames[key][0];
    const description = document.createElement("p");
    description.textContent = `${testNames[key][1]} · reddedilmedi`;
    copy.append(heading, description);
    const quantile = document.createElement("div");
    quantile.className = "validation-quantile";
    quantile.innerHTML = `${result.quantile.map((value) => value.toFixed(3)).join(" / ")}<small>quantile</small>`;
    item.append(icon, copy, quantile);
    grid.appendChild(item);
  });
  setText("replay-days", formatInteger(state.snapshot.evaluation.replay_days));
  setText("replay-events", formatInteger(state.snapshot.evaluation.replay_target_events));
  setText("replay-ig", state.snapshot.evaluation.information_gain_per_event_vs_poisson.toFixed(3));
}

function renderParameters() {
  const grid = document.getElementById("parameter-grid");
  grid.replaceChildren();
  Object.entries(state.snapshot.model.parameters).forEach(([name, value]) => {
    const item = document.createElement("div");
    item.className = "parameter-item";
    const label = document.createElement("span");
    label.textContent = name;
    const number = document.createElement("strong");
    number.textContent = Number(value).toPrecision(6);
    item.append(label, number);
    grid.appendChild(item);
  });
  setText("branching-ratio", state.snapshot.model.branching_ratio.toFixed(6));
  const definition = state.snapshot.grid.definition;
  setText("grid-definition", `${definition.cell_degrees.toFixed(1)}° · ${definition.latitude_cells}×${definition.longitude_cells}`);
}

function resizeAndDraw() {
  const rect = stage.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  drawMap(rect.width, rect.height);
}

function drawMap(width = stage.clientWidth, height = stage.clientHeight) {
  if (!state.snapshot || width <= 0 || height <= 0) return;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#eef2ef";
  context.fillRect(0, 0, width, height);

  const projection = createProjection(width, height);
  const polygon = state.snapshot.model.polygon_lat_lon;
  context.save();
  tracePolygon(polygon, projection);
  context.clip();
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, width, height);

  const values = state.snapshot.grid.cells.map((cell) => cell[state.metric][state.thresholdIndex]);
  const scaleMaximum = quantile(values.filter((value) => value > 0), 0.985) || 1;
  const cellSize = state.snapshot.grid.definition.cell_degrees;
  state.snapshot.grid.cells.forEach((cell) => {
    const value = cell[state.metric][state.thresholdIndex];
    if (value <= 0) return;
    const topLeft = projection(cell.longitude - cellSize / 2, cell.latitude + cellSize / 2);
    const bottomRight = projection(cell.longitude + cellSize / 2, cell.latitude - cellSize / 2);
    context.fillStyle = heatColor(Math.min(value / scaleMaximum, 1));
    context.fillRect(topLeft.x, topLeft.y, bottomRight.x - topLeft.x + 0.5, bottomRight.y - topLeft.y + 0.5);
  });

  if (state.showEvents) drawRecentEvents(projection);
  context.restore();

  context.lineWidth = 1.4;
  context.strokeStyle = "#3e5550";
  tracePolygon(polygon, projection);
  context.stroke();
  drawCities(projection);
}

function drawRecentEvents(projection) {
  state.snapshot.catalog.recent_events.forEach((event) => {
    const point = projection(event.longitude, event.latitude);
    const radius = Math.max(1.5, 1.2 + (event.magnitude - 2.5) * 1.8);
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fillStyle = "rgba(212, 92, 76, 0.74)";
    context.fill();
    context.strokeStyle = "rgba(255,255,255,0.85)";
    context.lineWidth = 0.7;
    context.stroke();
  });
}

function drawCities(projection) {
  const cities = [
    ["San Francisco", -122.4194, 37.7749],
    ["Sacramento", -121.4944, 38.5816],
    ["Los Angeles", -118.2437, 34.0522],
    ["San Diego", -117.1611, 32.7157],
  ];
  context.font = "10px system-ui";
  cities.forEach(([name, longitude, latitude]) => {
    const point = projection(longitude, latitude);
    context.beginPath();
    context.arc(point.x, point.y, 2.2, 0, Math.PI * 2);
    context.fillStyle = "#17201e";
    context.fill();
    context.fillStyle = "#35433f";
    context.fillText(name, point.x + 5, point.y - 4);
  });
}

function tracePolygon(polygon, projection) {
  context.beginPath();
  polygon.forEach(([latitude, longitude], index) => {
    const point = projection(longitude, latitude);
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.closePath();
}

function createProjection(width, height) {
  const definition = state.snapshot.grid.definition;
  const padding = width < 600 ? 22 : 34;
  const availableWidth = width - padding * 2;
  const availableHeight = height - padding * 2;
  const lonRange = definition.max_longitude - definition.min_longitude;
  const latRange = definition.max_latitude - definition.min_latitude;
  const scale = Math.min(availableWidth / lonRange, availableHeight / latRange);
  const mapWidth = lonRange * scale;
  const mapHeight = latRange * scale;
  const offsetX = (width - mapWidth) / 2;
  const offsetY = (height - mapHeight) / 2;
  return (longitude, latitude) => ({
    x: offsetX + (longitude - definition.min_longitude) * scale,
    y: offsetY + (definition.max_latitude - latitude) * scale,
  });
}

function heatColor(value) {
  const stops = [
    [217, 238, 231],
    [8, 127, 122],
    [230, 173, 56],
  ];
  const segment = value < 0.62 ? 0 : 1;
  const local = segment === 0 ? value / 0.62 : (value - 0.62) / 0.38;
  const start = stops[segment];
  const end = stops[segment + 1];
  const rgb = start.map((channel, index) => Math.round(channel + (end[index] - channel) * local));
  return `rgba(${rgb.join(",")},0.86)`;
}

function handleMapPointer(event) {
  if (!state.snapshot) return;
  const rect = canvas.getBoundingClientRect();
  const projection = createProjection(rect.width, rect.height);
  let nearest = null;
  let nearestDistance = Infinity;
  state.snapshot.grid.cells.forEach((cell) => {
    const value = cell[state.metric][state.thresholdIndex];
    if (value <= 0) return;
    const point = projection(cell.longitude, cell.latitude);
    const distance = Math.hypot(point.x - (event.clientX - rect.left), point.y - (event.clientY - rect.top));
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = cell;
    }
  });
  if (!nearest || nearestDistance > 20) {
    tooltip.classList.remove("visible");
    return;
  }
  tooltip.innerHTML = `<strong>${coordinateLabel(nearest)}</strong><br>${formatMetric(nearest[state.metric][state.thresholdIndex])} · M≥${formatMagnitude(state.snapshot.grid.thresholds[state.thresholdIndex])}`;
  tooltip.style.left = `${Math.min(event.clientX - rect.left + 12, rect.width - 155)}px`;
  tooltip.style.top = `${Math.max(event.clientY - rect.top - 48, 8)}px`;
  tooltip.classList.add("visible");
}

function coordinateLabel(cell) {
  const cities = [
    ["Los Angeles çevresi", -118.24, 34.05],
    ["San Diego çevresi", -117.16, 32.72],
    ["San Francisco çevresi", -122.42, 37.77],
    ["Central Coast", -121.0, 35.5],
    ["Eastern California", -117.5, 36.5],
    ["Northern California", -123.0, 40.0],
  ];
  let nearest = cities[0];
  let distance = Infinity;
  cities.forEach((city) => {
    const value = Math.hypot(cell.longitude - city[1], cell.latitude - city[2]);
    if (value < distance) { nearest = city; distance = value; }
  });
  return distance < 1.4 ? nearest[0] : "California hücresi";
}

function quantile(values, probability) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(probability * sorted.length))];
}

function formatMetric(value) {
  return state.metric === "probability" ? formatPercent(value) : value.toFixed(value < 0.01 ? 3 : 2);
}
function formatPercent(value) { return `%${(value * 100).toFixed(value < 0.01 ? 2 : 1)}`; }
function formatMagnitude(value) { return Number(value).toFixed(1); }
function formatCount(value) { return Number(value).toFixed(0); }
function formatInteger(value) { return new Intl.NumberFormat("tr-TR").format(value); }
function formatDate(value) { return new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(value)); }
function formatDateTime(value) { return new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hour12: false }).format(new Date(value)); }
function setText(id, value) { document.getElementById(id).textContent = value; }
function showError(message) { const banner = document.getElementById("error-banner"); banner.textContent = message; banner.classList.add("visible"); }
function hideError() { document.getElementById("error-banner").classList.remove("visible"); }

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll(".tab-view").forEach((view) => view.classList.remove("active"));
    document.getElementById(`${button.dataset.tab}-view`).classList.add("active");
    if (button.dataset.tab === "forecast") requestAnimationFrame(resizeAndDraw);
  });
});

document.querySelectorAll("[data-metric]").forEach((button) => {
  button.addEventListener("click", () => {
    state.metric = button.dataset.metric;
    document.querySelectorAll("[data-metric]").forEach((item) => item.classList.toggle("active", item === button));
    renderHotspots();
    drawMap();
  });
});

document.getElementById("events-toggle").addEventListener("change", (event) => {
  state.showEvents = event.target.checked;
  drawMap();
});
document.getElementById("refresh-button").addEventListener("click", loadSnapshot);
canvas.addEventListener("pointermove", handleMapPointer);
canvas.addEventListener("pointerleave", () => tooltip.classList.remove("visible"));
new ResizeObserver(() => resizeAndDraw()).observe(stage);

loadSnapshot();
