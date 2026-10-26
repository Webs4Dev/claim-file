const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const REQUEST_TIMEOUT_MS = 20000;
const SUBMISSION_KEY_STORAGE = "claimfile.pendingSubmissionKey";

export const getApiBase = () => API_BASE;

/** [form field name, human label] for every document the backend accepts. */
export const DOCUMENT_FIELDS = [
  ["policy_schedule", "Policy schedule"],
  ["policy_document", "Policy wording document"],
  ["vehicle_registration", "Vehicle registration"],
  ["driving_license", "Driving licence"],
  ["damage_survey_report", "Damage survey report"],
  ["repair_estimate", "Repair estimate"],
  ["repair_invoice", "Repair invoice"],
  ["police_report", "Police report"],
  ["fir_document", "FIR document"],
  ["accident_report", "Accident report"],
];

/** Documents that must be attached when a claim is first submitted. */
export const REQUIRED_DOCUMENTS = [
  "policy_schedule",
  "vehicle_registration",
  "driving_license",
  "damage_survey_report",
];

export async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
    });
  } catch (err) {
    throw new Error(
      err.name === "AbortError"
        ? "The server took too long to respond."
        : `Cannot reach the server at ${API_BASE}. Is the backend running?`,
    );
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const detail =
      data?.detail || data?.message || `Request failed (${response.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const checkHealth = () => apiRequest("/health");

export async function listClaims() {
  const data = await apiRequest("/claims");
  const items = Array.isArray(data) ? data : data?.claims;
  if (!Array.isArray(items)) throw new Error("Unexpected claims list format.");
  return items;
}

export const getClaim = (id) => apiRequest(`/claims/${encodeURIComponent(id)}`);

function appendFiles(body, files) {
  Object.entries(files).forEach(([key, file]) => {
    if (file) body.append(key, file);
  });
}

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    return (character === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

function getSubmissionKey() {
  try {
    let key = localStorage.getItem(SUBMISSION_KEY_STORAGE);
    if (!key) {
      key = createUuid();
      localStorage.setItem(SUBMISSION_KEY_STORAGE, key);
    }
    return key;
  } catch {
    return createUuid();
  }
}

export async function createClaim(form, files) {
  const body = new FormData();
  body.append("claim_form", JSON.stringify(form));
  appendFiles(body, files);
  const key = getSubmissionKey();
  const result = await apiRequest("/claims", {
    method: "POST",
    body,
    headers: { "Idempotency-Key": key },
  });
  try {
    localStorage.removeItem(SUBMISSION_KEY_STORAGE);
  } catch {
    /* storage unavailable - the server still enforces this request key */
  }
  return result;
}

export const retryClaim = (id) =>
  apiRequest(`/claims/${encodeURIComponent(id)}/retry`, { method: "POST" });

export async function uploadAdditionalDocuments(id, files) {
  const body = new FormData();
  appendFiles(body, files);
  return apiRequest(`/claims/${encodeURIComponent(id)}/documents`, {
    method: "POST",
    body,
  });
}

function sendDecision(id, action, decidedBy, reason) {
  return apiRequest(`/claims/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decided_by: decidedBy, reason: reason || null }),
  });
}

export const approveClaim = (id, decidedBy, reason) =>
  sendDecision(id, "approve", decidedBy, reason);

export const rejectClaim = (id, decidedBy, reason) =>
  sendDecision(id, "reject", decidedBy, reason);
