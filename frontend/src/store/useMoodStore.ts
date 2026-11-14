import { create } from "zustand";
import { getMood } from "../api/Service.ts";
import type { Mood } from "../api/Service.ts";

type MoodStore = {
  mood: Mood[];
  isLoadingMood: boolean;
  hasMoodError: boolean;
  loadMood: () => Promise<void>;
};

export const useMoodStore = create<MoodStore>()((set, get) => ({
  mood: [],
  isLoadingMood: false,
  hasMoodError: false,
  loadMood: async () => {
    if (get().isLoadingMood) return;

    set({ isLoadingMood: true, hasMoodError: false });

    try {
      const mood = await getMood();
      set({ mood });
    } catch (error) {
      set({ hasMoodError: true });
      throw error;
    } finally {
      set({ isLoadingMood: false });
    }
  },
}));
