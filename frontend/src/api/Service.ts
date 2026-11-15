import axios from "axios";
import { TELEMETRY } from "../Constants.ts";
import {
  errorDetail,
  parseAssistantReply,
  parseDictionary,
  parseEnvironmentId,
  parseFinding,
  parseHistory,
  parseReading,
  parseStreamData,
} from "./parse.ts";

import type { TelemetryDictionary, TelemetryFinding, TelemetryReading } from "./types.ts";

// Re-exported so existing importers keep one address for the API.
export type {
  ChannelDisplay,
  ChannelInfo,
  ChannelValueType,
  ConsciousnessLevel,
  Evaluation,
  FindingInfo,
  FindingSeverity,
  MissionEnvironment,
  ReadingValue,
  TelemetryDictionary,
  TelemetryFinding,
  TelemetryReading,
} from "./types.ts";

export type TelemetryStreamHandlers = {
  onDictionary: (dictionary: TelemetryDictionary) => void;
  onEnvironment: (environmentId: string) => void;
  onReading: (reading: TelemetryReading) => void;
  onFinding: (finding: TelemetryFinding) => void;
  onError: (error: Error) => void;
};

// The transport only: every payload shape lives in ./parse.ts, where `npm test`
// can reach it without a browser or a server.
export const openTelemetryStream = (handlers: TelemetryStreamHandlers): EventSource => {
  const stream = new EventSource(TELEMETRY.STREAM_URL);

  const listen = <T>(
    eventName: string,
    parse: (data: unknown) => T,
    handle: (value: T) => void,
  ) => {
    stream.addEventListener(eventName, (event: MessageEvent<unknown>) => {
      try {
        handle(parse(parseStreamData(event.data)));
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
  return parseHistory(response.data);
};

export const putEnvironment = async (environmentId: string): Promise<string> => {
  const response = await axios.put<unknown>(TELEMETRY.ENVIRONMENT_URL, { id: environmentId });
  return parseEnvironmentId(response.data);
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

// the assistant's next message; the backend briefs the model with the live state
export const postAssistant = async (messages: ChatMessage[]): Promise<string> => {
  const response = await axios.post<unknown>(TELEMETRY.ASSISTANT_URL, { messages });
  return parseAssistantReply(response.data);
};

// the backend's reason when the assistant is unavailable, if it sent one
export const assistantErrorDetail = (error: unknown): string | null =>
  axios.isAxiosError(error) ? errorDetail(error.response?.data) : null;
