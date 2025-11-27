import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const canvas = document.getElementById("canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 5000);
camera.position.set(40, 35, 40);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 5;
controls.maxDistance = 250;

scene.add(new THREE.AmbientLight(0xffffff, 1.15));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
dirLight.position.set(25, 40, 15);
scene.add(dirLight);

const nodesGroup = new THREE.Group();
const edgesGroup = new THREE.Group();
scene.add(nodesGroup);
scene.add(edgesGroup);

const baseEdgeGeometry = new THREE.CylinderGeometry(0.12, 0.12, 1, 16, 1, true);
const baseEdgeMaterial = new THREE.MeshStandardMaterial({
  color: 0x89a6ff,
  transparent: true,
  opacity: 0.45,
  metalness: 0.25,
  roughness: 0.35,
  emissive: 0x1b2b4a,
  emissiveIntensity: 0.35,
});
const baseDotGeometry = new THREE.SphereGeometry(0.18, 14, 14);
const baseDotMaterial = new THREE.MeshStandardMaterial({
  color: 0xc6d8ff,
  transparent: true,
  opacity: 0.65,
  emissive: 0x1a2542,
  emissiveIntensity: 0.5,
});
const upAxis = new THREE.Vector3(0, 1, 0);

const geometries = {
  Block: new THREE.BoxGeometry(0.65, 0.65, 0.65),
  Point: new THREE.SphereGeometry(0.18, 20, 20),
  Sphere: new THREE.SphereGeometry(0.4, 28, 28),
  default: new THREE.SphereGeometry(0.3, 24, 24)
};

const palette = {
  Block: 0x4c8bf5,
  Point: 0x46d19c,
  Sphere: 0xf28d4b,
  default: 0xb0b0b0,
};

const dataTypeColors = {
  str: 0xdfe4f5,
  string: 0xdfe4f5,
  "numpy.ndarray": 0x35d07a,
  dict: 0xf5a742,
  object: 0xf5a742,
  bytes: 0xe46bff,
  bytearray: 0x57e0ff,
};

const orphanColor = 0xff4e4e;
const noneTypeColor = 0x050505;

const typeLightnessAdjust = {
  Sphere: -0.2,
  Block: -0.06,
  Point: 0.12,
  default: 0,
};

const templateMaterial = (color) =>
  new THREE.MeshStandardMaterial({
    color,
    transparent: true,
    opacity: 0.78,
    roughness: 0.32,
    metalness: 0.12,
    emissive: new THREE.Color(0x111a24),
    emissiveIntensity: 0.4,
  });

function createEdgeMesh(start, end) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  if (!length) {
    return null;
  }

  const mesh = new THREE.Mesh(baseEdgeGeometry, baseEdgeMaterial);
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  mesh.position.copy(midpoint);
  mesh.scale.set(connectorThicknessScale, length, connectorThicknessScale);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    upAxis,
    direction.normalize()
  );
  mesh.quaternion.copy(quaternion);
  return mesh;
}

function createEdgeDots(start, end) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  if (!length) {
    return null;
  }

  const steps = Math.max(2, Math.ceil(length / 1.25));
  const group = new THREE.Group();
  for (let i = 0; i <= steps; i += 1) {
    const ratio = i / steps;
    const position = new THREE.Vector3().copy(start).lerp(end, ratio);
    const dot = new THREE.Mesh(baseDotGeometry, baseDotMaterial);
    dot.position.copy(position);
    dot.scale.set(connectorThicknessScale, connectorThicknessScale, connectorThicknessScale);
    group.add(dot);
  }
  return group;
}

const nodeMeshes = new Map();
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const tooltip = document.getElementById("tooltip");
const tableBody = document.querySelector("#node-table tbody");
const nodeForm = document.getElementById("node-form");
const formStatus = document.getElementById("form-status");
const formSubmitButton = nodeForm?.querySelector("button[type='submit']");
const tablePanelElement = document.getElementById("table-panel");
const collapseTableButton = document.getElementById("collapse-table");
const tableTabButton = document.getElementById("table-tab");
const tableResizer = document.getElementById("table-resizer");
const connectorVisibleCheckbox = document.getElementById("connector-visible");
const connectorThicknessSlider = document.getElementById("connector-thickness");
const motionSpeedSlider = document.getElementById("motion-speed");
const motionSpeedValueLabel = document.getElementById("motion-speed-value");
const openFormButton = document.getElementById("open-node-form");
const closeFormButton = document.getElementById("close-node-form");
const modalBackdrop = document.getElementById("modal-backdrop");
const formModal = document.getElementById("control-panel");
const resetFormButton = document.getElementById("reset-node-form");
const pauseVisualizerButton = document.getElementById("pause-visualizer");
const historyPanel = document.getElementById("history-panel");
const historyNodeLabel = document.getElementById("history-node-label");
const historyNodeAddr = document.getElementById("history-node-addr");
const historyStream = document.getElementById("history-stream");
const historyCloseButton = document.getElementById("history-close");
let hoveredMesh = null;
let cachedNodes = [];
let connectorThicknessScale = Number(connectorThicknessSlider?.value ?? 1);
let motionDurationMs = motionSpeedSlider ? Number(motionSpeedSlider.value) * 1000 : 0;
let isPaused = false;
let queuedPayload = null;
let selectedNodeId = null;
let historyPollingHandle = null;
let pointerDownSnapshot = null;
let idToNodeMap = new Map();
let idToAddressMap = new Map();
let cameraTween = null;
let currentPositionScale = 1;
const TABLE_PANEL_STORAGE_KEY = "lunar-table-panel-height";
const TABLE_PANEL_MIN_HEIGHT = 180;
const TARGET_SCENE_SPAN = 90;
const MAX_POSITION_SCALE = 420;
const CAMERA_FOCUS_MIN_DISTANCE = 8;
const CAMERA_FOCUS_MAX_DISTANCE = 26;
const CAMERA_TWEEN_DURATION = 650;
edgesGroup.visible = connectorVisibleCheckbox ? connectorVisibleCheckbox.checked : true;

function readStoredTableHeight() {
  try {
    const raw = window.localStorage.getItem(TABLE_PANEL_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  } catch (error) {
    console.warn("Failed to read stored table height", error);
    return null;
  }
}

function storeTableHeight(height) {
  try {
    window.localStorage.setItem(TABLE_PANEL_STORAGE_KEY, String(height));
  } catch (error) {
    console.warn("Failed to persist table height", error);
  }
}

function clampTableHeight(value) {
  const maxHeight = Math.max(TABLE_PANEL_MIN_HEIGHT, window.innerHeight * 0.8);
  return Math.min(Math.max(value, TABLE_PANEL_MIN_HEIGHT), maxHeight);
}

function applyTableHeight(height) {
  if (!tablePanelElement || typeof height !== "number") {
    return;
  }
  tablePanelElement.style.setProperty("--table-panel-height", `${height}px`);
}

function vectorFromArray(values) {
  if (!Array.isArray(values) || values.length < 3) {
    return new THREE.Vector3();
  }
  const x = Number(values[0]);
  const y = Number(values[1]);
  const z = Number(values[2]);
  return new THREE.Vector3(
    Number.isFinite(x) ? x : 0,
    Number.isFinite(y) ? y : 0,
    Number.isFinite(z) ? z : 0
  );
}

function getScaledPositionVector(values) {
  return vectorFromArray(values).multiplyScalar(currentPositionScale);
}

function updatePositionScale(nodes) {
  if (!Array.isArray(nodes) || !nodes.length) {
    currentPositionScale = 1;
    return;
  }
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;

  nodes.forEach((node) => {
    if (!Array.isArray(node.pos) || node.pos.length < 3) {
      return;
    }
    const [xRaw, yRaw, zRaw] = node.pos;
    const x = Number(xRaw);
    const y = Number(yRaw);
    const z = Number(zRaw);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      return;
    }
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);
  });

  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const spanZ = maxZ - minZ;
  const largestSpan = Math.max(spanX, spanY, spanZ);

  if (!Number.isFinite(largestSpan) || largestSpan <= 0) {
    currentPositionScale = MAX_POSITION_SCALE;
    return;
  }

  const desiredScale = TARGET_SCENE_SPAN / largestSpan;
  currentPositionScale = Math.min(
    MAX_POSITION_SCALE,
    Math.max(1, desiredScale)
  );
}

function hashString(input = "") {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash << 5) - hash + input.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function adjustColorForNodeType(color, nodeType) {
  const adjustment = typeLightnessAdjust[nodeType] ?? typeLightnessAdjust.default;
  if (!adjustment) {
    return color;
  }
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  hsl.l = THREE.MathUtils.clamp(hsl.l + adjustment, 0.05, 0.95);
  color.setHSL(hsl.h, hsl.s, hsl.l);
  return color;
}

function getColorForNode(node) {
  const neighborCount = Array.isArray(node.neighbors) ? node.neighbors.length : 0;
  if (neighborCount === 0) {
    return new THREE.Color(orphanColor);
  }
  const typeKey = (node.data_type ?? "").toLowerCase();
  const isNonePayload = !node.data_type || typeKey === "nonetype" || typeKey === "none";
  const dataColorHex = isNonePayload ? noneTypeColor : dataTypeColors[typeKey];
  const fallbackHex = palette[node.type] ?? palette.default;
  const color = new THREE.Color(dataColorHex ?? fallbackHex);
  return adjustColorForNodeType(color, node.type ?? "default");
}

function computeNeighborScale(node) {
  const neighborCount = Array.isArray(node.neighbors) ? node.neighbors.length : 0;
  return 1 + Math.log1p(neighborCount) * 0.44;
}

function applyNodeScale(mesh, node) {
  const base = mesh.userData.baseScale ?? new THREE.Vector3(1, 1, 1);
  const factor = computeNeighborScale(node);
  const scaled = base.clone().multiplyScalar(factor);
  mesh.userData.renderScale = scaled;
  mesh.scale.copy(scaled);
}

function upsertNodeMesh(node) {
  let mesh = nodeMeshes.get(node.id);
  let isNew = false;
  if (!mesh) {
    const geometry = geometries[node.type] ?? geometries.default;
    const color = getColorForNode(node);
    mesh = new THREE.Mesh(geometry, templateMaterial(color));
    mesh.userData = {};
    nodeMeshes.set(node.id, mesh);
    nodesGroup.add(mesh);
    mesh.userData.baseScale = mesh.scale.clone();
    isNew = true;
  } else {
    const color = getColorForNode(node);
    mesh.material.color.copy(color);
  }
  applyNodeScale(mesh, node);
  let animation = mesh.userData.motion;
  if (!animation) {
    animation = {
      start: mesh.position.clone(),
      target: new THREE.Vector3(),
      startTime: performance.now(),
      duration: motionDurationMs,
    };
    mesh.userData.motion = animation;
  }
  const targetVector = getScaledPositionVector(node.pos);
  animation.target.copy(targetVector);
  animation.startTime = performance.now();
  animation.duration = motionDurationMs;
  if (isNew) {
    mesh.position.copy(targetVector);
    animation.start.copy(targetVector);
    animation.duration = 0;
  } else {
    animation.start.copy(mesh.position);
    if (motionDurationMs <= 0) {
      mesh.position.copy(animation.target);
    }
  }
  mesh.userData.lastSeen = performance.now();
  mesh.userData.isAnchor = node.is_anchor;
  mesh.userData.nodeMeta = node;
}

function pruneNodes() {
  const cutoff = performance.now() - 2000;
  for (const [id, mesh] of nodeMeshes.entries()) {
    if ((mesh.userData.lastSeen ?? 0) < cutoff) {
      nodesGroup.remove(mesh);
      nodeMeshes.delete(id);
      if (id === selectedNodeId) {
        closeHistoryPanel();
      }
    }
  }
}

function rebuildEdges(nodes) {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  while (edgesGroup.children.length) {
    edgesGroup.remove(edgesGroup.children[0]);
  }

  nodes.forEach((node) => {
    (node.neighbors || []).forEach((neighborId) => {
      const neighbor = nodeMap.get(neighborId);
      if (!neighbor || neighbor.id < node.id) {
        return; // avoid duplicate lines
      }
      const start = getScaledPositionVector(node.pos);
      const end = getScaledPositionVector(neighbor.pos);
      const edgeMesh = createEdgeMesh(start, end);
      if (edgeMesh) {
        edgesGroup.add(edgeMesh);
      }
      const dots = createEdgeDots(start, end);
      if (dots) {
        edgesGroup.add(dots);
      }
    });
  });
}

function updateStats(nodes) {
  const nodeCountEl = document.getElementById("node-count");
  const avgGravityEl = document.getElementById("avg-gravity");
  const statusEl = document.getElementById("status");

  nodeCountEl.textContent = nodes.length.toString();
  const avgGravity = nodes.length
    ? nodes.reduce((sum, node) => sum + node.gravity, 0) / nodes.length
    : 0;
  avgGravityEl.textContent = avgGravity.toFixed(3);
  statusEl.textContent = `Live (nodes: ${nodes.length})`;
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function truncate(value = "", max = 16) {
  const text = String(value ?? "");
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function formatNumber(value, digits = 3) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return value.toFixed(digits);
}

function formatVector(values, digits = 2) {
  if (!Array.isArray(values) || values.length !== 3) {
    return "—";
  }
  const parts = values.map((val) => {
    if (typeof val !== "number" || Number.isNaN(val)) {
      return "?";
    }
    return val.toFixed(digits);
  });
  return `[${parts.join(", ")}]`;
}

function resolveNeighborAddresses(ids) {
  if (!Array.isArray(ids) || ids.length === 0) {
    return [];
  }
  return ids.map((neighborId) => idToAddressMap.get(neighborId) ?? `#${neighborId}`);
}


function formatDataSerialized(node) {
  if (node.data_serialized == null) {
    const fallback = node.data ?? "";
    return {
      full: String(fallback ?? ""),
      short: truncate(fallback ?? "", 28),
    };
  }
  try {
    const serialized =
      typeof node.data_serialized === "string"
        ? node.data_serialized
        : JSON.stringify(node.data_serialized);
    return {
      full: serialized,
      short: truncate(serialized, 28),
    };
  } catch (error) {
    const fallback = String(node.data ?? "");
    return { full: fallback, short: truncate(fallback, 28) };
  }
}

function formatBoolean(value) {
  return value ? "Yes" : "No";
}

function renderNodeTable(nodes) {
  if (!tableBody) {
    return;
  }

  if (!nodes.length) {
    tableBody.innerHTML = '<tr><td colspan="15">No nodes</td></tr>';
    return;
  }

  const rows = nodes
    .slice(0, 50)
    .map((node) => {
      const addr = truncate(node.addr ?? "", 14);
      const { full: dataFull, short: dataShort } = formatDataSerialized(node);
      const dataType = node.data_type ?? "Unknown";
      const posText = formatVector(node.pos ?? []);
      const velText = formatVector(node.velocity ?? []);
      const neighborAddresses = resolveNeighborAddresses(node.neighbors);
      const neighborsText = neighborAddresses.length
        ? neighborAddresses.map((addr) => truncate(addr, 16)).join(", ")
        : "∅";
      const neighborsFull = neighborAddresses.join(", ") || "∅";
      const gravityText = formatNumber(Number(node.gravity ?? NaN), 3);
      const connectionText = formatNumber(Number(node.connection_threshold ?? NaN), 3);
      const influenceText = formatNumber(Number(node.influence_radius ?? NaN), 3);
      const tickText = formatNumber(Number(node.tick_interval ?? NaN), 3);
      return `
        <tr data-node-id="${escapeHtml(String(node.id))}">
          <td>${escapeHtml(node.id)}</td>
          <td>${escapeHtml(node.type)}</td>
          <td title="${escapeHtml(node.addr ?? "")}">${escapeHtml(addr)}</td>
          <td title="${escapeHtml(dataFull)}">${escapeHtml(dataShort)}</td>
          <td>${escapeHtml(dataType)}</td>
          <td>${escapeHtml(node.attempts ?? 0)}</td>
          <td>${escapeHtml(connectionText)}</td>
          <td>${escapeHtml(influenceText)}</td>
          <td title="${escapeHtml(posText)}">${escapeHtml(posText)}</td>
          <td title="${escapeHtml(velText)}">${escapeHtml(velText)}</td>
          <td>${escapeHtml(gravityText)}</td>
          <td title="${escapeHtml(neighborsFull)}">${escapeHtml(
            truncate(neighborsText, 24)
          )}</td>
          <td>${escapeHtml(formatBoolean(!!node.is_anchor))}</td>
          <td>${escapeHtml(node.stability_window ?? "—")}</td>
          <td>${escapeHtml(tickText)}</td>
        </tr>
      `;
    })
    .join("");

  tableBody.innerHTML = rows;
}

function activateNodeFromSnapshot(nodeId) {
  if (!Number.isFinite(nodeId)) {
    return;
  }
  const node = idToNodeMap.get(nodeId);
  if (!node) {
    return;
  }
  focusCameraOnNode(nodeId);
  openHistoryPanelForNode(node);
}

function refreshHistoryHeader() {
  if (!selectedNodeId || !historyNodeLabel || !historyNodeAddr) {
    return;
  }
  const node = idToNodeMap.get(selectedNodeId);
  if (!node) {
    closeHistoryPanel();
    return;
  }
  historyNodeLabel.textContent = `${node.type} #${node.id}`;
  historyNodeAddr.textContent = truncate(node.addr ?? "", 48);
}

function updateSelectionHighlight() {
  nodeMeshes.forEach((mesh, id) => {
    if (!mesh.material) {
      return;
    }
    mesh.material.emissiveIntensity = id === selectedNodeId ? 1.0 : 0.4;
  });
}

function setHistoryMessage(message) {
  if (historyStream) {
    historyStream.innerHTML = `<p class="history-empty">${escapeHtml(message)}</p>`;
  }
}

async function fetchNodeHistory(nodeId, { silent = false } = {}) {
  if (!historyStream) {
    return;
  }
  if (!silent) {
    setHistoryMessage("Loading history…");
  }
  try {
    const response = await fetch(`/nodes/${nodeId}/history`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const entries = await response.json();
    renderHistoryEntries(entries);
  } catch (error) {
    console.error("History fetch failed", error);
    setHistoryMessage(`History unavailable: ${error.message ?? error}`);
  }
}

function renderHistoryEntries(entries) {
  if (!historyStream) {
    return;
  }
  if (!entries || !entries.length) {
    setHistoryMessage("No history recorded yet.");
    return;
  }
  const content = entries
    .slice(-60)
    .map((entry) => {
      const neighborChips = (entry.neighbors ?? []).length
        ? entry.neighbors
            .map((neighbor) => {
              const label = truncate(neighbor?.addr ?? `#${neighbor?.id ?? "?"}`, 16);
              return `<span class="neighbor-chip" title="${escapeHtml(neighbor?.addr ?? "")}">${escapeHtml(label)}</span>`;
            })
            .join("")
        : '<span class="history-empty">∅</span>';
      return `
        <div class="history-entry">
          <div><strong>${escapeHtml(entry.timestamp ?? "—")}</strong> · idx ${escapeHtml(entry.idx ?? 0)}</div>
          <div>Pos ${escapeHtml(formatVector(entry.pos ?? []))}</div>
          <div>Vel ${escapeHtml(formatVector(entry.velocity ?? []))}</div>
          <div>Neighbors ${neighborChips}</div>
        </div>
      `;
    })
    .join("");
  historyStream.innerHTML = content;
  historyStream.scrollTop = historyStream.scrollHeight;
}

function startHistoryPolling(nodeId) {
  stopHistoryPolling();
  historyPollingHandle = window.setInterval(() => {
    fetchNodeHistory(nodeId, { silent: true });
  }, 2000);
}

function stopHistoryPolling() {
  if (historyPollingHandle) {
    window.clearInterval(historyPollingHandle);
    historyPollingHandle = null;
  }
}

function openHistoryPanelForNode(node) {
  if (!node) {
    return;
  }
  selectedNodeId = node.id;
  if (historyNodeLabel) {
    historyNodeLabel.textContent = `${node.type} #${node.id}`;
  }
  if (historyNodeAddr) {
    historyNodeAddr.textContent = truncate(node.addr ?? "", 48);
  }
  refreshHistoryHeader();
  historyPanel?.classList.remove("hidden");
  updateSelectionHighlight();
  setHistoryMessage("Loading history…");
  fetchNodeHistory(node.id);
  startHistoryPolling(node.id);
}

function closeHistoryPanel() {
  stopHistoryPolling();
  selectedNodeId = null;
  historyPanel?.classList.add("hidden");
  if (historyNodeLabel) {
    historyNodeLabel.textContent = "Click a node";
  }
  if (historyNodeAddr) {
    historyNodeAddr.textContent = "";
  }
  setHistoryMessage("Select a node in the scene to begin streaming its history.");
  updateSelectionHighlight();
}

function setPauseState(paused) {
  isPaused = paused;
  if (pauseVisualizerButton) {
    pauseVisualizerButton.textContent = paused ? "Resume" : "Pause";
    pauseVisualizerButton.classList.toggle("active", paused);
  }
  if (!paused && queuedPayload) {
    applyPayload(queuedPayload);
    queuedPayload = null;
  }
}

function showTooltip(node, x, y) {
  if (!node || !tooltip) {
    return;
  }
  const { full: dataFull } = formatDataSerialized(node);
  const posText = formatVector(node.pos ?? []);
  const velText = formatVector(node.velocity ?? []);
  const neighborAddresses = resolveNeighborAddresses(node.neighbors);
  const neighborsFull = neighborAddresses.join(", ") || "∅";
  const neighborsPreview = truncate(neighborsFull, 48);
  tooltip.style.display = "block";
  tooltip.style.left = `${x + 14}px`;
  tooltip.style.top = `${y + 14}px`;
  tooltip.innerHTML = `
    <strong>${escapeHtml(node.type)} #${escapeHtml(node.id)}</strong><br />
    Addr: ${escapeHtml(truncate(node.addr ?? "", 32))}<br />
    Data (${escapeHtml(node.data_type ?? "Unknown")}): ${escapeHtml(
      truncate(dataFull, 48)
    )}<br />
    Pos: ${escapeHtml(posText)}<br />
    Vel: ${escapeHtml(velText)}<br />
    Conn: ${escapeHtml(formatNumber(Number(node.connection_threshold ?? NaN), 3))}
    · Infl: ${escapeHtml(formatNumber(Number(node.influence_radius ?? NaN), 3))}<br />
    Gravity: ${escapeHtml(formatNumber(Number(node.gravity ?? NaN), 3))}
    · Tick: ${escapeHtml(formatNumber(Number(node.tick_interval ?? NaN), 3))}<br />
    Attempts: ${escapeHtml(node.attempts ?? 0)} · Anchor: ${escapeHtml(
      formatBoolean(!!node.is_anchor)
    )}<br />
    Neighbors: ${escapeHtml(neighborsPreview)}
  `;
}

function hideTooltip() {
  if (tooltip) {
    tooltip.style.display = "none";
  }
  if (hoveredMesh) {
    const restingScale = hoveredMesh.userData.renderScale || hoveredMesh.userData.baseScale;
    if (restingScale) {
      hoveredMesh.scale.copy(restingScale);
    } else {
      hoveredMesh.scale.set(1, 1, 1);
    }
    hoveredMesh = null;
  }
}

function handleHover(event) {
  updatePointerFromEvent(event);
  raycaster.setFromCamera(mouse, camera);
  const intersections = raycaster.intersectObjects(nodesGroup.children, false);

  if (!intersections.length) {
    hideTooltip();
    return;
  }

  const mesh = intersections[0].object;
  if (hoveredMesh && hoveredMesh !== mesh) {
    const previousScale = hoveredMesh.userData.renderScale || hoveredMesh.userData.baseScale;
    if (previousScale) {
      hoveredMesh.scale.copy(previousScale);
    } else {
      hoveredMesh.scale.set(1, 1, 1);
    }
  }
  hoveredMesh = mesh;
  const base = hoveredMesh.userData.renderScale || hoveredMesh.userData.baseScale;
  if (base) {
    hoveredMesh.scale.copy(base).multiplyScalar(1.12);
  } else {
    hoveredMesh.scale.set(1.12, 1.12, 1.12);
  }
  showTooltip(mesh.userData.nodeMeta, event.clientX, event.clientY);
}

function updatePointerFromEvent(event) {
  const bounds = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  mouse.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
}

function getMeshUnderPointer(event) {
  updatePointerFromEvent(event);
  raycaster.setFromCamera(mouse, camera);
  const intersections = raycaster.intersectObjects(nodesGroup.children, false);
  if (!intersections.length) {
    return null;
  }
  return intersections[0].object;
}

function handleCanvasClick(event) {
  const mesh = getMeshUnderPointer(event);
  if (!mesh) {
    return;
  }
  const node = mesh.userData.nodeMeta;
  if (!node) {
    return;
  }
  openHistoryPanelForNode(node);
  focusCameraOnNode(node.id);
}

function applyPayload(payload) {
  const nodes = payload.nodes ?? [];
  cachedNodes = nodes;
  idToNodeMap = new Map(nodes.map((node) => [node.id, node]));
  idToAddressMap = new Map(nodes.map((node) => [node.id, node.addr]));
  window.__lunarLastPayload = payload; // exposed for debugging
  console.debug("Visualizer payload", { count: nodes.length, sample: nodes[0] });
  updatePositionScale(nodes);
  nodes.forEach(upsertNodeMesh);
  pruneNodes();
  rebuildEdges(nodes);
  updateStats(nodes);
  renderNodeTable(nodes);
  refreshHistoryHeader();
  updateSelectionHighlight();
}

function handlePayload(payload) {
  if (isPaused) {
    queuedPayload = payload;
    return;
  }
  applyPayload(payload);
}

function updateMeshPositions() {
  const now = performance.now();
  nodeMeshes.forEach((mesh) => {
    const animation = mesh.userData.motion;
    if (!animation) {
      return;
    }
    if (!animation.target) {
      return;
    }
    if (animation.duration <= 0) {
      mesh.position.copy(animation.target);
      return;
    }
    const progress = Math.min((now - animation.startTime) / animation.duration, 1);
    const eased = progress * progress * (3 - 2 * progress); // smoothstep easing
    mesh.position.lerpVectors(animation.start, animation.target, eased);
    if (progress >= 1) {
      animation.start.copy(animation.target);
      animation.duration = 0;
    }
  });
}

function updateCameraTween() {
  if (!cameraTween) {
    return;
  }
  const now = performance.now();
  const progress = Math.min((now - cameraTween.startTime) / cameraTween.duration, 1);
  const eased = progress * progress * (3 - 2 * progress);
  camera.position.lerpVectors(cameraTween.startPos, cameraTween.endPos, eased);
  controls.target.lerpVectors(cameraTween.startTarget, cameraTween.endTarget, eased);
  if (progress >= 1) {
    cameraTween = null;
  }
}

function focusCameraOnNode(nodeId) {
  const mesh = nodeMeshes.get(nodeId);
  if (!mesh) {
    return;
  }
  const targetPos = mesh.position.clone();
  const currentOffset = camera.position.clone().sub(controls.target);
  let direction = currentOffset.clone();
  let currentDistance = direction.length();
  if (!Number.isFinite(currentDistance) || currentDistance < 0.01) {
    direction.set(0.4, 0.7, 0.6);
    currentDistance = direction.length();
  }
  direction.normalize();
  const desiredDistance = Math.min(
    CAMERA_FOCUS_MAX_DISTANCE,
    Math.max(CAMERA_FOCUS_MIN_DISTANCE, currentDistance * 0.4 + 6)
  );
  const desiredOffset = direction.multiplyScalar(desiredDistance);
  const desiredCameraPos = targetPos.clone().add(desiredOffset);
  const minimumHeight = targetPos.y + Math.max(4, desiredDistance * 0.35);
  if (desiredCameraPos.y < minimumHeight) {
    desiredCameraPos.y = minimumHeight;
  }
  cameraTween = {
    startTime: performance.now(),
    duration: CAMERA_TWEEN_DURATION,
    startPos: camera.position.clone(),
    endPos: desiredCameraPos,
    startTarget: controls.target.clone(),
    endTarget: targetPos,
  };
}

function animate() {
  requestAnimationFrame(animate);
  updateMeshPositions();
  updateCameraTween();
  controls.update();
  renderer.render(scene, camera);
}
animate();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

renderer.domElement.addEventListener("pointermove", handleHover);
renderer.domElement.addEventListener("pointerleave", () => {
  pointerDownSnapshot = null;
  hideTooltip();
});
renderer.domElement.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) {
    return;
  }
  pointerDownSnapshot = {
    x: event.clientX,
    y: event.clientY,
    time: performance.now(),
  };
});
renderer.domElement.addEventListener("pointerup", (event) => {
  if (event.button !== 0 || !pointerDownSnapshot) {
    pointerDownSnapshot = null;
    return;
  }
  const dx = Math.abs(event.clientX - pointerDownSnapshot.x);
  const dy = Math.abs(event.clientY - pointerDownSnapshot.y);
  const dt = performance.now() - pointerDownSnapshot.time;
  pointerDownSnapshot = null;
  if (dx <= 4 && dy <= 4 && dt <= 300) {
    handleCanvasClick(event);
  }
});

function setFormStatus(message, variant = "") {
  if (!formStatus) {
    return;
  }
  formStatus.textContent = message;
  formStatus.classList.remove("error", "success");
  if (variant) {
    formStatus.classList.add(variant);
  }
}

function openNodeModal() {
  formModal?.classList.add("open");
  modalBackdrop?.classList.add("active");
  setFormStatus("", "");
}

function closeNodeModal() {
  formModal?.classList.remove("open");
  modalBackdrop?.classList.remove("active");
}

function collapseTablePanel() {
  tablePanelElement?.classList.add("collapsed");
  tableTabButton?.classList.add("visible");
}

function expandTablePanel() {
  tablePanelElement?.classList.remove("collapsed");
  tableTabButton?.classList.remove("visible");
}

let isResizingTable = false;
let resizeStartY = 0;
let resizeStartHeight = 0;

function stopTableResize() {
  if (!isResizingTable) {
    return;
  }
  isResizingTable = false;
  document.body.classList.remove("resizing-table");
  window.removeEventListener("pointermove", handleTableResizeMove);
  window.removeEventListener("pointerup", stopTableResize);
}

function handleTableResizeMove(event) {
  if (!isResizingTable) {
    return;
  }
  const deltaY = resizeStartY - event.clientY;
  const nextHeight = clampTableHeight(resizeStartHeight + deltaY);
  applyTableHeight(nextHeight);
  storeTableHeight(nextHeight);
}

function handleTableResizeStart(event) {
  if (!tablePanelElement) {
    return;
  }
  event.preventDefault();
  const currentHeight = tablePanelElement.getBoundingClientRect().height;
  isResizingTable = true;
  resizeStartY = event.clientY;
  resizeStartHeight = currentHeight;
  document.body.classList.add("resizing-table");
  window.addEventListener("pointermove", handleTableResizeMove);
  window.addEventListener("pointerup", stopTableResize);
}

function parseVectorFields(formData, keys, label) {
  const values = keys.map((key) => formData.get(key)?.toString().trim() ?? "");
  if (values.every((value) => value === "")) {
    return null;
  }
  if (values.some((value) => value === "")) {
    throw new Error(`Provide all three ${label} components or leave them blank`);
  }
  const result = values.map((value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      throw new Error(`${label} must be numeric`);
    }
    return numeric;
  });
  return result;
}

function parseOptionalNumberField(formData, key, label, { integer = false } = {}) {
  const raw = formData.get(key)?.toString().trim();
  if (!raw) {
    return null;
  }
  const numeric = integer ? Number.parseInt(raw, 10) : Number(raw);
  if (!Number.isFinite(numeric)) {
    throw new Error(`${label} must be numeric`);
  }
  return numeric;
}

function parseDataField(dataRaw, format) {
  if (!dataRaw) {
    return null;
  }
  if (format === "json") {
    return parseJsonLike(dataRaw);
  }
  if (format === "ndarray") {
    const value = parseJsonLike(dataRaw);
    if (!Array.isArray(value)) {
      throw new Error("ndarray mode expects a JSON array or list literal");
    }
    return value;
  }
  return dataRaw; // bytes/bytearray send base64 directly
}

function parseJsonLike(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }
  try {
    return JSON.parse(trimmed);
  } catch (primaryError) {
    try {
      const normalized = trimmed
        .replace(/([{,]\s*)([A-Za-z0-9_]+)\s*:/g, '$1"$2":')
        .replace(/'/g, '"');
      return JSON.parse(normalized);
    } catch (secondaryError) {
      throw new Error(
        "Data must be valid JSON (tip: wrap keys in double quotes)."
      );
    }
  }
}

async function handleNodeFormSubmit(event) {
  event.preventDefault();
  if (!nodeForm) {
    return;
  }

  const formData = new FormData(nodeForm);
  const nodeType = formData.get("nodeType")?.toString() ?? "Block";
  const dataFormat = formData.get("dataFormat")?.toString() ?? "json";
  const dataRaw = formData.get("nodeData")?.toString().trim() ?? "";
  const payload = { node_type: nodeType, data_format: dataFormat };

  try {
    const pos = parseVectorFields(
      formData,
      ["posX", "posY", "posZ"],
      "position"
    );
    if (pos) {
      payload.pos = pos;
    }

    const velocity = parseVectorFields(
      formData,
      ["velX", "velY", "velZ"],
      "velocity"
    );
    if (velocity) {
      payload.velocity = velocity;
    }

    const connectionThreshold = parseOptionalNumberField(
      formData,
      "connectionThreshold",
      "Connection threshold"
    );
    if (connectionThreshold !== null) {
      payload.connection_threshold = connectionThreshold;
    }

    const influenceRadius = parseOptionalNumberField(
      formData,
      "influenceRadius",
      "Influence radius"
    );
    if (influenceRadius !== null) {
      payload.influence_radius = influenceRadius;
    }

    const gravity = parseOptionalNumberField(
      formData,
      "gravity",
      "Gravity"
    );
    if (gravity !== null) {
      payload.gravity = gravity;
    }

    const tickInterval = parseOptionalNumberField(
      formData,
      "tickInterval",
      "Tick interval"
    );
    if (tickInterval !== null) {
      payload.tick_interval = tickInterval;
    }

    const attempts = parseOptionalNumberField(
      formData,
      "attempts",
      "Attempts",
      { integer: true }
    );
    if (attempts !== null) {
      payload.attempts = attempts;
    }

    const stabilityWindow = parseOptionalNumberField(
      formData,
      "stabilityWindow",
      "Stability window",
      { integer: true }
    );
    if (stabilityWindow !== null) {
      payload.stability_window = stabilityWindow;
    }

    if (formData.get("isAnchor") === "on") {
      payload.is_anchor = true;
    }

    const parsedData = parseDataField(dataRaw, dataFormat);
    if (parsedData !== null) {
      payload.data = parsedData;
    }
  } catch (error) {
    setFormStatus(error.message, "error");
    return;
  }

  try {
    setFormStatus("Creating node…");
    if (formSubmitButton) {
      formSubmitButton.disabled = true;
    }

    const response = await fetch("/nodes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      const message = detail?.detail ?? `Failed with status ${response.status}`;
      throw new Error(message);
    }

    const result = await response.json();
    setFormStatus(`Created node #${result.id}`, "success");
  } catch (error) {
    setFormStatus(error.message || "Unexpected error", "error");
  } finally {
    if (formSubmitButton) {
      formSubmitButton.disabled = false;
    }
  }
}

if (nodeForm) {
  nodeForm.addEventListener("submit", handleNodeFormSubmit);
}

resetFormButton?.addEventListener("click", () => {
  nodeForm?.reset();
  setFormStatus("Form reset", "");
});

pauseVisualizerButton?.addEventListener("click", () => {
  setPauseState(!isPaused);
});

historyCloseButton?.addEventListener("click", () => {
  closeHistoryPanel();
});

openFormButton?.addEventListener("click", () => {
  openNodeModal();
});

closeFormButton?.addEventListener("click", () => {
  closeNodeModal();
});

modalBackdrop?.addEventListener("click", () => {
  closeNodeModal();
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && formModal?.classList.contains("open")) {
    closeNodeModal();
  }
});

collapseTableButton?.addEventListener("click", () => {
  collapseTablePanel();
});

tableTabButton?.addEventListener("click", () => {
  expandTablePanel();
});

if (tableResizer) {
  tableResizer.addEventListener("pointerdown", handleTableResizeStart);
}

tableBody?.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-node-id]");
  if (!row) {
    return;
  }
  const nodeId = Number(row.dataset.nodeId);
  activateNodeFromSnapshot(nodeId);
});

const storedHeight = readStoredTableHeight();
if (storedHeight) {
  applyTableHeight(clampTableHeight(storedHeight));
}

connectorVisibleCheckbox?.addEventListener("change", (event) => {
  const isChecked = event.target.checked;
  edgesGroup.visible = isChecked;
});

connectorThicknessSlider?.addEventListener("input", (event) => {
  const value = Number(event.target.value);
  if (!Number.isFinite(value)) {
    return;
  }
  connectorThicknessScale = value;
  rebuildEdges(cachedNodes);
});

function updateMotionLabel(valueSeconds) {
  if (motionSpeedValueLabel) {
    motionSpeedValueLabel.textContent = `${valueSeconds.toFixed(1)}s`;
  }
}

if (motionSpeedSlider) {
  const initialSeconds = Number(motionSpeedSlider.value ?? 0);
  updateMotionLabel(initialSeconds);
}

motionSpeedSlider?.addEventListener("input", (event) => {
  const valueSeconds = Number(event.target.value);
  if (!Number.isFinite(valueSeconds)) {
    return;
  }
  motionDurationMs = valueSeconds * 1000;
  updateMotionLabel(valueSeconds);
});

setPauseState(false);

function connectWebSocket() {
  const statusEl = document.getElementById("status");
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/nodes`);

  socket.addEventListener("open", () => {
    statusEl.textContent = "Connected";
  });

  socket.addEventListener("message", event => {
    try {
      const payload = JSON.parse(event.data);
      handlePayload(payload);
    } catch (error) {
      console.error("Malformed payload", error);
      statusEl.textContent = "Payload error";
    }
  });

  socket.addEventListener("close", () => {
    statusEl.textContent = "Disconnected – retrying...";
    setTimeout(connectWebSocket, 1500);
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}

connectWebSocket();
