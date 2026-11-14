export const VITALS_READING_LABELS = {
  HEART_RATE: "heart rate",
  BLOOD_PRESSURE: "blood pressure",
  BLOOD_SUGAR: "blood sugar",
  BODY_TEMPERATURE: "body temperature",
  DAILY_SLEEP_HOURS: "daily sleep",
  VITALS_HISTORY: "vitals history",
};

export const VITALS_HISTORY = {
  DEFAULT_DURATION_MS: 24 * 60 * 60 * 1000,
  MOCK_INTERVAL_MS: 60 * 60 * 1000,
  INVALID_RANGE_MESSAGE: "Vitals history requires a valid start time before the end time.",
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
  optimal: "Optimal",
  normal: "Normal",
  unusual: "Unusual",
  critical: "Critical",
};

export type VitalSeries = {
  CHANNEL: string;
  LABEL: string;
  COLOR: string;
};

export type VitalMetric = {
  LABEL: string;
  SERIES: readonly VitalSeries[];
};

export const VITALS_METRICS = {
  HEART_RATE: {
    LABEL: "Heart rate",
    SERIES: [
      { CHANNEL: "heart_rate", LABEL: "Heart rate", COLOR: "var(--color-chart-heart-rate)" },
    ],
  },
  BLOOD_PRESSURE: {
    LABEL: "Blood pressure",
    SERIES: [
      { CHANNEL: "bp_systolic", LABEL: "Systolic", COLOR: "var(--color-chart-systolic)" },
      { CHANNEL: "bp_diastolic", LABEL: "Diastolic", COLOR: "var(--color-chart-diastolic)" },
    ],
  },
  BLOOD_SUGAR: {
    LABEL: "Blood sugar",
    SERIES: [
      { CHANNEL: "blood_sugar", LABEL: "Blood sugar", COLOR: "var(--color-chart-blood-sugar)" },
    ],
  },
  BODY_TEMPERATURE: {
    LABEL: "Body temperature",
    SERIES: [
      {
        CHANNEL: "body_temperature",
        LABEL: "Body temperature",
        COLOR: "var(--color-chart-temperature)",
      },
    ],
  },
  DAILY_SLEEP: {
    LABEL: "Daily sleep",
    SERIES: [
      { CHANNEL: "daily_sleep_hours", LABEL: "Daily sleep", COLOR: "var(--color-chart-sleep)" },
    ],
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
  OPACITY: 0.55,
  QUALITY: 0.5,
  MAX_PIXEL_RATIO: 1.5,
  MAX_VOLUME_PIXELS: 900000,
  MAX_FRAME_DELTA_SECONDS: 0.05,
  FALLBACK_MESSAGE: "Animated background unavailable. Showing the static background.",
};
