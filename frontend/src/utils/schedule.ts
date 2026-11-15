import { SCHEDULE } from "../Constants.ts";
import type { ChannelInfo } from "../api/Service.ts";
import type { VitalReading } from "../store/useTelemetryStore.ts";

export type ChannelSchedule =
  | { state: "unscheduled" }
  | { state: "missing"; intervalS: number }
  | { state: "overdue"; intervalS: number; overdueS: number }
  | { state: "due"; intervalS: number; dueInS: number };

// one missed sample is tolerated, and never less than the minimum grace,
// so a 1 s channel is not flagged by ordinary network jitter
export const channelSchedule = (
  channel: ChannelInfo,
  reading: VitalReading | undefined,
  now: number,
): ChannelSchedule => {
  const intervalS = channel.schedule_s;
  if (intervalS === null) return { state: "unscheduled" };
  if (reading === undefined) return { state: "missing", intervalS };

  const elapsedS = (now - Date.parse(reading.measured_at)) / 1000;
  const graceS = Math.max(intervalS, SCHEDULE.MIN_GRACE_S);
  if (elapsedS > intervalS + graceS) {
    return { state: "overdue", intervalS, overdueS: elapsedS - intervalS };
  }
  return { state: "due", intervalS, dueInS: Math.max(0, intervalS - elapsedS) };
};
