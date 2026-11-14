// Live view of /api/stream/: findings, then a crew and a cabin table with one
// row per channel.
// Shapes: docs/json-shape.md.

const statusLine = document.getElementById("status");
const tablesDiv = document.getElementById("tables");

let channels = {}; // channel id -> {name, body_regions, explanation}
let findings = {}; // finding id -> {name, channels}
const latest = new Map(); // channel -> reading
let received = 0;

function render(reading) {
  const tableId = `scope-${reading.scope}`;
  let tbody = document.getElementById(tableId);
  if (!tbody) {
    const section = document.createElement("section");
    section.innerHTML =
      `<h2></h2><table><thead><tr><th>Channel</th><th>Value</th><th>Unit</th>` +
      `<th>Evaluation</th><th>Measured at</th></tr></thead><tbody></tbody></table>`;
    section.querySelector("h2").textContent = reading.scope === "crew" ? "Crew" : "Cabin";
    section.querySelector("tbody").id = tableId;
    tablesDiv.append(section);
    tbody = section.querySelector("tbody");
  }

  const rowId = `${tableId}-${reading.channel}`;
  let row = document.getElementById(rowId);
  if (!row) {
    row = document.createElement("tr");
    row.id = rowId;
    row.innerHTML = "<td></td><td class='value'></td><td></td><td></td><td></td>";
    tbody.append(row);
  }

  const info = channels[reading.channel] ?? { name: reading.channel, explanation: "" };
  const [name, value, unit, evaluation, measuredAt] = row.children;
  name.textContent = info.name;
  name.title = info.explanation;
  value.textContent =
    typeof reading.value === "number" ? reading.value.toPrecision(4) : String(reading.value);
  unit.textContent = reading.unit;
  evaluation.textContent = reading.evaluation;
  evaluation.className = reading.evaluation;
  measuredAt.textContent = reading.measured_at;

  flash(row);
}

function flash(row) {
  row.classList.add("flash");
  setTimeout(() => row.classList.remove("flash"), 300);
}

// status is a bool (finding present or not) or a severity string.
function statusLabel(status) {
  if (status === true) return ["present", "warning"];
  if (status === false) return ["none", "nominal"];
  return [status, status];
}

function renderFinding(finding) {
  const rowId = `finding-${finding.id}`;
  let row = document.getElementById(rowId);
  if (!row) {
    row = document.createElement("tr");
    row.id = rowId;
    row.innerHTML = "<td></td><td></td><td></td><td class='action'></td>";
    document.getElementById("findings").append(row);
  }
  const [name, status, triggers, action] = row.children;
  name.textContent = findings[finding.id]?.name ?? finding.id;
  const [label, level] = statusLabel(finding.status);
  status.textContent = label;
  status.className = level;
  triggers.textContent = finding.triggers.join("; ");
  action.textContent = finding.action;
  flash(row);
}

const stream = new EventSource("/api/stream/");

stream.addEventListener("dictionary", (event) => {
  ({ channels, findings } = JSON.parse(event.data));
  if (received === 0) {
    statusLine.textContent = "Connected · waiting for readings (is the simulator running?)";
  }
});

stream.addEventListener("reading", (event) => {
  const reading = JSON.parse(event.data);
  received += 1;
  const previous = latest.get(reading.channel);
  // Late lab results arrive out of order: keep the newer measurement.
  if (!previous || Date.parse(reading.measured_at) >= Date.parse(previous.measured_at)) {
    latest.set(reading.channel, reading);
    render(reading);
  }
  statusLine.textContent = `Connected · ${received} readings received · last ${reading.channel}`;
});

stream.addEventListener("finding", (event) => {
  renderFinding(JSON.parse(event.data));
});

stream.onerror = () => {
  statusLine.textContent = "Disconnected; the browser retries automatically …";
};
