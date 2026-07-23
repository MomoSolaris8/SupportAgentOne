"use client";

import { Check, RefreshCw, ShieldAlert, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyWorkspace, HarnessBadge, OperationsPageHeader, OperationsShell } from "../components/operations-shell";
import { Claim, ClaimDetail, ProposedAction, displayLabel, loadClaimsWithDetails, readApiError } from "../claims/types";

type ApprovalItem = {
  claim: Claim;
  action: ProposedAction;
};

function actionTone(status: string): "good" | "warn" | "bad" | "info" | "neutral" {
  if (status === "APPROVED" || status === "SUCCEEDED") return "good";
  if (status === "REJECTED" || status === "FAILED" || status === "VERIFICATION_FAILED") return "bad";
  if (status === "PROPOSED" || status === "WAITING_FOR_APPROVAL") return "warn";
  if (status === "EXECUTING") return "info";
  return "neutral";
}

export default function ApprovalsPage() {
  const [details, setDetails] = useState<ClaimDetail[]>([]);
  const [filter, setFilter] = useState<"pending" | "decided" | "all">("pending");
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setDetails(await loadClaimsWithDetails());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load approval queue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const items = useMemo<ApprovalItem[]>(
    () =>
      details.flatMap((detail) =>
        detail.proposed_actions.map((action) => ({ claim: detail.claim, action }))
      ),
    [details]
  );
  const pendingStatuses = new Set(["PROPOSED", "WAITING_FOR_APPROVAL"]);
  const visible = items.filter(({ action }) => {
    if (filter === "pending") return pendingStatuses.has(action.status);
    if (filter === "decided") return !pendingStatuses.has(action.status);
    return true;
  });
  const pendingCount = items.filter(({ action }) => pendingStatuses.has(action.status)).length;

  async function decide(item: ApprovalItem, decision: "approve" | "reject") {
    const verb = decision === "approve" ? "approve" : "reject";
    if (!window.confirm(`${displayLabel(verb)} ${displayLabel(item.action.action_type)} for ${item.claim.customer_reference}?`)) {
      return;
    }
    setBusyAction(item.action.id);
    setError(null);
    try {
      const response = await fetch(
        `/api/claims/${item.claim.id}/actions/${item.action.id}/${decision}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ comment: `${displayLabel(decision)}d in approval queue` })
        }
      );
      if (!response.ok) throw new Error(await readApiError(response));
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Decision failed");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <OperationsShell active="approvals">
      <OperationsPageHeader
        actions={
          <button className="opsSecondaryButton" disabled={loading} onClick={() => void load()} type="button">
            <RefreshCw size={14} /> Refresh
          </button>
        }
        description="Human decisions for actions proposed by the claim review workflow."
        eyebrow="Control plane"
        title="Approval queue"
      />

      <div className="opsPageContent">
        <section className="opsMetrics">
          <article><span>Pending decisions</span><strong>{pendingCount}</strong></article>
          <article><span>Approved</span><strong>{items.filter(({ action }) => action.status === "APPROVED").length}</strong></article>
          <article><span>Rejected</span><strong>{items.filter(({ action }) => action.status === "REJECTED").length}</strong></article>
        </section>

        <section className="opsPanel">
          <header className="opsPanelHeader">
            <div><h2>Controlled actions</h2><p>Approval applies only to the immutable action shown below.</p></div>
            <div className="opsTabs">
              {(["pending", "decided", "all"] as const).map((value) => (
                <button className={filter === value ? "active" : ""} key={value} onClick={() => setFilter(value)} type="button">
                  {displayLabel(value)}
                </button>
              ))}
            </div>
          </header>

          {error ? <div className="opsInlineError"><ShieldAlert size={15} /><span>{error}</span></div> : null}
          {loading ? <p className="opsLoading">Loading approval queue…</p> : null}
          {!loading && !visible.length ? (
            <EmptyWorkspace
              title={filter === "pending" ? "No actions are waiting for approval" : "No actions match this view"}
              description="Proposed actions appear here after a claim review identifies a controlled operational next step."
            />
          ) : null}

          <div className="approvalList">
            {visible.map((item) => {
              const pending = pendingStatuses.has(item.action.status);
              return (
                <article className="approvalRow" key={item.action.id}>
                  <div className="approvalIdentity">
                    <span className={`approvalRisk ${item.action.risk_level}`}>{item.action.risk_level}</span>
                    <div>
                      <a href={`/claims/${item.claim.id}`}>{item.claim.customer_reference}</a>
                      <small>{item.claim.policy_id} · {displayLabel(item.claim.claim_type)}</small>
                    </div>
                  </div>
                  <div className="approvalAction">
                    <strong>{displayLabel(item.action.action_type)}</strong>
                    <span>{item.action.reason}</span>
                    <code>{item.action.tool_server} / {item.action.tool_name}</code>
                  </div>
                  <HarnessBadge tone={actionTone(item.action.status)}>{displayLabel(item.action.status)}</HarnessBadge>
                  <div className="approvalDecision">
                    {pending ? (
                      <>
                        <button
                          className="approve"
                          disabled={busyAction === item.action.id}
                          onClick={() => void decide(item, "approve")}
                          title="Approve action"
                          type="button"
                        >
                          <Check size={14} /> Approve
                        </button>
                        <button
                          className="reject"
                          disabled={busyAction === item.action.id}
                          onClick={() => void decide(item, "reject")}
                          title="Reject action"
                          type="button"
                        >
                          <X size={14} /> Reject
                        </button>
                      </>
                    ) : (
                      <span className="approvalActor">
                        {item.action.approved_by ? `Decided by ${item.action.approved_by.slice(0, 8)}` : "Decision recorded"}
                      </span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </OperationsShell>
  );
}
