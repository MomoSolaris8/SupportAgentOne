"use client";

import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

type AuthMode = "login" | "register" | "forgot" | "reset";

type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
};

export default function SignInPage() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [resetLink, setResetLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("reset_token");
    if (token) {
      setResetToken(token);
      setMode("reset");
      setNotice("Choose a new password for your account.");
      window.history.replaceState(null, "", window.location.pathname);
    }

    fetch("/api/auth/me", { credentials: "include" })
      .then((response) => {
        if (response.ok && !token) window.location.replace("/claims");
      })
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);
    setResetLink(null);

    const endpoint =
      mode === "forgot"
        ? "forgot-password"
        : mode === "reset"
          ? "reset-password"
          : mode;
    const payload =
      mode === "forgot"
        ? { email }
        : mode === "reset"
          ? { token: resetToken, password }
          : {
              email,
              password,
              display_name: mode === "register" ? displayName : undefined
            };

    try {
      const response = await fetch(`/api/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      const data = (await response.json().catch(() => null)) as
        | AuthUser
        | { detail?: string; message?: string; reset_url?: string | null }
        | null;
      if (!response.ok) {
        throw new Error(data && "detail" in data && data.detail ? data.detail : `Authentication failed (${response.status})`);
      }

      if (mode === "forgot") {
        const result = data as { message?: string; reset_url?: string | null };
        setNotice(result.message ?? "If the account exists, a reset link has been sent.");
        setResetLink(result.reset_url ?? null);
        return;
      }
      if (mode === "reset") {
        setPassword("");
        setResetToken("");
        setMode("login");
        setNotice("Password updated. Sign in with your new password.");
        return;
      }
      window.location.replace("/claims");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next: AuthMode) {
    setMode(next);
    setError(null);
    setNotice(null);
    setResetLink(null);
    setPassword("");
  }

  return (
    <main className="opsAuthShell">
      <section className="opsAuthContext">
        <div className="opsAuthBrand"><span>SA</span><strong>SupportAgent</strong></div>
        <div>
          <p>Insurance operations</p>
          <h1>Evidence-bound claims control.</h1>
          <span>Review claim materials, inspect policy evidence, and govern every operational action.</span>
        </div>
        <ul>
          <li><ShieldCheck size={15} /><span><strong>Human approval</strong> for controlled actions</span></li>
          <li><LockKeyhole size={15} /><span><strong>Evidence gates</strong> before recommendations</span></li>
        </ul>
      </section>

      <section className="opsAuthFormPanel">
        <div>
          <p>Controlled workspace</p>
          <h2>
            {mode === "login"
              ? "Sign in"
              : mode === "register"
                ? "Create account"
                : mode === "forgot"
                  ? "Reset password"
                  : "Set new password"}
          </h2>
          <span>Use your SupportAgent account to access the claims workspace.</span>
        </div>

        <form onSubmit={submit}>
          {mode !== "reset" ? (
            <label>Email
              <input autoComplete="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </label>
          ) : null}
          {mode === "register" ? (
            <label>Display name
              <input autoComplete="name" onChange={(event) => setDisplayName(event.target.value)} type="text" value={displayName} />
            </label>
          ) : null}
          {mode !== "forgot" ? (
            <label>Password
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "login" ? 1 : 8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
          ) : null}
          {notice ? <p className="opsAuthNotice">{notice}</p> : null}
          {resetLink ? <a className="opsAuthResetLink" href={resetLink}>Open reset link</a> : null}
          {error ? <p className="opsAuthError">{error}</p> : null}
          <button disabled={loading} type="submit">
            {loading
              ? "Please wait…"
              : mode === "login"
                ? "Continue"
                : mode === "register"
                  ? "Create account"
                  : mode === "forgot"
                    ? "Send reset link"
                    : "Update password"}
            {!loading ? <ArrowRight size={15} /> : null}
          </button>
        </form>

        <div className="opsAuthLinks">
          {mode === "login" ? <button onClick={() => switchMode("forgot")} type="button">Forgot password?</button> : null}
          <button onClick={() => switchMode(mode === "login" ? "register" : "login")} type="button">
            {mode === "login" ? "Create a local account" : "Use an existing account"}
          </button>
        </div>
      </section>
    </main>
  );
}
