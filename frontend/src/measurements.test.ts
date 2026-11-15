// Run with `npm test` (node's built-in runner; no test dependency).
import assert from "node:assert/strict";
import { test } from "node:test";
import { groupByScope, measurementMinSpan } from "./measurements.ts";
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
