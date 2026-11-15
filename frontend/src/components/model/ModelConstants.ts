import type { Evaluation } from "../../api/Service.ts";

export const BODY_SCAN_VIEW = {
  CAMERA_POSITION: [0, 0, 100] as [number, number, number],
  CAMERA_ZOOM: 50,
  MODEL_ROTATION_Y: -Math.PI / 8,
  FRAME_FILL: 0.9,
  AMBIENT_INTENSITY: 0.5,
  KEY_LIGHT_POSITION: [-3, 4, 5] as [number, number, number],
  KEY_LIGHT_INTENSITY: 2,
  FILL_LIGHT_POSITION: [3, 1, 2] as [number, number, number],
  FILL_LIGHT_INTENSITY: 0.55,
  RIM_LIGHT_POSITION: [2, 3, -4] as [number, number, number],
  RIM_LIGHT_INTENSITY: 2.2,
  MATERIAL_ROUGHNESS: 0.55,
  MATERIAL_METALNESS: 0.12,
  COLOR_SATURATION_SCALE: 0.75,
  COLOR_LIGHTNESS_SCALE: 0.9,
  MIN_POLAR_ANGLE: Math.PI / 3,
  MAX_POLAR_ANGLE: (2 * Math.PI) / 3,
};

export const BODY_REGIONS = {
  HEAD: "head",
  NECK: "neck",
  CHEST: "chest",
  ABDOMEN: "abdomen",
  PELVIS: "pelvis",
  LEFT_SHOULDER: "left_shoulder",
  RIGHT_SHOULDER: "right_shoulder",
  LEFT_UPPER_ARM: "left_upper_arm",
  RIGHT_UPPER_ARM: "right_upper_arm",
  LEFT_ELBOW: "left_elbow",
  RIGHT_ELBOW: "right_elbow",
  LEFT_FOREARM: "left_forearm",
  RIGHT_FOREARM: "right_forearm",
  LEFT_HAND: "left_hand",
  RIGHT_HAND: "right_hand",
  LEFT_THIGH: "left_thigh",
  RIGHT_THIGH: "right_thigh",
  LEFT_KNEE: "left_knee",
  RIGHT_KNEE: "right_knee",
  LEFT_LOWER_LEG: "left_lower_leg",
  RIGHT_LOWER_LEG: "right_lower_leg",
  LEFT_FOOT: "left_foot",
  RIGHT_FOOT: "right_foot",
} as const;

export type BodyRegion = (typeof BODY_REGIONS)[keyof typeof BODY_REGIONS];

export const BODY_REGION_IDS = Object.values(BODY_REGIONS);

export const BODY_MODEL_THEME = {
  NEUTRAL: "--color-body-neutral",
  WARNING: "--color-status-warning",
  CRITICAL: "--color-status-critical",
};

export const BODY_EVALUATION_PRIORITY = {
  nominal: 0,
  unspecified: 1,
  warning: 2,
  critical: 3,
} as const;

export const worstEvaluation = (
  evaluations: readonly (Evaluation | undefined)[],
): Evaluation | undefined =>
  evaluations.reduce<Evaluation | undefined>(
    (worst, evaluation) =>
      evaluation !== undefined &&
      (worst === undefined ||
        BODY_EVALUATION_PRIORITY[evaluation] > BODY_EVALUATION_PRIORITY[worst])
        ? evaluation
        : worst,
    undefined,
  );

export const BODY_MODEL_SURFACE = {
  RESOLUTION: 128,
  MAX_TRIANGLES: 80000,
  HALF_EXTENTS: [0.6, 1, 0.3] as [number, number, number],
  BLEND_RADIUS: 0.025,
  HAND_BLEND_RADIUS: 0.012,
};

export type BodyShape = {
  REGION: BodyRegion;
  CENTER: readonly [number, number, number];
  RADII: readonly [number, number, number];
  ROTATION_Z?: number;
};

type PairedBodyShape = Omit<BodyShape, "REGION"> & {
  LEFT_REGION: BodyRegion;
  RIGHT_REGION: BodyRegion;
};

export const BODY_MODEL_CORE: readonly BodyShape[] = [
  { REGION: BODY_REGIONS.HEAD, CENTER: [0, 0.788, -0.012], RADII: [0.086, 0.088, 0.096] },
  { REGION: BODY_REGIONS.HEAD, CENTER: [0, 0.73, 0.02], RADII: [0.066, 0.062, 0.07] },
  { REGION: BODY_REGIONS.HEAD, CENTER: [0, 0.69, 0.034], RADII: [0.04, 0.03, 0.04] },
  { REGION: BODY_REGIONS.NECK, CENTER: [0, 0.623, -0.005], RADII: [0.047, 0.075, 0.048] },
  { REGION: BODY_REGIONS.CHEST, CENTER: [0, 0.445, -0.012], RADII: [0.185, 0.18, 0.102] },
  { REGION: BODY_REGIONS.ABDOMEN, CENTER: [0, 0.265, -0.005], RADII: [0.132, 0.16, 0.082] },
  { REGION: BODY_REGIONS.PELVIS, CENTER: [0, 0.105, -0.015], RADII: [0.153, 0.123, 0.095] },
];

export const BODY_MODEL_PAIRED_SHAPES: readonly PairedBodyShape[] = [
  {
    LEFT_REGION: BODY_REGIONS.CHEST,
    RIGHT_REGION: BODY_REGIONS.CHEST,
    CENTER: [0.085, 0.555, -0.01],
    RADII: [0.105, 0.05, 0.068],
    ROTATION_Z: -0.2,
  },
  {
    LEFT_REGION: BODY_REGIONS.CHEST,
    RIGHT_REGION: BODY_REGIONS.CHEST,
    CENTER: [0.078, 0.47, 0.066],
    RADII: [0.098, 0.075, 0.044],
  },
  {
    LEFT_REGION: BODY_REGIONS.PELVIS,
    RIGHT_REGION: BODY_REGIONS.PELVIS,
    CENTER: [0.073, 0.065, -0.062],
    RADII: [0.085, 0.095, 0.059],
  },
  {
    LEFT_REGION: BODY_REGIONS.CHEST,
    RIGHT_REGION: BODY_REGIONS.CHEST,
    CENTER: [0.07, 0.585, -0.03],
    RADII: [0.09, 0.035, 0.05],
    ROTATION_Z: -0.45,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_SHOULDER,
    RIGHT_REGION: BODY_REGIONS.RIGHT_SHOULDER,
    CENTER: [0.204, 0.507, -0.003],
    RADII: [0.068, 0.077, 0.068],
    ROTATION_Z: 0.3,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_UPPER_ARM,
    RIGHT_REGION: BODY_REGIONS.RIGHT_UPPER_ARM,
    CENTER: [0.256, 0.386, 0],
    RADII: [0.05, 0.135, 0.052],
    ROTATION_Z: 0.29,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_ELBOW,
    RIGHT_REGION: BODY_REGIONS.RIGHT_ELBOW,
    CENTER: [0.297, 0.253, 0.003],
    RADII: [0.037, 0.043, 0.039],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOREARM,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOREARM,
    CENTER: [0.325, 0.157, 0.017],
    RADII: [0.039, 0.111, 0.041],
    ROTATION_Z: 0.24,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOREARM,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOREARM,
    CENTER: [0.347, 0.065, 0.028],
    RADII: [0.026, 0.068, 0.028],
    ROTATION_Z: 0.18,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_HAND,
    RIGHT_REGION: BODY_REGIONS.RIGHT_HAND,
    CENTER: [0.363, -0.014, 0.032],
    RADII: [0.033, 0.056, 0.021],
    ROTATION_Z: 0.14,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_HAND,
    RIGHT_REGION: BODY_REGIONS.RIGHT_HAND,
    CENTER: [0.372, -0.078, 0.033],
    RADII: [0.028, 0.045, 0.017],
    ROTATION_Z: 0.1,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_HAND,
    RIGHT_REGION: BODY_REGIONS.RIGHT_HAND,
    CENTER: [0.343, -0.032, 0.05],
    RADII: [0.012, 0.034, 0.014],
    ROTATION_Z: -0.4,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_THIGH,
    RIGHT_REGION: BODY_REGIONS.RIGHT_THIGH,
    CENTER: [0.093, -0.115, -0.006],
    RADII: [0.084, 0.211, 0.084],
    ROTATION_Z: 0.06,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_THIGH,
    RIGHT_REGION: BODY_REGIONS.RIGHT_THIGH,
    CENTER: [0.109, -0.225, 0.015],
    RADII: [0.061, 0.137, 0.063],
    ROTATION_Z: 0.06,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_KNEE,
    RIGHT_REGION: BODY_REGIONS.RIGHT_KNEE,
    CENTER: [0.119, -0.364, 0.018],
    RADII: [0.045, 0.085, 0.047],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_LOWER_LEG,
    RIGHT_REGION: BODY_REGIONS.RIGHT_LOWER_LEG,
    CENTER: [0.129, -0.514, -0.018],
    RADII: [0.052, 0.17, 0.058],
    ROTATION_Z: 0.02,
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_LOWER_LEG,
    RIGHT_REGION: BODY_REGIONS.RIGHT_LOWER_LEG,
    CENTER: [0.128, -0.49, -0.045],
    RADII: [0.048, 0.1, 0.045],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_LOWER_LEG,
    RIGHT_REGION: BODY_REGIONS.RIGHT_LOWER_LEG,
    CENTER: [0.134, -0.655, -0.003],
    RADII: [0.029, 0.132, 0.032],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOOT,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOOT,
    CENTER: [0.136, -0.778, 0.005],
    RADII: [0.029, 0.042, 0.033],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOOT,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOOT,
    CENTER: [0.136, -0.81, -0.012],
    RADII: [0.033, 0.034, 0.04],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOOT,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOOT,
    CENTER: [0.139, -0.824, 0.05],
    RADII: [0.041, 0.026, 0.085],
  },
  {
    LEFT_REGION: BODY_REGIONS.LEFT_FOOT,
    RIGHT_REGION: BODY_REGIONS.RIGHT_FOOT,
    CENTER: [0.143, -0.832, 0.112],
    RADII: [0.04, 0.019, 0.036],
  },
];
