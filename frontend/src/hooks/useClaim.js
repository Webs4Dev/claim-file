import { useCallback, useEffect, useRef, useState } from "react";
import { getClaim } from "../api";
import { ACTIVE_STATUSES } from "../utils";

const POLL_MS = 8000;

/** Loads a single claim and keeps it fresh while it is still being processed. */
export default function useClaim(id, demoFallback) {
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const currentId = useRef(id);
  const fallbackRef = useRef(demoFallback);
  fallbackRef.current = demoFallback;

  const load = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setLoading(true);
        setError("");
      }
      try {
        const data = await getClaim(id);
        if (currentId.current !== id) return;
        setClaim(data);
        setError("");
      } catch (err) {
        if (currentId.current !== id) return;
        if (fallbackRef.current && String(id).startsWith("DEMO-")) {
          setClaim(fallbackRef.current);
          setError("This is a demo record. It is not stored in the backend.");
        } else if (!silent) {
          setError(err.message || "Unable to load claim details.");
        }
      } finally {
        if (currentId.current === id && !silent) setLoading(false);
      }
    },
    [id],
  );

  useEffect(() => {
    currentId.current = id;
    setClaim(null);
    load();
  }, [id, load]);

  const isActive = claim && ACTIVE_STATUSES.includes(claim.status);
  useEffect(() => {
    if (!isActive) return undefined;
    const timer = setInterval(() => load({ silent: true }), POLL_MS);
    return () => clearInterval(timer);
  }, [isActive, load]);

  return { claim, loading, error, setError, reload: load };
}
