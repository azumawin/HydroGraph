import { create } from "zustand";
import { getBodyTemperature } from "../api/Service.ts";
import type { NumericVital } from "../api/Service.ts";

type BodyTemperatureStore = {
  bodyTemperature: NumericVital[];
  isLoadingBodyTemperature: boolean;
  hasBodyTemperatureError: boolean;
  loadBodyTemperature: () => Promise<void>;
};

export const useBodyTemperatureStore = create<BodyTemperatureStore>()((set, get) => ({
  bodyTemperature: [],
  isLoadingBodyTemperature: false,
  hasBodyTemperatureError: false,
  loadBodyTemperature: async () => {
    if (get().isLoadingBodyTemperature) return;

    set({ isLoadingBodyTemperature: true, hasBodyTemperatureError: false });

    try {
      const bodyTemperature = await getBodyTemperature();
      set({ bodyTemperature });
    } catch {
      set({ hasBodyTemperatureError: true });
    } finally {
      set({ isLoadingBodyTemperature: false });
    }
  },
}));
