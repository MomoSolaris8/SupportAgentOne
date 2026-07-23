"use client";

import { ArrowLeft, Play, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HarnessBadge, OperationsPageHeader, OperationsShell } from "../../components/operations-shell";
import { ClaimDetail, ClaimReview, ProposedAction, displayLabel, readApiError } from "../types";

function ActionCard({ action, claimId, onChanged }: { action: ProposedAction; claimId: string; onChanged: () => void }) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canDecide = action.status === "PROPOSED" || action.status === "WAITING_FOR_APPROVAL";

  async function decide(decision: "approve" | "reject") {
    const label = decision === "approve" ? "approve" : "reject";
    if (!window.confirm(`${displayLabel(label)} ${displayLabel(action.action_type)}? This decision will be written to the audit trail.`)) {
      return;
    }
    setBusy(decision);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/actions/${action.id}/${decision}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comment: `${displayLabel(decision)}d in Claims Desk` })
    });
    if (!response.ok) {
      setError(await readApiError(response));
      setBusy(null);
      return;
    }
    await onChanged();
    setBusy(null);
  }

  return (
    <article className="actionCard">
      <div className="actionCardTop"><span className={`riskBadge risk-${action.risk_level}`}>{action.risk_level} risk</span><span className="actionStatus">{displayLabel(action.status)}</span></div>
      <h3>{displayLabel(action.action_type)}</h3>
      <p>{action.reason}</p>
      <dl><div><dt>Tool</dt><dd>{action.tool_server} / {action.tool_name}</dd></div><div><dt>Arguments</dt><dd><code>{JSON.stringify(action.arguments)}</code></dd></div></dl>
      {canDecide ? <div className="decisionButtons"><button disabled={busy !== null} onClick={() => decide("approve")}>{busy === "approve" ? "Approving…" : "Approve"}</button><button className="rejectButton" disabled={busy !== null} onClick={() => decide("reject")}>{busy === "reject" ? "Rejecting…" : "Reject"}</button></div> : null}
      {error ? <p className="inlineError">{error}</p> : null}
    </article>
  );
}

export default function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>();
  const [detail, setDetail] = useState<ClaimDetail | null>(null);
  const [review, setReview] = useState<ClaimReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadClaim = useCallback(async () => {
    const response = await fetch(`/api/claims/${claimId}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await readApiError(response));
    setDetail((await response.json()) as ClaimDetail);
  }, [claimId]);

  useEffect(() => {
    loadClaim().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load claim")).finally(() => setLoading(false));
  }, [loadClaim]);

  async function runReview() {
    setReviewing(true);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    if (!response.ok) {
      setError(await readApiError(response));
      setReviewing(false);
      return;
    }
    setReview((await response.json()) as ClaimReview);
    await loadClaim();
    setReviewing(false);
  }

  if (loading) return <main className="claimDetailLoading">Loading claim…</main>;
  if (!detail) return <main className="claimDetailLoading"><strong>Claim unavailable.</strong><p>{error}</p><a href="/claims">Return to claims</a></main>;

  const { claim, documents, proposed_actions } = detail;
  const actions = review?.proposed_action && !proposed_actions.some((item) => item.id === review.proposed_action?.id) ? [review.proposed_action, ...proposed_actions] : proposed_actions;

  return (
    <OperationsShell
      active="claims"
      claimContext={{
        id: claim.id,
        customerReference: claim.customer_reference,
        policyId: claim.policy_id,
        claimType: displayLabel(claim.claim_type)
      }}
    >
      <OperationsPageHeader
        actions={
          <>
            <HarnessBadge tone={claim.status === "DOCUMENTS_PENDING" ? "warn" : "info"}>{displayLabel(claim.status)}</HarnessBadge>
            <button className="opsPrimaryButton" onClick={runReview} disabled={reviewing} type="button">
              <Play size={13} /> {reviewing ? "Review running…" : "Review case"}
            </button>
          </>
        }
        description={`${claim.policy_id} · ${displayLabel(claim.product_line)} · ${claim.jurisdiction}`}
        eyebrow={claim.customer_reference}
        title={displayLabel(claim.claim_type)}
      />
      <div className="claimDetailContent">
        <a className="claimBackLink" href="/claims"><ArrowLeft size={12} /> Claims queue</a>
        <section className="caseSummary">
          <div><span>Policy</span><strong>{claim.policy_id}</strong><small>{claim.policy_version ?? "No version"}</small></div>
          <div><span>Product</span><strong>{displayLabel(claim.product_line)}</strong><small>{claim.jurisdiction}</small></div>
          <div><span>Incident date</span><strong>{claim.incident_date ?? "Not recorded"}</strong><small>Customer ref. {claim.customer_reference}</small></div>
          <div className="controlSummary"><span>Control boundary</span><strong><ShieldCheck size={12} /> Approval required</strong><small>Status-changing actions cannot auto-execute.</small></div>
        </section>

        {error ? <div className="claimsError"><strong>Operation failed</strong><span>{error}</span></div> : null}

        <div className="claimColumns">
          <div className="claimPrimary">
            <section className="claimsPanel detailPanel">
              <div className="claimsPanelHeader"><div><h2>Submitted documents</h2><p>{documents.length} materials attached to this claim.</p></div></div>
              <div className="documentList">
                {documents.map((document) => <article key={document.id}><span className="documentIcon">DOC</span><div><strong>{document.filename}</strong><small>{displayLabel(document.document_type)}</small></div><span className="extractionStatus">{displayLabel(document.extraction_status)}</span></article>)}
                {!documents.length ? <p className="claimsMessage">No documents submitted.</p> : null}
              </div>
            </section>

            <section className="claimsPanel detailPanel">
              <div className="claimsPanelHeader"><div><h2>Decision support</h2><p>Document rules are checked before policy evidence is used for a recommendation.</p></div>{review ? <span className={`evidenceBadge evidence-${review.evidence_status}`}>{displayLabel(review.evidence_status)} evidence</span> : null}</div>
              {!review ? <div className="reviewEmpty"><strong>No case review in this session.</strong><p>Start a review to inspect missing materials, retrieved policy evidence, and the controlled next action.</p><button onClick={runReview} disabled={reviewing}>{reviewing ? "Review running…" : "Review case"}</button></div> : (
                <div className="reviewResult">
                  <div className="reviewLists"><div><h3>Present</h3>{review.present_documents.map((item) => <span className="docPill present" key={item}>✓ {displayLabel(item)}</span>)}</div><div><h3>Missing required</h3>{review.missing_documents.length ? review.missing_documents.map((item) => <span className="docPill missing" key={item}>! {displayLabel(item)}</span>) : <span className="docPill present">No required documents missing</span>}</div><div><h3>Conditional</h3>{review.conditional_documents.map((item) => <span className="docPill conditional" key={item}>{displayLabel(item)}</span>)}</div></div>
                  <div className="recommendation"><span>Decision support</span><p>{review.recommendation}</p><small>{review.evidence_reason}</small></div>
                  <div><h3>Evidence used</h3><div className="evidenceList">{review.evidence.length ? review.evidence.map((item) => <article key={`${item.source_id}-${item.title}`}><strong>{item.title}</strong><span>{item.source} · {item.source_id}</span>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">Open source ↗</a> : null}</article>) : <p className="claimsMessage">No qualifying policy evidence was used.</p>}</div></div>
                  <small className="runId">Run ID: {review.run_id}</small>
                </div>
              )}
            </section>
          </div>

          <aside className="claimActions">
            <div className="claimsPanelHeader"><div><h2>Controlled actions</h2><p>Each action is proposed, decided, and executed as a separate state.</p></div></div>
            {actions.map((action) => <ActionCard action={action} claimId={claimId} key={action.id} onChanged={loadClaim} />)}
            {!actions.length ? <div className="reviewEmpty compact"><strong>No actions proposed</strong><p>A review may produce an approval-bound action when follow-up is required.</p></div> : null}
          </aside>
        </div>
      </div>
    </OperationsShell>
  );
}
