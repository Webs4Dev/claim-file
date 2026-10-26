import { useCallback, useEffect, useRef, useState } from "react";
import { listClaims } from "../api";
import { ACTIVE_STATUSES } from "../utils";

const POLL_MS = 15000;

/** The claims the signed-in user may see (own claims, or all for reviewers). */
export default function useClaims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const mounted = useRef(true);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    try {
      const items = await listClaims();
      if (!mounted.current) return;
      setClaims(items);
      setError("");
    } catch (err) {
      if (mounted.current && !silent) setError(err.message || "Unable to load claims.");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  // Quietly refresh while any claim is still being processed.
  const hasActive = claims.some((c) => ACTIVE_STATUSES.includes(c.status));
  useEffect(() => {
    if (!hasActive) return undefined;
    const timer = setInterval(() => refresh({ silent: true }), POLL_MS);
    return () => clearInterval(timer);
  }, [hasActive, refresh]);

  return { claims, loading, error, refresh };
}
