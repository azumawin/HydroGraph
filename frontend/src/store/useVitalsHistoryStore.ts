import { create } from "zustand";
import { postVitalsHistory } from "../api/Service.ts";
import type { VitalsHistoryPoint, VitalsHistoryRequest } from "../api/Service.ts";

type VitalsHistoryStore = {
  vitalsHistory: VitalsHistoryPoint[];
  vitalsHistoryRange: VitalsHistoryRequest | null;
  isLoadingVitalsHistory: boolean;
  hasVitalsHistoryError: boolean;
  loadVitalsHistory: (request: VitalsHistoryRequest) => Promise<void>;
};

export const useVitalsHistoryStore = create<VitalsHistoryStore>()((set, get) => ({
  vitalsHistory: [],
  vitalsHistoryRange: null,
  isLoadingVitalsHistory: false,
  hasVitalsHistoryError: false,
  loadVitalsHistory: async (request) => {
    if (get().isLoadingVitalsHistory) return;

    set({
      isLoadingVitalsHistory: true,
      hasVitalsHistoryError: false,
      vitalsHistoryRange: request,
      vitalsHistory: [],
    });

    try {
      const vitalsHistory = await postVitalsHistory(request);
      set({ vitalsHistory });
    } catch {
      set({ hasVitalsHistoryError: true });
    } finally {
      set({ isLoadingVitalsHistory: false });
    }
  },
}));
