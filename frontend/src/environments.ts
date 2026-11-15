// What a mission environment sets, formatted the way the dashboard shows it.
//
// Both the header's switcher and the picker that opens the app read these, so
// the same environment reads the same in both places. Pure functions, so
// `npm test` covers the numbers without a browser or a store.
import type { MissionEnvironment } from "./api/types.ts";

const NUMBER = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
const SECONDS_PER_MINUTE = 60;
const HOURS_PER_DAY = 24;
// Beyond two days, a light-dark cycle reads better in days: the lunar day is
// 708.7 hours, which tells a reader nothing.
const MAX_HOURS_SHOWN = 48;

export const formatGravity = (g: number): string => `${NUMBER.format(g)} g`;

export const formatDoseRate = (usvPerHour: number): string => `${NUMBER.format(usvPerHour)} µSv/h`;

export const formatCommDelay = (seconds: number): string =>
  seconds < SECONDS_PER_MINUTE
    ? `${NUMBER.format(seconds)} s`
    : `${NUMBER.format(seconds / SECONDS_PER_MINUTE)} min`;

export const formatDayLength = (hours: number): string =>
  hours <= MAX_HOURS_SHOWN
    ? `${NUMBER.format(hours)} h`
    : `${NUMBER.format(hours / HOURS_PER_DAY)} days`;

export type EnvironmentFactLabels = {
  GRAVITY: string;
  COMM_DELAY: string;
  DAY_LENGTH: string;
  RADIATION: string;
};

export type EnvironmentFact = { label: string; value: string };

// Labels come from the caller rather than this module, which stays free of the
// dashboard's constants and so of Vite's import.meta.
export const environmentFacts = (
  environment: MissionEnvironment,
  labels: EnvironmentFactLabels,
): EnvironmentFact[] => [
  { label: labels.GRAVITY, value: formatGravity(environment.gravity_g) },
  { label: labels.COMM_DELAY, value: formatCommDelay(environment.comm_delay_rt_s) },
  { label: labels.DAY_LENGTH, value: formatDayLength(environment.day_length_h) },
  { label: labels.RADIATION, value: formatDoseRate(environment.baseline_dose_rate_usv_h) },
];

// What choosing this environment changes in the running demo, from its own
// numbers: the simulator holds every result for half the round trip before
// sending it, and the backend grades a dose-rate spike above this baseline
// rather than against an absolute cutoff.
export const environmentEffect = (environment: MissionEnvironment): string =>
  `Results arrive ${formatCommDelay(environment.comm_delay_rt_s / 2)} after they are taken. ` +
  `A dose-rate spike is graded above ${formatDoseRate(environment.baseline_dose_rate_usv_h)}.`;
