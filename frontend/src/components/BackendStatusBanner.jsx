import { useEffect, useState } from "react";
import { checkHealth } from "../api";

// Render's free tier puts the backend to sleep after 15 minutes idle, and
// the next request can take up to a minute to succeed while it wakes back
// up, sometimes failing a connection attempt or two along the way before
// the container is actually ready. This polls /health until it succeeds,
// showing a visible message the whole time, rather than a single failed
// attempt permanently telling someone the backend is down when it is
// really just still starting.
const POLL_INTERVAL_MS = 3000;
const SLOW_AFTER_MS = 2500;
const GIVE_UP_AFTER_MS = 75000;

export default function BackendStatusBanner() {
  const [status, setStatus] = useState("checking"); // checking | slow | awake | unreachable

  useEffect(() => {
    let cancelled = false;
    const startedAt = Date.now();
    const slowTimer = setTimeout(() => {
      if (!cancelled) setStatus((s) => (s === "checking" ? "slow" : s));
    }, SLOW_AFTER_MS);

    async function poll() {
      while (!cancelled) {
        const ok = await checkHealth().catch(() => false);
        if (cancelled) return;
        if (ok) {
          setStatus("awake");
          return;
        }
        if (Date.now() - startedAt > GIVE_UP_AFTER_MS) {
          setStatus("unreachable");
          return;
        }
        setStatus("slow");
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, []);

  if (status === "awake" || status === "checking") return null;

  if (status === "slow") {
    return (
      <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2 text-xs text-amber-300">
        Waking up the backend. It sleeps after inactivity on the free hosting tier, this can take up to a minute
        the first time, predictions below will work as soon as it is up.
      </div>
    );
  }

  return (
    <div className="bg-rose-500/10 border-b border-rose-500/30 px-6 py-2 text-xs text-rose-300">
      Could not reach the backend after a minute of trying. Reload the page, or try again shortly.
    </div>
  );
}
