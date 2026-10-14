import { statusLabel, statusTone } from "../utils";

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge tone-${statusTone(status)}`}>
      <i aria-hidden="true" />
      {statusLabel(status)}
    </span>
  );
}
