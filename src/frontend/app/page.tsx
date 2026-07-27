"use client";

import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { LanguageSwitcher, useI18n } from "./components/i18n";

type AuthMode = "login" | "register" | "forgot" | "reset";

type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
};

export default function SignInPage() {
  const { t } = useI18n();
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
          <p>{t("Insurance operations")}</p>
          <h1>{t("Evidence-bound claims control.")}</h1>
          <span>{t("Review claim materials, inspect policy evidence, and govern every operational action.")}</span>
        </div>
        <ul>
          <li><ShieldCheck size={15} /><span><strong>{t("Human approval")}</strong> {t("for controlled actions")}</span></li>
          <li><LockKeyhole size={15} /><span><strong>{t("Evidence gates")}</strong> {t("before recommendations")}</span></li>
        </ul>
      </section>

      <section className="opsAuthFormPanel">
        <LanguageSwitcher />
        <div className="opsAuthIntro">
          <p>{t("Controlled workspace")}</p>
          <h2>
            {mode === "login"
              ? t("Sign in")
              : mode === "register"
                ? t("Create account")
                : mode === "forgot"
                  ? t("Reset password")
                  : t("Set new password")}
          </h2>
          <span>{t("Use your SupportAgent account to access the claims workspace.")}</span>
        </div>

        <form onSubmit={submit}>
          {mode !== "reset" ? (
            <label>{t("Email")}
              <input autoComplete="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </label>
          ) : null}
          {mode === "register" ? (
            <label>{t("Display name")}
              <input autoComplete="name" onChange={(event) => setDisplayName(event.target.value)} type="text" value={displayName} />
            </label>
          ) : null}
          {mode !== "forgot" ? (
            <label>{t("Password")}
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
          {resetLink ? <a className="opsAuthResetLink" href={resetLink}>{t("Open reset link")}</a> : null}
          {error ? <p className="opsAuthError">{error}</p> : null}
          <button disabled={loading} type="submit">
            {loading
              ? t("Please wait…")
              : mode === "login"
                ? t("Continue")
                : mode === "register"
                  ? t("Create account")
                  : mode === "forgot"
                    ? t("Send reset link")
                    : t("Update password")}
            {!loading ? <ArrowRight size={15} /> : null}
          </button>
        </form>

        <div className="opsAuthLinks">
          {mode === "login" ? <button onClick={() => switchMode("forgot")} type="button">{t("Forgot password?")}</button> : null}
          <button onClick={() => switchMode(mode === "login" ? "register" : "login")} type="button">
            {mode === "login" ? t("Create a local account") : t("Use an existing account")}
          </button>
        </div>
      </section>
    </main>
  );
}
