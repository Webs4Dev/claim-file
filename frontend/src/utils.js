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
export const publicDocuments = (claim) => claim?.claim_documents || [];
