import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  CarFront,
  ClipboardList,
  Clock3,
  FileWarning,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import Metric from "../components/Metric";
import Notice from "../components/Notice";
import StatusBadge from "../components/StatusBadge";
import {
  ACTIVE_STATUSES,
  CLOSED_STATUSES,
  REVIEW_STATUSES,
  claimFormOf,
  formatDate,
} from "../utils";

const FILTERS = {
  all: () => true,
  documents: (c) => c.status === "waiting_for_documents",
  review: (c) => REVIEW_STATUSES.includes(c.status),
  active: (c) => ACTIVE_STATUSES.includes(c.status),
  closed: (c) => CLOSED_STATUSES.includes(c.status),
};

const submittedAt = (c) => new Date(c.created_at || c.submitted_at || 0).getTime() || 0;

export default function Dashboard({
  view,
  user,
  claims,
  loading,
  error,
  onRefresh,
  onNewClaim,
  onOpenClaim,
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return claims
      .filter((claim) => {
        const form = claimFormOf(claim);
        const matches = [
          claim.claim_id,
          form.insured_name,
          form.vehicle_registration_number,
          form.policy_number,
        ].some((value) => String(value || "").toLowerCase().includes(query));
        return matches && FILTERS[filter](claim);
      })
      .sort((a, b) => submittedAt(b) - submittedAt(a));
  }, [claims, search, filter]);

  const countOf = (key) => claims.filter(FILTERS[key]).length;
  const isOverview = view === "dashboard";
  const isReviewer = user.role === "reviewer";

  return (
    <>
      <section className="welcome-row">
        <div>
          <div className="eyebrow">
            <span /> MOTOR INSURANCE &middot;{" "}
            {isReviewer ? (isOverview ? "REVIEW QUEUE" : "ALL CLAIMS") : isOverview ? "CLAIMS OVERVIEW" : "MY CLAIMS"}
          </div>
          {isReviewer ? (
            <h1>{isOverview ? "Review queue" : "All claims"}</h1>
          ) : isOverview ? (
            <h1>
              Your claims, <em>all in one place.</em>
            </h1>
          ) : (
            <h1>My claims</h1>
          )}
          <p>
            {isReviewer
              ? "Every submitted claim, from automated assessment to your decision."
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

      {isOverview && (
        <section className="metrics-grid">
          <Metric
            Icon={ClipboardList}
            title="Total claims"
            value={claims.length}
            note="Claims in this view"
            tone="mint"
          />
          <Metric
            Icon={Clock3}
            title="In progress"
            value={countOf("active")}
            note="Currently being processed"
            tone="blue"
          />
          <Metric
            Icon={FileWarning}
            title="Awaiting documents"
            value={countOf("documents")}
            note="Action may be needed"
            tone="amber"
          />
          <Metric
            Icon={ShieldCheck}
            title="Under review"
            value={countOf("review")}
            note="Awaiting further assessment"
            tone="violet"
          />
        </section>
      )}

      <section className="panel claims-panel">
        <div className="panel-heading">
          <div>
            <h2>Claims overview</h2>
            <p>Search and review your submitted claims.</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
          </button>
        </div>

        <div className="table-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search claim, policyholder or vehicle"
              aria-label="Search claims"
            />
          </label>
          <select
            className="select-field"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="all">All statuses ({claims.length})</option>
            <option value="active">In progress ({countOf("active")})</option>
            <option value="documents">Awaiting documents ({countOf("documents")})</option>
            <option value="review">Under review ({countOf("review")})</option>
            <option value="closed">Closed claims ({countOf("closed")})</option>
          </select>
        </div>

        <div className="table-wrap">
          <table className="claims-table">
            <thead>
              <tr>
                <th>CLAIM REFERENCE</th>
                <th>VEHICLE</th>
                <th>SUBMITTED</th>
                <th>STATUS</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((claim, index) => {
                const form = claimFormOf(claim);
                const vehicle = [form.vehicle_make, form.vehicle_model]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <tr key={claim.claim_id || index}>
                    <td>
                      <button
                        type="button"
                        className="claim-reference"
                        onClick={() => onOpenClaim(claim.claim_id)}
                      >
                        {claim.claim_id || "—"} <ArrowUpRight size={13} />
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
                    <td>{formatDate(claim.created_at || claim.submitted_at)}</td>
                    <td>
                      <StatusBadge status={claim.status} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="table-arrow"
                        onClick={() => onOpenClaim(claim.claim_id)}
                        aria-label={`Open claim ${claim.claim_id}`}
                      >
                        &rarr;
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!filtered.length && (
                <tr>
                  <td colSpan="5">
                    <div className="empty-state">
                      <ClipboardList size={28} />
                      <strong>{loading ? "Loading claims..." : "No claims found"}</strong>
                      <p>
                        {search || filter !== "all"
                          ? "Try a different search or filter."
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
            Showing <strong>{filtered.length}</strong> of {claims.length} claim
            {claims.length === 1 ? "" : "s"}
          </span>
          <span>ClaimFile &middot; Motor claims</span>
        </div>
      </section>

      <div className="dashboard-bottom">
        <div className="info-strip">
          <ShieldCheck size={18} />
          <span>
            <strong>Your information matters.</strong> Claim decisions depend on the
            evidence and policy terms.
          </span>
        </div>
      </div>
    </>
  );
}
