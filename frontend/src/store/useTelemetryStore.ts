import { create } from "zustand";
import { openTelemetryStream } from "../api/Service.ts";
import type {
  ChannelInfo,
  Evaluation,
  TelemetryDictionary,
  TelemetryFinding,
  TelemetryReading,
} from "../api/Service.ts";
import { VITALS_DISPLAY_UNITS, VITALS_HISTORY } from "../Constants.ts";

export type VitalReading = ChannelInfo & {
  channel: string;
  value: number | boolean;
  unit: string;
  evaluation: Evaluation;
  measured_at: string;
};

export type VitalHistoryPoint = {
  timestamp: number;
  value: number;
  unit: string;
};

type TelemetryStore = {
  dictionary: TelemetryDictionary | null;
  readings: Record<string, VitalReading>;
  history: Record<string, VitalHistoryPoint[]>;
  findings: Record<string, TelemetryFinding>;
  hasTelemetryError: boolean;
  connectTelemetry: () => () => void;
};

const toVitalReading = (reading: TelemetryReading, info: ChannelInfo): VitalReading => {
  const { channel, value, unit, evaluation, measured_at } = reading;
  const display = VITALS_DISPLAY_UNITS[channel];
  if (display === undefined || typeof value !== "number") {
    return { ...info, channel, value, unit, evaluation, measured_at };
  }
  return {
    ...info,
    channel,
    value: value * display.SCALE + display.OFFSET,
    unit: display.UNIT,
    evaluation,
    measured_at,
  };
};

const withHistoryPoint = (
  points: VitalHistoryPoint[],
  point: VitalHistoryPoint,
): VitalHistoryPoint[] =>
  [...points.filter((existing) => existing.timestamp !== point.timestamp), point]
    .toSorted((first, second) => first.timestamp - second.timestamp)
    .slice(-VITALS_HISTORY.MAX_POINTS_PER_CHANNEL);

export const useTelemetryStore = create<TelemetryStore>()((set, get) => ({
  dictionary: null,
  readings: {},
  history: {},
  findings: {},
  hasTelemetryError: false,
  connectTelemetry: () => {
    const stream = openTelemetryStream({
      onDictionary: (dictionary) => set({ dictionary, hasTelemetryError: false }),
      onReading: (reading) => {
        const { dictionary, readings, history } = get();
        const info = dictionary?.channels[reading.channel];
        if (info === undefined) {
          set({ hasTelemetryError: true });
          return;
        }
        const vital = toVitalReading(reading, info);
        const timestamp = Date.parse(vital.measured_at);
        const latest = readings[vital.channel];
        const isNewest = latest === undefined || timestamp >= Date.parse(latest.measured_at);
        set({
          readings: isNewest ? { ...readings, [vital.channel]: vital } : readings,
          history:
            typeof vital.value === "number"
              ? {
                  ...history,
                  [vital.channel]: withHistoryPoint(history[vital.channel] ?? [], {
                    timestamp,
                    value: vital.value,
                    unit: vital.unit,
                  }),
                }
              : history,
        });
      },
      onFinding: (finding) => set({ findings: { ...get().findings, [finding.id]: finding } }),
      onError: () => set({ hasTelemetryError: true }),
    });

    return () => stream.close();
  },
}));
