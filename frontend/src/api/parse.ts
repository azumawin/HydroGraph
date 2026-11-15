// Every message the backend sends, checked into the dashboard's own types.
//
// The dashboard trusts nothing on the wire: a payload that does not match the
// contract raises instead of flowing into the store as a partly-filled reading,
// which would surface as a blank row or an unexplained chart rather than the
// error banner. Transport-free and pure, so `npm test` covers the contract
// without a browser, a stream or a running backend.
import type {
  ChannelDisplay,
  ChannelInfo,
  ChannelValueType,
  ConsciousnessLevel,
  Evaluation,
  FindingInfo,
  FindingSeverity,
  MissionEnvironment,
  TelemetryDictionary,
  TelemetryFinding,
  TelemetryReading,
} from "./types.ts";

export const MALFORMED_MESSAGE =
  "Received a telemetry message that does not match the backend contract.";

const malformed = () => new TypeError(MALFORMED_MESSAGE);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isRecordOf = <T>(
  value: unknown,
  isEntry: (entry: unknown) => entry is T,
): value is Record<string, T> => isRecord(value) && Object.values(value).every(isEntry);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

const isFindingSeverity = (value: unknown): value is FindingSeverity =>
  value === "nominal" || value === "warning" || value === "critical";

const isEvaluation = (value: unknown): value is Evaluation =>
  isFindingSeverity(value) || value === "unspecified";

const isScope = (value: unknown): value is ChannelInfo["scope"] =>
  value === "crew" || value === "environment";

const isChannelDisplay = (value: unknown): value is ChannelDisplay =>
  isRecord(value) &&
  typeof value.unit === "string" &&
  typeof value.scale === "number" &&
  typeof value.offset === "number";

const isValueType = (value: unknown): value is ChannelValueType =>
  value === "number" || value === "boolean" || value === "enum";

const isChannelInfo = (value: unknown): value is ChannelInfo =>
  isRecord(value) &&
  typeof value.name === "string" &&
  isScope(value.scope) &&
  typeof value.unit === "string" &&
  isValueType(value.value_type) &&
  isChannelDisplay(value.display) &&
  isStringArray(value.body_regions) &&
  typeof value.explanation === "string";

const isFindingInfo = (value: unknown): value is FindingInfo =>
  isRecord(value) && typeof value.name === "string" && isStringArray(value.channels);

const isMissionEnvironment = (value: unknown): value is MissionEnvironment =>
  isRecord(value) &&
  typeof value.name === "string" &&
  typeof value.gravity_g === "number" &&
  typeof value.comm_delay_rt_s === "number" &&
  typeof value.baseline_dose_rate_usv_h === "number" &&
  typeof value.storm_shelter_available === "boolean" &&
  typeof value.day_length_h === "number";

const isConsciousness = (value: unknown): value is ConsciousnessLevel =>
  typeof value === "string" &&
  ["ALERT", "CONFUSION", "VOICE", "PAIN", "UNRESPONSIVE"].includes(value);

// One server-sent event's `data`: JSON text holding an object.
export const parseStreamData = (data: unknown): Record<string, unknown> => {
  if (typeof data !== "string") throw malformed();
  const parsed: unknown = JSON.parse(data);
  if (!isRecord(parsed)) throw malformed();
  return parsed;
};

export const parseReading = (data: unknown): TelemetryReading => {
  if (!isRecord(data)) throw malformed();
  const { channel, value, measured_at, evaluation } = data;
  if (
    typeof channel !== "string" ||
    (typeof value !== "number" &&
      typeof value !== "boolean" &&
      !(channel === "consciousness_level" && isConsciousness(value))) ||
    typeof measured_at !== "string" ||
    !isEvaluation(evaluation)
  ) {
    throw malformed();
  }
  return { channel, value, measured_at, evaluation };
};

export const parseFinding = (data: unknown): TelemetryFinding => {
  if (!isRecord(data)) throw malformed();
  const { id, status, triggers, action, values } = data;
  if (
    typeof id !== "string" ||
    !isFindingSeverity(status) ||
    !isStringArray(triggers) ||
    typeof action !== "string" ||
    !isRecord(values)
  ) {
    throw malformed();
  }
  return { id, status, triggers, action, values };
};

export const parseEnvironmentId = (data: unknown): string => {
  if (!isRecord(data)) throw malformed();
  const { id } = data;
  if (typeof id !== "string") throw malformed();
  return id;
};

export const parseDictionary = (data: unknown): TelemetryDictionary => {
  if (!isRecord(data)) throw malformed();
  const { environments, channels, findings } = data;
  if (
    !isRecordOf(environments, isMissionEnvironment) ||
    !isRecordOf(channels, isChannelInfo) ||
    !isRecordOf(findings, isFindingInfo)
  ) {
    throw malformed();
  }
  return { environments, channels, findings };
};

// GET /api/readings/: the latest readings per channel, oldest first. Flattened,
// since the store merges them with live readings by channel and timestamp.
export const parseHistory = (data: unknown): TelemetryReading[] => {
  if (!isRecord(data) || !isRecord(data.readings)) throw malformed();
  return Object.values(data.readings).flatMap((readings) => {
    if (!Array.isArray(readings)) throw malformed();
    return readings.map(parseReading);
  });
};

// The backend's own reason for a failed request, if its body carries one: the
// assistant's 503 says why it is unavailable, and the chat shows that text.
export const errorDetail = (data: unknown): string | null => {
  if (!isRecord(data)) return null;
  const { detail } = data;
  return typeof detail === "string" ? detail : null;
};

export const parseAssistantReply = (data: unknown): string => {
  if (!isRecord(data) || typeof data.reply !== "string") throw malformed();
  return data.reply;
};
