"use client";

import { RefreshCw, ShieldCheck, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyWorkspace, HarnessBadge, OperationsPageHeader, OperationsShell } from "../components/operations-shell";
import { ClaimDetail, displayLabel, loadClaimsWithDetails } from "../claims/types";

type McpAuditLog = {
  id: number;
  server_name: string;
  tool_name: string;
  status: string;
  arguments: Record<string, unknown>;
  result_preview: string | null;
  error: string | null;
  created_at: string;
};

type AuditEntry = {
  id: string;
  category: "decision" | "tool";
  title: string;
  subject: string;
  status: string;
  actor: string;
  timestamp: string;
  detail: string;
};

function statusTone(status: string): "good" | "warn" | "bad" | "info" | "neutral" {
  const normalized = status.toUpperCase();
  if (["SUCCESS", "SUCCEEDED", "APPROVED"].includes(normalized)) return "good";
  if (["ERROR", "FAILED", "REJECTED", "VERIFICATION_FAILED"].includes(normalized)) return "bad";
  if (["PROPOSED", "WAITING_FOR_APPROVAL"].includes(normalized)) return "warn";
  if (["EXECUTING"].includes(normalized)) return "info";
  return "neutral";
}

export default function AuditPage() {
  const [claimDetails, setClaimDetails] = useState<ClaimDetail[]>([]);
  const [toolLogs, setToolLogs] = useState<McpAuditLog[]>([]);
  const [filter, setFilter] = useState<"all" | "decision" | "tool">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [details, auditResponse] = await Promise.all([
        loadClaimsWithDetails(),
        fetch("/api/mcp/audit", { cache: "no-store" })
      ]);
      if (!auditResponse.ok) throw new Error(`MCP audit request failed (${auditResponse.status})`);
      const payload = (await auditResponse.json()) as { audit_logs: McpAuditLog[] };
      setClaimDetails(details);
      setToolLogs(payload.audit_logs);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load audit activity");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const entries = useMemo<AuditEntry[]>(() => {
    const decisions: AuditEntry[] = claimDetails.flatMap((detail) =>
      detail.proposed_actions.map((action) => ({
        id: `action:${action.id}`,
        category: "decision" as const,
        title: displayLabel(action.action_type),
        subject: detail.claim.customer_reference,
        status: action.status,
        actor: action.approved_by ? action.approved_by.slice(0, 12) : action.proposed_by,
        timestamp: action.updated_at,
        detail: `${action.tool_server} / ${action.tool_name}`
      }))
    );
    const tools: AuditEntry[] = toolLogs.map((log) => ({
      id: `tool:${log.id}`,
      category: "tool",
      title: log.tool_name,
      subject: log.server_name,
      status: log.status,
      actor: "MCP runtime",
      timestamp: log.created_at,
      detail: log.error || log.result_preview || JSON.stringify(log.arguments)
    }));
    return [...decisions, ...tools].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  }, [claimDetails, toolLogs]);
  const visible = filter === "all" ? entries : entries.filter((entry) => entry.category === filter);

  return (
    <OperationsShell active="audit">
      <OperationsPageHeader
        actions={
          <button className="opsSecondaryButton" disabled={loading} onClick={() => void load()} type="button">
            <RefreshCw size={14} /> Refresh
          </button>
        }
        description="Review decisions and MCP tool calls retained by the current system."
        eyebrow="Governance"
        title="Audit activity"
      />

      <div className="opsPageContent">
        <section className="opsMetrics">
          <article><span>Recorded activity</span><strong>{entries.length}</strong></article>
          <article><span>Action states</span><strong>{entries.filter((entry) => entry.category === "decision").length}</strong></article>
          <article><span>Tool calls</span><strong>{entries.filter((entry) => entry.category === "tool").length}</strong></article>
          <article><span>Failures</span><strong>{entries.filter((entry) => statusTone(entry.status) === "bad").length}</strong></article>
        </section>

        <section className="opsPanel">
          <header className="opsPanelHeader">
            <div><h2>Activity ledger</h2><p>Latest persisted state per controlled action plus append-only MCP call records.</p></div>
            <div className="opsTabs">
              {(["all", "decision", "tool"] as const).map((value) => (
                <button className={filter === value ? "active" : ""} key={value} onClick={() => setFilter(value)} type="button">
                  {displayLabel(value)}
                </button>
              ))}
            </div>
          </header>
          {error ? <div className="opsInlineError"><span>{error}</span></div> : null}
          {loading ? <p className="opsLoading">Loading audit activity…</p> : null}
          {!loading && !visible.length ? (
            <EmptyWorkspace title="No audit activity in this view" description="Approval decisions and MCP tool calls will appear as the controlled workflow is exercised." />
          ) : null}

          <div className="auditTimeline">
            {visible.map((entry) => (
              <article key={entry.id}>
                <span className={`auditIcon ${entry.category}`}>
                  {entry.category === "decision" ? <ShieldCheck size={14} /> : <Wrench size={14} />}
                </span>
                <div className="auditPrimary">
                  <strong>{entry.title}</strong>
                  <span>{entry.subject} · {entry.detail}</span>
                </div>
                <div className="auditActor">
                  <span>{entry.actor}</span>
                  <time>{new Date(entry.timestamp).toLocaleString("de-DE")}</time>
                </div>
                <HarnessBadge tone={statusTone(entry.status)}>{displayLabel(entry.status)}</HarnessBadge>
              </article>
            ))}
          </div>
        </section>
      </div>
    </OperationsShell>
  );
}
