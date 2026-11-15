// The backend contract the dashboard is built on. Run with `npm test`.
//
// These are the only checks standing between a changed payload and a dashboard
// that renders wrong instead of saying so: the store writes whatever comes back
// here straight into the rows, charts and body scan. Every field asserted below
// is one the dashboard reads, so a backend change that drops or renames one
// must fail here rather than in a demo.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  MALFORMED_MESSAGE,
  errorDetail,
  parseAssistantReply,
  parseDictionary,
  parseEnvironmentId,
  parseFinding,
  parseHistory,
  parseReading,
  parseStreamData,
} from "./parse.ts";

const READING = {
  channel: "spo2",
  value: 0.979,
  measured_at: "2026-11-14T08:00:00Z",
  evaluation: "nominal",
};
const FINDING = {
  id: "blood_pressure_1_4",
  status: "warning",
  triggers: ["shock index > 0.9"],
  action: "Repeat the measurement seated.",
  values: { map_mmhg: 93.3 },
};
const CHANNEL = {
  name: "Blood oxygen",
  scope: "crew",
  unit: "1",
  value_type: "number",
  display: { unit: "%", scale: 100, offset: 0 },
  body_regions: ["chest"],
  explanation: "Pulse oximetry",
};
const ENVIRONMENT = {
  name: "ISS, low Earth orbit",
  gravity_g: 0,
  comm_delay_rt_s: 0.5,
  baseline_dose_rate_usv_h: 14.6,
  storm_shelter_available: true,
  day_length_h: 1.5,
};
const DICTIONARY = {
  environments: { iss_leo: ENVIRONMENT },
  channels: { spo2: CHANNEL },
  findings: { blood_pressure_1_4: { name: "Blood pressure", channels: ["bp_systolic"] } },
};

// Each case must be rejected: a payload the dashboard cannot trust raises, so
// the error banner shows instead of a half-filled row.
const rejects = (parse: (data: unknown) => unknown, cases: Record<string, unknown>) => {
  for (const [why, data] of Object.entries(cases)) {
    assert.throws(() => parse(data), { message: MALFORMED_MESSAGE }, why);
  }
};

void test("a server-sent event carries JSON text holding an object", () => {
  assert.deepEqual(parseStreamData('{"id":"iss_leo"}'), { id: "iss_leo" });
  rejects(parseStreamData, {
    "not a string": { id: "iss_leo" },
    "an array, not an object": "[1, 2]",
    "a bare string": '"iss_leo"',
    null: "null",
    undefined: undefined,
  });
  assert.throws(() => parseStreamData("{broken"), SyntaxError);
});

void test("a reading keeps every field the rows and charts read", () => {
  assert.deepEqual(parseReading(READING), READING);
  assert.deepEqual(parseReading({ ...READING, value: true }).value, true, "a flag channel");
  assert.equal(parseReading({ ...READING, evaluation: "unspecified" }).evaluation, "unspecified");
  for (const evaluation of ["nominal", "warning", "critical"]) {
    assert.equal(parseReading({ ...READING, evaluation }).evaluation, evaluation);
  }
});

void test("a reading that would render wrong is rejected, not patched", () => {
  rejects(parseReading, {
    "no channel": { ...READING, channel: undefined },
    "a numeric channel id": { ...READING, channel: 7 },
    "text in a numeric channel": { ...READING, value: "0.979" },
    "no value": { ...READING, value: undefined },
    "no timestamp": { ...READING, measured_at: undefined },
    "a numeric timestamp": { ...READING, measured_at: 1794650400000 },
    "an unknown evaluation": { ...READING, evaluation: "elevated" },
    "no evaluation": { ...READING, evaluation: undefined },
    "not an object": "spo2",
  });
});

void test("ACVPU text is a reading only on the consciousness channel", () => {
  const acvpu = { ...READING, channel: "consciousness_level", value: "CONFUSION" };
  assert.equal(parseReading(acvpu).value, "CONFUSION");
  rejects(parseReading, {
    "an invalid state": { ...acvpu, value: "DROWSY" },
    "a state on another channel": { ...READING, value: "ALERT" },
  });
});

void test("a finding keeps the status, triggers and action the conditions tab shows", () => {
  assert.deepEqual(parseFinding(FINDING), FINDING);
  assert.deepEqual(parseFinding({ ...FINDING, triggers: [] }).triggers, []);
  rejects(parseFinding, {
    "an unknown status": { ...FINDING, status: "elevated" },
    "unspecified, which gradable channels use but findings never do": {
      ...FINDING,
      status: "unspecified",
    },
    "triggers that are not text": { ...FINDING, triggers: [1] },
    "a single trigger string": { ...FINDING, triggers: "shock index > 0.9" },
    "no action": { ...FINDING, action: undefined },
    "no values": { ...FINDING, values: undefined },
    "values as a list": { ...FINDING, values: [] },
  });
});

void test("the dictionary keeps every field the tabs build their rows from", () => {
  const dictionary = parseDictionary(DICTIONARY);
  assert.deepEqual(dictionary, DICTIONARY);
  // The all-measurements tab reads all of these per channel.
  assert.deepEqual(Object.keys(dictionary.channels.spo2 ?? {}).toSorted(), [
    "body_regions",
    "display",
    "explanation",
    "name",
    "scope",
    "unit",
    "value_type",
  ]);
  assert.deepEqual(parseDictionary({ environments: {}, channels: {}, findings: {} }).channels, {});
});

void test("a dictionary missing what a tab needs is rejected", () => {
  const without = (field: keyof typeof CHANNEL) => {
    const { [field]: _dropped, ...rest } = CHANNEL;
    return { ...DICTIONARY, channels: { spo2: rest } };
  };
  rejects(parseDictionary, {
    "no channels": { ...DICTIONARY, channels: undefined },
    "no findings": { ...DICTIONARY, findings: undefined },
    "no environments": { ...DICTIONARY, environments: undefined },
    "a channel without a name": without("name"),
    "a channel without a display conversion": without("display"),
    "a channel without body regions": without("body_regions"),
    "a channel without an explanation": without("explanation"),
    "a channel without a value type": without("value_type"),
    "a channel without a scope": without("scope"),
    "an unknown scope": {
      ...DICTIONARY,
      channels: { spo2: { ...CHANNEL, scope: "vehicle" } },
    },
    "an unknown value type": {
      ...DICTIONARY,
      channels: { spo2: { ...CHANNEL, value_type: "text" } },
    },
    "a display without a scale": {
      ...DICTIONARY,
      channels: { spo2: { ...CHANNEL, display: { unit: "%", offset: 0 } } },
    },
    "a finding without its input channels": {
      ...DICTIONARY,
      findings: { blood_pressure_1_4: { name: "Blood pressure" } },
    },
    "an environment without its dose baseline": {
      ...DICTIONARY,
      environments: { iss_leo: { ...ENVIRONMENT, baseline_dose_rate_usv_h: undefined } },
    },
    "an environment without a day length": {
      ...DICTIONARY,
      environments: { iss_leo: { ...ENVIRONMENT, day_length_h: "1.5" } },
    },
  });
});

void test("the selected environment is read from its id alone", () => {
  assert.equal(parseEnvironmentId({ id: "lunar_surface" }), "lunar_surface");
  rejects(parseEnvironmentId, {
    "no id": {},
    "a numeric id": { id: 3 },
    "not an object": "lunar_surface",
  });
});

void test("history arrives per channel and is flattened for the store", () => {
  const second = { ...READING, channel: "heart_rate", value: 1.2 };
  assert.deepEqual(parseHistory({ readings: { spo2: [READING], heart_rate: [second] } }), [
    READING,
    second,
  ]);
  assert.deepEqual(parseHistory({ readings: {} }), [], "no channels have readings yet");
  rejects(parseHistory, {
    "no readings key": {},
    "readings as a list": { readings: [] },
    "a channel holding one reading, not a list": { readings: { spo2: READING } },
    "a channel holding a malformed reading": { readings: { spo2: [{ channel: "spo2" }] } },
  });
});

void test("the assistant's reply and its reason for being unavailable", () => {
  assert.equal(parseAssistantReply({ reply: "Crew is nominal." }), "Crew is nominal.");
  assert.equal(parseAssistantReply({ reply: "" }), "", "an empty reply is still a reply");
  rejects(parseAssistantReply, {
    "no reply": {},
    "a reply that is not text": { reply: 7 },
    "not an object": "Crew is nominal.",
  });

  // The 503 body the chat shows verbatim; anything else leaves the fallback.
  const unavailable = "The assistant is not configured.";
  assert.equal(errorDetail({ detail: unavailable }), unavailable);
  assert.equal(errorDetail({}), null);
  assert.equal(errorDetail({ detail: 503 }), null);
  assert.equal(errorDetail(undefined), null);
});
