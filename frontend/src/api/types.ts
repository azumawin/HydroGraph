// Free of runtime imports so the Node tests can type-check against it.

export type MissionEnvironment = {
  name: string;
  gravity_g: number;
  comm_delay_rt_s: number;
  baseline_dose_rate_usv_h: number;
  storm_shelter_available: boolean;
  day_length_h: number;
};
