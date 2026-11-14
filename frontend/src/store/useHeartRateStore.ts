import { create } from "zustand";
import { getHeartRate } from "../api/Service.ts";
import type { HeartRate } from "../api/Service.ts";

type HeartRateStore = {
  heartRate: HeartRate[];
  isLoadingHeartRate: boolean;
  hasHeartRateError: boolean;
  loadHeartRate: () => Promise<void>;
};

export const useHeartRateStore = create<HeartRateStore>()((set, get) => ({
  heartRate: [],
  isLoadingHeartRate: false,
  hasHeartRateError: false,
  loadHeartRate: async () => {
    if (get().isLoadingHeartRate) return;

    set({ isLoadingHeartRate: true, hasHeartRateError: false });

    try {
      const heartRate = await getHeartRate();
      set({ heartRate });
    } catch {
      set({ hasHeartRateError: true });
    } finally {
      set({ isLoadingHeartRate: false });
    }
  },
}));
