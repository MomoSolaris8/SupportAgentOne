# PPT 内容：SupportAgent — Agent AI 落地实战 / Harness Engineering in der Praxis

> 用法：每个 `## Folie` 是一页。标题德语（瑞士面试用），要点中文（你自己讲），关键句给了德语口播版。

---

## Folie 1 — Titel

**AI Agents in Production: Model × Harness**
SupportAgent — Ein Versicherungs-Claim-Agent mit RAG, MCP und Human-in-the-Loop

副标题口播（DE）：
"Heute zeige ich nicht nur, *was* mein Agent kann, sondern *warum* er zuverlässig ist — das ist der Unterschied zwischen einem Demo und einem Produkt."

---

## Folie 2 — Kernthese / 核心论点

**Agent = Model × Harness**

- 同一个模型、不同的 Harness，产品效果天差地别。这个差距就是 Harness Engineering 要填补的工程鸿沟。
- Harness 拆成两部分：
  - **Environment（手脚）**：上下文、工具、记忆 → 让 Agent 能干事
  - **Zügel（缰绳）**：约束、验证、纠正 → 让 Agent 不出错
- 只有上下文和工具 = 失控的天才；只有约束 = 安全的废物。两者缺一不可。

口播（DE）: "Gleiche Modelle, unterschiedliche Harnesses — völlig unterschiedliche Produkte. Diese Lücke füllt Harness Engineering."

---

## Folie 3 — Agenda（5 部分）

1. Was ist Harness Engineering?
2. Den Agent **fähig** machen — Kontext, Tools (MCP), Memory, RAG
3. Den Agent **zuverlässig** machen — Constraints, Validierung, Human-in-the-Loop
4. Produkt bauen wie Forschung — Offline Evals, Observability
5. Ausblick — Sandbox, Business Workflows, was ich daraus lerne

---

## Folie 4 — 项目一句话 + Live Demo 预告

**SupportAgent**：面向保险场景的 AI Agent 平台 —— RAG 知识问答 + Claim 审查 Workflow + MCP 工具调用 + 双层记忆 + 离线评估。

Tech Stack: FastAPI + LangGraph + Postgres/pgvector + Next.js + MCP (stdio) + Langfuse

Live Demo 将展示：
1. "Wie spät ist es?" / "Wie ist das Wetter heute in Zürich?" → Agent 自动路由到 MCP 工具
2. 保险知识问答 → RAG 检索 + 引用来源，证据不足时**拒答**而不是编造
3. Claim 审查 → LangGraph Workflow 产出 ProposedAction，人工批准后才执行

---

## Folie 5 — System-Architektur（架构图，见文末 ASCII，可直接重画）

分层讲法（从上往下）：

- **Frontend**: Next.js（operations-shell、Claims、Approvals、Audit 页面），API routes 做 proxy
- **API Layer**: FastAPI 薄控制器 — `api/ask.py` 只做参数校验，业务在下层
- **Agent Layer**: LangGraph StateGraph — `agent/workflow.py`，8 个节点、2 个条件分支
- **Capability Layer**:
  - RAG: `rag/`（chunking → embedding → pgvector → retrieval）
  - MCP Client: `mcp_client/tool_agent.py` 动态 tool-calling loop
  - Memory: `memory/`（short + long）
  - LLM Registry: `llm/registry.py` 多 provider（Qwen/OpenAI/Anthropic/Kimi），按任务分模型策略（CHAT / CLAIM_REVIEW / TOOL / VISION）
- **MCP Servers（独立进程, stdio）**: time_mcp / weather_mcp / teams_mcp
- **Data**: Postgres + pgvector（chunks、messages、long memories、claims、audit log 全在一个库）
- **Observability**: Langfuse + structured logging

---

## Folie 6 — Ausführungspfad einer Anfrage（一条请求的执行路径）

```
POST /ask
  └─ answer_with_agent()            agent/workflow.py
       ├─ load_memory      读 thread 短期历史 + pgvector 语义召回长期记忆
       ├─ mcp_tools        动态 MCP agent：能答就直接结束（时间/天气/Teams）
       │     └─(条件分支) 工具已给出答案 → END；否则继续
       ├─ route            规则路由：Confluence / Jira / both
       ├─ rewrite          LLM query rewrite（多轮指代消解）
       ├─ retrieve         pgvector 相似度检索
       ├─ check_evidence   证据门控
       │     └─(条件分支) insufficient → refuse_answer（固定拒答文案）
       └─ generate_answer  带引用生成 + 二次自检（回答里承认证据不足 → 状态改写）
```

讲点：**每个节点单一职责、可单测；条件分支就是"缰绳"**。

---

## TEIL 2: Den Agent fähig machen（Environment / 手脚）

## Folie 7 — MCP: 3 eigene Server, 21 Tools

我自己写了 3 个 MCP Server（FastMCP, stdio transport，可切 sse/http）：

| Server | Tools | 说明 |
|---|---|---|
| time_mcp | get_current_time | 时区感知 |
| weather_mcp | get_weather | 双 provider：有 API key 用商业接口，没有降级 Open-Meteo |
| teams_mcp | 19 个 tools | Microsoft Graph：Calendar CRUD、OneDrive 文档/文件夹、Chat 消息、用户 Profile |

工程细节（面试官会追问的）：
- **凭证注入**：`tool_agent.py::_tool_schema` 把 `access_token`/`api_key` 从暴露给 LLM 的 schema 里**剥掉**，由服务端按用户注入 → 模型永远拿不到 secret
- **工具白名单**：`mcp_client/config.py::READ_ONLY_TOOLS` — 只有只读工具允许自动执行，写操作走审批
- **审计**：每次 tool call 写 audit log，前端有 Audit 页面

口播（DE）: "Das Modell sieht nie ein Access-Token — Credentials werden serverseitig injiziert. Das ist Harness, nicht Prompt-Engineering."

---

## Folie 8 — Memory: Short + Long

两层记忆（`memory/service.py::load_memory_context`）：

- **Short Memory**：当前 thread 的对话历史（Postgres，按 thread_id），解决多轮上下文
- **Long Memory**：跨会话用户记忆，**embedding + pgvector 语义检索** —— 不是全量塞 prompt，而是按当前问题召回相关记忆
- History 处理：消息可编辑/删除（`update_user_message` / `delete_user_turn`），thread 列表带消息数

讲点：记忆失败时 **fail-open**（异常 → 返回空记忆，主流程不挂），这也是 Harness 思维：辅助能力的故障不能拖垮核心链路。

---

## Folie 9 — RAG + Multi-LLM Registry

- RAG pipeline: Confluence/Jira 真实数据 → chunking → embedding → pgvector → retrieval（`rag/`）
- Query rewrite 节点先做指代消解，再检索
- **LLM Registry**（`llm/registry.py`）：Qwen / OpenAI / Anthropic / Kimi 多 provider；关键设计：**按任务定模型策略** —— `CLAIM_REVIEW_MODEL`、`TOOL_MODEL`、`VISION_MODEL` 是后端锁定的，用户在 UI 换聊天模型不影响业务任务模型
- Vision: 图片上传 → vision service 提取上下文进 Agent state

---

## TEIL 3: Den Agent zuverlässig machen（Zügel / 缰绳）

## Folie 10 — Constraints & Validierung（约束与验证）

四道缰绳，全部是**确定性代码**，不是 prompt：

1. **Evidence Gate**（`agent/evidence.py`）：检索证据不足 → 直接拒答固定文案，宁可不答不编造。生成后还有二次自检：回答里承认证据不足 → 状态改写为 insufficient
2. **State Machine**（`claims/state_machine.py::CLAIM_TRANSITIONS`）：Claim 状态转移显式建模成表，非法转移直接抛异常 —— LLM 无法让 Claim 跳过流程
3. **Human-in-the-Loop**：所有写操作初始状态强制 `WAITING_FOR_APPROVAL`（`initial_action_status`），模型只能**提议** ProposedAction，人批准后确定性代码才执行
4. **Tool 白名单 + Audit Log**：只读工具自动放行，写工具必须走审批，全部留痕

口播（DE）: "Die LLM darf vorschlagen — ausführen darf nur deterministischer Code nach menschlicher Freigabe."

---

## Folie 11 — LLM 与业务代码的职责边界（这页最能体现 SDE 功底）

LLM 负责（模糊问题）：理解自然语言（"morgen Nachmittag"）、生成 Agenda/摘要、判断路由意图
确定性代码负责（正确性问题）：日期校验、邮箱校验、状态转移、必填字段检查、创建 ProposedAction、调用外部 API

原则：**凡是能用代码验证的，绝不交给模型自由发挥。**

---

## TEIL 4: Produkt bauen wie Forschung

## Folie 12 — Offline Evals + Tests + Observability

- **离线评估**（`evaluation/runner.py`）：claim review 用 JSONL 数据集（`evals/*.jsonl`）跑回归，输出带**阈值的指标报告**（minimum/maximum metric）+ 数据集指纹（fingerprint）→ 改 prompt/模型前后可对比，防回退
- **在线评估**：`evaluation/online_runner.py` + 成本核算（`pricing.py`）
- **测试**：28 个测试文件、100+ 单测，覆盖 workflow、router、state machine、每个 MCP server、auth security
- **Observability**：Langfuse trace（`record_langfuse_trace`）记录每次请求的 route 决策、rewrite、evidence 状态、chunk 数、每个 tool call、模型、memory 命中数 → 线上任何一次回答都能还原"Agent 当时为什么这么做"

口播（DE）: "Jede Antwort in Produktion ist nachvollziehbar: welche Route, welche Evidenz, welche Tools — vollständig getraced."

---

## TEIL 5: Ausblick

## Folie 13 — Nächster Schritt 1: Business Workflow "Expertenprüfung koordinieren"

目标体验：用户在 Claim 页输入一句 "Bitte koordiniere die Expertenprüfung morgen Nachmittag"，Agent 自动：读案件 → 读审查结果 → 找负责人和专家 → 生成 Agenda → 只追问缺失时间 → 显示可编辑业务卡片 → 确认后经 teams_mcp 创建 Outlook 日程 + Audit Log。

设计要点（不是加正则，而是升级为后端 Workflow）：
- 新增 `SCHEDULE_EXPERT_REVIEW` ActionType + `claim_team_members` 表
- 新 `expert_review_workflow.py`（LangGraph）：load_claim → load_review → build_agenda → resolve_schedule → validate → ProposedAction
- 复用现有缰绳：审批 → ActionExecutor 状态流转（APPROVED → EXECUTING → SUCCEEDED/FAILED）
- 前端只展示**业务卡片**（Termin/Teilnehmer/Agenda），不展示 MCP 参数

## Folie 14 — Nächster Schritt 2: Sandbox + Frontier Harness

- **Sandbox**：让 Agent 在隔离环境执行代码/文件操作 —— Environment 的下一块拼图（参考 Claude Code / OpenAI 的做法：能力越强，越需要隔离执行环境）
- 从 Claude Code 学到的 Harness 模式：工具结果缓存、并行 tool call、sub-agent 隔离上下文
- 消融实验思路：每个 Harness 组件（rewrite、evidence gate、memory）都可以单独开关量化贡献 —— eval runner 已具备基础

## Folie 15 — Schluss / 收尾

**Model × Harness = Agent.**

- 模型每 6 个月换一代，**Harness 是沉淀下来的工程资产**：状态机、审批流、评估集、审计、可观测性
- 我的核心心得：Agent 落地难点不在模型，在于**把不可靠的模型放进可靠的系统里**
- 基座模型公司做 Harness 有天然优势（模型和 Harness 协同训练），但**业务 Harness**（保险状态机、审批边界、领域评估集）永远长在业务方 —— 这正是 AI Application Engineer 的价值所在

口播（DE）: "Modelle werden ausgetauscht — der Harness bleibt. Genau dort liegt der Engineering-Wert."

---

---

# 附录 A：架构图（ASCII，可照此重画）

```
┌─────────────────────────── Frontend (Next.js) ───────────────────────────┐
│  Chat / Claims / Approvals / Audit / Integrations      API-Route-Proxy   │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │ POST /ask, /claims/*, /mcp/*
┌──────────────────────────────────▼────────────────────────────────────────┐
│                        Backend (FastAPI, thin controllers)                │
│  api/ask.py · api/claims.py · api/mcp.py · auth/ (Sessions, Microsoft)   │
└───────┬──────────────────────────┬───────────────────────────┬───────────┘
        │                          │                           │
┌───────▼────────────┐   ┌─────────▼───────────┐   ┌───────────▼─────────┐
│  Agent Workflow    │   │  Claim Review        │   │  Dynamic MCP Agent  │
│  (LangGraph)       │   │  Workflow (LangGraph)│   │  tool_agent.py      │
│  load_memory       │   │  documents → RAG     │   │  tool-calling loop  │
│  → mcp_tools ──────┼──►│  evidence → recommen-│   │  cred-injection     │
│  → route → rewrite │   │  dation → Proposed-  │   │  allowlist + audit  │
│  → retrieve        │   │  Action              │   └───────────┬─────────┘
│  → evidence gate   │   │  + State Machine     │               │ stdio
│  → answer/refuse   │   │  + Human Approval    │   ┌───────────▼─────────┐
└───────┬────────────┘   └─────────┬───────────┘   │  MCP Servers (3)    │
        │                          │                │  time_mcp   (1 Tool)│
┌───────▼──────────────────────────▼───────────┐   │  weather_mcp(1 Tool)│
│  Capabilities                                 │   │  teams_mcp (19 T.)  │
│  RAG (chunk/embed/retrieve) · Memory (short+  │   │  → Microsoft Graph  │
│  long) · LLM Registry (multi-provider, task-  │   └─────────────────────┘
│  policies) · Vision · Skills                  │
└───────┬───────────────────────────────────────┘
┌───────▼───────────────────────────────────────┐   ┌─────────────────────┐
│  Postgres + pgvector                          │   │  Observability      │
│  chunks · messages · long_memories · claims · │   │  Langfuse Traces    │
│  proposed_actions · audit_log · users         │   │  structured Logging │
└───────────────────────────────────────────────┘   └─────────────────────┘
```

# 附录 B：Demo 台本（3 分钟）

1. Chat 输入 "Wie spät ist es?" → 指给面试官看：走的是 mcp_tools 节点，time_mcp，**没有**碰 RAG
2. "Wie ist das Wetter in Zürich?" → weather_mcp，讲降级策略（无 key → Open-Meteo）
3. 问一个知识库里**没有**的问题 → 展示拒答（evidence gate），强调"不编造"
4. 打开一个 Claim → Review → 展示 ProposedAction 卡片 → 批准 → Audit 页面看留痕
5. Integrations 页面展示 3 个 MCP server / 21 tools

# 附录 C：面试官可能追问 & 一句话回答

- **为什么 MCP 而不是直接函数调用？** 进程隔离 + 标准协议：工具可独立部署/替换/复用，凭证不进模型上下文，第三方 server 即插即用。
- **为什么 mcp_tools 放在 RAG 前面？** 时间/天气/操作类问题检索毫无意义；工具答不了自动 fallback 到 RAG，责任链清晰。
- **长记忆为什么用向量检索而不是全部注入？** Token 成本 + 噪声控制：只召回与当前问题相关的记忆。
- **怎么防止 Agent 乱执行写操作？** 三层：白名单（只读自动）、ProposedAction + 人工审批、状态机拒绝非法转移。
- **怎么知道改动没有让 Agent 变差？** 离线 eval（JSONL 数据集 + 阈值指标 + 数据集指纹）+ 108 个单测 + Langfuse 线上 trace。
