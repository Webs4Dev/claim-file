import { useRef } from "react";
import { CheckCircle2, FileText, UploadCloud, X } from "lucide-react";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = ".pdf,.txt,application/pdf,text/plain";

function formatSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentUpload({
  fields,
  selectedFiles,
  setSelectedFiles,
  required = [],
  onReject,
}) {
  const inputs = useRef({});

  const choose = (field, file) => {
    if (file && file.size > MAX_BYTES) {
      onReject?.(`"${file.name}" is larger than 10 MB. Please choose a smaller file.`);
      if (inputs.current[field]) inputs.current[field].value = "";
      return;
    }
    setSelectedFiles((prev) => ({ ...prev, [field]: file || null }));
  };

  const clear = (field) => {
    choose(field, null);
    if (inputs.current[field]) inputs.current[field].value = "";
  };

  return (
    <div className="document-grid">
      {fields.map(([field, label]) => {
        const file = selectedFiles[field];
        return (
          <div className={`upload-card ${file ? "has-file" : ""}`} key={field}>
            <input
              ref={(node) => {
                inputs.current[field] = node;
              }}
              type="file"
              accept={ACCEPT}
              hidden
              onChange={(e) => choose(field, e.target.files?.[0])}
            />
            <div className="upload-card-top">
              <span className="upload-file-icon">
                {file ? <FileText /> : <UploadCloud />}
              </span>
              {required.includes(field) && <span className="required-tag">Required</span>}
            </div>
            <strong>{label}</strong>
            <p>{file ? `${file.name} (${formatSize(file.size)})` : "PDF or text, up to 10 MB"}</p>
            {file ? (
              <div className="upload-actions">
                <span className="file-ready">
                  <CheckCircle2 size={14} /> Ready to upload
                </span>
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => clear(field)}
                  aria-label={`Remove ${label}`}
                >
                  <X size={15} />
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="choose-file"
                onClick={() => inputs.current[field]?.click()}
              >
                Choose file
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
