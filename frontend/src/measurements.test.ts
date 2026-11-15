// Run with `npm test` (node's built-in runner; no test dependency).
import assert from "node:assert/strict";
import { test } from "node:test";
import { groupByScope, measurementMinSpan, pointsInRange } from "./measurements.ts";
import type { ChannelInfo } from "./api/types.ts";

const channel = (scope: ChannelInfo["scope"]): ChannelInfo => ({
  name: "",
  scope,
  unit: "1",
  value_type: "number",
  display: { unit: "", scale: 1, offset: 0 },
  body_regions: [],
  explanation: "",
});

// Interleaved, as the backend lists them: the view must keep this order within
// each group rather than sorting by name.
const channels: Record<string, ChannelInfo> = {
  heart_rate: channel("crew"),
  ambient_ppco2: channel("environment"),
  spo2: channel("crew"),
  ambient_dose_rate: channel("environment"),
  jugular_strain_pct: channel("crew"),
};

void test("channels are grouped by scope, crew first, in dictionary order", () => {
  assert.deepEqual(groupByScope(channels, ["crew", "environment"]), [
    { scope: "crew", channels: ["heart_rate", "spo2", "jugular_strain_pct"] },
    { scope: "environment", channels: ["ambient_ppco2", "ambient_dose_rate"] },
  ]);
  // Every channel lands in exactly one group.
  const grouped = groupByScope(channels, ["crew", "environment"]).flatMap((g) => g.channels);
  assert.deepEqual(grouped.toSorted(), Object.keys(channels).toSorted());
});

void test("a curated vital keeps its own axis span; other channels scale with their value", () => {
  assert.equal(measurementMinSpan(2, 97.98, 0.05, 0.001), 2, "curated SpO2 span wins");
  assert.equal(measurementMinSpan(undefined, 40, 0.05, 0.001), 2, "5% of 40");
  assert.equal(measurementMinSpan(undefined, -40, 0.05, 0.001), 2, "magnitude, not sign");
  assert.equal(measurementMinSpan(undefined, 0, 0.05, 0.001), 0.001, "floor at zero");
  assert.equal(measurementMinSpan(undefined, undefined, 0.05, 0.001), 0.001, "floor when unread");
});

// The window the timeframe buttons select. Minute-scale windows are what the
// data supports: 120 points per channel at cadences from 1 s to 60 s.
const NEWEST = Date.UTC(2026, 10, 14, 12);
const point = (secondsAgo: number) => ({ timestamp: NEWEST - secondsAgo * 1000, value: 1 });
const series = [point(1800), point(600), point(240), point(30), point(0)];

void test("a null range draws the whole history", () => {
  assert.deepEqual(pointsInRange(series, null), series);
  assert.deepEqual(pointsInRange([], null), []);
  assert.deepEqual(pointsInRange([], 60), []);
});

void test("a range keeps the points inside it, measured back from the newest", () => {
  assert.deepEqual(pointsInRange(series, 60), [point(30), point(0)]);
  assert.deepEqual(pointsInRange(series, 300), [point(240), point(30), point(0)]);
  assert.deepEqual(pointsInRange(series, 1800), series, "the boundary point is inside");
});

void test("a range wider than the history keeps all of it", () => {
  assert.deepEqual(pointsInRange(series, 86400), series);
});

void test("the newest point is always in range, so no chart goes empty", () => {
  // The window ends at the newest reading, not at the clock: a 1 Hz channel
  // holds two minutes and a once-a-minute channel two hours, and a finished run
  // keeps neither up to date.
  const stale = [point(7200), point(7140)];
  assert.deepEqual(pointsInRange(stale, 30), [point(7140)]);
  assert.deepEqual(pointsInRange(stale, 300), stale);
});
