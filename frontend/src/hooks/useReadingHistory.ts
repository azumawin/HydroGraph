import { useEffect, useState } from "react";
import { fetchReadingHistory } from "../api/Service.ts";
import type { TelemetryReading } from "../api/Service.ts";

type ReadingHistoryState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; readings: TelemetryReading[] };

// readings are graded against the environment in effect when they are fetched,
// so the caller remounts this hook per environment
export const useReadingHistory = (limit: number) => {
  const [historyState, setHistoryState] = useState<ReadingHistoryState>({ status: "loading" });

  useEffect(() => {
    let isCancelled = false;

    fetchReadingHistory(limit)
      .then((readings) => {
        if (!isCancelled) setHistoryState({ status: "ready", readings });
      })
      .catch(() => {
        if (!isCancelled) setHistoryState({ status: "error" });
      });

    return () => {
      isCancelled = true;
    };
  }, [limit]);

  return historyState;
};
