"use client";

import { ArrowUpRight, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { HarnessBadge, OperationsPageHeader, OperationsShell } from "../components/operations-shell";
import { Claim, displayLabel, readApiError } from "./types";

export default function ClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  async function loadClaims() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/claims", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      const payload = (await response.json()) as { claims: Claim[] };
      setClaims(payload.claims);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load claims");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadClaims();
  }, []);

  const visibleClaims = useMemo(
    () => (filter === "all" ? claims : claims.filter((claim) => claim.status === filter)),
    [claims, filter]
  );
  const pendingCount = claims.filter((claim) => claim.status === "DOCUMENTS_PENDING").length;
  const readyCount = claims.filter((claim) => claim.status === "READY_FOR_REVIEW").length;
  const reviewCount = claims.filter((claim) => claim.status === "UNDER_REVIEW").length;

  return (
    <OperationsShell active="claims">
      <OperationsPageHeader
        actions={
          <>
            <HarnessBadge tone={error ? "bad" : "good"}>{error ? "Connection issue" : "Live queue"}</HarnessBadge>
            <button className="opsSecondaryButton" disabled={loading} onClick={() => void loadClaims()} type="button">
              <RefreshCw size={14} /> Refresh
            </button>
          </>
        }
        description="Prioritized cases, evidence readiness, and controlled next actions."
        eyebrow="Claims operations"
        title="Claims queue"
      />
        <div className="claimsContent">
          <section className="claimsMetrics" aria-label="Claim metrics">
            <article><span>Total cases</span><strong>{claims.length}</strong></article>
            <article><span>Documents pending</span><strong>{pendingCount}</strong></article>
            <article><span>Ready for review</span><strong>{readyCount}</strong></article>
            <article><span>Under review</span><strong>{reviewCount}</strong></article>
          </section>

          <section className="claimsPanel">
            <div className="claimsPanelHeader">
              <div><h2>Assigned cases</h2><p>Open a case to inspect submitted materials, policy evidence, and approval-bound actions.</p></div>
              <label className="claimsFilter">Status
                <select value={filter} onChange={(event) => setFilter(event.target.value)}>
                  <option value="all">All statuses</option>
                  <option value="DOCUMENTS_PENDING">Documents pending</option>
                  <option value="READY_FOR_REVIEW">Ready for review</option>
                  <option value="UNDER_REVIEW">Under review</option>
                </select>
              </label>
            </div>

            {loading ? <p className="claimsMessage">Loading claims…</p> : null}
            {error ? <div className="claimsError"><strong>Claims could not be loaded.</strong><span>{error}</span><a href="/">Return to sign in</a></div> : null}
            {!loading && !error ? (
              <div className="claimsTableWrap">
                <table className="claimsTable">
                  <thead><tr><th>Case</th><th>Product</th><th>Incident</th><th>Policy evidence</th><th>Status</th><th /></tr></thead>
                  <tbody>
                    {visibleClaims.map((claim) => (
                      <tr key={claim.id}>
                        <td><strong>{claim.customer_reference}</strong><small>{claim.id.slice(0, 8)}</small></td>
                        <td>{displayLabel(claim.product_line)}</td>
                        <td>{displayLabel(claim.claim_type)}</td>
                        <td><strong>{claim.policy_id}</strong><small>{claim.policy_version ?? "Version not set"} · {claim.jurisdiction}</small></td>
                        <td><span className={`claimStatus status-${claim.status.toLowerCase()}`}>{displayLabel(claim.status)}</span></td>
                        <td><a className="claimsOpen" href={`/claims/${claim.id}`}>Open <ArrowUpRight size={11} /></a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!visibleClaims.length ? <p className="claimsMessage">No claims match this filter.</p> : null}
              </div>
            ) : null}
          </section>
        </div>
    </OperationsShell>
  );
}
