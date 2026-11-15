// The all-measurements view: every channel the backend describes, grouped and
// annotated with what the dictionary says about it. Pure functions, so
// `npm test` covers them without a browser or a store.
import type { ChannelInfo } from "./api/types.ts";

export type MeasurementGroup = {
  scope: ChannelInfo["scope"];
  channels: string[];
};

// Channels in the dictionary's own order, split by scope in the order given.
export const groupByScope = (
  channels: Record<string, ChannelInfo>,
  order: readonly ChannelInfo["scope"][],
): MeasurementGroup[] =>
  order.map((scope) => ({
    scope,
    channels: Object.keys(channels).filter((id) => channels[id]?.scope === scope),
  }));

// The narrowest y-axis window for a channel's chart. The curated vitals carry
// their own clinically chosen span; every other numeric channel gets a window
// proportional to its current value, with a floor so a channel sitting at zero
// still has an axis.
export const measurementMinSpan = (
  curated: number | undefined,
  latest: number | undefined,
  fraction: number,
  floor: number,
): number => curated ?? Math.max(Math.abs(latest ?? 0) * fraction, floor);

// The history a chart draws for the selected timeframe. The window ends at the
// channel's own newest point rather than at the clock: cadences here run from
// one a second to one a minute, and a run can be paused or over, so anchoring
// to "now" would empty the slower charts. A window wider than the history
// yields all of it, and the newest point is always in range.
export const pointsInRange = <Point extends { timestamp: number }>(
  points: readonly Point[],
  rangeSeconds: number | null,
): readonly Point[] => {
  if (rangeSeconds === null || points.length === 0) return points;
  const newest = points.reduce(
    (latest, point) => (point.timestamp > latest ? point.timestamp : latest),
    Number.NEGATIVE_INFINITY,
  );
  const from = newest - rangeSeconds * 1000;
  return points.filter((point) => point.timestamp >= from);
};
