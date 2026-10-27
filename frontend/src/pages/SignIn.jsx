import { useState } from "react";
import { ArrowRight, FileCheck2, ShieldCheck, Timer, UserRoundCheck } from "lucide-react";
import Notice from "../components/Notice";

const HIGHLIGHTS = [
  [FileCheck2, "Submit a claim in minutes", "Upload your policy, licence and survey documents in one place."],
  [Timer, "Follow every step", "See validation, investigation and review results as they happen."],
  [UserRoundCheck, "Decided by people", "A reviewer confirms every automated recommendation."],
];

export default function SignIn({ onSignIn, onRegister }) {
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const registering = mode === "register";

  const change = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  function switchMode(next) {
    setMode(next);
    setError("");
    setInfo("");
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      if (registering) {
        await onRegister(form.name, form.email, form.password);
        setMode("signin");
        setForm((f) => ({ ...f, password: "" }));
        setInfo("Account created. Sign in with your email and password.");
        setBusy(false);
      } else {
        await onSignIn(form.email, form.password);
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-brand">
        <div className="auth-brand-mark">
          <span className="brand-mark">
            <ShieldCheck />
          </span>
          <span>
            <strong>ClaimFile</strong>
            <small>Insurance portal</small>
          </span>
        </div>
        <h1>
          Motor claims, <em>made clearer.</em>
        </h1>
        <ul className="auth-highlights">
          {HIGHLIGHTS.map(([Icon, title, text]) => (
            <li key={title}>
              <span>
                <Icon size={18} />
              </span>
              <div>
                <strong>{title}</strong>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="auth-panel">
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-tabs" role="tablist" aria-label="Account">
            {[
              ["signin", "Sign in"],
              ["register", "Create account"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                className={mode === id ? "active" : ""}
                onClick={() => switchMode(id)}
              >
                {label}
              </button>
            ))}
          </div>

          <h2>{registering ? "Create your account" : "Welcome back"}</h2>
          <p className="auth-sub">
            {registering
              ? "Claimant accounts let you submit and track your own claims."
              : "Sign in to submit claims or review them."}
          </p>

          {error && <Notice variant="error">{error}</Notice>}
          {info && <Notice variant="success">{info}</Notice>}

          {registering && (
            <label className="form-field">
              <span>Full name</span>
              <input
                name="name"
                value={form.name}
                onChange={change}
                autoComplete="name"
                maxLength={100}
                required
              />
            </label>
          )}
          <label className="form-field">
            <span>Email</span>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={change}
              autoComplete="email"
              maxLength={254}
              required
            />
          </label>
          <label className="form-field">
            <span>Password</span>
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={change}
              autoComplete={registering ? "new-password" : "current-password"}
              minLength={registering ? 8 : undefined}
              maxLength={72}
              required
            />
            {registering && <small className="field-hint">At least 8 characters.</small>}
          </label>

          <button className="btn btn-primary auth-submit" type="submit" disabled={busy}>
            {busy ? "Please wait..." : registering ? "Create account" : "Sign in"}
            <ArrowRight size={16} />
          </button>

          <p className="auth-foot">
            Reviewer accounts are created by your ClaimFile administrator.
          </p>
        </form>
      </section>
    </div>
  );
}
