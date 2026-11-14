import { create } from "zustand";
import { getBloodSugar } from "../api/Service.ts";
import type { NumericVital } from "../api/Service.ts";

type BloodSugarStore = {
  bloodSugar: NumericVital[];
  isLoadingBloodSugar: boolean;
  hasBloodSugarError: boolean;
  loadBloodSugar: () => Promise<void>;
};

export const useBloodSugarStore = create<BloodSugarStore>()((set, get) => ({
  bloodSugar: [],
  isLoadingBloodSugar: false,
  hasBloodSugarError: false,
  loadBloodSugar: async () => {
    if (get().isLoadingBloodSugar) return;

    set({ isLoadingBloodSugar: true, hasBloodSugarError: false });

    try {
      const bloodSugar = await getBloodSugar();
      set({ bloodSugar });
    } catch {
      set({ hasBloodSugarError: true });
    } finally {
      set({ isLoadingBloodSugar: false });
    }
  },
}));
