import { create } from "zustand";
import { fetchReadingHistory, openTelemetryStream, putEnvironment } from "../api/Service.ts";
import type {
  ChannelInfo,
  Evaluation,
  TelemetryDictionary,
  TelemetryFinding,
  TelemetryReading,
} from "../api/Service.ts";
import { TELEMETRY, VITALS_HISTORY } from "../Constants.ts";

// a reading in its channel's display unit; everything static about the channel
// stays in the dictionary
export type VitalReading = {
  channel: string;
  value: TelemetryReading["value"];
  unit: string;
  evaluation: Evaluation;
  measured_at: string;
};

export type VitalHistoryPoint = {
  timestamp: number;
  value: number;
};

type TelemetryStore = {
  dictionary: TelemetryDictionary | null;
  readings: Record<string, VitalReading>;
  history: Record<string, VitalHistoryPoint[]>;
  findings: Record<string, TelemetryFinding>;
  hasTelemetryError: boolean;
  hasHistoryError: boolean;
  environmentId: string | null;
  isSelectingEnvironment: boolean;
  hasEnvironmentSelectError: boolean;
  connectTelemetry: () => () => void;
  selectEnvironment: (environmentId: string) => Promise<void>;
};

const toVitalReading = (reading: TelemetryReading, info: ChannelInfo): VitalReading => {
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
  hasHistoryError: false,
  environmentId: null,
  isSelectingEnvironment: false,
  hasEnvironmentSelectError: false,
  connectTelemetry: () => {
    let pendingReadings: TelemetryReading[] = [];
    let pendingFindings: TelemetryFinding[] = [];
    let flushTimeoutId: number | undefined;
    let isClosed = false;

    // one store update per interval instead of per message keeps rendering fast
    // when the simulator sends hundreds of readings a second
    const flushPending = () => {
      flushTimeoutId = undefined;
      const { dictionary } = get();
      const readings = { ...get().readings };
      const history = { ...get().history };
      const findings = { ...get().findings };
      let hasUnknownChannel = false;

      for (const reading of pendingReadings) {
        const info = dictionary?.channels[reading.channel];
        if (info === undefined) {
          hasUnknownChannel = true;
          continue;
        }
        const vital = toVitalReading(reading, info);
        const timestamp = Date.parse(vital.measured_at);
        const latest = readings[vital.channel];
        if (latest === undefined || timestamp >= Date.parse(latest.measured_at)) {
          readings[vital.channel] = vital;
        }
        if (typeof vital.value === "number") {
          history[vital.channel] = withHistoryPoint(history[vital.channel] ?? [], {
            timestamp,
            value: vital.value,
          });
        }
      }
      for (const finding of pendingFindings) {
        findings[finding.id] = finding;
      }
      pendingReadings = [];
      pendingFindings = [];
      set({
        readings,
        history,
        findings,
        ...(hasUnknownChannel ? { hasTelemetryError: true } : {}),
      });
    };

    const scheduleFlush = () => {
      flushTimeoutId ??= window.setTimeout(flushPending, TELEMETRY.FLUSH_INTERVAL_MS);
    };

    const stream = openTelemetryStream({
      onDictionary: (dictionary) => {
        set({ dictionary, hasTelemetryError: false });
        // after the dictionary, so every history reading can be converted; sent on each
        // (re)connect, and the flush merges history with live readings by timestamp
        fetchReadingHistory(VITALS_HISTORY.MAX_POINTS_PER_CHANNEL)
          .then((readings) => {
            if (isClosed) return;
            pendingReadings.push(...readings);
            set({ hasHistoryError: false });
            scheduleFlush();
          })
          .catch(() => {
            if (!isClosed) set({ hasHistoryError: true });
          });
      },
      onEnvironment: (environmentId) => set({ environmentId }),
      onReading: (reading) => {
        pendingReadings.push(reading);
        scheduleFlush();
      },
      onFinding: (finding) => {
        pendingFindings.push(finding);
        scheduleFlush();
      },
      onError: () => set({ hasTelemetryError: true }),
    });

    return () => {
      isClosed = true;
      stream.close();
      window.clearTimeout(flushTimeoutId);
    };
  },
  selectEnvironment: async (environmentId) => {
    if (get().isSelectingEnvironment) return;

    set({ isSelectingEnvironment: true, hasEnvironmentSelectError: false });

    try {
      const selectedId = await putEnvironment(environmentId);
      set({ environmentId: selectedId });
    } catch {
      set({ hasEnvironmentSelectError: true });
    } finally {
      set({ isSelectingEnvironment: false });
    }
  },
}));
