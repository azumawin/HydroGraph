import axios from "axios";
import { TELEMETRY } from "../Constants.ts";

export type Evaluation = "nominal" | "warning" | "critical" | "unspecified";

export type FindingSeverity = "nominal" | "warning" | "critical";

export type TelemetryReading = {
  channel: string;
  value: number | boolean;
  measured_at: string;
  evaluation: Evaluation;
};

export type TelemetryFinding = {
  id: string;
  status: FindingSeverity;
  triggers: string[];
  action: string;
  values: Record<string, unknown>;
};

export type ChannelDisplay = {
  unit: string;
  scale: number;
  offset: number;
};

export type ChannelInfo = {
  name: string;
  scope: "crew" | "environment";
  unit: string;
  display: ChannelDisplay;
  body_regions: string[];
  explanation: string;
};

export type FindingInfo = {
  name: string;
  channels: string[];
};

export type MissionEnvironment = {
  name: string;
  gravity_g: number;
  comm_delay_rt_s: number;
  baseline_dose_rate_usv_h: number;
  storm_shelter_available: boolean;
  day_length_h: number;
};

export type TelemetryDictionary = {
  environments: Record<string, MissionEnvironment>;
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

const isChannelInfo = (value: unknown): value is ChannelInfo =>
  isRecord(value) &&
  typeof value.name === "string" &&
  isScope(value.scope) &&
  typeof value.unit === "string" &&
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

const malformed = () => new TypeError(TELEMETRY.MALFORMED_MESSAGE);

const parseData = (event: MessageEvent<unknown>): Record<string, unknown> => {
  if (typeof event.data !== "string") throw malformed();
  const data: unknown = JSON.parse(event.data);
  if (!isRecord(data)) throw malformed();
  return data;
};

const parseReading = (data: Record<string, unknown>): TelemetryReading => {
  const { channel, value, measured_at, evaluation } = data;
  if (
    typeof channel !== "string" ||
    (typeof value !== "number" && typeof value !== "boolean") ||
    typeof measured_at !== "string" ||
    !isEvaluation(evaluation)
  ) {
    throw malformed();
  }
  return { channel, value, measured_at, evaluation };
};

const parseFinding = (data: Record<string, unknown>): TelemetryFinding => {
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

const parseEnvironmentId = (data: Record<string, unknown>): string => {
  const { id } = data;
  if (typeof id !== "string") throw malformed();
  return id;
};

const parseDictionary = (data: Record<string, unknown>): TelemetryDictionary => {
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

// the latest `limit` readings per channel, oldest first
export const fetchReadingHistory = async (limit: number): Promise<TelemetryReading[]> => {
  const response = await axios.get<unknown>(TELEMETRY.READINGS_URL, { params: { limit } });
  if (!isRecord(response.data) || !isRecord(response.data.readings)) throw malformed();
  return Object.values(response.data.readings).flatMap((readings) => {
    if (!Array.isArray(readings)) throw malformed();
    return readings.map((reading) => {
      if (!isRecord(reading)) throw malformed();
      return parseReading(reading);
    });
  });
};

export const putEnvironment = async (environmentId: string): Promise<string> => {
  const response = await axios.put<unknown>(TELEMETRY.ENVIRONMENT_URL, { id: environmentId });
  if (!isRecord(response.data)) throw malformed();
  return parseEnvironmentId(response.data);
};
