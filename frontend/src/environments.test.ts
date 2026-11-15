// What the picker's cards and the header both print for an environment. Run
// with `npm test`.
//
// The four entries below are hydrograph_core.ENVIRONMENTS as the backend sends
// them, so these assertions are the contract the e2e suite greps for in the
// browser ("29.53 days", "26 min", "14.6 µSv/h"): a formatting change that
// would quietly rewrite a card fails here first.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  environmentEffect,
  environmentFacts,
  formatCommDelay,
  formatDayLength,
  formatDoseRate,
  formatGravity,
} from "./environments.ts";
import type { MissionEnvironment } from "./api/types.ts";

const LABELS = {
  GRAVITY: "Gravity",
  COMM_DELAY: "Comm delay, round trip",
  DAY_LENGTH: "Day",
  RADIATION: "Radiation baseline",
};

const ISS: MissionEnvironment = {
  name: "ISS, low Earth orbit",
  gravity_g: 0,
  comm_delay_rt_s: 1.2,
  baseline_dose_rate_usv_h: 14.6,
  storm_shelter_available: true,
  day_length_h: 1.52,
};
const LUNAR: MissionEnvironment = {
  name: "Lunar surface",
  gravity_g: 0.166,
  comm_delay_rt_s: 2.6,
  baseline_dose_rate_usv_h: 57.1,
  storm_shelter_available: true,
  day_length_h: 708.7,
};
const TRANSIT: MissionEnvironment = {
  name: "Mars transit",
  gravity_g: 0,
  comm_delay_rt_s: 1560,
  baseline_dose_rate_usv_h: 76.7,
  storm_shelter_available: true,
  day_length_h: 24,
};
const MARS: MissionEnvironment = {
  name: "Mars surface",
  gravity_g: 0.377,
  comm_delay_rt_s: 1560,
  baseline_dose_rate_usv_h: 26.7,
  storm_shelter_available: true,
  day_length_h: 24.66,
};

const values = (environment: MissionEnvironment) =>
  environmentFacts(environment, LABELS).map((fact) => fact.value);

void test("every catalog environment reads as the dashboard shows it", () => {
  assert.deepEqual(values(ISS), ["0 g", "1.2 s", "1.52 h", "14.6 µSv/h"]);
  assert.deepEqual(values(LUNAR), ["0.17 g", "2.6 s", "29.53 days", "57.1 µSv/h"]);
  assert.deepEqual(values(TRANSIT), ["0 g", "26 min", "24 h", "76.7 µSv/h"]);
  assert.deepEqual(values(MARS), ["0.38 g", "26 min", "24.66 h", "26.7 µSv/h"]);
});

void test("the four facts come back labelled and in the order both views show", () => {
  assert.deepEqual(
    environmentFacts(ISS, LABELS).map((fact) => fact.label),
    ["Gravity", "Comm delay, round trip", "Day", "Radiation baseline"],
  );
});

void test("a delay reads in seconds up to a minute, then in minutes", () => {
  assert.equal(formatCommDelay(0), "0 s");
  assert.equal(formatCommDelay(59.4), "59.4 s");
  assert.equal(formatCommDelay(60), "1 min");
  assert.equal(formatCommDelay(364), "6.07 min", "the fastest Mars round trip");
  assert.equal(formatCommDelay(2684), "44.73 min", "the slowest");
});

void test("a light-dark cycle reads in hours up to two days, then in days", () => {
  assert.equal(formatDayLength(1.52), "1.52 h", "an ISS orbit");
  assert.equal(formatDayLength(48), "48 h");
  assert.equal(formatDayLength(48.1), "2 days");
  assert.equal(formatDayLength(708.7), "29.53 days", "a lunar synodic day");
});

void test("gravity and dose rate carry their units", () => {
  assert.equal(formatGravity(0), "0 g");
  assert.equal(formatGravity(0.166), "0.17 g");
  assert.equal(formatDoseRate(57.1), "57.1 µSv/h");
});

void test("a card says what its environment does to the running demo", () => {
  // The simulator holds a result for half the round trip; the backend grades a
  // dose-rate spike above the baseline. Both are the environment's own numbers.
  assert.equal(
    environmentEffect(ISS),
    "Results arrive 0.6 s after they are taken. A dose-rate spike is graded above 14.6 µSv/h.",
  );
  assert.match(environmentEffect(TRANSIT), /^Results arrive 13 min /, "half of 26 min");
  assert.match(environmentEffect(LUNAR), /above 57.1 µSv\/h\.$/);
});
