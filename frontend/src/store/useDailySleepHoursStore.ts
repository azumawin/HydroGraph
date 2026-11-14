import { create } from "zustand";
import { getDailySleepHours } from "../api/Service.ts";
import type { NumericVital } from "../api/Service.ts";

type DailySleepHoursStore = {
  dailySleepHours: NumericVital[];
  isLoadingDailySleepHours: boolean;
  hasDailySleepHoursError: boolean;
  loadDailySleepHours: () => Promise<void>;
};

export const useDailySleepHoursStore = create<DailySleepHoursStore>()((set, get) => ({
  dailySleepHours: [],
  isLoadingDailySleepHours: false,
  hasDailySleepHoursError: false,
  loadDailySleepHours: async () => {
    if (get().isLoadingDailySleepHours) return;

    set({ isLoadingDailySleepHours: true, hasDailySleepHoursError: false });

    try {
      const dailySleepHours = await getDailySleepHours();
      set({ dailySleepHours });
    } catch {
      set({ hasDailySleepHoursError: true });
    } finally {
      set({ isLoadingDailySleepHours: false });
    }
  },
}));
