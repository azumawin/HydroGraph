import axios from "axios";
import { TELEMETRY } from "../Constants.ts";

export type Evaluation = "nominal" | "warning" | "critical" | "unspecified";

export type FindingSeverity = "nominal" | "warning" | "critical";

export type ConsciousnessLevel = "ALERT" | "CONFUSION" | "VOICE" | "PAIN" | "UNRESPONSIVE";

export type TelemetryReading = {
  channel: string;
  value: number | boolean | ConsciousnessLevel;
  unit: string;
  evaluation: Evaluation;
  measured_at: string;
  scope: "crew" | "environment";
};

export type TelemetryFinding = {
  id: string;
  status: boolean | FindingSeverity;
  triggers: string[];
  action: string;
  news2_score?: number;
  qsofa_score?: number;
  il6_source_channel?: string;
};

export type ChannelInfo = {
  name: string;
  body_regions: string[];
  explanation: string;
};

export type FindingInfo = {
  name: string;
  channels: string[];
};

export type MissionEnvironment = {
  id: string;
  name: string;
  gravity_g: number;
  comm_delay_rt_s: number;
  baseline_dose_rate_usv_h: number;
  storm_shelter_available: boolean;
  day_length_h: number;
};

export type TelemetryDictionary = {
  environments: MissionEnvironment[];
  channels: Record<string, ChannelInfo>;
  findings: Record<string, FindingInfo>;
};

export type TelemetryStreamHandlers = {
  onDictionary: (dictionary: TelemetryDictionary) => void;
  onEnvironment: (environmentId: string) => void;
  onReading: (reading: TelemetryReading) => void;
  onFinding: (finding: TelemetryFinding) => void;
  onError: (error: Error) => void;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

const isFindingSeverity = (value: unknown): value is FindingSeverity =>
  value === "nominal" || value === "warning" || value === "critical";

const isEvaluation = (value: unknown): value is Evaluation =>
  isFindingSeverity(value) || value === "unspecified";

const isScope = (value: unknown): value is TelemetryReading["scope"] =>
  value === "crew" || value === "environment";

const isChannelInfo = (value: unknown): value is ChannelInfo =>
  isRecord(value) &&
  typeof value.name === "string" &&
  isStringArray(value.body_regions) &&
  typeof value.explanation === "string";

const isFindingInfo = (value: unknown): value is FindingInfo =>
  isRecord(value) && typeof value.name === "string" && isStringArray(value.channels);

const isMissionEnvironment = (value: unknown): value is MissionEnvironment =>
  isRecord(value) &&
  typeof value.id === "string" &&
  typeof value.name === "string" &&
  typeof value.gravity_g === "number" &&
  typeof value.comm_delay_rt_s === "number" &&
  typeof value.baseline_dose_rate_usv_h === "number" &&
  typeof value.storm_shelter_available === "boolean" &&
  typeof value.day_length_h === "number";

const malformed = () => new TypeError(TELEMETRY.MALFORMED_MESSAGE);

const parseData = (event: MessageEvent<unknown>): Record<string, unknown> => {
  if (typeof event.data !== "string") throw malformed();
  const data: unknown = JSON.parse(event.data);
  if (!isRecord(data)) throw malformed();
  return data;
};

const isConsciousness = (value: unknown): value is ConsciousnessLevel =>
  typeof value === "string" &&
  ["ALERT", "CONFUSION", "VOICE", "PAIN", "UNRESPONSIVE"].includes(value);

const parseReading = (data: Record<string, unknown>): TelemetryReading => {
  const { channel, value, unit, evaluation, measured_at, scope } = data;
  if (
    typeof channel !== "string" ||
    (typeof value !== "number" &&
      typeof value !== "boolean" &&
      !(channel === "consciousness_level" && isConsciousness(value))) ||
    typeof unit !== "string" ||
    !isEvaluation(evaluation) ||
    typeof measured_at !== "string" ||
    !isScope(scope)
  ) {
    throw malformed();
  }
  return { channel, value, unit, evaluation, measured_at, scope };
};

const parseFinding = (data: Record<string, unknown>): TelemetryFinding => {
  const { id, status, triggers, action } = data;
  if (
    typeof id !== "string" ||
    (typeof status !== "boolean" && !isFindingSeverity(status)) ||
    !isStringArray(triggers) ||
    typeof action !== "string"
  ) {
    throw malformed();
  }
  return {
    id,
    status,
    triggers,
    action,
    ...(typeof data.news2_score === "number" ? { news2_score: data.news2_score } : {}),
    ...(typeof data.qsofa_score === "number" ? { qsofa_score: data.qsofa_score } : {}),
    ...(typeof data.il6_source_channel === "string"
      ? { il6_source_channel: data.il6_source_channel }
      : {}),
  };
};

const parseEnvironmentId = (data: Record<string, unknown>): string => {
  const { id } = data;
  if (typeof id !== "string") throw malformed();
  return id;
};

const parseDictionary = (data: Record<string, unknown>): TelemetryDictionary => {
  const { environments, channels, findings } = data;
  if (
    !Array.isArray(environments) ||
    !environments.every(isMissionEnvironment) ||
    !isRecord(channels) ||
    !isRecord(findings)
  ) {
    throw malformed();
  }
  const channelEntries = Object.entries(channels);
  const findingEntries = Object.entries(findings);
  if (
    !channelEntries.every(([, info]) => isChannelInfo(info)) ||
    !findingEntries.every(([, info]) => isFindingInfo(info))
  ) {
    throw malformed();
  }
  return {
    environments,
    channels: Object.fromEntries(
      channelEntries.flatMap(([channel, info]) => (isChannelInfo(info) ? [[channel, info]] : [])),
    ),
    findings: Object.fromEntries(
      findingEntries.flatMap(([finding, info]) => (isFindingInfo(info) ? [[finding, info]] : [])),
    ),
  };
};

export const openTelemetryStream = (handlers: TelemetryStreamHandlers): EventSource => {
  const stream = new EventSource(TELEMETRY.STREAM_URL);

  const listen = <T>(
    eventName: string,
    parse: (data: Record<string, unknown>) => T,
    handle: (value: T) => void,
  ) => {
    stream.addEventListener(eventName, (event: MessageEvent<unknown>) => {
      try {
        handle(parse(parseData(event)));
      } catch (error) {
        handlers.onError(error instanceof Error ? error : new Error(String(error)));
      }
    });
  };

  listen(TELEMETRY.EVENTS.DICTIONARY, parseDictionary, handlers.onDictionary);
  listen(TELEMETRY.EVENTS.ENVIRONMENT, parseEnvironmentId, handlers.onEnvironment);
  listen(TELEMETRY.EVENTS.READING, parseReading, handlers.onReading);
  listen(TELEMETRY.EVENTS.FINDING, parseFinding, handlers.onFinding);
  stream.addEventListener("error", () => {
    handlers.onError(new Error(TELEMETRY.DISCONNECTED_MESSAGE));
  });

  return stream;
};

export const putEnvironment = async (environmentId: string): Promise<string> => {
  const response = await axios.put<unknown>(TELEMETRY.ENVIRONMENT_URL, { id: environmentId });
  if (!isRecord(response.data)) throw malformed();
  return parseEnvironmentId(response.data);
};
