import {
  Activity,
  Droplet,
  HeartPulse,
  FileCode,
  List,
  Stethoscope,
  Thermometer,
  TrendingUp,
  Wind,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export const TELEMETRY = {
  STREAM_URL: `${BACKEND_URL}/api/stream/`,
  ENVIRONMENT_URL: `${BACKEND_URL}/api/environment/`,
  READINGS_URL: `${BACKEND_URL}/api/readings/`,
  ASSISTANT_URL: `${BACKEND_URL}/api/assistant/`,
  RULES_URL: `${BACKEND_URL}/api/rules/`,
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

export const formatCommDelay = (seconds: number) =>
  seconds < ENVIRONMENT_FORMAT.SECONDS_PER_MINUTE
    ? `${ENVIRONMENT_FORMAT.NUMBER.format(seconds)} s`
    : `${ENVIRONMENT_FORMAT.NUMBER.format(seconds / ENVIRONMENT_FORMAT.SECONDS_PER_MINUTE)} min`;

// The front door, before any telemetry is shown: the demo runs in one mission
// environment and the choice is per page load, so a reload asks again rather
// than resuming in a setting nobody picked. Formatting of what each one sets
// lives in environments.ts.
export const ENVIRONMENT_PICKER = {
  TITLE: "Choose the mission environment",
  LEAD:
    "Every reading in this demo is taken in one of these. The choice sets the gravity, " +
    "how late a result reaches the dashboard, the light-dark cycle behind the circadian " +
    "findings, and the dose rate a radiation spike is graded against.",
  LOADING: "Loading the mission environments…",
  IN_EFFECT: "In effect",
  CHOOSE: "Start here",
};

// a round trip short enough to talk to the ground while acting
export const ADVICE = {
  REALTIME_GROUND_MAX_RT_S: 10,
  GROUND_AVAILABLE_TITLE: "Ground available",
  AUTONOMOUS_TITLE: "Act on your own",
  NO_FINDINGS: "No findings evaluated yet.",
  ALL_CLEAR: "No active findings. No action needed.",
  ESCALATION: {
    ground: {
      critical: "Start the action now and call the flight surgeon.",
      warning: "Report this to the flight surgeon and follow their guidance.",
    },
    autonomous: {
      critical: "Start the action now. Send a report; do not wait for the reply.",
      warning: "Start the action and log it for the next ground report.",
    },
  },
};

export const RULES = {
  TEMPLATE: `ID = "resting_tachycardia"
NAME = "Resting tachycardia"
CHANNELS = ("heart_rate",)


def evaluate(inputs):
    bpm = inputs["latest"]["heart_rate"] * 60
    if bpm > 120:
        return {"status": "critical", "triggers": ["HR > 120 bpm"], "action": "Rest and recheck in 10 min", "bpm": bpm}
    return {"status": "nominal", "triggers": [], "action": "No finding", "bpm": bpm}
`,
  FALLBACK_ERROR: "The rule change failed. Try again.",
  LOAD_ERROR: "Could not load the rules.",
};

export const ASSISTANT = {
  PLACEHOLDER: "Ask about the findings…",
  SEND_LABEL: "Send",
  THINKING: "Thinking…",
  MAX_CONTEXT_MESSAGES: 40,
  FALLBACK_ERROR: "The assistant could not answer. Try again.",
  LATEST_LABEL: "Latest message",
  SCROLL_THRESHOLD_PX: 48,
};

export const MAIN_PANEL_TABS = [
  { ID: "vitals", LABEL: "Vitals", ICON: Activity },
  { ID: "measurements", LABEL: "All measurements", ICON: List },
  { ID: "trends", LABEL: "Trends", ICON: TrendingUp },
  { ID: "advice", LABEL: "Advice", ICON: Stethoscope },
  { ID: "rules", LABEL: "Rules", ICON: FileCode },
] as const;

export type MainPanelTabId = (typeof MAIN_PANEL_TABS)[number]["ID"];

export const MEASUREMENTS = {
  SCOPE_LABELS: { crew: "Crew", environment: "Habitat" },
  COLUMNS: ["Measurement", "Latest", "Status", "Measured", "Next", "Change"],
  NO_READING: "No reading",
  NOW_REFRESH_MS: 30000,
  CHANGE_PRECISION: 10,
  CHANGE_FORMAT: new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    signDisplay: "exceptZero",
  }),
};

const HOUR_MS = 3600000;

export const TRENDS = {
  PERIODS: [
    { ID: "day", LABEL: "Day", DURATION_MS: 24 * HOUR_MS },
    { ID: "week", LABEL: "Week", DURATION_MS: 7 * 24 * HOUR_MS },
    { ID: "month", LABEL: "Month", DURATION_MS: 30 * 24 * HOUR_MS },
    { ID: "half_year", LABEL: "6 months", DURATION_MS: 182 * 24 * HOUR_MS },
  ],
  BUCKET_COUNT: 24,
  HISTORY_LIMIT: 1000,
  NOT_EVALUATED: "Not evaluated",
  NO_READING: "No reading",
  HISTORY_ERROR: "Could not load the reading history. Switch tabs to try again.",
};

const RELATIVE_TIME = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

const RELATIVE_TIME_UNITS = [
  { UNIT: "day", SECONDS: 86400 },
  { UNIT: "hour", SECONDS: 3600 },
  { UNIT: "minute", SECONDS: 60 },
  { UNIT: "second", SECONDS: 1 },
] as const;

export const formatTimeAgo = (timestamp: number, now: number): string => {
  const elapsedSeconds = Math.max(0, (now - timestamp) / 1000);
  const { UNIT, SECONDS } =
    RELATIVE_TIME_UNITS.find((unit) => elapsedSeconds >= unit.SECONDS) ??
    RELATIVE_TIME_UNITS[RELATIVE_TIME_UNITS.length - 1];
  return RELATIVE_TIME.format(-Math.floor(elapsedSeconds / SECONDS), UNIT);
};

export const SCHEDULE = {
  MIN_GRACE_S: 120,
  UPCOMING_MIN_INTERVAL_S: 3600,
  UPCOMING_WINDOW_S: 86400,
};

const INTERVAL_UNITS = [
  { LABEL: "d", SECONDS: 86400 },
  { LABEL: "h", SECONDS: 3600 },
  { LABEL: "min", SECONDS: 60 },
  { LABEL: "s", SECONDS: 1 },
] as const;

export const formatInterval = (seconds: number): string => {
  const { LABEL, SECONDS } =
    INTERVAL_UNITS.find((unit) => seconds >= unit.SECONDS) ??
    INTERVAL_UNITS[INTERVAL_UNITS.length - 1];
  return `${ENVIRONMENT_FORMAT.NUMBER.format(Math.round((seconds / SECONDS) * 10) / 10)} ${LABEL}`;
};

export const VITALS_HISTORY = {
  MAX_POINTS_PER_CHANNEL: 120,
};

export const VITALS_FORMAT = {
  TIME: new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }),
  MEASURED_AT: new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }),
  VALUE: new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }),
};

// a reading for display: numbers formatted, text codes such as "UNRESPONSIVE"
// or "NOT_SET" in sentence case ("Unresponsive", "Not set")
export const formatReadingValue = (value: number | boolean | string): string => {
  if (typeof value === "number") return VITALS_FORMAT.VALUE.format(value);
  if (typeof value === "boolean") return String(value);
  const words = value.replaceAll("_", " ").trim().toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
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
  FINDING_ID?: string;
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
    FINDING_ID: "blood_pressure_1_4",
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

export const BODY_SCAN_FORMAT = {
  VALUE: new Intl.NumberFormat(undefined, { maximumSignificantDigits: 5 }),
};

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
  OPACITY: 0.55,
  QUALITY: 0.5,
  MAX_PIXEL_RATIO: 1.5,
  MAX_VOLUME_PIXELS: 900000,
  MAX_FRAME_DELTA_SECONDS: 0.05,
  FALLBACK_MESSAGE: "Animated background unavailable. Showing the static background.",
};
