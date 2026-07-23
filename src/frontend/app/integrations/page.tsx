"use client";

import { CloudSun, PlugZap, RefreshCw, Server, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyWorkspace, HarnessBadge, OperationsPageHeader, OperationsShell } from "../components/operations-shell";

type McpParameter = {
  name: string;
  type: string;
  required: boolean;
  description: string | null;
};

type McpTool = {
  server: string;
  name: string;
  description: string;
  parameters: McpParameter[];
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
  enabled: boolean;
};

export default function IntegrationsPage() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [tools, setTools] = useState<McpTool[]>([]);
  const [policies, setPolicies] = useState<McpPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedServer, setSelectedServer] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [serverResponse, toolResponse] = await Promise.all([
        fetch("/api/mcp/servers", { cache: "no-store" }),
        fetch("/api/mcp/tools", { cache: "no-store" })
      ]);
      if (!serverResponse.ok || !toolResponse.ok) {
        throw new Error(`Integration discovery failed (${serverResponse.status}/${toolResponse.status})`);
      }
      const serverPayload = (await serverResponse.json()) as { servers: McpServer[]; policies: McpPolicy[] };
      const toolPayload = (await toolResponse.json()) as { tools: McpTool[] };
      setServers(serverPayload.servers);
      setPolicies(serverPayload.policies);
      setTools(toolPayload.tools);
      setSelectedServer((current) => current ?? serverPayload.servers[0]?.server_name ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load integrations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const toolsByServer = useMemo(() => {
    const grouped = new Map<string, McpTool[]>();
    for (const tool of tools) {
      grouped.set(tool.server, [...(grouped.get(tool.server) ?? []), tool]);
    }
    return grouped;
  }, [tools]);
  const activeTools = selectedServer ? toolsByServer.get(selectedServer) ?? [] : [];

  function policyFor(tool: McpTool) {
    return policies.find((policy) => policy.server_name === tool.server && policy.tool_name === tool.name);
  }

  return (
    <OperationsShell active="integrations">
      <OperationsPageHeader
        actions={
          <>
            <a className="opsPrimaryButton" href="/api/auth/microsoft/start"><PlugZap size={14} /> Connect Microsoft</a>
            <button className="opsSecondaryButton" disabled={loading} onClick={() => void load()} type="button">
              <RefreshCw size={14} /> Discover tools
            </button>
          </>
        }
        description="MCP servers, dynamically discovered tools, and execution policy."
        eyebrow="Harness"
        title="Integrations"
      />

      <div className="opsPageContent">
        <section className="opsMetrics">
          <article><span>Configured servers</span><strong>{servers.length}</strong></article>
          <article><span>Enabled servers</span><strong>{servers.filter((server) => server.enabled).length}</strong></article>
          <article><span>Discovered tools</span><strong>{tools.length}</strong></article>
          <article><span>Confirmation required</span><strong>{policies.filter((policy) => policy.requires_confirmation).length}</strong></article>
        </section>

        {error ? <div className="opsInlineError"><span>{error}</span></div> : null}
        <div className="integrationColumns">
          <section className="opsPanel integrationServers">
            <header className="opsPanelHeader"><div><h2>MCP servers</h2><p>Capabilities are loaded from each server through list_tools.</p></div></header>
            {loading ? <p className="opsLoading">Discovering integrations…</p> : null}
            {!loading && !servers.length ? (
              <EmptyWorkspace icon="integration" title="No MCP servers configured" description="Configured servers will appear here after the backend registry is initialized." />
            ) : null}
            <div className="integrationServerList">
              {servers.map((server) => {
                const toolCount = toolsByServer.get(server.server_name)?.length ?? 0;
                const WeatherIcon = server.server_name.includes("weather") ? CloudSun : Server;
                return (
                  <button
                    className={selectedServer === server.server_name ? "active" : ""}
                    key={server.server_name}
                    onClick={() => setSelectedServer(server.server_name)}
                    type="button"
                  >
                    <span className="integrationIcon"><WeatherIcon size={15} /></span>
                    <div>
                      <strong>{server.display_name}</strong>
                      <small>{server.server_name} · {server.transport}</small>
                    </div>
                    <div className="integrationCount">
                      <HarnessBadge tone={server.enabled ? "good" : "neutral"}>{server.enabled ? "Enabled" : "Disabled"}</HarnessBadge>
                      <span>{toolCount} tools</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="opsPanel integrationTools">
            <header className="opsPanelHeader">
              <div>
                <h2>{servers.find((server) => server.server_name === selectedServer)?.display_name ?? "Discovered tools"}</h2>
                <p>Tool schemas are read from the selected MCP server; policies are enforced by the backend.</p>
              </div>
              {selectedServer ? <HarnessBadge tone="info">{selectedServer}</HarnessBadge> : null}
            </header>
            {!loading && !activeTools.length ? (
              <EmptyWorkspace icon="integration" title="No tools discovered" description="The selected server did not return any enabled tools." />
            ) : null}
            <div className="integrationToolList">
              {activeTools.map((tool) => {
                const policy = policyFor(tool);
                return (
                  <article key={`${tool.server}:${tool.name}`}>
                    <div className="integrationToolHead">
                      <span className="integrationIcon"><Wrench size={14} /></span>
                      <div><code>{tool.name}</code><p>{tool.description}</p></div>
                    </div>
                    <div className="integrationPolicy">
                      <HarnessBadge tone={policy?.enabled === false ? "bad" : "good"}>{policy?.enabled === false ? "Disabled" : "Enabled"}</HarnessBadge>
                      <HarnessBadge tone={policy?.requires_confirmation ? "warn" : "neutral"}>
                        {policy?.requires_confirmation ? "Confirmation" : "No confirmation"}
                      </HarnessBadge>
                      <HarnessBadge tone={policy?.auto_allowed ? "info" : "neutral"}>
                        {policy?.auto_allowed ? "Auto allowed" : "Manual route"}
                      </HarnessBadge>
                    </div>
                    <div className="integrationParameters">
                      {tool.parameters.length ? tool.parameters.map((parameter) => (
                        <span key={parameter.name}>
                          <code>{parameter.name}</code>
                          <small>{parameter.type}{parameter.required ? " · required" : ""}</small>
                        </span>
                      )) : <em>No parameters</em>}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </OperationsShell>
  );
}
