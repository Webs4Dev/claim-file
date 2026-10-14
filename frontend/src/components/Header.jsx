import { Menu, ShieldCheck } from "lucide-react";

const HEALTH_LABEL = {
  true: "API connected",
  false: "API unavailable",
  null: "Checking API",
};

export default function Header({ onMenu, healthy, onRecheck }) {
  const state = healthy === true ? "connected" : healthy === false ? "disconnected" : "";
  return (
    <header className="topbar">
      <button
        type="button"
        className="mobile-menu"
        onClick={onMenu}
        aria-label="Toggle navigation"
      >
        <Menu size={19} />
      </button>
      <div className="breadcrumb">
        <span>ClaimFile</span>
        <span>/</span>
        <strong>Motor claims portal</strong>
      </div>
      <div className="topbar-right">
        <button
          type="button"
          className={`connection-pill ${state}`}
          onClick={onRecheck}
          title="Click to re-check the connection"
        >
          <i aria-hidden="true" />
          {HEALTH_LABEL[String(healthy)]}
        </button>
        <span className="topbar-avatar" aria-hidden="true">
          <ShieldCheck size={17} />
        </span>
      </div>
    </header>
  );
}
