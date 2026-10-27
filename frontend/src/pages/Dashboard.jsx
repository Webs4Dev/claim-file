import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  CarFront,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileWarning,
  Gavel,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import ClaimProgress from "../components/ClaimProgress";
import Metric from "../components/Metric";
import Notice from "../components/Notice";
import StatusBadge from "../components/StatusBadge";
import useClaims from "../hooks/useClaims";
import {
  ACTIVE_STATUSES,
  CLOSED_STATUSES,
  REVIEW_STATUSES,
  claimFormOf,
  formatDate,
} from "../utils";

// Statuses sent to the server for each filter; null = every claim.
const FILTER_STATUSES = {
  all: null,
  decision: REVIEW_STATUSES,
  documents: ["waiting_for_documents"],
  active: ACTIVE_STATUSES,
  closed: CLOSED_STATUSES,
};

const SEARCH_DELAY_MS = 300;

const CLAIMANT_CHIPS = [
  ["all", "All"],
  ["active", "In progress"],
  ["documents", "Action needed"],
  ["decision", "Under review"],
  ["closed", "Closed"],
];

const REVIEWER_CHIPS = [
  ["decision", "Needs decision"],
  ["active", "Processing"],
  ["documents", "Awaiting claimant"],
  ["closed", "Closed"],
  ["all", "All"],
];

const submittedAt = (c) => new Date(c.created_at || 0).getTime() || 0;

function timeAgo(timestamp, now) {
  const seconds = Math.max(0, Math.round((now - timestamp) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

/** Re-renders on an interval so relative times stay current. */
function useNow(intervalMs) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}

function LiveIndicator({ updatedAt, loading, stale }) {
  const now = useNow(5000);
  const since = updatedAt ? timeAgo(updatedAt, now) : null;
  let text = since ? `Live · updated ${since}` : "Live";
  if (loading) text = "Syncing...";
  else if (stale) text = since ? `Offline · last updated ${since}` : "Offline";
  // No aria-live: the relative time changes every few seconds.
  return (
    <span className={`live-indicator ${loading ? "syncing" : ""} ${stale ? "stale" : ""}`}>
      <i aria-hidden="true" />
      {text}
    </span>
  );
}

function SkeletonRows() {
  return Array.from({ length: 4 }, (_, index) => (
    <tr key={index} className="skeleton-row" aria-hidden="true">
      {[150, 130, 170, 90, 110, 24].map((width, cell) => (
        <td key={cell}>
          <span className="skeleton" style={{ width }} />
        </td>
      ))}
    </tr>
  ));
}

export default function Dashboard({ view, user, onRecheck, onNewClaim, onOpenClaim }) {
  const isReviewer = user.role === "reviewer";
  const isOverview = view === "dashboard";
  const chips = isReviewer ? REVIEWER_CHIPS : CLAIMANT_CHIPS;
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState(isReviewer && isOverview ? "decision" : "all");
  const now = useNow(60000);

  // Search on the server once typing pauses, not on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [search]);

  // The reviewer queue is worked oldest-first: longest waiting on top.
  const {
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
  } = useClaims({
    statuses: FILTER_STATUSES[filter],
    query,
    oldestFirst: isReviewer && filter === "decision",
  });

  const onRefresh = () => {
    onRecheck();
    refresh();
  };

  // Counts cover every claim the user may see, whatever is listed below.
  const allCount = Object.values(statusCounts).reduce((sum, count) => sum + count, 0);
  const countOf = (key) =>
    key === "all"
      ? allCount
      : FILTER_STATUSES[key].reduce((sum, status) => sum + (statusCounts[status] || 0), 0);

  const metrics = isReviewer
    ? [
        [Gavel, "Needs decision", countOf("decision"), "Waiting for a reviewer", "violet", "decision"],
        [Clock3, "Processing", countOf("active"), "Automated checks running", "blue", "active"],
        [FileWarning, "Awaiting claimant", countOf("documents"), "Documents requested", "amber", "documents"],
        [CheckCircle2, "Closed", countOf("closed"), "Approved or rejected", "mint", "closed"],
      ]
    : [
        [ClipboardList, "Total claims", allCount, "Everything you've submitted", "mint", "all"],
        [Clock3, "In progress", countOf("active"), "Being assessed now", "blue", "active"],
        [FileWarning, "Action needed", countOf("documents"), "Documents requested", "amber", "documents"],
        [ShieldCheck, "Under review", countOf("decision"), "With a reviewer", "violet", "decision"],
      ];

  const heading = isReviewer
    ? isOverview
      ? "Review queue"
      : "All claims"
    : isOverview
      ? null
      : "My claims";

  return (
    <>
      <section className="welcome-row">
        <div>
          <div className="eyebrow">
            <span /> MOTOR INSURANCE &middot; {(heading || "Claims overview").toUpperCase()}
          </div>
          {heading ? (
            <h1>{heading}</h1>
          ) : (
            <h1>
              Your claims, <em>all in one place.</em>
            </h1>
          )}
          <p>
            {isReviewer
              ? "Claims the automated assessment has finished with, waiting for your decision."
              : "Follow your motor insurance claims from submission to decision."}
          </p>
        </div>
        {!isReviewer && (
          <button type="button" className="btn btn-primary" onClick={onNewClaim}>
            <Plus size={17} /> Start a claim
          </button>
        )}
      </section>

      {error && <Notice variant="error">{error}</Notice>}

      {isReviewer && isOverview && countOf("decision") > 0 && (
        <div className="queue-callout">
          <AlertTriangle size={18} />
          <span>
            <strong>{countOf("decision")}</strong> claim{countOf("decision") === 1 ? "" : "s"}{" "}
            waiting for a decision. The oldest is at the top.
          </span>
        </div>
      )}

      {isOverview && (
        <section className="metrics-grid">
          {metrics.map(([Icon, title, value, note, tone, key]) => (
            <button
              type="button"
              key={title}
              className={`metric-button ${filter === key ? "selected" : ""}`}
              onClick={() => setFilter(key)}
              aria-pressed={filter === key}
            >
              <Metric
                Icon={Icon}
                title={title}
                value={updatedAt ? value : "–"}
                note={note}
                tone={tone}
              />
            </button>
          ))}
        </section>
      )}

      <section className="panel claims-panel">
        <div className="panel-heading">
          <div>
            <h2>{isReviewer ? "Claims" : "Your claims"}</h2>
            <p>
              {isReviewer
                ? "Open a claim to review the evidence and decide."
                : "Open a claim to see each step of its assessment."}
            </p>
          </div>
          <div className="panel-heading-actions">
            <LiveIndicator updatedAt={updatedAt} loading={loading} stale={stale} />
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        <div className="table-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search claim, policyholder, vehicle or policy"
              maxLength={100}
              aria-label="Search claims"
            />
          </label>
          <div className="filter-chips" role="group" aria-label="Filter by status">
            {chips.map(([key, label]) => (
              <button
                type="button"
                key={key}
                className={`filter-chip ${filter === key ? "active" : ""}`}
                onClick={() => setFilter(key)}
                aria-pressed={filter === key}
              >
                {label}
                <span>{countOf(key)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="table-wrap">
          <table className="claims-table">
            <thead>
              <tr>
                <th>CLAIM</th>
                <th>VEHICLE</th>
                <th>PROGRESS</th>
                <th>SUBMITTED</th>
                <th>STATUS</th>
                <th>
                  <span className="sr-only">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && !claims.length && <SkeletonRows />}
              {claims.map((claim) => {
                const form = claimFormOf(claim);
                const vehicle = [form.vehicle_make, form.vehicle_model].filter(Boolean).join(" ");
                return (
                  <tr
                    key={claim.claim_id}
                    className={`claim-row ${changedIds.has(claim.claim_id) ? "row-updated" : ""}`}
                    onClick={() => onOpenClaim(claim.claim_id)}
                  >
                    <td>
                      <button
                        type="button"
                        className="claim-reference"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenClaim(claim.claim_id);
                        }}
                        title={claim.claim_id}
                      >
                        {claim.claim_id.slice(0, 8).toUpperCase()} <ArrowUpRight size={13} />
                      </button>
                      <div className="table-sub">{form.insured_name || "Policyholder"}</div>
                    </td>
                    <td>
                      <span className="vehicle-cell">
                        <span className="vehicle-thumb">
                          <CarFront size={17} />
                        </span>
                        <span>
                          {form.vehicle_registration_number || "Not provided"}
                          <small>{vehicle}</small>
                        </span>
                      </span>
                    </td>
                    <td>
                      <ClaimProgress claim={claim} />
                    </td>
                    <td>
                      {formatDate(claim.created_at)}
                      <div className="table-sub">{timeAgo(submittedAt(claim), now)}</div>
                    </td>
                    <td>
                      <StatusBadge status={claim.status} />
                    </td>
                    <td>
                      <span className="table-arrow" aria-hidden="true">
                        &rarr;
                      </span>
                    </td>
                  </tr>
                );
              })}
              {!loading && !claims.length && (
                <tr>
                  <td colSpan="6">
                    <div className="empty-state">
                      {isReviewer && filter === "decision" ? (
                        <CheckCircle2 size={28} />
                      ) : (
                        <ClipboardList size={28} />
                      )}
                      <strong>
                        {isReviewer && filter === "decision" && !search
                          ? "Queue clear"
                          : "No claims found"}
                      </strong>
                      <p>
                        {search
                          ? "Try a different search."
                          : isReviewer && filter === "decision"
                            ? "Nothing is waiting for a decision right now."
                            : filter !== "all"
                              ? "No claims with this status."
                              : "Submit a claim to see it listed here."}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="panel-foot">
          <span>
            Showing <strong>{claims.length}</strong> of {total} claim
            {total === 1 ? "" : "s"}
          </span>
          {canLoadMore ? (
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={loadMore}
              disabled={loading}
            >
              Load more
            </button>
          ) : claims.length < total ? (
            <span>Search or filter to find older claims</span>
          ) : (
            <span>Updates automatically</span>
          )}
        </div>
      </section>
    </>
  );
}
