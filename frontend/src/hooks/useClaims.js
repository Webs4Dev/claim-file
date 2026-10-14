import { useCallback, useEffect, useRef, useState } from "react";
import { getClaim, listClaims } from "../api";
import { ACTIVE_STATUSES } from "../utils";

const STORAGE_KEY = "claimfile.recentClaimIds";
const POLL_MS = 15000;

const DEMO_CLAIMS = [
  {
    claim_id: "DEMO-CLM-001",
    status: "needs_internal_review",
    created_at: "2026-10-12",
    claim_form: {
      insured_name: "Sample Policyholder",
      policy_number: "DEMO-POL-1001",
      vehicle_registration_number: "MH 01 AB 1234",
      vehicle_make: "Maruti Suzuki",
      vehicle_model: "Swift",
    },
    claim_documents: [],
  },
  {
    claim_id: "DEMO-CLM-002",
    status: "waiting_for_documents",
    created_at: "2026-10-10",
    claim_form: {
      insured_name: "Example Policyholder",
      policy_number: "DEMO-POL-1002",
      vehicle_registration_number: "MH 02 CD 5678",
      vehicle_make: "Hyundai",
      vehicle_model: "i20",
    },
    claim_documents: [],
    pending_documents: [],
  },
];

function readStoredIds() {
  try {
    const ids = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(ids) ? ids : [];
  } catch {
    return [];
  }
}

/** Remember a claim ID so it can be listed even if the API has no list endpoint. */
export function rememberClaimId(id) {
  try {
    const ids = [id, ...readStoredIds().filter((x) => x !== id)].slice(0, 30);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* storage unavailable - ignore */
  }
}

/**
 * Loads the claims list.
 * 1. GET /claims if the backend supports it.
 * 2. Otherwise fetch each claim this browser has submitted.
 * 3. Otherwise show clearly-labelled demo rows.
 * `source` is "api" | "local" | "demo".
 */
export default function useClaims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("api");
  const mounted = useRef(true);

  const refresh = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    let items;
    let origin = "api";
    try {
      items = await listClaims();
    } catch {
      const results = await Promise.allSettled(readStoredIds().map(getClaim));
      items = results.filter((r) => r.status === "fulfilled").map((r) => r.value);
      origin = "local";
      if (!items.length) {
        items = DEMO_CLAIMS;
        origin = "demo";
      }
    }
    if (!mounted.current) return;
    setClaims(items);
    setSource(origin);
    setLoading(false);
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
    if (!hasActive || source === "demo") return undefined;
    const timer = setInterval(() => refresh({ silent: true }), POLL_MS);
    return () => clearInterval(timer);
  }, [hasActive, source, refresh]);

  return { claims, loading, source, refresh };
}

export { DEMO_CLAIMS };
