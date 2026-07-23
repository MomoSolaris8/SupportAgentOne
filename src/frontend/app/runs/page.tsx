"use client";

import { Activity, ArrowUpRight, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyWorkspace, HarnessBadge, OperationsPageHeader, OperationsShell } from "../components/operations-shell";
import { Claim, ClaimDetail, ProposedAction, displayLabel, loadClaimsWithDetails } from "../claims/types";

type RunIndexItem = {
  runId: string;
  claim: Claim;
  actions: ProposedAction[];
  createdAt: string;
};

function runTone(actions: ProposedAction[]): "good" | "warn" | "bad" | "info" {
  if (actions.some((action) => action.status === "FAILED" || action.status === "VERIFICATION_FAILED")) return "bad";
  if (actions.some((action) => action.status === "EXECUTING")) return "info";
  if (actions.some((action) => action.status === "PROPOSED" || action.status === "WAITING_FOR_APPROVAL")) return "warn";
  return "good";
}

function runStatus(actions: ProposedAction[]) {
  if (actions.some((action) => action.status === "FAILED")) return "Execution failed";
  if (actions.some((action) => action.status === "VERIFICATION_FAILED")) return "Verification failed";
  if (actions.some((action) => action.status === "EXECUTING")) return "Executing";
  if (actions.some((action) => action.status === "PROPOSED" || action.status === "WAITING_FOR_APPROVAL")) return "Awaiting decision";
  if (actions.some((action) => action.status === "APPROVED")) return "Approved";
  if (actions.every((action) => action.status === "REJECTED")) return "Rejected";
  return "Recorded";
}

export default function RunsPage() {
  const [details, setDetails] = useState<ClaimDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setDetails(await loadClaimsWithDetails());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load runs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const runs = useMemo<RunIndexItem[]>(() => {
    const index = new Map<string, RunIndexItem>();
    for (const detail of details) {
      for (const action of detail.proposed_actions) {
        if (!action.run_id) continue;
        const existing = index.get(action.run_id);
        if (existing) {
          existing.actions.push(action);
        } else {
          index.set(action.run_id, {
            runId: action.run_id,
            claim: detail.claim,
            actions: [action],
            createdAt: action.created_at
          });
        }
      }
    }
    return [...index.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, [details]);

  return (
    <OperationsShell active="runs">
      <OperationsPageHeader
        actions={
          <button className="opsSecondaryButton" disabled={loading} onClick={() => void load()} type="button">
            <RefreshCw size={14} /> Refresh
          </button>
        }
        description="Persisted review outputs and their downstream action state."
        eyebrow="Harness"
        title="Agent runs"
      />

      <div className="opsPageContent">
        <section className="opsMetrics">
          <article><span>Indexed runs</span><strong>{runs.length}</strong></article>
          <article><span>Awaiting decision</span><strong>{runs.filter((run) => runStatus(run.actions) === "Awaiting decision").length}</strong></article>
          <article><span>Execution failures</span><strong>{runs.filter((run) => runTone(run.actions) === "bad").length}</strong></article>
        </section>

        <section className="opsPanel">
          <header className="opsPanelHeader">
            <div><h2>Run index</h2><p>One review run may produce one or more controlled actions.</p></div>
            <HarnessBadge tone="info">Partial tracing</HarnessBadge>
          </header>
          <div className="opsCoverageNotice">
            <Activity size={15} />
            <p>
              The current schema retains a run ID with each proposed action. Node-level timings and transitions are not yet persisted.
            </p>
          </div>
          {error ? <div className="opsInlineError"><span>{error}</span></div> : null}
          {loading ? <p className="opsLoading">Loading run index…</p> : null}
          {!loading && !runs.length ? (
            <EmptyWorkspace
              title="No persisted review runs"
              description="A run appears after a claim review produces a controlled action with a run ID."
            />
          ) : null}

          <div className="runList">
            {runs.map((run) => (
              <article className="runRow" key={run.runId}>
                <div className="runMarker"><Activity size={14} /></div>
                <div className="runIdentity">
                  <code>{run.runId}</code>
                  <span>{new Date(run.createdAt).toLocaleString("de-DE")}</span>
                </div>
                <div className="runClaim">
                  <strong>{run.claim.customer_reference}</strong>
                  <span>{run.claim.policy_id} · {displayLabel(run.claim.claim_type)}</span>
                </div>
                <div className="runOutput">
                  <strong>{run.actions.length} controlled action{run.actions.length === 1 ? "" : "s"}</strong>
                  <span>{run.actions.map((action) => displayLabel(action.action_type)).join(", ")}</span>
                </div>
                <HarnessBadge tone={runTone(run.actions)}>{runStatus(run.actions)}</HarnessBadge>
                <a className="runOpen" href={`/claims/${run.claim.id}`} title="Open claim">
                  <ArrowUpRight size={14} />
                </a>
              </article>
            ))}
          </div>
        </section>
      </div>
    </OperationsShell>
  );
}
