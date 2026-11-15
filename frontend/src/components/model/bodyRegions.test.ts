// How the body scan decides what colour each part of the body is drawn with.
// Run with `npm test`.
//
// The model has twenty-three parts and the channels name only ten of them, so
// what keeps the body from being mostly grey -- and from disagreeing with the
// legend beside it -- is the mapping below. The groups here are
// BODY_SCAN_REGION_GROUPS as Constants.ts defines them; the backend pins the
// same list against core's channels in api/test_contracts.py.
import assert from "node:assert/strict";
import { test } from "node:test";
import { BODY_REGION_IDS, groupEvaluationByRegion, worstEvaluation } from "./ModelConstants.ts";
import type { BodyRegionGroup } from "./ModelConstants.ts";
import type { Evaluation } from "../../api/types.ts";

const GROUPS: readonly BodyRegionGroup[] = [
  { LABEL: "Head & neck", REGIONS: ["head", "neck"] },
  { LABEL: "Upper body", REGIONS: ["heart", "chest", "abdomen"] },
  {
    LABEL: "Arms",
    REGIONS: [
      "left_shoulder",
      "right_shoulder",
      "left_upper_arm",
      "right_upper_arm",
      "left_forearm",
      "right_forearm",
      "left_hand",
      "right_hand",
    ],
  },
  {
    LABEL: "Lower body",
    REGIONS: [
      "pelvis",
      "left_thigh",
      "right_thigh",
      "left_lower_leg",
      "right_lower_leg",
      "left_foot",
      "right_foot",
    ],
  },
  { LABEL: "Joints", REGIONS: ["left_elbow", "right_elbow", "left_knee", "right_knee"] },
];

void test("every part of the model belongs to exactly one group in the legend", () => {
  // Otherwise that part could never be coloured, whatever was measured.
  const grouped = GROUPS.flatMap((group) => group.REGIONS);
  for (const region of BODY_REGION_IDS) {
    assert.equal(
      grouped.filter((name) => name === region).length,
      1,
      `${region} is drawn but not in exactly one legend group`,
    );
  }
  // "heart" is the one region in the legend with no mesh of its own.
  assert.deepEqual(
    grouped.filter((region) => !BODY_REGION_IDS.includes(region as never)),
    ["heart"],
  );
});

void test("a reading colours every part of its group, not just its own", () => {
  // A jugular-strain warning sits on the neck; the head is in its group and
  // reads the same, as the legend's single "Head & neck" row does.
  const drawn = groupEvaluationByRegion(GROUPS, { neck: "warning" });

  assert.equal(drawn.neck, "warning");
  assert.equal(drawn.head, "warning");
  // Nothing was read anywhere else, so the rest of the body stays neutral.
  assert.equal(drawn.chest, undefined);
  assert.equal(drawn.left_hand, undefined);
  assert.equal(drawn.pelvis, undefined);
});

void test("the heart reaches the mesh through the group it shares", () => {
  // Five cardiovascular channels name "heart", which has no mesh; the chest
  // and abdomen carry it instead.
  const drawn = groupEvaluationByRegion(GROUPS, { heart: "critical" });

  assert.equal(drawn.chest, "critical");
  assert.equal(drawn.abdomen, "critical");
  assert.equal(drawn.heart, "critical", "kept, though nothing draws it");
});

void test("the worst reading in a group is the one drawn", () => {
  const drawn = groupEvaluationByRegion(GROUPS, {
    pelvis: "nominal",
    left_thigh: "warning",
    right_lower_leg: "critical",
  });

  for (const region of GROUPS[3]?.REGIONS ?? []) {
    assert.equal(drawn[region], "critical", region);
  }
  // Including the feet, which no channel measures.
  assert.equal(drawn.left_foot, "critical");
  assert.equal(drawn.right_foot, "critical");
});

void test("a nominal group is drawn nominal, not left looking unread", () => {
  // The legend shows a green dot for this; the model used to draw it in the
  // same grey as a part with no reading at all.
  const drawn = groupEvaluationByRegion(GROUPS, { head: "nominal", neck: "nominal" });

  assert.equal(drawn.head, "nominal");
  assert.equal(drawn.neck, "nominal");
});

void test("an ungraded reading is measured but carries no colour of its own", () => {
  // "No threshold": the specs give this channel no cutoff. It must not mask a
  // warning elsewhere in the group.
  assert.equal(groupEvaluationByRegion(GROUPS, { chest: "unspecified" }).abdomen, "unspecified");
  assert.equal(
    groupEvaluationByRegion(GROUPS, { chest: "unspecified", heart: "warning" }).abdomen,
    "warning",
  );
});

void test("nothing read leaves the whole body neutral", () => {
  assert.deepEqual(groupEvaluationByRegion(GROUPS, {}), {});
  assert.deepEqual(groupEvaluationByRegion([], { head: "critical" }), {});
});

void test("the worst of a set of evaluations ranks critical over warning over nominal", () => {
  const cases: [readonly (Evaluation | undefined)[], Evaluation | undefined][] = [
    [[], undefined],
    [[undefined], undefined],
    [["nominal"], "nominal"],
    [["nominal", "unspecified"], "unspecified"],
    [["unspecified", "warning"], "warning"],
    [["warning", "critical"], "critical"],
    [["critical", undefined, "nominal"], "critical"],
  ];
  for (const [evaluations, worst] of cases) {
    assert.equal(worstEvaluation(evaluations), worst, JSON.stringify(evaluations));
  }
});
