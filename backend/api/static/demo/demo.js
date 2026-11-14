// Live view of /api/stream/: one table per owner, one row per channel.
// Shapes: docs/json-shape.md.

const statusLine = document.getElementById("status");
const ownersDiv = document.getElementById("owners");

let channels = {}; // channel id -> {name, body_regions, explanation}
const latest = new Map(); // "owner/channel" -> reading
let received = 0;

function render(reading) {
  const tableId = `owner-${reading.owner_id}`;
  let tbody = document.getElementById(tableId);
  if (!tbody) {
    const section = document.createElement("section");
    section.innerHTML =
      `<h2></h2><table><thead><tr><th>Channel</th><th>Value</th><th>Unit</th>` +
      `<th>Evaluation</th><th>Measured at</th></tr></thead><tbody></tbody></table>`;
    section.querySelector("h2").textContent = `${reading.owner_id} (${reading.scope})`;
    section.querySelector("tbody").id = tableId;
    ownersDiv.append(section);
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

  row.classList.add("flash");
  setTimeout(() => row.classList.remove("flash"), 300);
}

const stream = new EventSource("/api/stream/");

stream.addEventListener("dictionary", (event) => {
  channels = JSON.parse(event.data).channels;
  if (received === 0) {
    statusLine.textContent = "Connected · waiting for readings (is the simulator running?)";
  }
});

stream.addEventListener("reading", (event) => {
  const reading = JSON.parse(event.data);
  received += 1;
  const key = `${reading.owner_id}/${reading.channel}`;
  const previous = latest.get(key);
  // Late lab results arrive out of order: keep the newer measurement.
  if (!previous || Date.parse(reading.measured_at) >= Date.parse(previous.measured_at)) {
    latest.set(key, reading);
    render(reading);
  }
  statusLine.textContent = `Connected · ${received} readings received · last ${reading.channel}`;
});

stream.onerror = () => {
  statusLine.textContent = "Disconnected; the browser retries automatically …";
};
