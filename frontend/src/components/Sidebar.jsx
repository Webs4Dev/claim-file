import {
  ChevronRight,
  CircleHelp,
  Files,
  LayoutDashboard,
  Plus,
  ShieldCheck,
} from "lucide-react";

const ITEMS = [
  ["dashboard", "Dashboard", LayoutDashboard],
  ["claims", "My claims", Files],
  ["new", "New claim", Plus],
];

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside className="sidebar">
      <button type="button" className="brand" onClick={() => onNavigate("dashboard")}>
        <span className="brand-mark">
          <ShieldCheck />
        </span>
        <span>
          <strong>ClaimFile</strong>
          <small>Insurance portal</small>
        </span>
      </button>

      <div className="side-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main">
        {ITEMS.map(([id, label, Icon]) => (
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
        <p>We're here to help you navigate your claim.</p>
        <button type="button" onClick={() => onNavigate("help")}>
          Help &amp; support <ChevronRight size={14} />
        </button>
      </div>

      <div className="profile-row">
        <div className="profile-avatar">CF</div>
        <div className="profile-copy">
          <strong>ClaimFile Portal</strong>
          <span>Motor claims</span>
        </div>
      </div>
    </aside>
  );
}
