import { create } from "zustand";
import { getBloodPressure } from "../api/Service.ts";
import type { BloodPressure } from "../api/Service.ts";

type BloodPressureStore = {
  bloodPressure: BloodPressure[];
  isLoadingBloodPressure: boolean;
  hasBloodPressureError: boolean;
  loadBloodPressure: () => Promise<void>;
};

export const useBloodPressureStore = create<BloodPressureStore>()((set, get) => ({
  bloodPressure: [],
  isLoadingBloodPressure: false,
  hasBloodPressureError: false,
  loadBloodPressure: async () => {
    if (get().isLoadingBloodPressure) return;

    set({ isLoadingBloodPressure: true, hasBloodPressureError: false });

    try {
      const bloodPressure = await getBloodPressure();
      set({ bloodPressure });
    } catch {
      set({ hasBloodPressureError: true });
    } finally {
      set({ isLoadingBloodPressure: false });
    }
  },
}));
