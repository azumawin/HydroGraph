// Run with `npm test` (node's built-in runner; no test dependency).
import assert from "node:assert/strict";
import { test } from "node:test";
import { vitalChartAxis } from "./chartAxis.ts";

const TICK_COUNT = 3;

// Measured over two minutes of badscenario1 at speed 1, in display units.
const SPO2_PCT = [97.9863, 97.9996];
const TEMPERATURE_C = [36.6921, 36.6943];
const HEART_RATE_BPM = [68.6184, 72.0];
const GLUCOSE_MMOL = [4.953, 5.2334];

const axis = (values: number[], minSpan: number) => vitalChartAxis(values, minSpan, TICK_COUNT);

const labels = (values: number[], minSpan: number) => {
  const result = axis(values, minSpan);
  return result.ticks.map(result.formatTick);
};

// How much of the chart's height the plotted line occupies.
const heightUsed = (values: number[], minSpan: number) => {
  const [low, high] = axis(values, minSpan).domain;
  return (Math.max(...values) - Math.min(...values)) / (high - low);
};

void test("a steady vital never prints the same tick label twice", () => {
  // The reported bug: "98 98 98" down the left while the line slid downward.
  assert.deepEqual(labels(SPO2_PCT, 2), ["97", "98", "99"]);
  assert.deepEqual(labels(TEMPERATURE_C, 1), ["36.2", "36.7", "37.2"]);

  for (const [values, minSpan] of [
    [SPO2_PCT, 2],
    [TEMPERATURE_C, 1],
    [HEART_RATE_BPM, 10],
    [GLUCOSE_MMOL, 1],
    [[98], 2],
  ] as const) {
    assert.equal(new Set(labels([...values], minSpan)).size, TICK_COUNT);
  }
});

void test("a steady vital is drawn flat instead of filling the chart", () => {
  // 0.013 percentage points of SpO2 drift is noise, not a desaturation.
  assert.ok(heightUsed(SPO2_PCT, 2) < 0.02, "SpO2 noise should stay flat");
  assert.ok(heightUsed(TEMPERATURE_C, 1) < 0.02, "temperature noise should stay flat");
});

void test("a vital that really moves still uses the whole chart", () => {
  // Exercise takes the heart rate well past its minimum span: the axis has to
  // follow the data rather than clip it.
  const exercise = [72, 120];
  assert.equal(heightUsed(exercise, 10), 1);
  assert.deepEqual(axis(exercise, 10).domain, [72, 120]);
  assert.deepEqual(labels(exercise, 10), ["72", "96", "120"]);

  // Resting heart rate and the glucose demo trend are visible, not flattened.
  assert.ok(heightUsed(HEART_RATE_BPM, 10) > 0.3);
  assert.ok(heightUsed(GLUCOSE_MMOL, 1) > 0.25);
});

void test("every value stays inside the axis window", () => {
  for (const [values, minSpan] of [
    [SPO2_PCT, 2],
    [TEMPERATURE_C, 1],
    [HEART_RATE_BPM, 10],
    [[72, 120], 10],
    [[98], 2],
  ] as const) {
    const [low, high] = axis([...values], minSpan).domain;
    assert.ok(Math.min(...values) >= low, "lowest value is on the chart");
    assert.ok(Math.max(...values) <= high, "highest value is on the chart");
  }
});
