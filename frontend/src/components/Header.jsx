import { LogOut, Menu } from "lucide-react";
import { initialsOf } from "../utils";

const HEALTH_LABEL = {
  true: "API connected",
  false: "API unavailable",
  null: "Checking API",
};

export default function Header({ onMenu, healthy, onRecheck, user, onLogout }) {
  const state = healthy === true ? "connected" : healthy === false ? "disconnected" : "";
  const isReviewer = user.role === "reviewer";
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
        <strong>{isReviewer ? "Reviewer workspace" : "Motor claims portal"}</strong>
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
        <div className="topbar-user">
          <span className={`topbar-avatar ${isReviewer ? "reviewer" : ""}`} aria-hidden="true">
            {initialsOf(user.name)}
          </span>
          <span className="topbar-user-copy">
            <strong>{user.name}</strong>
            <small>{isReviewer ? "Reviewer" : "Claimant"}</small>
          </span>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-small topbar-logout"
          onClick={onLogout}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut size={15} />
          <span>Sign out</span>
        </button>
      </div>
    </header>
  );
}
