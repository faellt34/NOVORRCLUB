import { useEffect } from "react";
import { getToken } from "../lib/api";

// Schedule after completion so a slow request never overlaps the next one.
export function useSessionPolling(task, delay, enabled) {
  useEffect(() => {
    if (!enabled) return;
    let stopped = false, timer;
    const controller = new AbortController();
    const run = async () => {
      if (stopped || !getToken()) return;
      try {
        if (document.visibilityState !== "hidden") await task(controller.signal);
      } catch (error) {
        if (error?.response?.status === 401) stopped = true;
      }
      if (!stopped && getToken()) timer = setTimeout(run, delay);
    };
    run();
    return () => { stopped = true; clearTimeout(timer); controller.abort(); };
  }, [task, delay, enabled]);
}
