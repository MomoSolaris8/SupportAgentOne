"use client";

import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock3,
  FileCheck2,
  Play,
  Send,
  ShieldCheck
} from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { HarnessBadge, OperationsPageHeader, OperationsShell } from "../../components/operations-shell";
import {
  ClaimDetail,
  ClaimReview,
  ClaimReviewRun,
  ClaimSubmission,
  ProposedAction,
  displayLabel,
  readApiError
} from "../types";

const REVIEW_STEPS = [
  ["LOAD_CLAIM", "Load claim"],
  ["CHECK_DOCUMENTS", "Validate required documents"],
  ["RETRIEVE_POLICY_EVIDENCE", "Retrieve policy evidence"],
  ["VERIFY_EVIDENCE", "Verify approved sources"],
  ["GENERATE_RECOMMENDATION", "Generate recommendation"],
  ["PREPARE_NEXT_ACTION", "Prepare next action"],
  ["COMPLETED", "Complete review"]
] as const;

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

function ReviewProgress({ run }: { run: ClaimReviewRun }) {
  const currentIndex = REVIEW_STEPS.findIndex(([step]) => step === run.current_step);
  const allComplete = run.status === "SUCCEEDED";

  return (
    <div className={`claimReviewProgress ${run.status.toLowerCase()}`}>
      <header>
        <div>
          <span>Review run</span>
          <strong>{run.status === "FAILED" ? "Review failed" : allComplete ? "Review completed" : "Review in progress"}</strong>
        </div>
        <em>{displayLabel(run.status)}</em>
      </header>
      <ol>
        {REVIEW_STEPS.map(([step, label], index) => {
          const complete = allComplete || currentIndex > index;
          const active = run.status === "RUNNING" && currentIndex === index;
          return (
            <li className={complete ? "complete" : active ? "active" : ""} key={step}>
              {complete ? <CheckCircle2 size={14} /> : active ? <Clock3 size={14} /> : <Circle size={14} />}
              <span>{label}</span>
            </li>
          );
        })}
      </ol>
      {run.error ? <p>{run.error}</p> : null}
      <small>Run ID: {run.id}</small>
    </div>
  );
}

export default function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>();
  const [detail, setDetail] = useState<ClaimDetail | null>(null);
  const [review, setReview] = useState<ClaimReview | null>(null);
  const [activeRun, setActiveRun] = useState<ClaimReviewRun | null>(null);
  const [submission, setSubmission] = useState<ClaimSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [nextStepBusy, setNextStepBusy] = useState(false);
  const [decisionDraft, setDecisionDraft] = useState<"APPROVE" | "REJECT" | null>(null);
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadClaim = useCallback(async () => {
    const response = await fetch(`/api/claims/${claimId}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await readApiError(response));
    const payload = (await response.json()) as ClaimDetail;
    setDetail(payload);
    setReview(payload.latest_review_run?.result ?? null);
    setActiveRun(payload.latest_review_run);
    setReviewing(payload.latest_review_run?.status === "RUNNING" || payload.latest_review_run?.status === "QUEUED");
  }, [claimId]);

  useEffect(() => {
    loadClaim()
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load claim"))
      .finally(() => setLoading(false));
  }, [loadClaim]);

  useEffect(() => {
    if (!activeRun || !["QUEUED", "RUNNING"].includes(activeRun.status)) return;
    let cancelled = false;

    async function poll() {
      const response = await fetch(`/api/claims/${claimId}/review-runs/${activeRun!.id}`, { cache: "no-store" });
      if (!response.ok || cancelled) return;
      const run = (await response.json()) as ClaimReviewRun;
      if (cancelled) return;
      setActiveRun(run);
      if (run.status === "SUCCEEDED" || run.status === "FAILED") {
        setReview(run.result);
        setReviewing(false);
        await loadClaim();
      }
    }

    void poll();
    const timer = window.setInterval(() => void poll(), 800);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [activeRun?.id, activeRun?.status, claimId, loadClaim]);

  async function submitForReview() {
    setSubmitting(true);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });
    if (!response.ok) {
      setError(await readApiError(response));
      setSubmitting(false);
      return;
    }
    setSubmission((await response.json()) as ClaimSubmission);
    await loadClaim();
    setSubmitting(false);
  }

  async function runReview() {
    setReviewing(true);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });
    if (!response.ok) {
      setError(await readApiError(response));
      setReviewing(false);
      return;
    }
    const run = (await response.json()) as ClaimReviewRun;
    setActiveRun(run);
    await loadClaim();
  }

  async function selectNextStep(nextStep: "REQUEST_INFORMATION" | "ESCALATE_TO_EXPERT") {
    if (!window.confirm(`Select next step: ${displayLabel(nextStep)}? This change will be audited.`)) return;
    setNextStepBusy(true);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/next-step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ next_step: nextStep })
    });
    if (!response.ok) {
      setError(await readApiError(response));
      setNextStepBusy(false);
      return;
    }
    await loadClaim();
    setNextStepBusy(false);
  }

  async function recordHumanDecision() {
    if (!decisionDraft) return;
    if (decisionDraft === "REJECT" && !decisionReason.trim()) return;
    setDecisionBusy(true);
    setError(null);
    const response = await fetch(`/api/claims/${claimId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: decisionDraft,
        reason: decisionReason.trim() || null
      })
    });
    if (!response.ok) {
      setError(await readApiError(response));
      setDecisionBusy(false);
      return;
    }
    setDecisionDraft(null);
    setDecisionReason("");
    await loadClaim();
    setDecisionBusy(false);
  }

  if (loading) return <main className="claimDetailLoading">Loading claim…</main>;
  if (!detail) return <main className="claimDetailLoading"><strong>Claim unavailable.</strong><p>{error}</p><a href="/claims">Return to claims</a></main>;

  const { claim, documents, proposed_actions, audit_events } = detail;
  const actions = review?.proposed_action && !proposed_actions.some((item) => item.id === review.proposed_action?.id) ? [review.proposed_action, ...proposed_actions] : proposed_actions;
  const canSubmit = ["DRAFT", "DOCUMENTS_PENDING", "NEEDS_INFORMATION"].includes(claim.status);
  const canReview = claim.status === "READY_FOR_REVIEW";

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
            <HarnessBadge tone={["DOCUMENTS_PENDING", "NEEDS_INFORMATION"].includes(claim.status) ? "warn" : "info"}>{displayLabel(claim.status)}</HarnessBadge>
            {canSubmit ? (
              <button className="opsPrimaryButton" onClick={submitForReview} disabled={submitting} type="button">
                <Send size={13} /> {submitting ? "Validating documents…" : claim.status === "DRAFT" ? "Submit for review" : "Recheck documents"}
              </button>
            ) : null}
            {canReview ? (
              <button className="opsPrimaryButton" onClick={runReview} disabled={reviewing} type="button">
                <Play size={13} /> {reviewing ? "Review running…" : "Review case"}
              </button>
            ) : null}
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
          <div className="controlSummary"><span>Current lifecycle state</span><strong><ShieldCheck size={12} /> {displayLabel(claim.status)}</strong><small>Every transition is persisted in the audit trail.</small></div>
        </section>

        {error ? <div className="claimsError"><strong>Operation failed</strong><span>{error}</span></div> : null}
        {submission ? (
          <div className={`claimSubmissionResult ${submission.missing_documents.length ? "pending" : "ready"}`}>
            <FileCheck2 size={17} />
            <div>
              <strong>{submission.missing_documents.length ? "Documents still required" : "Claim ready for review"}</strong>
              <span>
                {submission.present_documents.length} completed · {submission.missing_documents.length} missing
              </span>
            </div>
          </div>
        ) : null}

        <div className="claimColumns">
          <div className="claimPrimary">
            <section className="claimsPanel detailPanel">
              <div className="claimsPanelHeader"><div><h2>Submitted documents</h2><p>{documents.length} materials attached to this claim.</p></div></div>
              <div className="documentList">
                {documents.map((document) => {
                  const synthetic = document.extracted_fields.synthetic === true;
                  return (
                    <article key={document.id}>
                      <span className="documentIcon">{document.document_type.includes("photo") ? "IMG" : "DOC"}</span>
                      <div className="documentMeta">
                        <strong>{document.filename}</strong>
                        <small>{displayLabel(document.document_type)}</small>
                        {synthetic ? <em>Synthetic fixture · metadata only, no binary file attached</em> : null}
                      </div>
                      <div className="documentControls">
                        <span className="extractionStatus">{displayLabel(document.extraction_status)}</span>
                        {document.uploaded_file_id ? (
                          <a href={`/api/uploads/image/${document.uploaded_file_id}`} target="_blank" rel="noreferrer">Open file ↗</a>
                        ) : (
                          <small>No preview</small>
                        )}
                      </div>
                    </article>
                  );
                })}
                {!documents.length ? <p className="claimsMessage">No documents submitted.</p> : null}
              </div>
            </section>

            <section className="claimsPanel detailPanel">
              <div className="claimsPanelHeader"><div><h2>Decision support</h2><p>Document rules are checked before policy evidence is used for a recommendation.</p></div>{review ? <span className={`evidenceBadge evidence-${review.evidence_status}`}>{displayLabel(review.evidence_status)} evidence</span> : null}</div>
              {activeRun ? <ReviewProgress run={activeRun} /> : null}
              {!review && !activeRun ? (
                <div className="reviewEmpty">
                  <strong>{claim.status === "DRAFT" ? "Submit this draft before review." : claim.status === "DOCUMENTS_PENDING" ? "Required documents are still missing." : "No completed review is available."}</strong>
                  <p>The review becomes available only after deterministic document validation marks the claim ready.</p>
                  {canSubmit ? <button onClick={submitForReview} disabled={submitting}>{submitting ? "Validating…" : "Validate submission"}</button> : null}
                  {canReview ? <button onClick={runReview} disabled={reviewing}>{reviewing ? "Review running…" : "Review case"}</button> : null}
                </div>
              ) : null}
              {review ? (
                <div className="reviewResult">
                  <div className="reviewLists"><div><h3>Present</h3>{review.present_documents.map((item) => <span className="docPill present" key={item}>✓ {displayLabel(item)}</span>)}</div><div><h3>Missing required</h3>{review.missing_documents.length ? review.missing_documents.map((item) => <span className="docPill missing" key={item}>! {displayLabel(item)}</span>) : <span className="docPill present">No required documents missing</span>}</div><div><h3>Conditional</h3>{review.conditional_documents.map((item) => <span className="docPill conditional" key={item}>{displayLabel(item)}</span>)}</div></div>
                  <div className="recommendation"><span>Decision support</span><p>{review.recommendation}</p><small>{review.evidence_reason}</small></div>
                  <div><h3>Evidence used</h3><div className="evidenceList">{review.evidence.length ? review.evidence.map((item) => <article key={`${item.source_id}-${item.title}`}><strong>{item.title}</strong><span>{item.source} · {item.source_id}</span>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">Open source ↗</a> : null}</article>) : <p className="claimsMessage">No qualifying policy evidence was used.</p>}</div></div>
                  <small className="runId">Run ID: {review.run_id}</small>
                </div>
              ) : null}
            </section>
          </div>

          <aside className="claimActions">
            <div className="claimsPanelHeader"><div><h2>Controlled actions</h2><p>Choose the next business step after reviewing the evidence.</p></div></div>
            {claim.status === "READY_FOR_DECISION" ? (
              <article className="claimNextStepCard">
                <span>Human decision required</span>
                <h3>Record the claim decision</h3>
                <p>AI provided decision support only. Approval or rejection must be explicitly recorded by an authenticated human operator.</p>
                <button className="approveDecision" disabled={nextStepBusy} onClick={() => { setDecisionReason(""); setDecisionDraft("APPROVE"); }} type="button">Approve claim</button>
                <button className="rejectDecision" disabled={nextStepBusy} onClick={() => { setDecisionReason(""); setDecisionDraft("REJECT"); }} type="button">Reject claim</button>
                <div className="decisionDivider"><span>or choose a follow-up</span></div>
                <button disabled={nextStepBusy} onClick={() => selectNextStep("REQUEST_INFORMATION")} type="button">Request information</button>
                <button className="primary" disabled={nextStepBusy} onClick={() => selectNextStep("ESCALATE_TO_EXPERT")} type="button">Escalate to expert</button>
              </article>
            ) : null}
            {["APPROVED", "REJECTED"].includes(claim.status) ? (
              <div className={`claimFinalDecision ${claim.status.toLowerCase()}`}>
                <span>Human decision recorded</span>
                <strong>{displayLabel(claim.status)}</strong>
                <p>This terminal decision was made by a human operator and persisted in the audit trail.</p>
              </div>
            ) : null}
            {claim.status === "EXPERT_REVIEW_REQUIRED" ? (
              <div className="reviewEmpty compact"><strong>Expert review selected</strong><p>The handoff is recorded. A governed scheduling proposal can now be prepared as a separate action.</p></div>
            ) : null}
            {actions.map((action) => <ActionCard action={action} claimId={claimId} key={action.id} onChanged={loadClaim} />)}
            {!actions.length && claim.status !== "READY_FOR_DECISION" && claim.status !== "EXPERT_REVIEW_REQUIRED" ? <div className="reviewEmpty compact"><strong>No actions proposed</strong><p>Complete the review before selecting a controlled next step.</p></div> : null}
          </aside>
        </div>

        <section className="claimsPanel claimAuditPanel">
          <div className="claimsPanelHeader"><div><h2>Audit timeline</h2><p>Persistent lifecycle and review events for this claim.</p></div></div>
          <div className="claimAuditTimeline">
            {audit_events.map((event) => (
              <article key={event.id}>
                <i />
                <div>
                  <strong>{displayLabel(event.event_type)}</strong>
                  <span>{new Date(event.created_at).toLocaleString()}</span>
                  {"from" in event.payload && "to" in event.payload ? <p>{displayLabel(String(event.payload.from))} → {displayLabel(String(event.payload.to))}</p> : null}
                  {"step" in event.payload ? <p>{displayLabel(String(event.payload.step))}</p> : null}
                  {"decision" in event.payload ? <p>Human decision: {displayLabel(String(event.payload.decision))}</p> : null}
                  {"reason" in event.payload && event.payload.reason ? <p>Reason: {String(event.payload.reason)}</p> : null}
                </div>
              </article>
            ))}
            {!audit_events.length ? <p className="claimsMessage">No audit events recorded.</p> : null}
          </div>
        </section>
      </div>
      {decisionDraft ? (
        <div className="claimDecisionOverlay" role="presentation">
          <section aria-describedby="claim-decision-description" aria-labelledby="claim-decision-title" aria-modal="true" className="claimDecisionDialog" role="dialog">
            <span>Human-in-the-loop control</span>
            <h2 id="claim-decision-title">{decisionDraft === "APPROVE" ? "Approve this claim?" : "Reject this claim?"}</h2>
            <p id="claim-decision-description">
              {decisionDraft === "APPROVE"
                ? "You—not the AI—are confirming that this claim may proceed as approved."
                : "Rejection is a high-impact decision. Enter a clear reason before confirming."}
            </p>
            <label>
              {decisionDraft === "REJECT" ? "Rejection reason (required)" : "Decision note (optional)"}
              <textarea
                autoFocus
                onChange={(event) => setDecisionReason(event.target.value)}
                placeholder={decisionDraft === "REJECT" ? "Explain the policy or evidence basis for rejection…" : "Add an optional note for the audit trail…"}
                value={decisionReason}
              />
            </label>
            <div>
              <button className="cancel" disabled={decisionBusy} onClick={() => { setDecisionDraft(null); setDecisionReason(""); }} type="button">Cancel</button>
              <button
                className={decisionDraft === "APPROVE" ? "confirmApprove" : "confirmReject"}
                disabled={decisionBusy || (decisionDraft === "REJECT" && !decisionReason.trim())}
                onClick={recordHumanDecision}
                type="button"
              >
                {decisionBusy ? "Recording…" : decisionDraft === "APPROVE" ? "Confirm approval" : "Confirm rejection"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </OperationsShell>
  );
}
