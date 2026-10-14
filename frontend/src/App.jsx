import { useCallback, useState } from "react";
import { X } from "lucide-react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Toast from "./components/Toast";
import useApiHealth from "./hooks/useApiHealth";
import useClaims from "./hooks/useClaims";
import useHashRoute from "./hooks/useHashRoute";
import ClaimDetails from "./pages/ClaimDetails";
import Dashboard from "./pages/Dashboard";
import Help from "./pages/Help";
import NewClaim from "./pages/NewClaim";

export default function App() {
  const { page, claimId, navigate } = useHashRoute();
  const { healthy, recheck } = useApiHealth();
  const { claims, loading, source, refresh } = useClaims();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState("");
  const clearToast = useCallback(() => setToast(""), []);

  const go = (target) => {
    setMobileOpen(false);
    navigate(target === "dashboard" ? "/" : `/${target}`);
  };
  const openClaim = (id) => navigate(`/claims/${encodeURIComponent(id)}`);
  const sidebarPage = page === "details" ? "claims" : page;

  const handleCreated = (id) => {
    refresh({ silent: true });
    openClaim(id);
  };

  const refreshAll = () => {
    recheck();
    refresh();
  };

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
        <Sidebar page={sidebarPage} onNavigate={go} />
      </div>

      <main className="main-area">
        <Header
          onMenu={() => setMobileOpen((open) => !open)}
          healthy={healthy}
          onRecheck={recheck}
        />
        <div className="page-content">
          {(page === "dashboard" || page === "claims") && (
            <Dashboard
              view={page}
              claims={claims}
              loading={loading}
              source={source}
              onRefresh={refreshAll}
              onNewClaim={() => go("new")}
              onOpenClaim={openClaim}
            />
          )}
          {page === "new" && (
            <NewClaim
              onCreated={handleCreated}
              onCancel={() => go("dashboard")}
              onNotify={setToast}
            />
          )}
          {page === "details" && (
            <ClaimDetails
              key={claimId}
              claimId={claimId}
              demoClaim={claims.find((c) => c.claim_id === claimId)}
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
