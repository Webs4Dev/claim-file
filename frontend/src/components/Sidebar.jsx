import {
  ChevronRight,
  CircleHelp,
  Files,
  LayoutDashboard,
  ListChecks,
  Plus,
  ShieldCheck,
} from "lucide-react";
import { initialsOf } from "../utils";

const CLAIMANT_ITEMS = [
  ["dashboard", "Dashboard", LayoutDashboard],
  ["claims", "My claims", Files],
  ["new", "New claim", Plus],
];

const REVIEWER_ITEMS = [
  ["dashboard", "Review queue", ListChecks],
  ["claims", "All claims", Files],
];

export default function Sidebar({ page, onNavigate, user }) {
  const isReviewer = user.role === "reviewer";
  const items = isReviewer ? REVIEWER_ITEMS : CLAIMANT_ITEMS;

  return (
    <aside className="sidebar">
      <button type="button" className="brand" onClick={() => onNavigate("dashboard")}>
        <span className="brand-mark">
          <ShieldCheck />
        </span>
        <span>
          <strong>ClaimFile</strong>
          <small>{isReviewer ? "Reviewer workspace" : "Insurance portal"}</small>
        </span>
      </button>

      <div className="side-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main">
        {items.map(([id, label, Icon]) => (
          <button
            key={id}
            type="button"
            className={`side-link ${page === id ? "active" : ""}`}
            aria-current={page === id ? "page" : undefined}
            onClick={() => onNavigate(id)}
          >
            <Icon size={18} />
            <span>{label}</span>
            {id === "new" && <ChevronRight className="side-chevron" size={15} />}
          </button>
        ))}
      </nav>

      <div className="sidebar-spacer" />

      <div className="support-box">
        <CircleHelp size={19} />
        <strong>Need a hand?</strong>
        <p>
          {isReviewer
            ? "How claims move through validation, investigation and review."
            : "We're here to help you navigate your claim."}
        </p>
        <button type="button" onClick={() => onNavigate("help")}>
          Help &amp; support <ChevronRight size={14} />
        </button>
      </div>

      <div className="profile-row">
        <div className="profile-avatar">{initialsOf(user.name)}</div>
        <div className="profile-copy">
          <strong>{user.name}</strong>
          <span>{user.email}</span>
        </div>
      </div>
    </aside>
  );
}
