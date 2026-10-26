import { useCallback, useEffect, useRef, useState } from "react";
import { listClaims } from "../api";
import { ACTIVE_STATUSES } from "../utils";

const ACTIVE_POLL_MS = 15000;
const IDLE_POLL_MS = 60000;

/**
 * The claims the signed-in user may see (own claims, or all for reviewers),
 * kept fresh while the tab is visible. `changedIds` holds claims whose
 * status changed in the latest refresh, so the UI can highlight them;
 * `stale` is true when the last background refresh failed.
 */
export default function useClaims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const [changedIds, setChangedIds] = useState(() => new Set());
  const [stale, setStale] = useState(false);
  const mounted = useRef(true);
  const lastStatuses = useRef(null);
  const latestRequest = useRef(0);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    // A manual refresh can overlap a poll; only the newest response counts.
    const request = ++latestRequest.current;
    try {
      const items = await listClaims();
      if (!mounted.current || request !== latestRequest.current) return;

      const previous = lastStatuses.current;
      if (previous) {
        setChangedIds(
          new Set(
            items
              .filter((c) => previous.has(c.claim_id) && previous.get(c.claim_id) !== c.status)
              .map((c) => c.claim_id),
          ),
        );
      }
      lastStatuses.current = new Map(items.map((c) => [c.claim_id, c.status]));

      setClaims(items);
      setUpdatedAt(Date.now());
      setError("");
      setStale(false);
    } catch (err) {
      if (!mounted.current || request !== latestRequest.current) return;
      if (silent) setStale(true);
      else setError(err.message || "Unable to load claims.");
    } finally {
      if (mounted.current && request === latestRequest.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  // Poll faster while something is processing; pause in background tabs
  // and catch up as soon as the tab is visible again.
  const hasActive = claims.some((c) => ACTIVE_STATUSES.includes(c.status));
  useEffect(() => {
    const interval = hasActive ? ACTIVE_POLL_MS : IDLE_POLL_MS;
    const tick = () => {
      if (document.visibilityState === "visible") refresh({ silent: true });
    };
    const timer = setInterval(tick, interval);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [hasActive, refresh]);

  return { claims, loading, error, stale, updatedAt, changedIds, refresh };
}
