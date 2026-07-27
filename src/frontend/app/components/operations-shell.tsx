"use client";

import {
  Activity,
  Bot,
  Braces,
  CalendarDays,
  CheckSquare,
  ChevronLeft,
  CircleUserRound,
  ClipboardList,
  Copy,
  FileCheck2,
  LogOut,
  Menu,
  MessageSquareText,
  Moon,
  Pencil,
  Plus,
  PlugZap,
  Send,
  ShieldCheck,
  Sun,
  X
} from "lucide-react";
import { FormEvent, PointerEvent as ReactPointerEvent, ReactNode, useEffect, useRef, useState } from "react";
import { LanguageSwitcher, useI18n } from "./i18n";
import { MarkdownText } from "./markdown-text";

type NavigationKey = "claims" | "approvals" | "runs" | "integrations" | "audit";
type ColorTheme = "light" | "dark";

const themeStorageKey = "supportagent.ui-theme";

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
  calendarAction?: CalendarEventAction;
  actionQuestion?: string;
  actionStatus?: "pending" | "running" | "done" | "cancelled" | "error";
};

type CalendarEventAction = {
  subject: string;
  date: string;
  startTime: string;
  endTime: string;
  timezone: string;
  participants?: string[];
  participantsText?: string;
  agenda?: string;
  body?: string;
  webLink?: string;
  reused?: boolean;
};

type StoredThreadMessage = {
  id: number | null;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

type ThreadMessagesResponse = {
  thread_id: string;
  messages: StoredThreadMessage[];
};

type ConversationThread = {
  thread_id: string;
  title: string;
  updated_at: string;
  message_count: number;
};

type ChatModel = {
  id: string;
  label: string;
  provider: string;
  capabilities: string[];
  description: string;
  default: boolean;
};

type AskResponse = {
  answer: string;
  sources: Array<{ title: string; source: string }>;
  trace: {
    route_source: string;
    evidence_status: string;
    mcp_tool_calls: Array<{ server: string; tool: string }>;
    model: string;
  };
};

type McpCallResponse = {
  server: string;
  tool: string;
  result: unknown;
  replayed?: boolean;
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

function displayQuestion(content: string) {
  const marker = "Frage des Sachbearbeiters:";
  const markerIndex = content.lastIndexOf(marker);
  return markerIndex >= 0 ? content.slice(markerIndex + marker.length).trim() : content;
}

function restoreAssistantMessages(storedMessages: StoredThreadMessage[]): AssistantMessage[] {
  let previousCalendarAction: CalendarEventAction | undefined;
  return storedMessages.map((message, index) => {
    const content = message.role === "user" ? displayQuestion(message.content) : message.content;
    if (message.role === "user") {
      previousCalendarAction = parseCalendarEventAction(content) ?? undefined;
      return {
        id: `stored-${message.id ?? message.created_at}-${index}`,
        role: message.role,
        content
      };
    }

    const storedAction = parseStoredCalendarAction(content, previousCalendarAction);
    previousCalendarAction = undefined;
    return {
      id: `stored-${message.id ?? message.created_at}-${index}`,
      role: message.role,
      content: storedAction ? "Microsoft Calendar action completed." : content,
      calendarAction: storedAction ?? undefined,
      actionStatus: storedAction ? "done" : undefined
    };
  });
}

function displayThreadTitle(title: string, locale: "de" | "en") {
  const casePrefix = "Aktueller Schadenfall:";
  if (!title.startsWith(casePrefix)) return title;
  const reference = title.slice(casePrefix.length).split("\n", 1)[0].trim();
  return `${locale === "de" ? "Fall" : "Case"} ${reference}`;
}

function assistantStorageKey(claimContext?: ClaimContext) {
  return claimContext
    ? `supportagent.claim-assistant.${claimContext.id}`
    : "supportagent.operations-assistant";
}

function CaseAssistant({
  claimContext,
  onClose,
  onConversationSaved,
  threadId
}: {
  claimContext?: ClaimContext;
  onClose: () => void;
  onConversationSaved: () => void;
  threadId: string | null;
}) {
  const { locale, t } = useI18n();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [models, setModels] = useState<ChatModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const composerManualHeightRef = useRef<number | null>(null);
  const calendarActionLocksRef = useRef(new Set<string>());

  useEffect(() => {
    const composer = composerRef.current;
    if (!composer) return;
    if (!question) composerManualHeightRef.current = null;

    const maxHeight = Math.max(180, Math.min(420, window.innerHeight * 0.48));
    composer.style.height = "auto";
    const contentHeight = composer.scrollHeight;
    const targetHeight = Math.min(
      maxHeight,
      Math.max(contentHeight, composerManualHeightRef.current ?? 0)
    );
    composer.style.height = `${targetHeight}px`;
    composer.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
  }, [question]);

  useEffect(() => {
    if (!threadId) return;

    const controller = new AbortController();
    setQuestion("");
    setMessages([]);
    setHistoryLoading(true);
    fetch(`/api/threads/${encodeURIComponent(threadId)}/messages`, {
      credentials: "include",
      signal: controller.signal
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`History request failed (${response.status})`);
        }
        return (await response.json()) as ThreadMessagesResponse;
      })
      .then((payload) => setMessages(restoreAssistantMessages(payload.messages)))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setMessages([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setHistoryLoading(false);
      });

    return () => controller.abort();
  }, [threadId]);

  useEffect(() => {
    fetch("/api/models", { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) return { models: [] as ChatModel[] };
        return (await response.json()) as { models: ChatModel[] };
      })
      .then((payload) => {
        setModels(payload.models);
        const defaultModel = payload.models.find((model) => model.default) ?? payload.models[0];
        if (defaultModel) setSelectedModel(defaultModel.id);
      })
      .catch(() => setModels([]));
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading || historyLoading || !threadId) return;

    const userMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");

    const calendarAction = parseCalendarEventAction(trimmed);
    if (calendarAction) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: t("Calendar action detected. Review the details before execution."),
          calendarAction,
          actionQuestion: trimmed,
          actionStatus: "pending"
        }
      ]);
      return;
    }

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
          model: selectedModel || undefined,
          enabled_mcp_servers: ["time_mcp"],
          enabled_skills: []
        })
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string; error?: { message?: string } }
          | null;
        throw new Error(
          payload?.error?.message ??
            payload?.detail ??
            `Request failed (${response.status})`
        );
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
      onConversationSaved();
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

  async function confirmCalendarAction(messageId: string, action: CalendarEventAction, actionQuestion: string) {
    if (!threadId) return;
    if (calendarActionLocksRef.current.has(messageId)) return;
    calendarActionLocksRef.current.add(messageId);
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, actionStatus: "running" } : message
      )
    );

    try {
      const transactionId = await calendarTransactionId(action);
      const response = await fetch("/api/mcp/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          server: "teams_mcp",
          tool: "create_default_calendar_event",
          arguments: {
            subject: action.subject,
            start_time: `${action.date}T${action.startTime}:00`,
            end_time: `${action.date}T${action.endTime}:00`,
            timezone: action.timezone,
            body: buildCalendarBody(action) || "Created by SupportAgent MCP.",
            attendees: (action.participants ?? []).filter((participant) => isEmail(participant)),
            transaction_id: transactionId
          },
          confirmed: true,
          thread_id: threadId,
          question: actionQuestion
        })
      });
      const payload = (await response.json().catch(() => null)) as
        | McpCallResponse
        | { detail?: string }
        | null;
      if (!response.ok || !payload || !("result" in payload)) {
        throw new Error(payload && "detail" in payload ? payload.detail : `Action failed (${response.status})`);
      }
      const result = parseMcpResult(payload.result);
      const webLink = typeof result?.webLink === "string" ? result.webLink : undefined;
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                actionStatus: "done",
                calendarAction: { ...action, webLink, reused: Boolean(payload.replayed) }
              }
            : message
        )
      );
      onConversationSaved();
    } catch (error) {
      calendarActionLocksRef.current.delete(messageId);
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                actionStatus: "error",
                content: error instanceof Error ? error.message : t("Calendar action failed.")
              }
            : message
        )
      );
    }
  }

  async function copyMessage(message: AssistantMessage) {
    const calendarDetails = message.calendarAction
      ? [
          `${t("Title")}: ${message.calendarAction.subject}`,
          `${t("Date")}: ${message.calendarAction.date}`,
          `${t("Time")}: ${message.calendarAction.startTime}–${message.calendarAction.endTime}`,
          message.calendarAction.participants?.length
            ? `${t("Participants")}: ${message.calendarAction.participants.join(", ")}`
            : "",
          message.calendarAction.agenda ? `${t("Agenda")}: ${message.calendarAction.agenda}` : ""
        ].filter(Boolean).join("\n")
      : "";
    try {
      await navigator.clipboard.writeText([message.content, calendarDetails].filter(Boolean).join("\n\n"));
      setCopiedMessageId(message.id);
      window.setTimeout(() => setCopiedMessageId((current) => current === message.id ? null : current), 1500);
    } catch {
      setCopiedMessageId(null);
    }
  }

  function editAndResend(message: AssistantMessage) {
    setQuestion(message.content);
    window.requestAnimationFrame(() => {
      composerRef.current?.focus();
      composerRef.current?.setSelectionRange(message.content.length, message.content.length);
    });
  }

  function insertCalendarTemplate() {
    setQuestion(formatCalendarTemplate(emptyCalendarDraft(), locale));
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  function draftCalendarFromChat() {
    const recentConversation = messages
      .filter((message) => message.role === "user")
      .slice(-6)
      .reverse()
      .map((message) => message.content)
      .join("\n");
    setQuestion(formatCalendarTemplate(extractCalendarFields(recentConversation), locale));
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  return (
    <aside className="opsAssistant" aria-label={t("Case assistant")}>
      <header className="opsAssistantHeader">
        <div className="opsAssistantIdentity">
          <span className="opsIconTile"><Bot size={16} /></span>
          <div>
            <strong>{claimContext ? t("Case assistant") : t("Operations assistant")}</strong>
            <span>{claimContext ? claimContext.customerReference : t("Evidence-bound guidance")}</span>
          </div>
        </div>
        <button className="opsIconButton" onClick={onClose} title={t("Close assistant")} type="button">
          <X size={16} />
        </button>
      </header>

      {claimContext ? (
        <div className="opsAssistantContext">
          <span>{t("Active case")}</span>
          <strong>{claimContext.customerReference}</strong>
          <small>{claimContext.policyId} · {claimContext.claimType}</small>
        </div>
      ) : null}

      <div className="opsAssistantLog" ref={logRef}>
        {!historyLoading && !messages.length ? (
          <div className="opsAssistantEmpty">
            <MessageSquareText size={20} />
            <strong>{t("Ask about the active case")}</strong>
            <p>
              {t("Answers are constrained by approved policy evidence. Operational actions remain in the approval workflow.")}
            </p>
          </div>
        ) : null}
        {messages.map((message) => (
          <article className={`opsAssistantMessage ${message.role} ${message.error ? "error" : ""}`} key={message.id}>
            <div className="opsMessageHeader">
              <span>{message.role === "user" ? t("You") : "SupportAgent"}</span>
              <div>
                {message.role === "user" ? (
                  <button onClick={() => editAndResend(message)} title={t("Edit & resend")} type="button">
                    <Pencil size={10} />
                  </button>
                ) : null}
                <button onClick={() => void copyMessage(message)} title={t("Copy message")} type="button">
                  {copiedMessageId === message.id ? <span>{t("Copied")}</span> : <Copy size={10} />}
                </button>
              </div>
            </div>
            {message.role === "assistant" ? <MarkdownText text={message.content} /> : <p>{message.content}</p>}
            {message.calendarAction && message.actionStatus ? (
              <CalendarActionCard
                action={message.calendarAction}
                onCancel={
                  message.actionStatus === "pending"
                    ? () => setMessages((current) =>
                        current.map((item) =>
                          item.id === message.id ? { ...item, actionStatus: "cancelled" } : item
                        )
                      )
                    : undefined
                }
                onConfirm={
                  message.actionStatus === "pending" && message.actionQuestion
                    ? () => void confirmCalendarAction(message.id, message.calendarAction!, message.actionQuestion!)
                    : undefined
                }
                onChange={
                  message.actionStatus === "pending"
                    ? (nextAction) => setMessages((current) =>
                        current.map((item) =>
                          item.id === message.id ? { ...item, calendarAction: nextAction } : item
                        )
                      )
                    : undefined
                }
                status={message.actionStatus}
              />
            ) : null}
            {message.meta ? <small>{message.meta}</small> : null}
          </article>
        ))}
        {historyLoading ? (
          <article className="opsAssistantMessage assistant loading">
            <span>SupportAgent</span>
            <p>{t("Loading conversation…")}</p>
          </article>
        ) : null}
        {loading ? (
          <article className="opsAssistantMessage assistant loading">
            <span>SupportAgent</span>
            <p>{t("Reviewing available evidence…")}</p>
          </article>
        ) : null}
      </div>

      <footer className="opsAssistantFooter">
        <label className="opsAssistantModel">
          <span>{t("Assistant model")}</span>
          <select
            aria-label={t("Assistant model")}
            disabled={!models.length || loading}
            onChange={(event) => setSelectedModel(event.target.value)}
            value={selectedModel}
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label} · {model.provider}
              </option>
            ))}
          </select>
        </label>
        <div className="opsAssistantGuardrail">
          <ShieldCheck size={13} />
          <span>{t("Evidence-bound · No status changes")}</span>
        </div>
      </footer>
      <form className="opsAssistantComposer" onSubmit={submit}>
        <textarea
          aria-label={t("Ask about the active case")}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          onPointerUp={(event) => {
            composerManualHeightRef.current = event.currentTarget.getBoundingClientRect().height;
          }}
          placeholder={claimContext ? t("Ask about this claim…") : t("Ask about claims operations…")}
          ref={composerRef}
          rows={2}
          value={question}
        />
        <button disabled={loading || historyLoading || !question.trim()} title={t("Send message")} type="submit">
          <Send size={16} />
        </button>
        <div className="opsComposerTools">
          <button onClick={insertCalendarTemplate} type="button">
            <CalendarDays size={12} />
            {t("Calendar template")}
          </button>
          <button disabled={!messages.some((message) => message.role === "user")} onClick={draftCalendarFromChat} type="button">
            <Bot size={12} />
            {t("Draft from chat")}
          </button>
        </div>
      </form>
    </aside>
  );
}

async function calendarTransactionId(action: CalendarEventAction) {
  const canonicalEvent = [
    action.subject.normalize("NFKC").trim().toLocaleLowerCase(),
    action.date,
    action.startTime,
    action.endTime,
    action.timezone
  ].join("|");
  const digest = await window.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(canonicalEvent)
  );
  const fingerprint = Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
  return `supportagent-${fingerprint}`;
}

function parseCalendarEventAction(text: string): CalendarEventAction | null {
  const looksLikeCalendarAction =
    /(termin|kalender|calendar|event|meeting|besprechung)/i.test(text) &&
    /(hinzuf|eintrag|erstell|add|create|schedule)/i.test(text);
  if (!looksLikeCalendarAction) return null;
  return extractCalendarFields(text);
}

function extractCalendarFields(text: string): CalendarEventAction {
  const dateMatch = text.match(/(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
  const timeMatch =
    text.match(/(?:um\s+)(\d{1,2})(?::|\.)(\d{2})/i) ??
    text.match(/(?:start|beginn)\s*[:=]?[ \t]*(\d{1,2})(?::|\.)(\d{2})/i) ??
    text.match(/(?:um\s+)(\d{1,2})(?:\s*uhr)?/i) ??
    text.match(/\b(\d{1,2}):(\d{2})\b/);
  const endTimeMatch = text.match(
    /(?:ende|end|bis)\s*[:=]?[ \t]*(\d{1,2})(?::|\.)(\d{2})/i
  );

  const day = dateMatch?.[1].padStart(2, "0") ?? "";
  const month = dateMatch?.[2].padStart(2, "0") ?? "";
  const year = dateMatch?.[3] ?? "";
  const hour = timeMatch?.[1].padStart(2, "0") ?? "";
  const minute = timeMatch ? (timeMatch[2] ?? "00").padStart(2, "0") : "";
  const derivedEndHour = hour
    ? String(Math.min(Number(hour) + 1, 23)).padStart(2, "0")
    : "";
  const endHour = endTimeMatch?.[1].padStart(2, "0") || derivedEndHour;
  const endMinute = endTimeMatch?.[2].padStart(2, "0") || minute;
  const titleMatch =
    text.match(/(?:mit\s+dem\s+titel|titel|title|betreff|subject)[ \t]*[:=]?[ \t]*([^,，;.\n]+)/i) ??
    text.match(/(?:namens|called|heisst|heißt)\s+([^,，;.\n]+)/i);
  const participantsMatch = text.match(
    /(?:details\s+with|meeting\s+with|mit\s+(?:den\s+)?teilnehmern?|teilnehmer|participants?|attendees?|参会人|参与者)[ \t]*[:=]?[ \t]*(.+?)(?=(?:[,，][ \t]*)?(?:inhalt|agenda|thema|content|description|beschreibung|会议内容)[ \t]*[:=]?|$)/im
  );
  const agendaMatch = text.match(
    /(?:inhalt|agenda|thema|content|description|beschreibung|会议内容)[ \t]*[:=]?[ \t]*(.+)$/im
  );

  return {
    subject: titleMatch?.[1]?.trim() || "Termin",
    date: dateMatch ? `${year}-${month}-${day}` : "",
    startTime: timeMatch ? `${hour}:${minute}` : "",
    endTime: endHour ? `${endHour}:${endMinute}` : "",
    timezone: "W. Europe Standard Time",
    participants: participantsMatch?.[1] ? parseParticipants(participantsMatch[1]) : undefined,
    participantsText: participantsMatch?.[1]?.trim().replace(/[，,;]\s*$/, "") || undefined,
    agenda: agendaMatch?.[1]?.trim().replace(/[，,;]\s*$/, "") || undefined
  };
}

function emptyCalendarDraft(): CalendarEventAction {
  return {
    subject: "",
    date: "",
    startTime: "",
    endTime: "",
    timezone: "W. Europe Standard Time"
  };
}

function formatCalendarTemplate(action: CalendarEventAction, locale: "de" | "en") {
  const displayDate = action.date
    ? action.date.split("-").reverse().join(".")
    : "";
  if (locale === "de") {
    return [
      "Bitte erstelle einen Kalendertermin.",
      `Titel: ${action.subject}`,
      `Datum: ${displayDate}`,
      `Start: ${action.startTime}`,
      `Ende: ${action.endTime}`,
      `Teilnehmer: ${(action.participants ?? []).join(", ")}`,
      `Inhalt: ${action.agenda ?? ""}`
    ].join("\n");
  }
  return [
    "Please create a calendar event.",
    `Title: ${action.subject}`,
    `Date: ${displayDate}`,
    `Start: ${action.startTime}`,
    `End: ${action.endTime}`,
    `Participants: ${(action.participants ?? []).join(", ")}`,
    `Agenda: ${action.agenda ?? ""}`
  ].join("\n");
}

function parseStoredCalendarAction(
  content: string,
  questionAction?: CalendarEventAction
): CalendarEventAction | null {
  if (
    !content.includes("MCP-Aktion ausgefuehrt: teams_mcp.create_default_calendar_event") &&
    !content.includes("MCP action executed: teams_mcp.create_default_calendar_event")
  ) {
    return null;
  }

  function field(name: string) {
    return content.match(new RegExp(`^\\s*-?\\s*${name}:\\s*(.+)$`, "im"))?.[1]?.trim();
  }

  const start = field("start") ?? "";
  const end = field("end") ?? "";
  const rawSubject = field("subject");
  const bodyPreview = field("bodyPreview");
  const subject =
    questionAction?.subject && (!rawSubject || rawSubject === "Termin")
      ? questionAction.subject
      : rawSubject || questionAction?.subject || "Termin";
  return {
    subject,
    date: start.slice(0, 10) || questionAction?.date || "",
    startTime: start.slice(11, 16) || questionAction?.startTime || "",
    endTime: end.slice(11, 16) || questionAction?.endTime || "",
    timezone: questionAction?.timezone || "W. Europe Standard Time",
    participants: questionAction?.participants,
    participantsText: questionAction?.participantsText,
    agenda: questionAction?.agenda,
    body:
      questionAction?.body ||
      (bodyPreview && bodyPreview !== "Created by SupportAgent MCP." ? bodyPreview : undefined),
    webLink: field("webLink")
  };
}

function parseParticipants(value: string) {
  return value
    .replace(/[，,;]\s*$/, "")
    .split(/\s*(?:,|，|、|\bund\b|\band\b|与|和)\s*/i)
    .map((participant) => participant.trim())
    .filter(Boolean);
}

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function buildCalendarBody(action: CalendarEventAction) {
  const lines = [];
  if (action.participants?.length) {
    lines.push(`Participants: ${action.participants.join(", ")}`);
  }
  if (action.agenda) lines.push(`Agenda: ${action.agenda}`);
  if (action.body) lines.push(action.body);
  return lines.join("\n");
}

function parseMcpResult(result: unknown): Record<string, unknown> | null {
  if (result && typeof result === "object" && !Array.isArray(result)) {
    return result as Record<string, unknown>;
  }
  if (typeof result !== "string") return null;
  try {
    const parsed = JSON.parse(result) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null;
  } catch {
    return null;
  }
}

function CalendarActionCard({
  action,
  onCancel,
  onChange,
  onConfirm,
  status
}: {
  action: CalendarEventAction;
  onCancel?: () => void;
  onChange?: (action: CalendarEventAction) => void;
  onConfirm?: () => void;
  status: "pending" | "running" | "done" | "cancelled" | "error";
}) {
  const { locale, t } = useI18n();
  const isReady = Boolean(
    action.subject.trim() &&
    action.date &&
    action.startTime &&
    action.endTime
  );
  const date = action.date
    ? new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
      }).format(new Date(`${action.date}T12:00:00`))
    : "—";

  return (
    <div className={`opsActionCard ${status}`}>
      <header>
        <div>
          <span>Microsoft 365</span>
          <strong>{t("Calendar event")}</strong>
        </div>
        <em>{t(status === "done" ? action.reused ? "Existing event reused" : "Created" : status === "pending" ? "Approval required" : status)}</em>
      </header>
      {status === "pending" && onChange ? (
        <div className="opsActionForm">
            <label>
              <span>{t("Title")}</span>
              <input
                onChange={(event) => onChange({ ...action, subject: event.target.value })}
                placeholder={t("Event title")}
                value={action.subject}
              />
            </label>
            <div className="opsActionDateTime">
              <label>
                <span>{t("Date")}</span>
                <input
                  onChange={(event) => onChange({ ...action, date: event.target.value })}
                  type="date"
                  value={action.date}
                />
              </label>
              <label>
                <span>{t("Start")}</span>
                <input
                  onChange={(event) => onChange({ ...action, startTime: event.target.value })}
                  type="time"
                  value={action.startTime}
                />
              </label>
              <label>
                <span>{t("End")}</span>
                <input
                  onChange={(event) => onChange({ ...action, endTime: event.target.value })}
                  type="time"
                  value={action.endTime}
                />
              </label>
            </div>
            <label>
              <span>{t("Participants")}</span>
              <input
                onChange={(event) => onChange({
                  ...action,
                  participants: parseParticipants(event.target.value),
                  participantsText: event.target.value
                })}
                placeholder={t("Names or email addresses")}
                value={action.participantsText ?? (action.participants ?? []).join(", ")}
              />
            </label>
            <label>
              <span>{t("Agenda")}</span>
              <textarea
                onChange={(event) => onChange({ ...action, agenda: event.target.value })}
                placeholder={t("Meeting purpose and discussion topics")}
                rows={3}
                value={action.agenda ?? ""}
              />
            </label>
        </div>
      ) : (
        <dl>
          <>
            <div><dt>{t("Title")}</dt><dd>{action.subject}</dd></div>
            <div><dt>{t("Date")}</dt><dd>{date}</dd></div>
            <div><dt>{t("Time")}</dt><dd>{action.startTime}–{action.endTime}</dd></div>
            {action.participants?.length ? (
              <div><dt>{t("Participants")}</dt><dd>{action.participants.join(", ")}</dd></div>
            ) : null}
            {action.agenda ? <div><dt>{t("Agenda")}</dt><dd>{action.agenda}</dd></div> : null}
            {action.body ? <div><dt>{t("Details")}</dt><dd>{action.body.replace(/^Details:\s*/i, "")}</dd></div> : null}
          </>
        </dl>
      )}
      {action.participants?.some((participant) => !isEmail(participant)) ? (
        <p className="opsActionHint">{t("Email addresses are required to send invitations; names are saved in the event details.")}</p>
      ) : null}
      {status === "pending" ? (
        <>
          {!isReady ? <p className="opsActionMissing">{t("Complete title, date, start, and end before confirmation.")}</p> : null}
          <div className="opsActionButtons">
            <button className="primary" disabled={!isReady} onClick={onConfirm} type="button">{t("Confirm")}</button>
            <button onClick={onCancel} type="button">{t("Cancel")}</button>
          </div>
        </>
      ) : null}
      {status === "running" ? <p>{t("Creating calendar event…")}</p> : null}
      {status === "done" && action.webLink ? (
        <a href={action.webLink} rel="noreferrer" target="_blank">{t("Open in Outlook")}</a>
      ) : null}
      {status === "cancelled" ? <p>{t("Action cancelled.")}</p> : null}
    </div>
  );
}

export function OperationsShell({ active, children, claimContext }: OperationsShellProps) {
  const { locale, t } = useI18n();
  const [theme, setTheme] = useState<ColorTheme>("light");
  const [assistantOpen, setAssistantOpen] = useState(true);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [assistantWidth, setAssistantWidth] = useState(360);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [conversationThreads, setConversationThreads] = useState<ConversationThread[]>([]);
  const [conversationVersion, setConversationVersion] = useState(0);
  const [assistantThreadId, setAssistantThreadId] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(themeStorageKey);
    const initial: ColorTheme = stored === "light" || stored === "dark"
      ? stored
      : window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    setTheme(initial);
  }, []);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then(async (response) => (response.ok ? ((await response.json()) as AuthUser) : null))
      .then(setUser)
      .catch(() => setUser(null));

    if (window.matchMedia("(max-width: 860px)").matches) {
      setAssistantOpen(false);
    }
  }, []);

  useEffect(() => {
    const storageKey = assistantStorageKey(claimContext);
    const stored = window.localStorage.getItem(storageKey);
    const next = stored ?? crypto.randomUUID();
    if (!stored) window.localStorage.setItem(storageKey, next);
    setAssistantThreadId(next);
  }, [claimContext?.id]);

  useEffect(() => {
    if (!user) {
      setConversationThreads([]);
      return;
    }

    const controller = new AbortController();
    fetch("/api/threads", {
      credentials: "include",
      signal: controller.signal
    })
      .then(async (response) => {
        if (!response.ok) return { threads: [] as ConversationThread[] };
        return (await response.json()) as { threads: ConversationThread[] };
      })
      .then((payload) => setConversationThreads(payload.threads))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setConversationThreads([]);
      });

    return () => controller.abort();
  }, [user, conversationVersion]);

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

  function startNewConversation() {
    const next = crypto.randomUUID();
    window.localStorage.setItem(assistantStorageKey(claimContext), next);
    setAssistantThreadId(next);
    setAssistantOpen(true);
    setNavigationOpen(false);
  }

  function selectConversation(threadId: string) {
    window.localStorage.setItem(assistantStorageKey(claimContext), threadId);
    setAssistantThreadId(threadId);
    setAssistantOpen(true);
    setNavigationOpen(false);
  }

  function toggleTheme() {
    const next: ColorTheme = theme === "light" ? "dark" : "light";
    setTheme(next);
    window.localStorage.setItem(themeStorageKey, next);
  }

  return (
    <div
      className={`opsShell theme-${theme} ${assistantOpen ? "" : "assistantClosed"} ${navigationOpen ? "navigationOpen" : ""}`}
      style={{ "--ops-assistant-width": `${assistantWidth}px` } as React.CSSProperties}
    >
      <button className="opsMobileMenu" onClick={() => setNavigationOpen(true)} title={t("Open navigation")} type="button">
        <Menu size={18} />
      </button>

      <aside className="opsNavigation">
        <div className="opsBrand">
          <div className="opsBrandMain">
            <span>SA</span>
            <div className="opsBrandIdentity">
              <strong>SupportAgent</strong>
              <small>{t("Claims Control")}</small>
            </div>
          </div>
          <button className="opsMobileClose" onClick={() => setNavigationOpen(false)} title={t("Close navigation")} type="button">
            <X size={16} />
          </button>
          <div className="opsBrandControls">
            <LanguageSwitcher compact />
            <button
              aria-label={t(theme === "light" ? "Enable dark mode" : "Enable light mode")}
              className="opsThemeButton"
              onClick={toggleTheme}
              title={t(theme === "light" ? "Enable dark mode" : "Enable light mode")}
              type="button"
            >
              {theme === "light" ? <Moon size={13} /> : <Sun size={13} />}
              <span>{t(theme === "light" ? "Dark" : "Light")}</span>
            </button>
          </div>
        </div>

        <div className="opsEnvironment">
          <span><i /> {t("Controlled workspace")}</span>
          <small>{t("Synthetic training data")}</small>
        </div>

        <nav className="opsNavGroups" aria-label={t("Navigation")}>
          {navigation.map((group) => (
            <section key={group.label}>
              <p>{t(group.label)}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <a className={active === item.key ? "active" : ""} href={item.href} key={item.key}>
                    <Icon size={16} />
                    <span>{t(item.label)}</span>
                  </a>
                );
              })}
            </section>
          ))}
        </nav>

        <section className="opsSidebarChats">
          <header>
            <span>{t("Chats")}</span>
            <button onClick={startNewConversation} title={t("New chat")} type="button">
              <Plus size={12} />
              {t("New chat")}
            </button>
          </header>
          <div>
            {conversationThreads.slice(0, 5).map((thread) => (
              <button
                className={assistantThreadId === thread.thread_id ? "active" : ""}
                key={thread.thread_id}
                onClick={() => selectConversation(thread.thread_id)}
                type="button"
              >
                <span>{displayThreadTitle(thread.title, locale)}</span>
                <small>{thread.message_count} {locale === "de" ? "Nachrichten" : "messages"}</small>
              </button>
            ))}
            {!conversationThreads.length ? <p>{t("No saved chats yet.")}</p> : null}
          </div>
        </section>

        <div className="opsControlBoundary">
          <ShieldCheck size={16} />
          <div>
            <strong>{t("Human control")}</strong>
            <p>{t("Actions require an explicit decision before execution.")}</p>
          </div>
        </div>

        <div className="opsAccount">
          <CircleUserRound size={18} />
          <div>
            <strong>{user?.display_name || t("Claims operator")}</strong>
            <span>{user?.email || t("Local account")}</span>
          </div>
          <button onClick={logout} title={t("Sign out")} type="button"><LogOut size={15} /></button>
        </div>
      </aside>

      <button className="opsNavigationBackdrop" onClick={() => setNavigationOpen(false)} type="button" />

      <main className="opsWorkspace">{children}</main>

      {assistantOpen ? (
        <>
          <div
            aria-label={t("Resize assistant")}
            className="opsAssistantResizer"
            onPointerDown={startResize}
            role="separator"
          />
          <CaseAssistant
            claimContext={claimContext}
            onClose={() => setAssistantOpen(false)}
            onConversationSaved={() => setConversationVersion((current) => current + 1)}
            threadId={assistantThreadId}
          />
        </>
      ) : (
        <button className="opsAssistantReopen" onClick={() => setAssistantOpen(true)} type="button">
          <Bot size={16} />
          <span>{t("Assistant")}</span>
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
  const { t } = useI18n();
  return (
    <header className="opsPageHeader">
      <div>
        <p>{t(eyebrow)}</p>
        <h1>{t(title)}</h1>
        {description ? <span>{t(description)}</span> : null}
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
