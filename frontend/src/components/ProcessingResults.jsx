import { ChevronDown, ClipboardCheck, FileSearch, FileText, ScanSearch, UserCheck } from "lucide-react";
import { formatDate, humanize } from "../utils";

/**
 * Agent verdicts -> status tones (DESIGN.md): a concern is for a reviewer to
 * weigh (review); missing evidence is something the claimant can supply
 * (warning).
 */
const VERDICT_TONES = {
  VALID: "success",
  APPROVED: "success",
  INVALID: "danger",
  REJECTED: "danger",
  CONCERN: "review",
  NEEDS_INVESTIGATION: "review",
  INSUFFICIENT_EVIDENCE: "warning",
};

const VERDICT_LABELS = {
  INSUFFICIENT_EVIDENCE: "Missing evidence",
  NEEDS_INVESTIGATION: "Needs investigation",
};

/** Problems first, so a reviewer reads what needs judgement before what passed. */
const FINDING_ORDER = { INVALID: 0, CONCERN: 1, INSUFFICIENT_EVIDENCE: 2, VALID: 3 };

/**
 * Documents each investigation check relies on. Findings do not record their
 * source document, so these are shown as "related", not as citations.
 */
const RELATED_DOCUMENTS = {
  "Policy Validity": ["policy_schedule", "policy_document"],
  "Driver and Licence Information": ["driving_license"],
  "Vehicle Information": ["vehicle_registration", "policy_schedule"],
  "Accident Information": ["accident_report", "police_report", "fir_document", "damage_survey_report"],
  "Damage Information": ["damage_survey_report", "repair_estimate", "repair_invoice"],
  "Third-Party Involvement": ["accident_report", "police_report", "fir_document"],
  "Police/FIR Information": ["police_report", "fir_document"],
};

const DOCUMENT_TONES = { VALID: "valid", INVALID: "invalid" };

function Verdict({ value }) {
  if (!value) return null;
  const key = String(value).toUpperCase();
  const label = VERDICT_LABELS[key] || humanize(key.toLowerCase());
  return (
    <span className={`status-badge verdict tone-${VERDICT_TONES[key] || "info"}`}>
      <i aria-hidden="true" />
      {label}
    </span>
  );
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(displayValue).join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function Stage({ icon: Icon, title, verdict, note, children }) {
  return (
    <div className="result-stage">
      <div className="result-stage-head">
        <span className="result-stage-icon">
          <Icon size={17} />
        </span>
        <h3>{title}</h3>
        {note && <span className="result-stage-note">{note}</span>}
        <Verdict value={verdict} />
      </div>
      {children}
    </div>
  );
}

function ExtractedGroup({ name, value }) {
  if (Array.isArray(value) && value.some((row) => row && typeof row === "object")) {
    const columns = [...new Set(value.flatMap((row) => Object.keys(row || {})))];
    return (
      <div className="extracted-group wide">
        <h4>{humanize(name)}</h4>
        <div className="table-scroll">
          <table className="extracted-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{humanize(column)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {value.map((row, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td key={column}>
                      {column === "document_type"
                        ? humanize(row[column])
                        : displayValue(row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const rows =
    value && typeof value === "object" && !Array.isArray(value)
      ? Object.entries(value)
      : [[name, value]];

  return (
    <div className="extracted-group">
      <h4>{humanize(name)}</h4>
      <dl>
        {rows.map(([key, nested]) => (
          <div key={key}>
            <dt>{humanize(key)}</dt>
            <dd>{displayValue(nested)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** Plain strings, or required-document objects ({document_type, description?, reason?}). */
function listItemText(item) {
  if (typeof item === "string") return item;
  const label = item?.description || humanize(item?.document_type);
  return item?.reason ? `${label}: ${item.reason}` : label;
}

function ResultList({ title, items }) {
  const texts = (items || []).map(listItemText).filter(Boolean);
  if (!texts.length) return null;
  return (
    <div className="result-list">
      <h4>{title}</h4>
      <ul>
        {texts.map((text, index) => (
          <li key={index}>{text}</li>
        ))}
      </ul>
    </div>
  );
}

function RelatedDocuments({ category, documents }) {
  const types = RELATED_DOCUMENTS[category] || [];
  const related = documents.filter((doc) => types.includes(doc.document_type));
  if (!related.length) return null;
  return (
    <div className="finding-documents">
      <span>Related documents</span>
      <ul>
        {related.map((doc) => {
          const validity = String(doc.validity || "").toUpperCase();
          return (
            <li key={doc.document_type} className={DOCUMENT_TONES[validity] || "neutral"}>
              <FileText size={13} aria-hidden="true" />
              {humanize(doc.document_type)}
              <span className="sr-only">: {validity ? validity.toLowerCase() : "not checked"}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function ProcessingResults({ claim }) {
  const { extracted_data: extracted, investigation, review, human_approval: decision } = claim;
  if (!extracted && !investigation && !review && !decision) return null;

  const documents = claim.claim_documents || [];
  const findings = [...(investigation?.findings || [])].sort(
    (a, b) => (FINDING_ORDER[a.status] ?? 9) - (FINDING_ORDER[b.status] ?? 9),
  );
  const flagged = findings.filter((f) => f.status !== "VALID").length;

  return (
    <section className="panel claim-progress-panel">
      <div className="panel-heading">
        <div>
          <h2>Assessment</h2>
          <p>What the automated checks found, problems first</p>
        </div>
      </div>

      <div className="result-stages">
        {decision && (
          <Stage icon={UserCheck} title="Human decision" verdict={decision.decision}>
            <p className="result-summary">
              Decided by <strong>{decision.decided_by}</strong>
              {decision.decided_at && <> on {formatDate(decision.decided_at)}</>}
            </p>
            {decision.reason && <blockquote className="decision-note">{decision.reason}</blockquote>}
          </Stage>
        )}

        {review && (
          <Stage icon={ClipboardCheck} title="Automated review" verdict={review.status}>
            {review.summary && <p className="result-summary">{review.summary}</p>}
            <ResultList title="Concerns" items={review.concerns} />
            <ResultList title="Required actions" items={review.required_actions} />
            <ResultList title="Required documents" items={review.required_documents} />
          </Stage>
        )}

        {investigation && (
          <Stage
            icon={ScanSearch}
            title="Investigation"
            verdict={investigation.overall_status}
            note={
              findings.length
                ? flagged
                  ? `${flagged} of ${findings.length} checks need attention`
                  : `All ${findings.length} checks passed`
                : null
            }
          >
            <div className="finding-grid">
              {findings.map((finding, index) => (
                <article
                  className={`finding-card tone-edge-${VERDICT_TONES[finding.status] || "info"}`}
                  key={`${finding.category}-${index}`}
                >
                  <div className="finding-card-head">
                    <h4>{finding.category}</h4>
                    <Verdict value={finding.status} />
                  </div>
                  <p>{finding.finding}</p>
                  {finding.evidence && (
                    <p className="finding-evidence">
                      <span>Evidence</span>
                      {finding.evidence}
                    </p>
                  )}
                  <RelatedDocuments category={finding.category} documents={documents} />
                </article>
              ))}
            </div>
            <ResultList title="Missing information" items={investigation.missing_information} />
            <ResultList title="Contradictions" items={investigation.contradictions} />
          </Stage>
        )}

        {extracted && (
          <details className="result-stage extracted-details">
            <summary className="result-stage-head">
              <span className="result-stage-icon">
                <FileSearch size={17} />
              </span>
              <h3>Extracted information</h3>
              <span className="extracted-hint">From the uploaded documents</span>
              <ChevronDown size={17} className="extracted-chevron" aria-hidden="true" />
            </summary>
            <div className="extracted-grid">
              {Object.entries(extracted).map(([group, value]) => (
                <ExtractedGroup key={group} name={group} value={value} />
              ))}
            </div>
          </details>
        )}
      </div>
    </section>
  );
}
