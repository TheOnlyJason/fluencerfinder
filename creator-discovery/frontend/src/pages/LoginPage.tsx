import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as { from?: string } | null)?.from || "/groups";
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "signin") {
        await signIn(email, password);
        navigate(redirectTo);
      } else {
        const { needsConfirmation } = await signUp(email, password);
        if (needsConfirmation) {
          setNotice("Check your email to confirm your account, then sign in.");
          setMode("signin");
        } else {
          navigate(redirectTo);
        }
      }
    } catch (e: any) {
      setError(e.message || "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-card">
      <h1>{mode === "signin" ? "Sign in" : "Create an account"}</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        {mode === "signin"
          ? "Sign in to manage your creator groups."
          : "Create an account to save creators into groups."}
      </p>

      {notice && <div className="auth-notice">{notice}</div>}
      {error && <div className="error" style={{ padding: "0.5rem 0" }}>{error}</div>}

      <form className="auth-form" onSubmit={handleSubmit}>
        <input
          className="search-input"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <input
          className="search-input"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === "signin" ? "current-password" : "new-password"}
          minLength={6}
          required
        />
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
        </button>
      </form>

      <button
        type="button"
        className="auth-switch"
        onClick={() => {
          setMode((m) => (m === "signin" ? "signup" : "signin"));
          setError("");
          setNotice("");
        }}
      >
        {mode === "signin"
          ? "Don't have an account? Sign up"
          : "Already have an account? Sign in"}
      </button>
    </div>
  );
}
