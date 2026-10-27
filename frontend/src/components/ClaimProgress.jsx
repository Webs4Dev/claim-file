import { Check, X } from "lucide-react";
import { ACTIVE_STATUSES, REVIEW_STATUSES, claimOutcome } from "../utils";

const STAGES = [
  ["submitted", "Submitted"],
  ["documents", "Documents checked"],
  ["investigation", "Investigated"],
  ["review", "Reviewed"],
  ["decision", "Decided"],
];

/** Which pipeline stages a claim has completed, from the data it carries. */
function stageStates(claim) {
  const status = claim.status;
  const outcome = claimOutcome(claim);
  const rejected = outcome === "REJECTED" || status === "terminated";
  // Once a claim is with a reviewer the automated stages are over. Claimants
  // do not receive the investigation/review data until a decision, so the
  // status has to say so too.
  const automatedDone = REVIEW_STATUSES.includes(status) || Boolean(outcome);

  const done = {
    submitted: true,
    documents: Boolean(
      claim.document_validation || claim.extracted_data || claim.investigation || automatedDone,
    ),
    investigation: Boolean(claim.investigation) || automatedDone,
    review: Boolean(claim.review) || automatedDone,
    decision: Boolean(outcome) || status === "terminated",
  };

  // Uploading the requested documents restarts assessment from document
  // checks (the API clears the later results), so show it that way.
  if (status === "waiting_for_documents") {
    done.documents = done.investigation = done.review = done.decision = false;
  }

  const current = STAGES.find(([key]) => !done[key])?.[0];

  // What the first unfinished stage is doing right now.
  // "waiting" = the claimant must act; "review" = with a reviewer.
  let currentState = "pending";
  if (ACTIVE_STATUSES.includes(status)) currentState = "active";
  else if (status === "waiting_for_documents") currentState = "waiting";
  else if (REVIEW_STATUSES.includes(status)) currentState = "review";

  return STAGES.map(([key, label]) => {
    let state = "pending";
    if (done[key]) state = key === "decision" && rejected ? "rejected" : "done";
    else if (key === current) state = currentState;
    return { key, label, state };
  });
}

const ACTIVE_TEXT = {
  documents: "Checking documents",
  investigation: "Investigating",
  review: "Reviewing",
  decision: "Finalising",
};

/** One short phrase for what the claim is doing or waiting for. */
function summaryOf(claim, stages) {
  const current = stages.find((s) => !["done", "rejected"].includes(s.state));
  if (!current) {
    if (claim.status === "terminated" && !claimOutcome(claim)) return "Closed";
    return stages.at(-1).state === "rejected" ? "Rejected" : "Decided";
  }
  if (claim.status === "waiting_for_documents") return "Documents requested";
  if (REVIEW_STATUSES.includes(claim.status)) return "Awaiting decision";
  if (current.state === "active") return ACTIVE_TEXT[current.key] || "Processing";
  return `${current.label} pending`;
}

const STATE_TEXT = {
  done: "complete",
  rejected: "rejected",
  active: "in progress",
  waiting: "waiting for the claimant",
  review: "with a reviewer",
  pending: "not started",
};

export default function ClaimProgress({ claim, variant = "compact" }) {
  const stages = stageStates(claim);
  const reached = stages.filter((s) => s.state === "done" || s.state === "rejected").length;
  const summary = summaryOf(claim, stages);

  const compact = variant === "compact";

  // Compact: one summary for screen readers. Full: a readable list.
  return (
    <div
      className={`claim-progress ${variant}`}
      {...(compact && {
        role: "img",
        "aria-label": `Progress: ${reached} of ${stages.length} steps. ${summary}.`,
      })}
    >
      <ol aria-hidden={compact || undefined}>
        {stages.map(({ key, label, state }) => (
          <li key={key} className={`progress-step ${state}`}>
            <span className="progress-dot" aria-hidden="true">
              {state === "done" && <Check size={compact ? 9 : 13} strokeWidth={3} />}
              {state === "rejected" && <X size={compact ? 9 : 13} strokeWidth={3} />}
            </span>
            {!compact && (
              <span className="progress-label">
                {label}
                <span className="sr-only">: {STATE_TEXT[state]}</span>
              </span>
            )}
          </li>
        ))}
      </ol>
      {variant === "compact" && <span className="progress-summary">{summary}</span>}
    </div>
  );
}
