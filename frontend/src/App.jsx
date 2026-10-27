import { useCallback, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Toast from "./components/Toast";
import useApiHealth from "./hooks/useApiHealth";
import useAuth from "./hooks/useAuth";
import useHashRoute from "./hooks/useHashRoute";
import ClaimDetails from "./pages/ClaimDetails";
import Dashboard from "./pages/Dashboard";
import Help from "./pages/Help";
import NewClaim from "./pages/NewClaim";
import SignIn from "./pages/SignIn";

export default function App() {
  const { user, login, createAccount, logout } = useAuth();

  if (user === undefined) {
    return (
      <div className="loading-panel app-loading">
        <RefreshCw className="spin" /> Loading ClaimFile...
      </div>
    );
  }

  if (!user) return <SignIn onSignIn={login} onRegister={createAccount} />;

  // Keyed by user so nothing from a previous account survives a switch.
  return <Portal key={user.user_id} user={user} onLogout={logout} />;
}

function Portal({ user, onLogout }) {
  const { page: routedPage, claimId, navigate } = useHashRoute();
  const { healthy, recheck } = useApiHealth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState("");
  const clearToast = useCallback(() => setToast(""), []);

  const isReviewer = user.role === "reviewer";
  // Reviewers assess claims; they do not submit them.
  const page = isReviewer && routedPage === "new" ? "dashboard" : routedPage;

  const go = (target) => {
    setMobileOpen(false);
    navigate(target === "dashboard" ? "/" : `/${target}`);
  };
  const openClaim = (id) => navigate(`/claims/${encodeURIComponent(id)}`);
  const sidebarPage = page === "details" ? "claims" : page;


  return (
    <div className="app-shell">
      <div
        className={`mobile-scrim ${mobileOpen ? "visible" : ""}`}
        onClick={() => setMobileOpen(false)}
      />
      <div className={`sidebar-holder ${mobileOpen ? "open" : ""}`}>
        <button
          type="button"
          className="mobile-close"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
        >
          <X size={18} />
        </button>
        <Sidebar page={sidebarPage} onNavigate={go} user={user} />
      </div>

      <main className="main-area">
        <Header
          onMenu={() => setMobileOpen((open) => !open)}
          healthy={healthy}
          onRecheck={recheck}
          user={user}
          onLogout={onLogout}
        />
        <div className="page-content">
          {(page === "dashboard" || page === "claims") && (
            <Dashboard
              key={page}
              view={page}
              user={user}
              onRecheck={recheck}
              onNewClaim={() => go("new")}
              onOpenClaim={openClaim}
            />
          )}
          {page === "new" && (
            <NewClaim
              onCreated={openClaim}
              onCancel={() => go("dashboard")}
              onNotify={setToast}
            />
          )}
          {page === "details" && (
            <ClaimDetails
              key={claimId}
              claimId={claimId}
              user={user}
              onBack={() => go("claims")}
              onNotify={setToast}
            />
          )}
          {page === "help" && <Help />}

          <footer className="app-footer">
            <span>&copy; {new Date().getFullYear()} ClaimFile</span>
            <span>Motor claims, made clearer.</span>
          </footer>
        </div>
      </main>

      <Toast message={toast} onDone={clearToast} />
    </div>
  );
}
