// How the dashboard turns the stream's readings into what it shows: the
// display-unit conversion, which reading counts as the current one, and the
// rolling history behind each vitals chart. Pure functions, so `npm test`
// covers them without a browser or a store.
import type { ChannelInfo, ReadingValue, Evaluation, TelemetryReading } from "./api/types.ts";

// a reading in its channel's display unit; everything static about the channel
// stays in the dictionary. Only numbers are scaled and charted.
export type VitalReading = {
  channel: string;
  value: ReadingValue;
  unit: string;
  evaluation: Evaluation;
  measured_at: string;
};

export type VitalHistoryPoint = {
  timestamp: number;
  value: number;
};

export const toVitalReading = (reading: TelemetryReading, info: ChannelInfo): VitalReading => {
  const { channel, value, evaluation, measured_at } = reading;
  const { display } = info;
  return {
    channel,
    value: typeof value === "number" ? value * display.scale + display.offset : value,
    unit: display.unit,
    evaluation,
    measured_at,
  };
};

// "Current" means measured last, not received last: history fetched after the
// stream opened, or a preload written behind the live simulator, must never
// replace a newer reading. An equal timestamp is the same instant re-sent and
// does replace it.
export const isCurrent = (latest: VitalReading | undefined, timestamp: number): boolean =>
  latest === undefined || timestamp >= Date.parse(latest.measured_at);

// One point per timestamp (the later arrival wins), oldest first, and no more
// than the last `maxPoints`: the vitals charts show a recent window, so this is
// a rolling buffer, not a store of the whole history.
export const withHistoryPoint = (
  points: VitalHistoryPoint[],
  point: VitalHistoryPoint,
  maxPoints: number,
): VitalHistoryPoint[] =>
  [...points.filter((existing) => existing.timestamp !== point.timestamp), point]
    .toSorted((first, second) => first.timestamp - second.timestamp)
    .slice(-maxPoints);
