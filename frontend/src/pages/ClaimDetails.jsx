import { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileText,
  FileWarning,
  RefreshCw,
  ShieldCheck,
  UploadCloud,
  UserCheck,
  XCircle,
} from "lucide-react";
import {
  DOCUMENT_FIELDS,
  approveClaim,
  rejectClaim,
  requestReview,
  retryClaim,
  uploadAdditionalDocuments,
} from "../api";
import ClaimProgress from "../components/ClaimProgress";
import DocumentUpload from "../components/DocumentUpload";
import ProcessingResults from "../components/ProcessingResults";
import Notice from "../components/Notice";
import StatusBadge from "../components/StatusBadge";
import useClaim from "../hooks/useClaim";
import {
  ACTIVE_STATUSES,
  REVIEW_STATUSES,
  claimFormOf,
  claimOutcome,
  claimRef,
  displayStatus,
  formatDate,
  humanize,
  publicDocuments,
} from "../utils";

/**
 * Where the claim is, in plain words, for whoever is looking at it.
 * tone follows DESIGN.md: info = working, warning = claimant must act,
 * review = with a reviewer, success / danger = outcome.
 */
function describeClaim(claim, isReviewer) {
  const { status } = claim;
  const outcome = claimOutcome(claim);
  const decidedOn = claim.human_approval?.decided_at
    ? ` on ${formatDate(claim.human_approval.decided_at)}`
    : "";
  const reviewRequest = claim.review_request;

  if (ACTIVE_STATUSES.includes(status)) {
    return {
      tone: "info",
      Icon: Clock3,
      title: isReviewer ? "Automated checks running" : "We're checking your claim",
      text: isReviewer
        ? "Documents, policy and the accident details are being assessed."
        : "We're checking your documents and policy. This usually takes a few minutes, and this page updates by itself.",
    };
  }
  if (status === "waiting_for_documents") {
    return {
      tone: "warning",
      Icon: FileWarning,
      title: isReviewer ? "Waiting for the claimant" : "We need more documents from you",
      text: isReviewer
        ? "The claimant has been asked for the documents below."
        : "Your claim is paused until you upload the documents below. Once they arrive we'll continue automatically.",
    };
  }
  if (REVIEW_STATUSES.includes(status)) {
    if (!isReviewer) {
      return {
        tone: "review",
        Icon: UserCheck,
        title: "A reviewer is checking your claim",
        text: reviewRequest
          ? "You asked for a person to review the automatic decision. Someone from our team will look at your claim again and make the final decision. You don't need to do anything right now."
          : "A person from our team will approve or reject your claim. You don't need to do anything right now.",
      };
    }
    return status === "human_approval"
      ? {
          tone: "review",
          Icon: UserCheck,
          title: "Ready for your decision",
          text: reviewRequest
            ? `The automated checks rejected this claim, and the claimant asked for a person to review it on ${formatDate(reviewRequest.requested_at)}. Check the evidence, then record your decision.`
            : `The automated review recommends ${humanize(claim.review?.status).toLowerCase() || "a decision"}. Check the evidence, then record your decision.`,
          note: reviewRequest?.note,
        }
      : {
          tone: "review",
          Icon: UserCheck,
          title: "Needs a manual decision",
          text: "The automated assessment could not finish this claim. Record your decision, or rerun processing.",
        };
  }
  if (outcome === "APPROVED") {
    return {
      tone: "success",
      Icon: CheckCircle2,
      title: isReviewer ? "Approved" : "Your claim is approved",
      text: claim.human_approval
        ? `Approved by a reviewer${decidedOn}.`
        : "Your claim has been approved.",
      reason: claim.human_approval?.reason,
    };
  }
  if (outcome === "REJECTED") {
    return {
      tone: "danger",
      Icon: XCircle,
      title: isReviewer ? "Rejected" : "Your claim was not approved",
      text: claim.human_approval
        ? `Closed by a reviewer${decidedOn}.`
        : isReviewer
          ? "Rejected by the automated checks. The claimant can ask for a person to review it."
          : "Our automated checks found that your policy doesn't cover this claim. If you think this is wrong, you can ask a person from our team to review it.",
      reason: claim.human_approval?.reason || claim.review?.summary,
    };
  }
  if (status === "terminated") {
    return {
      tone: "danger",
      Icon: XCircle,
      title: isReviewer ? "Closed without a decision" : "Your claim was closed",
      text: isReviewer
        ? "Processing hit its step limit and stopped. Nobody approved or rejected this claim."
        : "Automated processing stopped before a decision was made. No approval or rejection has been recorded.",
    };
  }
  return {
    tone: "info",
    Icon: CheckCircle2,
    title: "Processing complete",
    text: "See the assessment details below.",
  };
}

export default function ClaimDetails({ claimId, user, onBack, onNotify }) {
  const { claim, loading, error, setError, reload } = useClaim(claimId);
  const isReviewer = user.role === "reviewer";
  const [showUpload, setShowUpload] = useState(false);
  const [files, setFiles] = useState({});
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [decisionNote, setDecisionNote] = useState("");
  const [reasonError, setReasonError] = useState("");
  const reasonRef = useRef(null);
  const [deciding, setDeciding] = useState("");
  const [showReviewRequest, setShowReviewRequest] = useState(false);
  const [reviewNote, setReviewNote] = useState("");
  const [requesting, setRequesting] = useState(false);

  const form = claimFormOf(claim);
  const docs = publicDocuments(claim);
  const pending = claim?.pending_documents || [];

  const uploadFields = useMemo(
    () =>
      DOCUMENT_FIELDS.filter(
        ([key]) => !pending.length || pending.some((d) => d.document_type === key),
      ),
    [pending],
  );

  if (loading && !claim) {
    return (
      <div className="loading-panel">
        <RefreshCw className="spin" /> Loading claim details...
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="panel error-panel">
        <AlertCircle />
        <h2>Claim details unavailable</h2>
        <p>{error || "Could not load this claim from the backend."}</p>
        <div className="error-actions">
          <button type="button" className="btn btn-secondary" onClick={onBack}>
            Back to claims
          </button>
          <button type="button" className="btn btn-primary" onClick={() => reload()}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  const needsDocuments = claim.status === "waiting_for_documents";
  const canRerun =
    isReviewer && ["needs_internal_review", "budget_exceeded"].includes(claim.status);
  const canDecide = isReviewer && REVIEW_STATUSES.includes(claim.status);
  // Same rule as the API: an automatic rejection nobody has reviewed yet.
  const canRequestReview =
    !isReviewer &&
    claim.status === "complete" &&
    !claim.human_approval &&
    claimOutcome(claim) === "REJECTED";
  const findings = claim.investigation?.findings || [];
  const flagged = findings.filter((f) => f.status !== "VALID").length;
  const status = describeClaim(claim, isReviewer);
  const pendingTypes = new Set(pending.map((d) => d.document_type));
  const vehicle = [form.vehicle_make, form.vehicle_model].filter(Boolean).join(" ");
  const subtitle = [
    form.vehicle_registration_number,
    vehicle,
    form.accident_date && `Accident on ${form.accident_date}`,
  ]
    .filter(Boolean)
    .join(" · ");

  const details = [
    ["Policy number", form.policy_number],
    ["Policyholder", form.insured_name],
    ["Vehicle registration", form.vehicle_registration_number],
    ["Vehicle", vehicle],
    ["Driver", form.driver_name],
    ["Driving licence", form.driver_license_number],
    ["Accident date", form.accident_date],
    ["Accident time", form.accident_time],
    ["Accident location", form.accident_location],
    [
      "Third-party involvement",
      form.third_party_involved === true
        ? "Yes"
        : form.third_party_involved === false
          ? "No"
          : "Not specified",
    ],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");

  async function handleRetry() {
    setRetrying(true);
    setError("");
    try {
      await retryClaim(claimId);
      await reload({ silent: true });
      onNotify("Claim processing restarted.");
    } catch (err) {
      setError(err.message || "Unable to restart claim processing.");
    } finally {
      setRetrying(false);
    }
  }

  async function handleDecision(action) {
    const note = decisionNote.trim();
    if (action === "reject" && !note) {
      // Next to the field, not at the top of the page, which may be scrolled away.
      setReasonError("Add a reason before rejecting the claim.");
      reasonRef.current?.focus();
      return;
    }
    setReasonError("");
    const prompt =
      action === "approve"
        ? "Approve this claim and mark it complete? This cannot be undone."
        : "Reject this claim and close it? This cannot be undone.";
    if (!window.confirm(prompt)) return;

    setDeciding(action);
    setError("");
    try {
      const send = action === "approve" ? approveClaim : rejectClaim;
      await send(claimId, note);
      await reload({ silent: true });
      onNotify(action === "approve" ? "Claim approved and completed." : "Claim rejected and closed.");
    } catch (err) {
      setError(err.message || "Unable to record the decision.");
    } finally {
      setDeciding("");
    }
  }

  async function handleReviewRequest(e) {
    e.preventDefault();
    setRequesting(true);
    setError("");
    try {
      await requestReview(claimId, reviewNote.trim());
      setReviewNote("");
      setShowReviewRequest(false);
      await reload({ silent: true });
      onNotify("Review requested. A person from our team will look at your claim.");
    } catch (err) {
      setError(err.message || "Unable to send your review request. Please try again.");
    } finally {
      setRequesting(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    setUploading(true);
    try {
      await uploadAdditionalDocuments(claimId, files);
      setFiles({});
      setShowUpload(false);
      await reload({ silent: true });
      onNotify("Documents submitted successfully.");
    } catch (err) {
      setError(err.message || "Unable to upload additional documents.");
    } finally {
      setUploading(false);
    }
  }

  const detailsGrid = (
    <div className="details-grid">
      <section className="panel detail-panel">
        <div className="panel-heading">
          <div>
            <h2>Claim information</h2>
            <p>{isReviewer ? "Details submitted by the claimant" : "Details you submitted"}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={() => reload()}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
          </button>
        </div>
        <div className="detail-list">
          {details.map(([label, value]) => (
            <div className="detail-item" key={label}>
              <span>{label}</span>
              <strong>{String(value)}</strong>
            </div>
          ))}
        </div>
        {form.accident_description && (
          <div className="description-block">
            <span>Accident description</span>
            <p>{form.accident_description}</p>
          </div>
        )}
        {form.damage_description && (
          <div className="description-block">
            <span>Damage description</span>
            <p>{form.damage_description}</p>
          </div>
        )}
      </section>

      <section className="panel detail-panel">
        <div className="panel-heading">
          <div>
            <h2>Documents</h2>
            <p>What has been received and checked</p>
          </div>
          <span className="document-count">
            {docs.length} file{docs.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="document-list">
          {docs.map((doc, i) => {
            const validity = String(doc.validity || "").toUpperCase();
            const needed = pendingTypes.has(doc.document_type);
            const [tone, label] = needed
              ? ["needed", "Needed"]
              : validity === "VALID"
                ? ["valid", "Valid"]
                : validity === "INVALID"
                  ? ["invalid", "Invalid"]
                  : ["neutral", doc.uploaded ? "Checking" : "Not uploaded"];
            return (
              <div className="document-row" key={`${doc.document_type}-${i}`}>
                <span className="document-row-icon">
                  <FileText size={18} />
                </span>
                <div className="document-row-copy">
                  <strong>{humanize(doc.document_type) || "Document"}</strong>
                  <span>{doc.uploaded ? "Uploaded" : "Not uploaded yet"}</span>
                </div>
                <span className={`mini-status ${tone}`}>{label}</span>
              </div>
            );
          })}
          {!docs.length && (
            <div className="empty-state">
              <FileText />
              <strong>No document details returned</strong>
            </div>
          )}
        </div>
      </section>
    </div>
  );

  const decisionPanel = (
    <section className="panel decision-panel" aria-labelledby="decision-heading">
      <h2 id="decision-heading">Your decision</h2>
      {claim.review?.status && (
        <p className="decision-recommendation">
          Automated review recommends{" "}
          <strong>{humanize(claim.review.status).toLowerCase()}</strong>
          {findings.length > 0 && (
            <>
              {" "}
              · {flagged ? `${flagged} of ${findings.length} checks need attention` : "all checks passed"}
            </>
          )}
        </p>
      )}
      <div className={`form-field ${reasonError ? "invalid" : ""}`}>
        <label htmlFor="decision-reason">Reason</label>
        <textarea
          id="decision-reason"
          ref={reasonRef}
          name="decision_reason"
          value={decisionNote}
          onChange={(e) => {
            setDecisionNote(e.target.value);
            setReasonError("");
          }}
          maxLength={2000}
          rows="4"
          aria-invalid={Boolean(reasonError) || undefined}
          aria-describedby={`decision-reason-hint${reasonError ? " decision-reason-error" : ""}`}
        />
        {reasonError && (
          <small id="decision-reason-error" className="field-error">
            {reasonError}
          </small>
        )}
        <small id="decision-reason-hint" className="field-hint">
          Required to reject. The claimant will see this reason.
        </small>
      </div>
      <div className="decision-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handleDecision("approve")}
          disabled={Boolean(deciding)}
        >
          <CheckCircle2 size={16} />
          {deciding === "approve" ? "Approving..." : "Approve & complete"}
        </button>
        <button
          type="button"
          className="btn btn-danger"
          onClick={() => handleDecision("reject")}
          disabled={Boolean(deciding)}
        >
          <XCircle size={16} />
          {deciding === "reject" ? "Rejecting..." : "Reject claim"}
        </button>
      </div>
      <p className="decision-meta">Recorded as {user.name}. This cannot be undone.</p>
    </section>
  );

  return (
    <div className="details-page">
      <button type="button" className="back-link" onClick={onBack}>
        <ArrowLeft size={16} /> Back to claims
      </button>

      <div className="details-heading">
        <div>
          <div className="eyebrow">
            <span /> CLAIM
          </div>
          <h1>Claim {claimRef(claim)}</h1>
          {subtitle && <p>{subtitle}</p>}
          <p className="details-ref">
            Submitted {formatDate(claim.created_at)} · Reference{" "}
            <span className="selectable">{claim.claim_id}</span>
          </p>
        </div>
        <StatusBadge status={displayStatus(claim)} />
      </div>

      {error && <Notice variant="error">{error}</Notice>}

      <section className="panel claim-status-card" data-tone={status.tone}>
        <div className="status-card-main">
          <span className="status-card-icon" aria-hidden="true">
            <status.Icon size={22} />
          </span>
          <div className="status-card-copy">
            <p className="status-card-kicker">{isReviewer ? "Claim status" : "Where your claim is"}</p>
            {/* Announced when polling changes the status; the step list is not. */}
            <div aria-live="polite">
              <h2>{status.title}</h2>
              <p>{status.text}</p>
            </div>

            {needsDocuments && pending.length > 0 && (
              <div className="status-card-needs">
                <strong>{isReviewer ? "Requested from the claimant" : "What we need"}</strong>
                <ul>
                  {pending.map((doc) => (
                    <li key={doc.document_type}>
                      {doc.description || humanize(doc.document_type)}
                      {doc.reason && <span> — {doc.reason}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {status.reason && (
              <p className="status-card-reason">
                <strong>Reason: </strong>
                {status.reason}
              </p>
            )}

            {status.note && (
              <p className="status-card-reason">
                <strong>Claimant's note: </strong>
                {status.note}
              </p>
            )}
          </div>

          {canRequestReview && (
            <div className="status-card-action">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowReviewRequest((v) => !v)}
                aria-expanded={showReviewRequest}
              >
                <UserCheck size={16} /> Ask for a review
              </button>
            </div>
          )}

          {needsDocuments && !isReviewer && (
            <div className="status-card-action">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowUpload((v) => !v)}
                aria-expanded={showUpload}
              >
                <UploadCloud size={16} /> Upload documents
              </button>
            </div>
          )}
          {canRerun && (
            <div className="status-card-action">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleRetry}
                disabled={retrying}
              >
                <RefreshCw size={15} className={retrying ? "spin" : ""} />
                {retrying ? "Restarting..." : "Rerun processing"}
              </button>
            </div>
          )}
        </div>
        <ClaimProgress claim={claim} variant="full" />
      </section>

      {showUpload && (
        <section className="panel additional-upload">
          <div className="panel-heading">
            <div>
              <h2>Upload documents</h2>
              <p>Choose a file for each requested document, then submit.</p>
            </div>
          </div>
          <form onSubmit={handleUpload}>
            <DocumentUpload
              fields={uploadFields}
              selectedFiles={files}
              setSelectedFiles={setFiles}
              required={pending.map((d) => d.document_type)}
              onReject={setError}
            />
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowUpload(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={uploading || !Object.values(files).some(Boolean)}
              >
                {uploading ? "Uploading..." : "Submit documents"} <UploadCloud size={16} />
              </button>
            </div>
          </form>
        </section>
      )}

      {showReviewRequest && canRequestReview && (
        <section className="panel review-request" aria-labelledby="review-request-heading">
          <div className="panel-heading">
            <div>
              <h2 id="review-request-heading">Ask for a person to review this</h2>
              <p>
                Someone from our team will look at your claim and documents again and make
                the final decision. You can ask once.
              </p>
            </div>
          </div>
          <form onSubmit={handleReviewRequest}>
            <div className="form-field">
              <label htmlFor="review-note">What should the reviewer know? (optional)</label>
              <textarea
                id="review-note"
                name="review_note"
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                maxLength={2000}
                rows="4"
                aria-describedby="review-note-hint"
              />
              <small id="review-note-hint" className="field-hint">
                For example, a detail you think the automated checks got wrong.
              </small>
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowReviewRequest(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" type="submit" disabled={requesting}>
                {requesting ? "Sending..." : "Send review request"}
              </button>
            </div>
          </form>
        </section>
      )}

      {canDecide ? (
        <div className="review-layout">
          <div className="review-main">
            <ProcessingResults claim={claim} />
            {detailsGrid}
          </div>
          <aside className="review-aside">{decisionPanel}</aside>
        </div>
      ) : (
        <>
          {detailsGrid}
          <ProcessingResults claim={claim} />
        </>
      )}

      <p className="details-footnote">
        <ShieldCheck size={15} aria-hidden="true" /> Claim information is handled through
        this portal.
      </p>
    </div>
  );
}
