import { useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CarFront,
  Check,
  ClipboardCheck,
  Files,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { DOCUMENT_FIELDS, REQUIRED_DOCUMENTS, createClaim } from "../api";
import DocumentUpload from "../components/DocumentUpload";
import { rememberClaimId } from "../hooks/useClaims";

const INITIAL_FORM = {
  policy_number: "",
  insured_name: "",
  vehicle_registration_number: "",
  vehicle_make: "",
  vehicle_model: "",
  accident_date: "",
  accident_time: "",
  accident_location: "",
  accident_description: "",
  driver_name: "",
  driver_license_number: "",
  damage_description: "",
  third_party_involved: false,
  additional_information: {},
};

const STEPS = [
  ["Policyholder", "Your details", ClipboardCheck],
  ["Vehicle", "Vehicle information", CarFront],
  ["Accident", "Incident details", MapPin],
  ["Documents", "Supporting files", Files],
];

const REQUIRED_BY_STEP = [
  ["policy_number", "insured_name"],
  [
    "vehicle_registration_number",
    "vehicle_make",
    "vehicle_model",
    "driver_name",
    "driver_license_number",
  ],
  ["accident_date", "accident_location", "accident_description", "damage_description"],
];

const LAST_STEP = STEPS.length - 1;
const today = () => new Date().toISOString().slice(0, 10);

function Field({ label, name, form, onChange, invalid, required, type = "text", wide }) {
  return (
    <label className={`form-field ${wide ? "wide" : ""} ${invalid ? "invalid" : ""}`}>
      <span>
        {label}
        {required && <b> *</b>}
      </span>
      <input
        name={name}
        value={form[name] ?? ""}
        onChange={onChange}
        type={type}
        max={type === "date" ? today() : undefined}
        aria-invalid={invalid || undefined}
        placeholder={type === "text" ? `Enter ${label.toLowerCase()}` : undefined}
      />
    </label>
  );
}

function TextArea({ label, name, form, onChange, invalid, placeholder }) {
  return (
    <label className={`form-field wide ${invalid ? "invalid" : ""}`}>
      <span>
        {label} <b>*</b>
      </span>
      <textarea
        name={name}
        value={form[name]}
        onChange={onChange}
        rows="3"
        aria-invalid={invalid || undefined}
        placeholder={placeholder}
      />
    </label>
  );
}

function SectionTitle({ Icon, title, subtitle }) {
  return (
    <div className="form-section-title">
      <div className="section-icon">
        <Icon />
      </div>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

export default function NewClaim({ onCreated, onCancel, onNotify }) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(INITIAL_FORM);
  const [files, setFiles] = useState({});
  const [missing, setMissing] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const change = (e) => {
    const { name, type, checked, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    setMissing((prev) => prev.filter((key) => key !== name));
  };

  const fieldProps = (name) => ({
    name,
    form,
    onChange: change,
    invalid: missing.includes(name),
  });

  function goNext() {
    const blank = REQUIRED_BY_STEP[step].filter((key) => !String(form[key] || "").trim());
    setMissing(blank);
    if (blank.length) {
      setError("Please complete the highlighted fields before continuing.");
      return;
    }
    setError("");
    setStep((s) => Math.min(LAST_STEP, s + 1));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (step < LAST_STEP) {
      goNext(); // Enter key on an earlier step continues instead of submitting.
      return;
    }
    if (!REQUIRED_DOCUMENTS.every((key) => files[key])) {
      setError(
        "Upload the policy schedule, vehicle registration, driving licence and damage survey report.",
      );
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      const data = await createClaim(form, files);
      const claimId = data?.claim_id || data?.claim?.claim_id;
      if (!claimId) throw new Error("The API response did not include a claim ID.");
      rememberClaimId(claimId);
      onNotify("Claim submitted successfully.");
      onCreated(claimId);
    } catch (err) {
      setError(err.message || "Unable to submit claim.");
      setSubmitting(false);
    }
  }

  return (
    <div className="form-page">
      <div className="form-page-head">
        <button type="button" className="back-link" onClick={onCancel}>
          <ArrowLeft size={16} /> Back to dashboard
        </button>
        <div className="eyebrow">
          <span /> NEW MOTOR CLAIM
        </div>
        <h1>Let's get your claim started.</h1>
        <p>Share the incident details and upload supporting documents.</p>
      </div>

      <ol className="stepper" aria-label="Progress">
        {STEPS.map(([title, subtitle, Icon], i) => (
          <li
            className={`step ${i === step ? "current" : ""} ${i < step ? "done" : ""}`}
            key={title}
            aria-current={i === step ? "step" : undefined}
          >
            <div className="step-circle">{i < step ? <Check size={16} /> : <Icon size={16} />}</div>
            <div className="step-copy">
              <strong>{title}</strong>
              <span>{subtitle}</span>
            </div>
            {i < LAST_STEP && <div className="step-line" />}
          </li>
        ))}
      </ol>

      <form className="panel claim-form-panel" onSubmit={handleSubmit} noValidate>
        {step === 0 && (
          <>
            <SectionTitle
              Icon={ClipboardCheck}
              title="Policyholder details"
              subtitle="Enter information as shown on your policy schedule."
            />
            <div className="form-grid">
              <Field label="Policy number" required {...fieldProps("policy_number")} />
              <Field
                label="Insured / policyholder name"
                required
                {...fieldProps("insured_name")}
              />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <SectionTitle
              Icon={CarFront}
              title="Vehicle and driver"
              subtitle="Use the details on the registration and driving licence."
            />
            <div className="form-grid">
              <Field
                label="Registration number"
                required
                {...fieldProps("vehicle_registration_number")}
              />
              <Field label="Vehicle make" required {...fieldProps("vehicle_make")} />
              <Field label="Vehicle model" required {...fieldProps("vehicle_model")} />
              <Field label="Driver name" required {...fieldProps("driver_name")} />
              <Field
                label="Driving licence number"
                required
                {...fieldProps("driver_license_number")}
              />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <SectionTitle
              Icon={MapPin}
              title="Accident details"
              subtitle="Tell us when and where it happened and what was damaged."
            />
            <div className="form-grid">
              <Field
                label="Accident date"
                type="date"
                required
                {...fieldProps("accident_date")}
              />
              <Field label="Accident time" type="time" {...fieldProps("accident_time")} />
              <Field
                label="Accident location"
                required
                wide
                {...fieldProps("accident_location")}
              />
              <TextArea
                label="Accident description"
                placeholder="Describe how the accident happened..."
                {...fieldProps("accident_description")}
              />
              <TextArea
                label="Damage description"
                placeholder="Describe the vehicle damage..."
                {...fieldProps("damage_description")}
              />
              <label className="checkbox-field wide">
                <input
                  type="checkbox"
                  name="third_party_involved"
                  checked={form.third_party_involved}
                  onChange={change}
                />
                <span>A third party was involved.</span>
              </label>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <SectionTitle
              Icon={Files}
              title="Supporting documents"
              subtitle="PDF or text files. Required documents are marked."
            />
            <DocumentUpload
              fields={DOCUMENT_FIELDS.filter(([key]) => key !== "policy_document")}
              selectedFiles={files}
              setSelectedFiles={setFiles}
              required={REQUIRED_DOCUMENTS}
              onReject={setError}
            />
            <div className="form-tip">
              <AlertCircle size={16} /> Additional evidence may be requested later.
            </div>
          </>
        )}

        {error && (
          <div className="form-error" role="alert">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <div className="form-actions">
          {step > 0 ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={submitting}
              onClick={() => {
                setError("");
                setMissing([]);
                setStep((s) => s - 1);
              }}
            >
              <ArrowLeft size={16} /> Previous
            </button>
          ) : (
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancel
            </button>
          )}

          <span className="step-counter">
            STEP {step + 1} OF {STEPS.length}
          </span>

          {step < LAST_STEP ? (
            <button type="button" className="btn btn-primary" onClick={goNext}>
              Continue <ArrowRight size={16} />
            </button>
          ) : (
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Submitting..." : "Submit claim"} <ArrowRight size={16} />
            </button>
          )}
        </div>
      </form>

      <p className="form-disclaimer">
        <ShieldCheck size={14} /> Submission does not guarantee approval; claims are
        assessed against the supplied evidence and policy terms.
      </p>
    </div>
  );
}
