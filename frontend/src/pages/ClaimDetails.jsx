import { useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  FileText,
  RefreshCw,
  ShieldCheck,
  UploadCloud,
  XCircle,
} from "lucide-react";
import {
  DOCUMENT_FIELDS,
  approveClaim,
  rejectClaim,
  retryClaim,
  uploadAdditionalDocuments,
} from "../api";
import DocumentUpload from "../components/DocumentUpload";
import ProcessingResults from "../components/ProcessingResults";
import Notice from "../components/Notice";
import StatusBadge from "../components/StatusBadge";
import useClaim from "../hooks/useClaim";
import {
  REVIEW_STATUSES,
  claimFormOf,
  formatDate,
  humanize,
  publicDocuments,
} from "../utils";

function describeStatus(status) {
  if (status === "waiting_for_documents") {
    return ["Action required", "Please provide the requested documents so the claim can continue."];
  }
  if (status === "human_approval") {
    return [
      "Awaiting human review",
      "Automated checks are complete. A reviewer will approve or reject this claim.",
    ];
  }
  if (REVIEW_STATUSES.includes(status)) {
    return [
      "Under review",
      "Your claim needs further review. No final decision is shown here yet.",
    ];
  }
  if (status === "complete") {
    return [
      "Processing completed",
      "The workflow has completed. Refer to the decision details if available.",
    ];
  }
  if (status === "terminated") {
    return ["Claim closed", "The claim workflow has been closed."];
  }
  return ["Claim received", "Your claim has been received and is being processed."];
}

export default function ClaimDetails({ claimId, demoClaim, onBack, onNotify }) {
  const { claim, loading, error, setError, reload } = useClaim(claimId, demoClaim);
  const [showUpload, setShowUpload] = useState(false);
  const [files, setFiles] = useState({});
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [reviewer, setReviewer] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [deciding, setDeciding] = useState("");

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
  const [statusTitle, statusText] = describeStatus(claim.status);

  const details = [
    ["Policy number", form.policy_number],
    ["Policyholder", form.insured_name],
    ["Vehicle registration", form.vehicle_registration_number],
    ["Vehicle", [form.vehicle_make, form.vehicle_model].filter(Boolean).join(" ")],
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
    const name = reviewer.trim();
    const note = decisionNote.trim();
    if (!name) {
      setError("Enter the reviewer's name before recording a decision.");
      return;
    }
    if (action === "reject" && !note) {
      setError("Add a reason before rejecting the claim.");
      return;
    }
    const prompt =
      action === "approve"
        ? "Approve this claim and mark it complete? This cannot be undone."
        : "Reject this claim and close it? This cannot be undone.";
    if (!window.confirm(prompt)) return;

    setDeciding(action);
    setError("");
    try {
      const send = action === "approve" ? approveClaim : rejectClaim;
      await send(claimId, name, note);
      await reload({ silent: true });
      onNotify(action === "approve" ? "Claim approved and completed." : "Claim rejected and closed.");
    } catch (err) {
      setError(err.message || "Unable to record the decision.");
    } finally {
      setDeciding("");
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

  return (
    <div className="details-page">
      <button type="button" className="back-link" onClick={onBack}>
        <ArrowLeft size={16} /> Back to claims
      </button>

      <div className="details-heading">
        <div>
          <div className="eyebrow">
            <span /> CLAIM OVERVIEW
          </div>
          <h1>{claim.claim_id || "Claim details"}</h1>
          <p>Review submitted information and the latest status.</p>
        </div>
        <StatusBadge status={claim.status} />
      </div>

      {error && <Notice variant="error">{error}</Notice>}

      {needsDocuments && (
        <div className="request-banner">
          <div>
            <strong>Additional documents requested</strong>
            <p>Upload the requested items to continue processing.</p>
            {pending.length > 0 && (
              <ul>
                {pending.map((doc, i) => (
                  <li key={i}>
                    <strong>{doc.description || humanize(doc.document_type)}</strong>
                    {doc.reason && <span> &mdash; {doc.reason}</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            type="button"
            className="btn btn-primary btn-small"
            onClick={() => setShowUpload((v) => !v)}
          >
            <UploadCloud size={15} /> Upload documents
          </button>
        </div>
      )}

      {claim.status === "human_approval" && (
        <section className="panel decision-panel">
          <div className="panel-heading">
            <div>
              <h2>Human review decision</h2>
              <p>
                Automated review recommends{" "}
                <strong>{humanize(claim.review?.status) || "a decision"}</strong>. Approving
                completes the claim; rejecting closes it.
              </p>
            </div>
          </div>
          <div className="form-grid">
            <label className="form-field">
              <span>
                Reviewer name <b>*</b>
              </span>
              <input
                name="decided_by"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                maxLength={100}
                placeholder="Who is making this decision"
              />
            </label>
            <label className="form-field wide">
              <span>Decision note (required to reject)</span>
              <textarea
                name="decision_reason"
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
                maxLength={2000}
                rows="3"
                placeholder="Reason for the decision"
              />
            </label>
          </div>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-danger"
              onClick={() => handleDecision("reject")}
              disabled={Boolean(deciding)}
            >
              <XCircle size={16} />
              {deciding === "reject" ? "Rejecting..." : "Reject claim"}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleDecision("approve")}
              disabled={Boolean(deciding)}
            >
              <CheckCircle2 size={16} />
              {deciding === "approve" ? "Approving..." : "Approve & complete"}
            </button>
          </div>
        </section>
      )}

      <div className="details-grid">
        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <h2>Claim information</h2>
              <p>Details submitted with your claim</p>
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
              <p>Uploaded files and validation status</p>
            </div>
            <span className="document-count">
              {docs.length} file{docs.length === 1 ? "" : "s"}
            </span>
          </div>
          <div className="document-list">
            {docs.map((doc, i) => {
              const validity = String(doc.validity || "").toUpperCase();
              const tone = validity === "VALID" ? "valid" : validity === "INVALID" ? "invalid" : "neutral";
              return (
                <div className="document-row" key={`${doc.document_type}-${i}`}>
                  <span className="document-row-icon">
                    <FileText size={18} />
                  </span>
                  <div className="document-row-copy">
                    <strong>{humanize(doc.document_type) || "Document"}</strong>
                    <span>{doc.uploaded ? "Uploaded" : "Not uploaded"}</span>
                  </div>
                  <span className={`mini-status ${tone}`}>{doc.validity || "Pending"}</span>
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

      <ProcessingResults claim={claim} />

      {showUpload && (
        <section className="panel additional-upload">
          <div className="panel-heading">
            <div>
              <h2>Upload additional documents</h2>
              <p>Select requested documents below.</p>
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

      <section className="panel claim-progress-panel">
        <div className="panel-heading">
          <div>
            <h2>Processing status</h2>
            <p>Customer-visible status of this claim</p>
          </div>
        </div>
        <div className="status-explanation">
          <div className={`status-large-dot ${needsDocuments ? "warn" : ""}`} />
          <div>
            <strong>{statusTitle}</strong>
            <p>{statusText}</p>
          </div>
        </div>
        {["needs_internal_review", "budget_exceeded"].includes(claim.status) && (
          <div className="request-banner">
            <div>
              <strong>Run processing again</strong>
              <p>Rerun the analysis with this claim’s saved details and uploaded documents.</p>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-small"
              onClick={handleRetry}
              disabled={retrying}
            >
              <RefreshCw size={15} className={retrying ? "spin" : ""} />
              {retrying ? "Restarting..." : "Rerun processing"}
            </button>
          </div>
        )}
        <div className="detail-meta">
          <span>
            <CalendarDays size={15} /> Submitted {formatDate(claim.created_at || claim.submitted_at)}
          </span>
          <span>
            <ShieldCheck size={15} /> Claim information is handled through this portal
          </span>
        </div>
      </section>
    </div>
  );
}
