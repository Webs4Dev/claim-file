import { useCallback, useEffect, useRef, useState } from "react";
import { CLAIMS_MAX_LOADED, CLAIMS_PAGE_SIZE, listClaims } from "../api";
import { ACTIVE_STATUSES } from "../utils";

const ACTIVE_POLL_MS = 15000;
const IDLE_POLL_MS = 60000;

/**
 * The first page(s) of claims the signed-in user may see (own claims, or
 * all for reviewers), filtered, searched and ordered by the server, and
 * kept fresh while the tab is visible. `changedIds` holds claims whose
 * status changed in the latest refresh, so the UI can highlight them;
 * `stale` is true when the last background refresh failed. `loadMore`
 * grows the list a page at a time up to CLAIMS_MAX_LOADED.
 */
export default function useClaims({ statuses = null, query = "", oldestFirst = false } = {}) {
  const [claims, setClaims] = useState([]);
  const [total, setTotal] = useState(0);
  const [statusCounts, setStatusCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);
  const [changedIds, setChangedIds] = useState(() => new Set());
  const [stale, setStale] = useState(false);
  const mounted = useRef(true);
  const lastStatuses = useRef(null);
  const latestRequest = useRef(0);

  // A string key, so a new array with the same statuses does not refetch.
  const statusKey = statuses ? statuses.join(",") : "";

  // The loaded size belongs to one filter + search; any other combination
  // starts again from the first page in the same render (no extra fetch).
  const filterKey = `${statusKey}|${query}|${oldestFirst}`;
  const [page, setPage] = useState({ key: filterKey, limit: CLAIMS_PAGE_SIZE });
  const limit = page.key === filterKey ? page.limit : CLAIMS_PAGE_SIZE;

  const refresh = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) setLoading(true);
      // A manual refresh can overlap a poll; only the newest response counts.
      const request = ++latestRequest.current;
      try {
        const page = await listClaims({
          statuses: statusKey ? statusKey.split(",") : null,
          query,
          oldestFirst,
          limit,
        });
        if (!mounted.current || request !== latestRequest.current) return;

        const items = page.claims;
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
        setTotal(page.total);
        setStatusCounts(page.status_counts || {});
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
    },
    [statusKey, query, oldestFirst, limit],
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll faster while something is processing; pause in background tabs
  // and catch up as soon as the tab is visible again.
  const hasActive = ACTIVE_STATUSES.some((status) => statusCounts[status] > 0);
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

  const canLoadMore = claims.length < total && limit < CLAIMS_MAX_LOADED;
  const loadMore = useCallback(
    () =>
      setPage({ key: filterKey, limit: Math.min(limit + CLAIMS_PAGE_SIZE, CLAIMS_MAX_LOADED) }),
    [filterKey, limit],
  );

  return {
    claims,
    total,
    statusCounts,
    loading,
    error,
    stale,
    updatedAt,
    changedIds,
    refresh,
    canLoadMore,
    loadMore,
  };
}
