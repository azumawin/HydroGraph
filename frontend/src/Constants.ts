import { Activity, Droplet, HeartPulse, Thermometer, Wind } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export const TELEMETRY = {
  STREAM_URL: `${BACKEND_URL}/api/stream/`,
  ENVIRONMENT_URL: `${BACKEND_URL}/api/environment/`,
  READINGS_URL: `${BACKEND_URL}/api/readings/`,
  ASSISTANT_URL: `${BACKEND_URL}/api/assistant/`,
  EVENTS: {
    DICTIONARY: "dictionary",
    ENVIRONMENT: "environment",
    READING: "reading",
    FINDING: "finding",
  },
  CONNECTION_LABEL: "live telemetry",
  HISTORY_LABEL: "reading history",
  FLUSH_INTERVAL_MS: 250,
  MALFORMED_MESSAGE: "Received a telemetry message that does not match the backend contract.",
  DISCONNECTED_MESSAGE: "Lost the connection to the telemetry stream.",
};

export const ENVIRONMENT_LABELS = {
  SELECT: "Mission environment",
  GRAVITY: "Gravity",
  COMM_DELAY: "Comm delay, round trip",
  DAY_LENGTH: "Day",
  RADIATION: "Radiation baseline",
  SELECT_FAILED: "the selected environment",
};

export const ENVIRONMENT_FORMAT = {
  NUMBER: new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }),
  SECONDS_PER_MINUTE: 60,
  HOURS_PER_DAY: 24,
  MAX_HOURS_SHOWN: 48,
};

export const ASSISTANT = {
  PLACEHOLDER: "Ask about the findings…",
  SEND_LABEL: "Send",
  THINKING: "Thinking…",
  STARTER: "Summarize the current findings and tell me what to do.",
  STARTER_LABEL: "Summarize findings and advise",
  FALLBACK_ERROR: "The assistant could not answer. Try again.",
};

export const VITALS_HISTORY = {
  MAX_POINTS_PER_CHANNEL: 120,
};

export const VITALS_FORMAT = {
  TIME: new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", hour12: false }),
  MEASURED_AT: new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }),
  VALUE: new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }),
};

export const VITALS_EVALUATION_LABELS = {
  nominal: "Nominal",
  warning: "Warning",
  critical: "Critical",
  unspecified: "No threshold",
};

export const FINDING_STATUS_LABELS = {
  nominal: "Nominal",
  warning: "Warning",
  critical: "Critical",
};

export type VitalSeries = {
  CHANNEL: string;
  LABEL: string;
  COLOR: string;
};

export type VitalMetric = {
  LABEL: string;
  ICON: LucideIcon;
  SERIES: readonly VitalSeries[];
};

export const VITALS_METRICS = {
  HEART_RATE: {
    LABEL: "Heart rate",
    ICON: HeartPulse,
    SERIES: [
      { CHANNEL: "heart_rate", LABEL: "Heart rate", COLOR: "var(--color-chart-heart-rate)" },
    ],
  },
  BLOOD_PRESSURE: {
    LABEL: "Blood pressure",
    ICON: Activity,
    SERIES: [
      { CHANNEL: "bp_systolic", LABEL: "Systolic", COLOR: "var(--color-chart-systolic)" },
      { CHANNEL: "bp_diastolic", LABEL: "Diastolic", COLOR: "var(--color-chart-diastolic)" },
    ],
  },
  BLOOD_SUGAR: {
    LABEL: "Blood sugar",
    ICON: Droplet,
    SERIES: [{ CHANNEL: "glucose", LABEL: "Blood sugar", COLOR: "var(--color-chart-blood-sugar)" }],
  },
  BODY_TEMPERATURE: {
    LABEL: "Body temperature",
    ICON: Thermometer,
    SERIES: [
      {
        CHANNEL: "body_temperature",
        LABEL: "Body temperature",
        COLOR: "var(--color-chart-temperature)",
      },
    ],
  },
  BLOOD_OXYGEN: {
    LABEL: "Blood oxygen",
    ICON: Wind,
    SERIES: [{ CHANNEL: "spo2", LABEL: "SpO2", COLOR: "var(--color-chart-oxygen)" }],
  },
} satisfies Record<string, VitalMetric>;

export const VITALS_CHART = {
  MARGIN: { top: 8, right: 12, bottom: 0, left: 0 },
  TICK: { fill: "var(--color-text-secondary)", fontSize: 11 },
  TICK_COUNT: 3,
  X_AXIS_HEIGHT: 24,
  Y_AXIS_WIDTH: 36,
  MIN_TICK_GAP: 36,
  STROKE_WIDTH: 2,
  DOT_RADIUS: 3,
  FILL_OPACITY: 0.12,
  TIME_DOMAIN: ["dataMin", "dataMax"] as const,
};

export const BODY_SCAN_REGION_GROUPS = [
  { LABEL: "Head & neck", REGIONS: ["head", "neck"] },
  { LABEL: "Upper body", REGIONS: ["heart", "chest", "abdomen"] },
  {
    LABEL: "Arms",
    REGIONS: [
      "left_shoulder",
      "right_shoulder",
      "left_upper_arm",
      "right_upper_arm",
      "left_forearm",
      "right_forearm",
      "left_hand",
      "right_hand",
    ],
  },
  {
    LABEL: "Lower body",
    REGIONS: [
      "pelvis",
      "left_thigh",
      "right_thigh",
      "left_lower_leg",
      "right_lower_leg",
      "left_foot",
      "right_foot",
    ],
  },
  { LABEL: "Joints", REGIONS: ["left_elbow", "right_elbow", "left_knee", "right_knee"] },
];

export const VITALS_NOTIFICATIONS = {
  ERROR_DURATION_MS: 4000,
};

export const VITALS_BACKGROUND = {
  COLOR_TOKEN: "--color-backdrop-silver",
  SPEED: 1,
  SCALE: 1.25,
  TWIST: 0.8,
  WAVE: 0.65,
  SOFTNESS: 0.65,
  SHINE: 0.35,
  BRIGHTNESS: 0.7,
  // capped so the plasma core stays dark enough behind the panel material
  OPACITY: 0.4,
  QUALITY: 0.5,
  MAX_PIXEL_RATIO: 1.5,
  MAX_VOLUME_PIXELS: 900000,
  MAX_FRAME_DELTA_SECONDS: 0.05,
  FALLBACK_MESSAGE: "Animated background unavailable. Showing the static background.",
};
