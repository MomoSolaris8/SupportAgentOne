"use client";

import {
  Activity,
  Bot,
  Braces,
  CheckSquare,
  ChevronLeft,
  CircleUserRound,
  ClipboardList,
  FileCheck2,
  LogOut,
  Menu,
  MessageSquareText,
  PlugZap,
  Send,
  ShieldCheck,
  X
} from "lucide-react";
import { FormEvent, PointerEvent as ReactPointerEvent, ReactNode, useEffect, useRef, useState } from "react";
import { MarkdownText } from "./markdown-text";

type NavigationKey = "claims" | "approvals" | "runs" | "integrations" | "audit";

type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
};

type ClaimContext = {
  id: string;
  customerReference: string;
  policyId: string;
  claimType: string;
};

type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: string;
  error?: boolean;
};

type AskResponse = {
  answer: string;
  sources: Array<{ title: string; source: string }>;
  trace: {
    route_source: string;
    evidence_status: string;
    mcp_tool_calls: Array<{ server: string; tool: string }>;
  };
};

type OperationsShellProps = {
  active: NavigationKey;
  children: ReactNode;
  claimContext?: ClaimContext;
};

const navigation = [
  {
    label: "Business",
    items: [
      { key: "claims" as const, label: "Claims", href: "/claims", icon: ClipboardList },
      { key: "approvals" as const, label: "Approvals", href: "/approvals", icon: CheckSquare }
    ]
  },
  {
    label: "Harness",
    items: [
      { key: "runs" as const, label: "Runs", href: "/runs", icon: Activity },
      { key: "integrations" as const, label: "Integrations", href: "/integrations", icon: PlugZap },
      { key: "audit" as const, label: "Audit", href: "/audit", icon: FileCheck2 }
    ]
  }
];

function CaseAssistant({ claimContext, onClose }: { claimContext?: ClaimContext; onClose: () => void }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storageKey = claimContext
      ? `supportagent.claim-assistant.${claimContext.id}`
      : "supportagent.operations-assistant";
    const stored = window.localStorage.getItem(storageKey);
    const next = stored ?? crypto.randomUUID();
    if (!stored) window.localStorage.setItem(storageKey, next);
    setThreadId(next);
    setMessages([]);
  }, [claimContext?.id]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading || !threadId) return;

    const userMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    const contextualQuestion = claimContext
      ? [
          `Aktueller Schadenfall: ${claimContext.customerReference}`,
          `Claim-ID: ${claimContext.id}`,
          `Police: ${claimContext.policyId}`,
          `Schadenart: ${claimContext.claimType}`,
          "",
          `Frage des Sachbearbeiters: ${trimmed}`
        ].join("\n")
      : trimmed;

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question: contextualQuestion,
          source: "confluence",
          thread_id: threadId,
          enabled_mcp_servers: [],
          enabled_skills: []
        })
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? `Request failed (${response.status})`);
      }
      const payload = (await response.json()) as AskResponse;
      const toolCount = payload.trace.mcp_tool_calls.length;
      const sourceLabel = payload.trace.evidence_status === "insufficient"
        ? payload.sources.length
          ? `Insufficient evidence · ${payload.sources.length} candidates reviewed`
          : "Insufficient evidence"
        : payload.sources.length
          ? `${payload.sources.length} evidence source${payload.sources.length === 1 ? "" : "s"}`
          : payload.trace.evidence_status;
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: payload.answer,
          meta: toolCount ? `${sourceLabel} · ${toolCount} tool call${toolCount === 1 ? "" : "s"}` : sourceLabel
        }
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: error instanceof Error ? error.message : "The assistant request failed.",
          error: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="opsAssistant" aria-label="Case assistant">
      <header className="opsAssistantHeader">
        <div className="opsAssistantIdentity">
          <span className="opsIconTile"><Bot size={16} /></span>
          <div>
            <strong>{claimContext ? "Case assistant" : "Operations assistant"}</strong>
            <span>{claimContext ? claimContext.customerReference : "Evidence-bound guidance"}</span>
          </div>
        </div>
        <button className="opsIconButton" onClick={onClose} title="Close assistant" type="button">
          <X size={16} />
        </button>
      </header>

      {claimContext ? (
        <div className="opsAssistantContext">
          <span>Active case</span>
          <strong>{claimContext.customerReference}</strong>
          <small>{claimContext.policyId} · {claimContext.claimType}</small>
        </div>
      ) : null}

      <div className="opsAssistantLog" ref={logRef}>
        {!messages.length ? (
          <div className="opsAssistantEmpty">
            <MessageSquareText size={20} />
            <strong>Ask about the active case</strong>
            <p>
              Answers are constrained by approved policy evidence. Operational actions remain in the approval workflow.
            </p>
          </div>
        ) : null}
        {messages.map((message) => (
          <article className={`opsAssistantMessage ${message.role} ${message.error ? "error" : ""}`} key={message.id}>
            <span>{message.role === "user" ? "You" : "SupportAgent"}</span>
            {message.role === "assistant" ? <MarkdownText text={message.content} /> : <p>{message.content}</p>}
            {message.meta ? <small>{message.meta}</small> : null}
          </article>
        ))}
        {loading ? (
          <article className="opsAssistantMessage assistant loading">
            <span>SupportAgent</span>
            <p>Reviewing available evidence…</p>
          </article>
        ) : null}
      </div>

      <form className="opsAssistantComposer" onSubmit={submit}>
        <textarea
          aria-label="Ask the case assistant"
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder={claimContext ? "Ask about this claim…" : "Ask about claims operations…"}
          rows={2}
          value={question}
        />
        <button disabled={loading || !question.trim()} title="Send message" type="submit">
          <Send size={16} />
        </button>
      </form>
      <footer className="opsAssistantFooter">
        <ShieldCheck size={13} />
        Evidence-bound · No status changes
      </footer>
    </aside>
  );
}

export function OperationsShell({ active, children, claimContext }: OperationsShellProps) {
  const [assistantOpen, setAssistantOpen] = useState(true);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [assistantWidth, setAssistantWidth] = useState(360);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then(async (response) => (response.ok ? ((await response.json()) as AuthUser) : null))
      .then(setUser)
      .catch(() => setUser(null));

    if (window.matchMedia("(max-width: 860px)").matches) {
      setAssistantOpen(false);
    }
  }, []);

  function startResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = assistantWidth;

    function move(pointerEvent: PointerEvent) {
      setAssistantWidth(Math.min(520, Math.max(300, startWidth + startX - pointerEvent.clientX)));
    }

    function stop() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      document.body.classList.remove("opsResizing");
    }

    document.body.classList.add("opsResizing");
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/";
  }

  return (
    <div
      className={`opsShell ${assistantOpen ? "" : "assistantClosed"} ${navigationOpen ? "navigationOpen" : ""}`}
      style={{ "--ops-assistant-width": `${assistantWidth}px` } as React.CSSProperties}
    >
      <button className="opsMobileMenu" onClick={() => setNavigationOpen(true)} title="Open navigation" type="button">
        <Menu size={18} />
      </button>

      <aside className="opsNavigation">
        <div className="opsBrand">
          <span>SA</span>
          <div>
            <strong>SupportAgent</strong>
            <small>Claims Control</small>
          </div>
          <button className="opsMobileClose" onClick={() => setNavigationOpen(false)} title="Close navigation" type="button">
            <X size={16} />
          </button>
        </div>

        <div className="opsEnvironment">
          <span><i /> Controlled workspace</span>
          <small>Synthetic training data</small>
        </div>

        <nav className="opsNavGroups" aria-label="Primary navigation">
          {navigation.map((group) => (
            <section key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <a className={active === item.key ? "active" : ""} href={item.href} key={item.key}>
                    <Icon size={16} />
                    <span>{item.label}</span>
                  </a>
                );
              })}
            </section>
          ))}
        </nav>

        <div className="opsControlBoundary">
          <ShieldCheck size={16} />
          <div>
            <strong>Human control</strong>
            <p>Actions require an explicit decision before execution.</p>
          </div>
        </div>

        <div className="opsAccount">
          <CircleUserRound size={18} />
          <div>
            <strong>{user?.display_name || "Claims operator"}</strong>
            <span>{user?.email || "Local account"}</span>
          </div>
          <button onClick={logout} title="Sign out" type="button"><LogOut size={15} /></button>
        </div>
      </aside>

      <button className="opsNavigationBackdrop" onClick={() => setNavigationOpen(false)} type="button" />

      <main className="opsWorkspace">{children}</main>

      {assistantOpen ? (
        <>
          <div
            aria-label="Resize assistant"
            className="opsAssistantResizer"
            onPointerDown={startResize}
            role="separator"
          />
          <CaseAssistant claimContext={claimContext} onClose={() => setAssistantOpen(false)} />
        </>
      ) : (
        <button className="opsAssistantReopen" onClick={() => setAssistantOpen(true)} type="button">
          <Bot size={16} />
          <span>Assistant</span>
          <ChevronLeft size={14} />
        </button>
      )}
    </div>
  );
}

export function OperationsPageHeader({
  eyebrow,
  title,
  description,
  actions
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="opsPageHeader">
      <div>
        <p>{eyebrow}</p>
        <h1>{title}</h1>
        {description ? <span>{description}</span> : null}
      </div>
      {actions ? <div className="opsPageActions">{actions}</div> : null}
    </header>
  );
}

export function HarnessBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" | "info" }) {
  return <span className={`harnessBadge ${tone}`}>{children}</span>;
}

export function EmptyWorkspace({
  icon = "activity",
  title,
  description
}: {
  icon?: "activity" | "integration";
  title: string;
  description: string;
}) {
  return (
    <div className="opsEmptyWorkspace">
      {icon === "integration" ? <Braces size={20} /> : <Activity size={20} />}
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
