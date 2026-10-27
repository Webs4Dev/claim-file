const STATUS_LABELS = {
  pending: "Submitted",
  in_progress: "In progress",
  waiting_for_documents: "Awaiting documents",
  budget_exceeded: "Under review",
  human_approval: "Awaiting human review",
  needs_internal_review: "Under review",
  complete: "Completed",
  terminated: "Closed",
  approved: "Approved",
  rejected: "Rejected",
};

export const REVIEW_STATUSES = [
  "human_approval",
  "needs_internal_review",
  "budget_exceeded",
];
export const ACTIVE_STATUSES = ["pending", "in_progress"];
export const CLOSED_STATUSES = ["complete", "terminated", "approved", "rejected"];

export function statusLabel(status) {
  return (
    STATUS_LABELS[status] || String(status || "Unknown").replaceAll("_", " ")
  );
}

export function statusTone(status) {
  if (["complete", "approved"].includes(status)) return "success";
  if (status === "waiting_for_documents") return "warning";
  if (["terminated", "rejected"].includes(status)) return "danger";
  if (REVIEW_STATUSES.includes(status)) return "review";
  return "info";
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export const humanize = (text) => String(text || "").replaceAll("_", " ");
export const claimFormOf = (claim) => claim?.claim_form || {};
/**
 * "APPROVED" / "REJECTED" once a claim is decided, else null. A reviewer's
 * decision wins; otherwise the automated verdict, but only on a "complete"
 * claim ("complete" alone does not mean approved). "terminated" without a
 * human decision is not an outcome: the step limit also ends claims that way.
 */
export function claimOutcome(claim) {
  if (claim?.human_approval?.decision) return claim.human_approval.decision;
  if (claim?.status === "complete") return claim.review?.status || null;
  return null;
}

/** The status to show people: the outcome when decided, else the workflow status. */
export function displayStatus(claim) {
  const outcome = claimOutcome(claim);
  if (outcome === "APPROVED") return "approved";
  if (outcome === "REJECTED") return "rejected";
  return claim?.status;
}

/** Short reference shown to people, e.g. "283FD52A". */
export const claimRef = (claim) => String(claim?.claim_id || "").slice(0, 8).toUpperCase();
export const publicDocuments = (claim) => claim?.claim_documents || [];

export const initialsOf = (name) =>
  String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
