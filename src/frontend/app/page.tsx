"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

type SourceFilter = "all" | "confluence" | "jira";

type Source = {
  id: number;
  title: string;
  url: string;
  source: string;
  content: string;
  distance: number;
};

type AgentTrace = {
  thread_id: string | null;
  short_memory_count: number;
  long_memory_count: number;
  route_source: string;
  route_reason: string;
  rewrite_changed: boolean;
  rewritten_query: string;
  evidence_status: string;
  evidence_reason: string;
  mcp_tool_calls: Array<{
    server: string;
    tool: string;
    arguments: Record<string, unknown>;
    result_preview: string;
  }>;
  mcp_error: string | null;
  enabled_skills: string[];
  model: string;
  image_count: number;
};

type AskResponse = {
  answer: string;
  sources: Source[];
  trace: AgentTrace;
};

type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
};

type Message = {
  id: string;
  storedUserMessageId?: number;
  question: string;
  response?: AskResponse;
  error?: string;
  pendingAction?: MicrosoftAction;
  actionStatus?: "pending" | "running" | "done" | "cancelled" | "error";
  actionResult?: string;
  imageAttachments?: UploadedImage[];
};

type CreateCalendarAction = {
  type: "create_calendar";
  name: string;
};

type CalendarEventAction = {
  type: "create_calendar_event";
  subject: string;
  date: string;
  startTime: string;
  endTime: string;
  timezone: string;
};

type MicrosoftAction = CreateCalendarAction | CalendarEventAction;

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

type ConversationThreadsResponse = {
  threads: ConversationThread[];
};

type McpParameter = {
  name: string;
  type: string;
  required: boolean;
  default: unknown;
  description: string | null;
};

type McpTool = {
  server: string;
  name: string;
  description: string;
  parameters: McpParameter[];
  example_arguments: Record<string, unknown>;
};

type McpToolsResponse = {
  tools: McpTool[];
};

type McpCallResponse = {
  server: string;
  tool: string;
  result: unknown;
};

type McpPolicy = {
  server_name: string;
  tool_name: string;
  enabled: boolean;
  auto_allowed: boolean;
  requires_confirmation: boolean;
};

type McpServer = {
  server_name: string;
  display_name: string;
  transport: string;
  config: Record<string, unknown>;
  enabled: boolean;
  updated_at?: string;
};

type McpServersResponse = {
  servers: McpServer[];
  policies: McpPolicy[];
};

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

type McpAuditResponse = {
  audit_logs: McpAuditLog[];
};

type InsuranceSkill = {
  skill_id: string;
  name: string;
  category: string;
  description: string;
  instruction: string;
};

type SkillsResponse = {
  skills: InsuranceSkill[];
};

type ChatModel = {
  id: string;
  label: string;
  default: boolean;
};

type ChatModelsResponse = {
  models: ChatModel[];
};

type UploadedImage = {
  id: string;
  filename: string;
  content_type: string;
  image_summary: string;
  preview_url: string;
  local_preview_url?: string;
};

const starterQuestions = [
  "Welche Unterlagen brauche ich fuer eine Schadenmeldung?",
  "Gibt es ein Jira Ticket zur Dokumentationsluecke?",
  "Was brauche ich nach einem Autounfall?"
];

const threadStorageKey = "supportagent.threadId";
const backendApiUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [messages, setMessages] = useState<Message[]>([]);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingQuestion, setEditingQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [runningActionId, setRunningActionId] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [threads, setThreads] = useState<ConversationThread[]>([]);
  const [mcpTools, setMcpTools] = useState<McpTool[]>([]);
  const [selectedToolKey, setSelectedToolKey] = useState("");
  const [toolArguments, setToolArguments] = useState("{}");
  const [toolResult, setToolResult] = useState<string | null>(null);
  const [toolError, setToolError] = useState<string | null>(null);
  const [isToolLoading, setIsToolLoading] = useState(false);
  const [actionCalendarName, setActionCalendarName] = useState("SupportAgent Test");
  const [actionFolderName, setActionFolderName] = useState("SupportAgent Test");
  const [actionDocumentName, setActionDocumentName] = useState("supportagent-test.txt");
  const [actionDocumentContent, setActionDocumentContent] = useState("Created by SupportAgent MCP OAuth.");
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [mcpPolicies, setMcpPolicies] = useState<McpPolicy[]>([]);
  const [mcpAuditLogs, setMcpAuditLogs] = useState<McpAuditLog[]>([]);
  const [selectedMcpServers, setSelectedMcpServers] = useState<string[]>([]);
  const [isMcpSelectionInitialized, setIsMcpSelectionInitialized] = useState(false);
  const [isMcpSelectorOpen, setIsMcpSelectorOpen] = useState(false);
  const [models, setModels] = useState<ChatModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("qwen-plus");
  const [isModelSelectorOpen, setIsModelSelectorOpen] = useState(false);
  const [attachedImages, setAttachedImages] = useState<UploadedImage[]>([]);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeImagePreview, setActiveImagePreview] = useState<UploadedImage | null>(null);
  const [skills, setSkills] = useState<InsuranceSkill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [isSkillSelectorOpen, setIsSkillSelectorOpen] = useState(false);
  const [isMcpCenterOpen, setIsMcpCenterOpen] = useState(false);
  const [mcpPanelTab, setMcpPanelTab] = useState<"actions" | "servers" | "tools" | "audit" | "debug">("actions");
  const [serverFormName, setServerFormName] = useState("");
  const [serverFormDisplayName, setServerFormDisplayName] = useState("");
  const [serverFormTransport, setServerFormTransport] = useState("stdio");
  const [serverFormConfig, setServerFormConfig] = useState(
    '{\n  "command": "python",\n  "args": ["-m", "supportagent.mcp_servers.weather_mcp", "--transport", "stdio"]\n}'
  );
  const [serverFormEnabled, setServerFormEnabled] = useState(true);
  const [serverFormStatus, setServerFormStatus] = useState<string | null>(null);
  const [credentialJson, setCredentialJson] = useState("{}");
  const [credentialStatus, setCredentialStatus] = useState<string | null>(null);

  const activeMessage = useMemo(() => messages[messages.length - 1], [messages]);
  const selectedTool = useMemo(
    () => mcpTools.find((tool) => toolKey(tool) === selectedToolKey) ?? null,
    [mcpTools, selectedToolKey]
  );
  const selectedPolicy = useMemo(
    () =>
      selectedTool
        ? mcpPolicies.find(
            (policy) =>
              policy.server_name === selectedTool.server &&
              policy.tool_name === selectedTool.name
          ) ?? null
        : null,
    [mcpPolicies, selectedTool]
  );
  const toolsByServer = useMemo(() => {
    const grouped = new Map<string, McpTool[]>();
    for (const tool of mcpTools) {
      grouped.set(tool.server, [...(grouped.get(tool.server) ?? []), tool]);
    }
    return grouped;
  }, [mcpTools]);

  useEffect(() => {
    const existingThreadId = window.localStorage.getItem(threadStorageKey);
    if (existingThreadId) {
      setThreadId(existingThreadId);
      return;
    }

    const nextThreadId = crypto.randomUUID();
    window.localStorage.setItem(threadStorageKey, nextThreadId);
    setThreadId(nextThreadId);
  }, []);

  useEffect(() => {
    if (!activeImagePreview) {
      return;
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setActiveImagePreview(null);
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [activeImagePreview]);

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        const response = await fetch("/api/auth/me", {
          credentials: "include"
        });
        if (!response.ok) {
          setUser(null);
          return;
        }
        const data = (await response.json()) as AuthUser;
        setUser(data);
      } finally {
        setIsAuthLoading(false);
      }
    }

    void loadCurrentUser();
  }, []);

  useEffect(() => {
    if (!user || !threadId) {
      return;
    }

    async function loadThreadHistory() {
      setIsHistoryLoading(true);
      try {
        const response = await fetch(`/api/threads/${threadId}/messages`, {
          credentials: "include"
        });
        if (!response.ok) {
          return;
        }
        const data = (await response.json()) as ThreadMessagesResponse;
        setMessages(hydrateMessages(data.messages));
      } finally {
        setIsHistoryLoading(false);
      }
    }

    void loadThreadHistory();
  }, [threadId, user]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError(null);
    setIsAuthLoading(true);

    try {
      const response = await fetch(`/api/auth/${authMode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
          display_name: authMode === "register" ? displayName : undefined
        })
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorBody?.detail ?? `Authentication failed with ${response.status}`);
      }

      const data = (await response.json()) as AuthUser;
      setUser(data);
      setAuthPassword("");
      setDisplayName("");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include"
    });
    setUser(null);
    setMessages([]);
    setThreads([]);
  }

  async function loadThreads() {
    const response = await fetch("/api/threads", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as ConversationThreadsResponse;
    setThreads(data.threads);
  }

  useEffect(() => {
    if (!user) {
      return;
    }

    void loadThreads();
    void loadMcpTools();
    void loadMcpConfig();
    void loadMcpAudit();
    void loadModels();
    void loadSkills();
  }, [user]);

  async function loadModels() {
    const response = await fetch("/api/models", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as ChatModelsResponse;
    setModels(data.models);
    const defaultModel = data.models.find((model) => model.default) ?? data.models[0];
    if (defaultModel) {
      setSelectedModel(defaultModel.id);
    }
  }

  async function loadSkills() {
    const response = await fetch("/api/skills", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as SkillsResponse;
    setSkills(data.skills);
  }

  async function loadMcpTools() {
    const response = await fetch("/api/mcp/tools", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as McpToolsResponse;
    setMcpTools(data.tools);
    if (data.tools.length && !selectedToolKey) {
      const firstTool = data.tools[0];
      setSelectedToolKey(toolKey(firstTool));
      setToolArguments(formatToolArguments(firstTool.example_arguments));
    }
  }

  function selectMcpTool(nextToolKey: string) {
    const nextTool = mcpTools.find((tool) => toolKey(tool) === nextToolKey);
    setSelectedToolKey(nextToolKey);
    setToolResult(null);
    setToolError(null);
    if (nextTool) {
      setToolArguments(formatToolArguments(nextTool.example_arguments));
      setCredentialJson("{}");
      setCredentialStatus(null);
    }
  }

  async function loadMcpConfig() {
    const response = await fetch("/api/mcp/servers", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as McpServersResponse;
    setMcpServers(data.servers);
    setMcpPolicies(data.policies);
    if (!isMcpSelectionInitialized) {
      setSelectedMcpServers(
        data.servers
          .filter((server) => server.enabled)
          .map((server) => server.server_name)
      );
      setIsMcpSelectionInitialized(true);
    }
  }

  async function saveMcpServer() {
    let config: Record<string, unknown>;
    try {
      config = JSON.parse(serverFormConfig) as Record<string, unknown>;
    } catch {
      setServerFormStatus("Server config must be valid JSON.");
      return;
    }
    const response = await fetch("/api/mcp/servers", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      credentials: "include",
      body: JSON.stringify({
        server_name: serverFormName,
        display_name: serverFormDisplayName || serverFormName,
        transport: serverFormTransport,
        config,
        enabled: serverFormEnabled
      })
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setServerFormStatus(body?.detail ?? "Could not save MCP server.");
      return;
    }
    setServerFormStatus("MCP server saved. Tools will refresh from list_tools.");
    await loadMcpConfig();
    await loadMcpTools();
  }

  function editMcpServer(server: McpServer) {
    setMcpPanelTab("servers");
    setServerFormName(server.server_name);
    setServerFormDisplayName(server.display_name);
    setServerFormTransport(server.transport);
    setServerFormConfig(JSON.stringify(server.config ?? {}, null, 2));
    setServerFormEnabled(server.enabled);
    setServerFormStatus(null);
  }

  function insertLocalWeatherConfig() {
    setServerFormName("weather_mcp");
    setServerFormDisplayName("Local Google Weather MCP server");
    setServerFormTransport("stdio");
    setServerFormConfig(
      '{\n  "command": "python",\n  "args": ["-m", "supportagent.mcp_servers.weather_mcp", "--transport", "stdio"]\n}'
    );
    setServerFormEnabled(true);
  }

  function insertRemoteExampleConfig() {
    setServerFormName("remote_mcp");
    setServerFormDisplayName("Remote MCP server");
    setServerFormTransport("sse");
    setServerFormConfig('{\n  "url": "https://example.com/sse"\n}');
    setServerFormEnabled(false);
  }

  async function loadMcpAudit() {
    const response = await fetch("/api/mcp/audit", {
      credentials: "include"
    });
    if (!response.ok) {
      return;
    }
    const data = (await response.json()) as McpAuditResponse;
    setMcpAuditLogs(data.audit_logs);
  }

  async function saveMcpCredentials() {
    if (!selectedTool) {
      return;
    }
    let credentials: Record<string, unknown>;
    try {
      credentials = JSON.parse(credentialJson) as Record<string, unknown>;
    } catch {
      setCredentialStatus("Credential JSON is invalid.");
      return;
    }
    const response = await fetch("/api/mcp/credentials", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      credentials: "include",
      body: JSON.stringify({
        server: selectedTool.server,
        credentials
      })
    });
    setCredentialStatus(response.ok ? "Credentials saved for this server." : "Could not save credentials.");
  }

  async function runMcpTool() {
    if (!selectedTool || isToolLoading) {
      return;
    }

    let parsedArguments: Record<string, unknown>;
    try {
      parsedArguments = JSON.parse(toolArguments) as Record<string, unknown>;
    } catch {
      setToolError("Arguments must be valid JSON.");
      setToolResult(null);
      return;
    }

    setIsToolLoading(true);
    setToolError(null);
    setToolResult(null);

    try {
      const confirmed =
        selectedPolicy?.requires_confirmation
          ? window.confirm("This MCP tool requires confirmation. Run it now?")
          : false;
      if (selectedPolicy?.requires_confirmation && !confirmed) {
        setToolError("Tool call cancelled.");
        return;
      }
      const response = await fetch("/api/mcp/call", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          server: selectedTool.server,
          tool: selectedTool.name,
          arguments: parsedArguments,
          confirmed,
          thread_id: threadId,
          question: `MCP debug call: ${selectedTool.server}.${selectedTool.name}`
        })
      });
      const data = (await response.json()) as McpCallResponse | { detail?: string };
      if (!response.ok) {
        throw new Error("detail" in data ? data.detail ?? `Tool call failed with ${response.status}` : `Tool call failed with ${response.status}`);
      }
      setToolResult(JSON.stringify((data as McpCallResponse).result, null, 2));
      void loadMcpAudit();
    } catch (error) {
      setToolError(error instanceof Error ? error.message : "Tool call failed");
    } finally {
      setIsToolLoading(false);
    }
  }

  async function runMcpAction(
    toolName: string,
    argumentsObject: Record<string, unknown>,
    requiresConfirmation = false
  ) {
    if (isToolLoading) {
      return;
    }
    if (requiresConfirmation && !window.confirm(`Run Microsoft Graph action ${toolName}?`)) {
      return;
    }

    setIsToolLoading(true);
    setToolError(null);
    setToolResult(null);
    setMcpPanelTab("actions");
    try {
      const response = await fetch("/api/mcp/call", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          server: "teams_mcp",
          tool: toolName,
          arguments: argumentsObject,
          confirmed: requiresConfirmation,
          thread_id: threadId,
          question: `MCP action: ${toolName}`
        })
      });
      const data = (await response.json()) as McpCallResponse | { detail?: string };
      if (!response.ok) {
        throw new Error("detail" in data ? data.detail ?? `Action failed with ${response.status}` : `Action failed with ${response.status}`);
      }
      setToolResult(JSON.stringify((data as McpCallResponse).result, null, 2));
      void loadMcpAudit();
    } catch (error) {
      setToolError(error instanceof Error ? error.message : "Action failed");
    } finally {
      setIsToolLoading(false);
    }
  }

  async function confirmMicrosoftAction(messageId: string, action: MicrosoftAction, question: string) {
    if (runningActionId) {
      return;
    }
    setRunningActionId(messageId);
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, actionStatus: "running", actionResult: undefined } : message
      )
    );
    try {
      const toolRequest =
        action.type === "create_calendar"
          ? {
              tool: "create_calendar",
              arguments: {
                user_id: "me",
                name: action.name
              }
            }
          : {
              tool: "create_default_calendar_event",
              arguments: {
                subject: action.subject,
                start_time: `${action.date}T${action.startTime}:00`,
                end_time: `${action.date}T${action.endTime}:00`,
                timezone: action.timezone,
                body: "Created by SupportAgent MCP."
              }
            };

      const response = await fetch("/api/mcp/call", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          server: "teams_mcp",
          tool: toolRequest.tool,
          arguments: toolRequest.arguments,
          confirmed: true,
          thread_id: threadId,
          question
        })
      });
      const data = (await response.json()) as McpCallResponse | { detail?: string };
      if (!response.ok) {
        throw new Error("detail" in data ? data.detail ?? `Action failed with ${response.status}` : `Action failed with ${response.status}`);
      }
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                actionStatus: "done",
                actionResult: JSON.stringify((data as McpCallResponse).result, null, 2)
              }
            : message
        )
      );
      void loadMcpAudit();
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                actionStatus: "error",
                actionResult: error instanceof Error ? error.message : "Action failed"
              }
            : message
        )
      );
    } finally {
      setRunningActionId(null);
    }
  }

  function cancelCalendarAction(messageId: string) {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, actionStatus: "cancelled" } : message
      )
    );
  }

  async function deleteMessage(message: Message) {
    if (message.storedUserMessageId && threadId) {
      const response = await fetch(`/api/threads/${threadId}/messages/${message.storedUserMessageId}`, {
        method: "DELETE",
        credentials: "include"
      });
      if (response.ok) {
        const data = (await response.json()) as ThreadMessagesResponse;
        setMessages(hydrateMessages(data.messages));
        void loadThreads();
        return;
      }
    }
    setMessages((current) => current.filter((item) => item.id !== message.id));
  }

  function startEditingMessage(message: Message) {
    setEditingMessageId(message.id);
    setEditingQuestion(message.question);
  }

  function cancelEditingMessage() {
    setEditingMessageId(null);
    setEditingQuestion("");
  }

  async function saveEditedMessage(message: Message) {
    const nextQuestion = editingQuestion.trim();
    if (!nextQuestion) {
      return;
    }

    if (message.storedUserMessageId && threadId) {
      const response = await fetch(`/api/threads/${threadId}/messages/${message.storedUserMessageId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({ content: nextQuestion })
      });
      if (response.ok) {
        const data = (await response.json()) as ThreadMessagesResponse;
        setMessages(hydrateMessages(data.messages));
        void loadThreads();
      }
    } else {
      setMessages((current) =>
        current.filter((item) => item.id !== message.id)
      );
    }
    setEditingMessageId(null);
    setEditingQuestion("");
    await askAgent(nextQuestion);
  }

  async function uploadImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || isUploadingImage) {
      return;
    }

    const localPreviewUrl = URL.createObjectURL(file);
    setIsUploadingImage(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (threadId) {
        formData.append("thread_id", threadId);
      }
      const response = await fetch("/api/uploads/image", {
        method: "POST",
        credentials: "include",
        body: formData
      });
      const responseText = await response.text();
      let data: UploadedImage | { detail?: string } | null = null;
      try {
        data = responseText ? (JSON.parse(responseText) as UploadedImage | { detail?: string }) : null;
      } catch {
        data = { detail: responseText || `Upload failed with ${response.status}` };
      }
      if (!response.ok) {
        throw new Error(data && "detail" in data ? data.detail ?? `Upload failed with ${response.status}` : `Upload failed with ${response.status}`);
      }
      if (!data || !("id" in data)) {
        throw new Error("Upload response did not include an image id.");
      }
      const uploaded = data as UploadedImage;
      setAttachedImages((current) => [
        ...current,
        {
          ...uploaded,
          preview_url: uploaded.preview_url || `/uploads/image/${uploaded.id}`,
          local_preview_url: localPreviewUrl
        }
      ]);
    } catch (error) {
      URL.revokeObjectURL(localPreviewUrl);
      setUploadError(error instanceof Error ? error.message : "Image upload failed");
    } finally {
      setIsUploadingImage(false);
    }
  }

  function removeAttachedImage(imageId: string) {
    setAttachedImages((current) => current.filter((image) => image.id !== imageId));
  }

  async function askAgent(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if ((!trimmed && !attachedImages.length) || isLoading) {
      return;
    }

    const id = crypto.randomUUID();
    const imageAttachments = attachedImages;
    const questionText = trimmed || "Bitte analysiere das hochgeladene Bild.";
    const pendingCalendarAction = parseMicrosoftAction(trimmed);
    if (pendingCalendarAction) {
      setMessages((current) => [
        ...current,
        {
          id,
          question: questionText,
          imageAttachments,
          pendingAction: pendingCalendarAction,
          actionStatus: "pending",
          response: {
            answer: "Ich habe einen Kalendertermin erkannt. Bitte pruefe die Angaben und bestaetige die Aktion.",
            sources: [],
            trace: {
              thread_id: threadId,
              short_memory_count: 0,
              long_memory_count: 0,
              route_source: "mcp_action_confirmation",
              route_reason: "Microsoft Graph write action requires explicit user confirmation.",
              rewrite_changed: false,
              rewritten_query: questionText,
              evidence_status: "action_pending",
              evidence_reason: "Waiting for user confirmation before calling Microsoft Graph.",
              mcp_tool_calls: [],
              mcp_error: null,
              enabled_skills: selectedSkills,
              model: selectedModel,
              image_count: imageAttachments.length
            }
          }
        }
      ]);
      setQuestion("");
      return;
    }

    setMessages((current) => [...current, { id, question: questionText, imageAttachments }]);
    setQuestion("");
    setAttachedImages([]);
    setIsLoading(true);

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          question: questionText,
          source: sourceFilter === "all" ? null : sourceFilter,
          thread_id: threadId,
          model: selectedModel,
          image_ids: imageAttachments.map((image) => image.id),
          enabled_mcp_servers: selectedMcpServers,
          enabled_skills: selectedSkills
        })
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = (await response.json()) as AskResponse;
      setMessages((current) =>
        current.map((message) =>
          message.id === id ? { ...message, response: data } : message
        )
      );
      void loadThreads();
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === id
            ? {
                ...message,
                error:
                  error instanceof Error
                    ? error.message
                    : "Request failed"
              }
            : message
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void askAgent(question);
  }

  function startNewChat() {
    const nextThreadId = crypto.randomUUID();
    window.localStorage.setItem(threadStorageKey, nextThreadId);
    setThreadId(nextThreadId);
    setMessages([]);
    setQuestion("");
  }

  function selectThread(nextThreadId: string) {
    if (nextThreadId === threadId) {
      return;
    }
    window.localStorage.setItem(threadStorageKey, nextThreadId);
    setThreadId(nextThreadId);
    setMessages([]);
    setQuestion("");
  }

  function toggleMcpServer(serverName: string) {
    setIsMcpSelectionInitialized(true);
    setSelectedMcpServers((current) =>
      current.includes(serverName)
        ? current.filter((name) => name !== serverName)
        : [...current, serverName]
    );
  }

  function selectAllMcpServers() {
    setIsMcpSelectionInitialized(true);
    setSelectedMcpServers(
      mcpServers.filter((server) => server.enabled).map((server) => server.server_name)
    );
  }

  function clearMcpServers() {
    setIsMcpSelectionInitialized(true);
    setSelectedMcpServers([]);
  }

  function toggleSkill(skillId: string) {
    setSelectedSkills((current) =>
      current.includes(skillId)
        ? current.filter((id) => id !== skillId)
        : [...current, skillId]
    );
  }

  function clearSkills() {
    setSelectedSkills([]);
  }

  if (isAuthLoading && !user) {
    return (
      <main className="authShell">
        <section className="authPanel">
          <div className="brandMark" aria-hidden="true">
            SA
          </div>
          <p className="eyebrow">SupportAgent</p>
          <h1>Loading account</h1>
        </section>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="authShell">
        <section className="authPanel">
          <div className="brandMark" aria-hidden="true">
            SA
          </div>
          <p className="eyebrow">SupportAgent</p>
          <h1>{authMode === "login" ? "Sign in" : "Create account"}</h1>
          <form className="authForm" onSubmit={submitAuth}>
            <label>
              Email
              <input
                autoComplete="email"
                onChange={(event) => setAuthEmail(event.target.value)}
                required
                type="email"
                value={authEmail}
              />
            </label>
            {authMode === "register" ? (
              <label>
                Display name
                <input
                  autoComplete="name"
                  onChange={(event) => setDisplayName(event.target.value)}
                  type="text"
                  value={displayName}
                />
              </label>
            ) : null}
            <label>
              Password
              <input
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
                minLength={authMode === "register" ? 8 : 1}
                onChange={(event) => setAuthPassword(event.target.value)}
                required
                type="password"
                value={authPassword}
              />
            </label>
            {authError ? <p className="errorText">{authError}</p> : null}
            <button disabled={isAuthLoading} type="submit">
              {authMode === "login" ? "Sign in" : "Register"}
            </button>
          </form>
          <button
            className="textButton"
            onClick={() => {
              setAuthError(null);
              setAuthMode(authMode === "login" ? "register" : "login");
            }}
            type="button"
          >
            {authMode === "login" ? "Create a local account" : "Use existing account"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Navigation">
        <div className="brand">
          <div className="brandMark" aria-hidden="true">
            SA
          </div>
          <div>
            <p className="eyebrow">SupportAgent</p>
            <h1>Insurance RAG</h1>
          </div>
        </div>

        <nav className="navList">
          <a className="navItem active" href="#">
            Chat
          </a>
          <button
            className="navItem navButton appCenterButton"
            onClick={() => setIsMcpCenterOpen(true)}
            type="button"
          >
            <span aria-hidden="true">M</span>
            MCP Center
          </button>
          <button className="navItem navButton" onClick={startNewChat} type="button">
            New chat
          </button>
        </nav>

        <section className="panel threadPanel">
          <p className="panelTitle">Chats</p>
          {threads.length ? (
            <div className="threadList">
              {threads.map((thread) => (
                <button
                  className={thread.thread_id === threadId ? "selected" : ""}
                  key={thread.thread_id}
                  onClick={() => selectThread(thread.thread_id)}
                  type="button"
                >
                  <span>{thread.title}</span>
                  <small>{thread.message_count} messages</small>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">No saved chats yet.</p>
          )}
        </section>

        <section className="panel">
          <p className="panelTitle">Source</p>
          <div className="segmented" role="group" aria-label="Source filter">
            {(["all", "confluence", "jira"] as const).map((source) => (
              <button
                className={sourceFilter === source ? "selected" : ""}
                key={source}
                onClick={() => setSourceFilter(source)}
                type="button"
              >
                {source === "all" ? "All" : source}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <p className="panelTitle">Try</p>
          <div className="questionList">
            {starterQuestions.map((starter) => (
              <button
                key={starter}
                onClick={() => void askAgent(starter)}
                type="button"
              >
                {starter}
              </button>
            ))}
          </div>
        </section>

        <section className="panel accountPanel">
          <p className="panelTitle">Account</p>
          <p>{user.display_name || user.email}</p>
          <small>{user.email}</small>
          <a className="connectButton" href={`${backendApiUrl}/auth/microsoft/start`}>
            Connect Microsoft
          </a>
          <button onClick={() => void logout()} type="button">
            Sign out
          </button>
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Knowledge assistant</p>
            <h2>Insurance Knowledge Workspace</h2>
          </div>
          <div className="statusBadge">
            <span aria-hidden="true" />
            LangGraph Agent
          </div>
        </header>

        <section className="chatSurface" aria-live="polite">
          {isHistoryLoading ? (
            <div className="emptyState">
              <h2>Loading conversation.</h2>
              <p>Restoring messages from this thread.</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="emptyState">
              <div className="omniMark" aria-hidden="true">SA</div>
              <h2>Insurance SupportAgent</h2>
              <p>
                Ask insurance questions, select MCP servers, and let the agent decide which tools to call.
              </p>
              <div className="modeSwitch" aria-label="Agent mode">
                <button className="selected" type="button">Daily mode</button>
                <button type="button">Agent mode</button>
              </div>
            </div>
          ) : (
            <div className="messageList">
              {messages.map((message) => (
                <article className="message" key={message.id}>
                  <div className="bubble userBubble">
                    <div className="messageHeader">
                      <span>Question</span>
                      <div>
                        <button onClick={() => startEditingMessage(message)} type="button">
                          Edit
                        </button>
                        <button onClick={() => void deleteMessage(message)} type="button">
                          Delete
                        </button>
                      </div>
                    </div>
                    {editingMessageId === message.id ? (
                      <div className="editPanel">
                        <textarea
                          onChange={(event) => setEditingQuestion(event.target.value)}
                          value={editingQuestion}
                        />
                        <div>
                          <button onClick={() => void saveEditedMessage(message)} type="button">
                            Save
                          </button>
                          <button onClick={cancelEditingMessage} type="button">
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p>{message.question}</p>
                    )}
                    {message.imageAttachments?.length ? (
                      <div className="messageAttachments">
                        {message.imageAttachments.map((image) => (
                          <figure className="imagePreview" key={image.id}>
                            <button
                              aria-label={`Open ${image.filename}`}
                              className="imagePreviewButton"
                              onClick={() => setActiveImagePreview(image)}
                              type="button"
                            >
                              <img
                                alt={image.filename}
                                onError={(event) => {
                                  event.currentTarget.style.display = "none";
                                }}
                                src={imagePreviewSrc(image)}
                              />
                            </button>
                            <figcaption>{image.filename}</figcaption>
                          </figure>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="bubble agentBubble">
                    <span>Answer</span>
                    {message.response ? (
                      <MarkdownText text={message.response.answer} />
                    ) : message.error ? (
                      <p className="errorText">{message.error}</p>
                    ) : (
                      <p className="muted">Thinking...</p>
                    )}
                    {message.pendingAction ? (
                      <CalendarActionCard
                        action={message.pendingAction}
                        onCancel={() => cancelCalendarAction(message.id)}
                        onConfirm={() => void confirmMicrosoftAction(message.id, message.pendingAction!, message.question)}
                        result={message.actionResult}
                        status={message.actionStatus ?? "pending"}
                      />
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          {attachedImages.length || uploadError ? (
            <div className="attachmentTray">
              {attachedImages.map((image) => (
                <figure className="imagePreview attachmentPreview" key={image.id}>
                  <button
                    aria-label={`Open ${image.filename}`}
                    className="imagePreviewButton"
                    onClick={() => setActiveImagePreview(image)}
                    type="button"
                  >
                    <img
                      alt={image.filename}
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                      src={imagePreviewSrc(image)}
                    />
                  </button>
                  <figcaption>{image.filename}</figcaption>
                  <button onClick={() => removeAttachedImage(image.id)} type="button">
                    Remove
                  </button>
                </figure>
              ))}
              {uploadError ? <p className="errorText">{uploadError}</p> : null}
            </div>
          ) : null}
          <input
            aria-label="Question"
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Send a message to SupportAgent..."
            value={question}
          />
          <button disabled={isLoading || (question.trim().length === 0 && attachedImages.length === 0)} type="submit">
            Send
          </button>
          <div className="composerControls">
            <label className="composerChip uploadChip">
              {isUploadingImage ? "Uploading..." : "Image"}
              <input
                accept="image/jpeg,image/png,image/webp,image/gif"
                disabled={isUploadingImage}
                onChange={uploadImage}
                type="file"
              />
            </label>
            <div className="composerControl">
              <button
                aria-expanded={isModelSelectorOpen}
                className="composerChip modelChip"
                onClick={() => {
                  setIsModelSelectorOpen((current) => !current);
                  setIsSkillSelectorOpen(false);
                  setIsMcpSelectorOpen(false);
                }}
                type="button"
              >
                {selectedModel}
              </button>
              {isModelSelectorOpen ? (
                <div className="mcpMenu modelMenu">
                  <div className="mcpMenuHeader">
                    <span>Model</span>
                  </div>
                  {models.length ? (
                    models.map((model) => (
                      <label key={model.id}>
                        <input
                          checked={selectedModel === model.id}
                          onChange={() => {
                            setSelectedModel(model.id);
                            setIsModelSelectorOpen(false);
                          }}
                          type="radio"
                        />
                        <span>{model.label}</span>
                        <small>{model.default ? "default" : "available"}</small>
                      </label>
                    ))
                  ) : (
                    <p className="muted">Models load after sign in.</p>
                  )}
                </div>
              ) : null}
            </div>
            <div className="composerControl">
              <button
                aria-expanded={isSkillSelectorOpen}
                className="composerChip"
                onClick={() => {
                  setIsSkillSelectorOpen((current) => !current);
                  setIsModelSelectorOpen(false);
                  setIsMcpSelectorOpen(false);
                }}
                type="button"
              >
                {selectedSkills.length ? `${selectedSkills.length} Skills` : "Skills"}
              </button>
              {isSkillSelectorOpen ? (
                <div className="mcpMenu skillMenu">
                  <div className="mcpMenuHeader">
                    <span>Skills</span>
                    <div>
                      <button onClick={clearSkills} type="button">
                        Clear
                      </button>
                    </div>
                  </div>
                  {skills.length ? (
                    skills.map((skill) => (
                      <label key={skill.skill_id}>
                        <input
                          checked={selectedSkills.includes(skill.skill_id)}
                          onChange={() => toggleSkill(skill.skill_id)}
                          type="checkbox"
                        />
                        <span>{skill.name}</span>
                        <small>{skill.category}</small>
                        <em>{skill.description}</em>
                      </label>
                    ))
                  ) : (
                    <p className="muted">Skills load after sign in.</p>
                  )}
                </div>
              ) : null}
            </div>
            <div className="composerControl">
              <button
                aria-expanded={isMcpSelectorOpen}
                className="composerChip"
                onClick={() => {
                  setIsMcpSelectorOpen((current) => !current);
                  setIsModelSelectorOpen(false);
                  setIsSkillSelectorOpen(false);
                }}
                type="button"
              >
                {selectedMcpServers.length ? `${selectedMcpServers.length} MCP` : "MCP"}
              </button>
              {isMcpSelectorOpen ? (
                <div className="mcpMenu">
                  <div className="mcpMenuHeader">
                    <span>MCP Servers</span>
                    <div>
                      <button onClick={selectAllMcpServers} type="button">
                        All
                      </button>
                      <button onClick={clearMcpServers} type="button">
                        None
                      </button>
                    </div>
                  </div>
                  {mcpServers.length ? (
                    mcpServers.map((server) => (
                      <label key={server.server_name}>
                        <input
                          checked={selectedMcpServers.includes(server.server_name)}
                          disabled={!server.enabled}
                          onChange={() => toggleMcpServer(server.server_name)}
                          type="checkbox"
                        />
                        <span>{server.display_name || server.server_name}</span>
                        <small>{server.enabled ? server.transport : "disabled"}</small>
                      </label>
                    ))
                  ) : (
                    <p className="muted">MCP servers load after sign in.</p>
                  )}
                </div>
              ) : null}
            </div>
            <button
              className="composerChip"
              onClick={() => setIsMcpCenterOpen(true)}
              type="button"
            >
              Manage MCP
            </button>
          </div>
        </form>
      </section>

      <aside className={`inspector ${isMcpCenterOpen ? "open" : ""}`}>
        <div className="drawerHeader">
          <div>
            <p className="eyebrow">Application center</p>
            <h2>MCP Servers</h2>
          </div>
          <button onClick={() => setIsMcpCenterOpen(false)} type="button">
            Close
          </button>
        </div>
        <section className="inspectorSection" id="trace">
          <p className="panelTitle">Agent trace</p>
          {activeMessage?.response ? (
            <dl className="traceList">
              <div>
                <dt>Model</dt>
                <dd>{activeMessage.response.trace.model}</dd>
              </div>
              <div>
                <dt>Images</dt>
                <dd>{activeMessage.response.trace.image_count}</dd>
              </div>
              <div>
                <dt>Route</dt>
                <dd>{activeMessage.response.trace.route_source}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>{activeMessage.response.trace.evidence_status}</dd>
              </div>
              <div>
                <dt>Short memory</dt>
                <dd>{activeMessage.response.trace.short_memory_count}</dd>
              </div>
              <div>
                <dt>Long memory</dt>
                <dd>{activeMessage.response.trace.long_memory_count}</dd>
              </div>
              <div>
                <dt>Rewrite</dt>
                <dd>{activeMessage.response.trace.rewrite_changed ? "yes" : "no"}</dd>
              </div>
              <div>
                <dt>Query</dt>
                <dd>{activeMessage.response.trace.rewritten_query}</dd>
              </div>
              <div>
                <dt>MCP tools</dt>
                <dd>
                  {activeMessage.response.trace.mcp_tool_calls.length
                    ? activeMessage.response.trace.mcp_tool_calls
                        .map((toolCall) => `${toolCall.server}/${toolCall.tool}`)
                        .join(", ")
                    : "none"}
                </dd>
              </div>
              <div>
                <dt>Skills</dt>
                <dd>
                  {activeMessage.response.trace.enabled_skills.length
                    ? activeMessage.response.trace.enabled_skills.join(", ")
                    : "none"}
                </dd>
              </div>
              {activeMessage.response.trace.mcp_error ? (
                <div>
                  <dt>MCP error</dt>
                  <dd>{activeMessage.response.trace.mcp_error}</dd>
                </div>
              ) : null}
            </dl>
          ) : (
            <p className="muted">Trace appears after the first answer.</p>
          )}
        </section>

        <section className="inspectorSection" id="mcp-manager">
          <p className="panelTitle">MCP center</p>
          <div className="mcpSummary">
            <div>
              <strong>{mcpServers.filter((server) => server.enabled).length}</strong>
              <span>servers</span>
            </div>
            <div>
              <strong>{mcpTools.length}</strong>
              <span>tools</span>
            </div>
            <div>
              <strong>{selectedMcpServers.length}</strong>
              <span>selected</span>
            </div>
          </div>
          <div className="mcpTabs" role="tablist" aria-label="MCP panels">
            {(["actions", "servers", "tools", "audit", "debug"] as const).map((tab) => (
              <button
                className={mcpPanelTab === tab ? "selected" : ""}
                key={tab}
                onClick={() => setMcpPanelTab(tab)}
                type="button"
              >
                {tab}
              </button>
            ))}
          </div>

          {mcpPanelTab === "actions" ? (
            <div className="mcpPanel actionPanel">
              <div className="actionGroup">
                <h3>Microsoft account</h3>
                <button
                  disabled={isToolLoading}
                  onClick={() => void runMcpAction("get_my_profile", {})}
                  type="button"
                >
                  Get my profile
                </button>
              </div>

              <div className="actionGroup">
                <h3>Calendar</h3>
                <button
                  disabled={isToolLoading}
                  onClick={() => void runMcpAction("get_calendars_list", { user_id: "me" })}
                  type="button"
                >
                  List calendars
                </button>
                <label>
                  Calendar name
                  <input
                    onChange={(event) => setActionCalendarName(event.target.value)}
                    value={actionCalendarName}
                  />
                </label>
                <button
                  disabled={isToolLoading}
                  onClick={() =>
                    void runMcpAction(
                      "create_calendar",
                      { user_id: "me", name: actionCalendarName },
                      true
                    )
                  }
                  type="button"
                >
                  Create calendar
                </button>
              </div>

              <div className="actionGroup">
                <h3>OneDrive</h3>
                <button
                  disabled={isToolLoading}
                  onClick={() => void runMcpAction("list_folder_files", { user_id: "me", folder_path: "root" })}
                  type="button"
                >
                  List root files
                </button>
                <label>
                  Folder name
                  <input
                    onChange={(event) => setActionFolderName(event.target.value)}
                    value={actionFolderName}
                  />
                </label>
                <button
                  disabled={isToolLoading}
                  onClick={() =>
                    void runMcpAction(
                      "create_folder",
                      { user_id: "me", name: actionFolderName },
                      true
                    )
                  }
                  type="button"
                >
                  Create folder
                </button>
                <label>
                  Document name
                  <input
                    onChange={(event) => setActionDocumentName(event.target.value)}
                    value={actionDocumentName}
                  />
                </label>
                <label>
                  Document content
                  <textarea
                    onChange={(event) => setActionDocumentContent(event.target.value)}
                    value={actionDocumentContent}
                  />
                </label>
                <button
                  disabled={isToolLoading}
                  onClick={() =>
                    void runMcpAction(
                      "create_document",
                      {
                        user_id: "me",
                        name: actionDocumentName,
                        content: actionDocumentContent,
                        folder_path: actionFolderName
                      },
                      true
                    )
                  }
                  type="button"
                >
                  Create document
                </button>
              </div>

              {toolError ? <p className="errorText">{toolError}</p> : null}
              {toolResult ? <pre className="toolResult">{toolResult}</pre> : null}
            </div>
          ) : null}

          {mcpPanelTab === "servers" ? (
            <div className="mcpPanel">
              <div className="serverList">
                {mcpServers.map((server) => (
                  <button
                    className={selectedMcpServers.includes(server.server_name) ? "selected" : ""}
                    key={server.server_name}
                    onClick={() => editMcpServer(server)}
                    type="button"
                  >
                    <strong>{server.display_name || server.server_name}</strong>
                    <small>
                      {server.server_name} / {server.transport} / {server.enabled ? "enabled" : "disabled"}
                    </small>
                    <span>{toolsByServer.get(server.server_name)?.length ?? 0} tools</span>
                  </button>
                ))}
              </div>

              <div className="mcpForm">
                <div className="mcpFormToolbar">
                  <button onClick={insertLocalWeatherConfig} type="button">
                    Local example
                  </button>
                  <button onClick={insertRemoteExampleConfig} type="button">
                    Remote example
                  </button>
                </div>
                <label>
                  Server name
                  <input
                    onChange={(event) => setServerFormName(event.target.value)}
                    placeholder="weather_mcp"
                    value={serverFormName}
                  />
                </label>
                <label>
                  Display name
                  <input
                    onChange={(event) => setServerFormDisplayName(event.target.value)}
                    placeholder="Local Weather MCP"
                    value={serverFormDisplayName}
                  />
                </label>
                <label>
                  Transport
                  <select
                    onChange={(event) => setServerFormTransport(event.target.value)}
                    value={serverFormTransport}
                  >
                    <option value="stdio">stdio</option>
                    <option value="sse">sse</option>
                    <option value="streamable_http">streamable_http</option>
                  </select>
                </label>
                <label className="checkboxRow">
                  <input
                    checked={serverFormEnabled}
                    onChange={(event) => setServerFormEnabled(event.target.checked)}
                    type="checkbox"
                  />
                  Enabled
                </label>
                <label>
                  Server config JSON
                  <textarea
                    onChange={(event) => setServerFormConfig(event.target.value)}
                    spellCheck={false}
                    value={serverFormConfig}
                  />
                </label>
                <button onClick={() => void saveMcpServer()} type="button">
                  Save server
                </button>
                {serverFormStatus ? <p className="muted">{serverFormStatus}</p> : null}
              </div>
            </div>
          ) : null}

          {mcpPanelTab === "tools" ? (
            <div className="mcpPanel">
              {mcpServers.map((server) => (
                <details className="toolGroup" key={server.server_name} open={selectedMcpServers.includes(server.server_name)}>
                  <summary>
                    <span>{server.server_name}</span>
                    <small>{toolsByServer.get(server.server_name)?.length ?? 0} tools from list_tools</small>
                  </summary>
                  {(toolsByServer.get(server.server_name) ?? []).map((tool) => (
                    <div className="toolCard" key={toolKey(tool)}>
                      <strong>{tool.name}</strong>
                      <p>{tool.description || "No description."}</p>
                      <div className="toolParams">
                        {tool.parameters.length ? (
                          tool.parameters.map((parameter) => (
                            <div key={parameter.name}>
                              <strong>{parameter.name}</strong>
                              <span>{parameter.required ? "required" : "optional"}</span>
                              <small>{parameter.type}</small>
                            </div>
                          ))
                        ) : (
                          <small className="muted">No parameters.</small>
                        )}
                      </div>
                    </div>
                  ))}
                </details>
              ))}
            </div>
          ) : null}

          {mcpPanelTab === "audit" ? (
            <div className="mcpPanel">
              {mcpAuditLogs.length ? (
                <div className="auditList">
                  {mcpAuditLogs.slice(0, 8).map((record) => (
                    <div key={record.id}>
                      <strong>{record.server_name}/{record.tool_name}</strong>
                      <span>{record.status}</span>
                      {record.error ? <small>{record.error}</small> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Tool calls will be audited here.</p>
              )}
            </div>
          ) : null}

          {mcpPanelTab === "debug" ? (
            <div className="mcpPanel">
              {mcpTools.length ? (
                <div className="toolRunner">
                  <label>
                    Tool
                    <select
                      onChange={(event) => selectMcpTool(event.target.value)}
                      value={selectedToolKey}
                    >
                      {mcpTools.map((tool) => (
                        <option key={toolKey(tool)} value={toolKey(tool)}>
                          {tool.server} / {tool.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {selectedTool ? (
                    <>
                      <p className="toolDescription">{selectedTool.description}</p>
                      <div className="toolPolicy">
                        <span>{selectedPolicy?.enabled === false ? "disabled" : "enabled"}</span>
                        <span>{selectedPolicy?.auto_allowed ? "auto" : "manual"}</span>
                        <span>{selectedPolicy?.requires_confirmation ? "confirm" : "no confirm"}</span>
                      </div>
                      <label>
                        Arguments
                        <textarea
                          onChange={(event) => setToolArguments(event.target.value)}
                          spellCheck={false}
                          value={toolArguments}
                        />
                      </label>
                      <button disabled={isToolLoading} onClick={() => void runMcpTool()} type="button">
                        {isToolLoading ? "Running" : "Run tool"}
                      </button>
                      <label>
                        Server credentials
                        <textarea
                          onChange={(event) => setCredentialJson(event.target.value)}
                          placeholder='{"api_key":"..."} or {"access_token":"..."}'
                          spellCheck={false}
                          value={credentialJson}
                        />
                      </label>
                      <button onClick={() => void saveMcpCredentials()} type="button">
                        Save credentials
                      </button>
                      {credentialStatus ? <p className="muted">{credentialStatus}</p> : null}
                      {toolError ? <p className="errorText">{toolError}</p> : null}
                      {toolResult ? <pre className="toolResult">{toolResult}</pre> : null}
                    </>
                  ) : null}
                </div>
              ) : (
                <p className="muted">Tool list appears after sign in.</p>
              )}
            </div>
          ) : null}
        </section>

        <section className="inspectorSection" id="sources">
          <p className="panelTitle">Sources</p>
          {activeMessage?.response?.sources.length ? (
            <div className="sourceList">
              {activeMessage.response.sources.map((source) => (
                <details key={source.id}>
                  <summary>
                    <span>{source.title}</span>
                    <small>{source.source}</small>
                  </summary>
                  <p>{source.content}</p>
                  <a href={source.url} rel="noreferrer" target="_blank">
                    Open original
                  </a>
                </details>
              ))}
            </div>
          ) : (
            <p className="muted">Cited chunks will show here.</p>
          )}
        </section>

      </aside>
      {activeImagePreview ? (
        <div
          aria-modal="true"
          className="imageViewer"
          onClick={() => setActiveImagePreview(null)}
          role="dialog"
        >
          <div className="imageViewerFrame" onClick={(event) => event.stopPropagation()}>
            <button
              aria-label="Close image preview"
              className="imageViewerClose"
              onClick={() => setActiveImagePreview(null)}
              type="button"
            >
              Close
            </button>
            <img alt={activeImagePreview.filename} src={imagePreviewSrc(activeImagePreview)} />
            <p>{activeImagePreview.filename}</p>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function hydrateMessages(storedMessages: StoredThreadMessage[]): Message[] {
  const messages: Message[] = [];

  for (let index = 0; index < storedMessages.length; index += 1) {
    const current = storedMessages[index];
    const next = storedMessages[index + 1];

    if (current.role !== "user") {
      continue;
    }

    const message: Message = {
      id: `${current.id ?? current.created_at}-${index}`,
      storedUserMessageId: current.id ?? undefined,
      question: current.content
    };

    if (next?.role === "assistant") {
      message.response = {
        answer: next.content,
        sources: [],
        trace: {
          thread_id: null,
          short_memory_count: 0,
          long_memory_count: 0,
          route_source: "restored",
          route_reason: "Loaded from stored conversation history.",
          rewrite_changed: false,
          rewritten_query: current.content,
          evidence_status: "restored",
          evidence_reason: "Sources and trace are available for newly generated answers.",
          mcp_tool_calls: [],
          mcp_error: null,
          enabled_skills: [],
          model: "restored",
          image_count: 0
        }
      };
      index += 1;
    }

    messages.push(message);
  }

  return messages;
}

function toolKey(tool: Pick<McpTool, "server" | "name">): string {
  return `${tool.server}:${tool.name}`;
}

function formatToolArguments(argumentsObject: Record<string, unknown>): string {
  return JSON.stringify(argumentsObject, null, 2);
}

function imagePreviewSrc(image: UploadedImage): string {
  if (image.local_preview_url) {
    return image.local_preview_url;
  }
  return `/api${image.preview_url || `/uploads/image/${image.id}`}`;
}

function parseMicrosoftAction(text: string): MicrosoftAction | null {
  return parseCreateCalendarAction(text) ?? parseCalendarEventAction(text);
}

function parseCreateCalendarAction(text: string): CreateCalendarAction | null {
  const lower = text.toLowerCase();
  const mentionsCalendarContainer = /(kalender|calendar)/i.test(text);
  const mentionsCreate = /(erstell|anleg|hinzuf|create|add|new)/i.test(text);
  const mentionsEvent = /(termin|event|meeting|besprechung)/i.test(text);
  const hasDateOrTime =
    /(\d{1,2})[./-](\d{1,2})[./-](\d{4})/.test(text) ||
    extractTimeMatch(text) !== null;
  if (!mentionsCalendarContainer || !mentionsCreate || mentionsEvent || hasDateOrTime) {
    return null;
  }

  const nameMatch =
    text.match(/(?:namens|called|heisst|heißt)\s+([^,;.]+)/i) ??
    text.match(/(?:name|titel|title)\s*[:=]\s*([^,;.]+)/i) ??
    text.match(/(?:kalender|calendar)\s+(?:fuer|für)?\s*([^,;.]+)/i);
  const name = nameMatch?.[1]?.trim() || (lower.includes("interview") ? "Interview Prep" : "");
  if (!name) {
    return null;
  }

  return {
    type: "create_calendar",
    name,
  };
}

function parseCalendarEventAction(text: string): CalendarEventAction | null {
  const lower = text.toLowerCase();
  const looksLikeCalendarAction =
    /(termin|kalender|calendar|event)/i.test(text) &&
    /(hinzuf|eintrag|erstell|add|create|schedule)/i.test(text);
  if (!looksLikeCalendarAction) {
    return null;
  }

  const dateMatch = text.match(/(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
  const timeMatch = extractTimeMatch(text);
  if (!dateMatch || !timeMatch) {
    return null;
  }

  const day = dateMatch[1].padStart(2, "0");
  const month = dateMatch[2].padStart(2, "0");
  const year = dateMatch[3];
  const hour = timeMatch[1].padStart(2, "0");
  const minute = (timeMatch[2] ?? "00").padStart(2, "0");
  const endHour = String(Math.min(Number(hour) + 1, 23)).padStart(2, "0");

  let subject = "Termin";
  const titleMatch =
    text.match(/(?:titel|title|betreff|subject)\s*[:=]\s*([^,;.]+)/i) ??
    text.match(/(?:namens|called|heisst|heißt)\s+([^,;.]+)/i);
  if (titleMatch?.[1]) {
    subject = titleMatch[1].trim();
  } else if (lower.includes("interview")) {
    subject = "Interview";
  }

  return {
    type: "create_calendar_event",
    subject,
    date: `${year}-${month}-${day}`,
    startTime: `${hour}:${minute}`,
    endTime: `${endHour}:${minute}`,
    timezone: "W. Europe Standard Time",
  };
}

function extractTimeMatch(text: string): RegExpMatchArray | null {
  return (
    text.match(/(?:um\s+)(\d{1,2})(?::|\.)(\d{2})/i) ??
    text.match(/(?:um\s+)(\d{1,2})(?:\s*uhr)?/i) ??
    text.match(/\b(\d{1,2}):(\d{2})\b/)
  );
}

function CalendarActionCard({
  action,
  onCancel,
  onConfirm,
  result,
  status,
}: {
  action: MicrosoftAction;
  onCancel: () => void;
  onConfirm: () => void;
  result?: string;
  status: "pending" | "running" | "done" | "cancelled" | "error";
}) {
  return (
    <div className="confirmationCard">
      <strong>Microsoft Calendar Aktion</strong>
      {action.type === "create_calendar" ? (
        <dl>
          <div>
            <dt>Aktion</dt>
            <dd>Kalender erstellen</dd>
          </div>
          <div>
            <dt>Name</dt>
            <dd>{action.name}</dd>
          </div>
          <div>
            <dt>Konto</dt>
            <dd>Verbundenes Microsoft Konto</dd>
          </div>
        </dl>
      ) : (
        <dl>
          <div>
            <dt>Aktion</dt>
            <dd>Termin erstellen</dd>
          </div>
          <div>
            <dt>Titel</dt>
            <dd>{action.subject}</dd>
          </div>
          <div>
            <dt>Datum</dt>
            <dd>{action.date}</dd>
          </div>
          <div>
            <dt>Zeit</dt>
            <dd>{action.startTime} - {action.endTime}</dd>
          </div>
          <div>
            <dt>Kalender</dt>
            <dd>Standardkalender</dd>
          </div>
        </dl>
      )}
      {status === "pending" ? (
        <div className="confirmationActions">
          <button onClick={onConfirm} type="button">Bestaetigen</button>
          <button onClick={onCancel} type="button">Abbrechen</button>
        </div>
      ) : null}
      {status === "running" ? <p className="muted">Aktion wird ausgefuehrt...</p> : null}
      {status === "done" ? <p className="muted">Aktion wurde ausgefuehrt.</p> : null}
      {status === "cancelled" ? <p className="muted">Aktion abgebrochen.</p> : null}
      {status === "error" ? <p className="errorText">{result}</p> : null}
    </div>
  );
}

function MarkdownText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let currentList: string[] = [];

  function flushList(keyPrefix: string) {
    if (!currentList.length) {
      return;
    }
    blocks.push(
      <ul key={`${keyPrefix}-list-${blocks.length}`}>
        {currentList.map((item, index) => (
          <li key={`${keyPrefix}-item-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    currentList = [];
  }

  text.split(/\n+/).forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList(`line-${index}`);
      return;
    }
    if (trimmed.startsWith("- ")) {
      currentList.push(trimmed.slice(2));
      return;
    }
    flushList(`line-${index}`);
    blocks.push(<p key={`line-${index}`}>{renderInlineMarkdown(trimmed)}</p>);
  });
  flushList("end");

  return <div className="markdownAnswer">{blocks}</div>;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
