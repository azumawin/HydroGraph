import { useEffect, useState } from "react";

export const useNow = (refreshMs: number) => {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setNow(Date.now()), refreshMs);
    return () => window.clearInterval(intervalId);
  }, [refreshMs]);

  return now;
};
