// Run with `npm test` (node's built-in runner; no test dependency).
import assert from "node:assert/strict";
import { test } from "node:test";
import { isCurrent, toVitalReading, withHistoryPoint } from "./history.ts";
import type { VitalHistoryPoint, VitalReading } from "./history.ts";

const MAX_POINTS = 120;

const spo2 = {
  name: "Blood oxygen (SpO2)",
  scope: "crew" as const,
  unit: "1",
  value_type: "number" as const,
  display: { unit: "%", scale: 100, offset: 0 },
  body_regions: ["chest"],
  explanation: "",
};

const temperature = {
  ...spo2,
  name: "Body temperature",
  unit: "K",
  display: { unit: "°C", scale: 1, offset: -273.15 },
};

const at = (second: number) => `2026-11-14T08:00:${String(second).padStart(2, "0")}Z`;

const reading = (channel: string, value: number | boolean | "ALERT", measured_at: string) => ({
  channel,
  value,
  measured_at,
  evaluation: "nominal" as const,
});

void test("a reading is shown in its channel's display unit", () => {
  // The wire carries SI; the dashboard and its charts share the converted value.
  assert.equal(toVitalReading(reading("spo2", 0.9797, at(0)), spo2).value, 97.97);
  const celsius = toVitalReading(reading("body_temperature", 309.85, at(0)), temperature);
  assert.ok(Math.abs((celsius.value as number) - 36.7) < 1e-9);
  assert.equal(celsius.unit, "°C");
});

void test("flags and ACVPU text are passed through unscaled", () => {
  assert.equal(toVitalReading(reading("spe_flag", true, at(0)), spo2).value, true);
  assert.equal(toVitalReading(reading("consciousness_level", "ALERT", at(0)), spo2).value, "ALERT");
});

void test("a reading measured earlier never replaces the current one", () => {
  // History fetched after the stream opened, or a demo preload written behind
  // the live simulator, arrives late but describes the past.
  const live: VitalReading = {
    channel: "spo2",
    value: 97.9,
    unit: "%",
    evaluation: "nominal",
    measured_at: at(30),
  };
  assert.equal(isCurrent(undefined, Date.parse(at(0))), true, "first reading is current");
  assert.equal(isCurrent(live, Date.parse(at(29))), false, "backdated reading is not");
  assert.equal(isCurrent(live, Date.parse(at(30))), true, "the same instant re-sent is");
  assert.equal(isCurrent(live, Date.parse(at(31))), true, "a newer reading is");
});

void test("history keeps one point per timestamp, oldest first, later arrival winning", () => {
  let points: VitalHistoryPoint[] = [];
  for (const [second, value] of [
    [20, 97.0],
    [0, 98.0],
    [10, 97.5],
    [10, 97.6], // the same instant again, e.g. from the history fetch
  ] as const) {
    points = withHistoryPoint(points, { timestamp: Date.parse(at(second)), value }, MAX_POINTS);
  }

  assert.deepEqual(
    points.map((point) => point.value),
    [98.0, 97.6, 97.0],
  );
});

void test("history is a rolling window, not a store of everything", () => {
  // The vitals charts show the recent past. A long-range trends view cannot
  // read months out of this buffer; it needs its own data path.
  let points: VitalHistoryPoint[] = [];
  for (let second = 0; second < MAX_POINTS + 25; second += 1) {
    points = withHistoryPoint(points, { timestamp: second * 1000, value: second }, MAX_POINTS);
  }

  assert.equal(points.length, MAX_POINTS);
  assert.equal(points[0]?.value, 25, "the oldest points are the ones dropped");
  assert.equal(points.at(-1)?.value, MAX_POINTS + 24);
});
