# Insurance Knowledge Search Dashboard - Architecture Proposal v0.1

Status: Draft  
Owner: AI Engineering Candidate Project  
Target users: Support Agents, Claims Operations, Product Owners, Knowledge Managers  
Primary language: German  
Last updated: 2026-06-12

## 1. Project Vision

Insurance companies store operational knowledge across multiple internal systems. Product rules, onboarding material, claims processes, escalation paths, and frequently asked questions often live in Confluence, while unresolved questions, documentation gaps, and historical decisions are discussed in Jira tickets.

The goal of this project is to build an internal knowledge search dashboard that allows employees to ask German natural-language questions and receive grounded answers with citations to the original Confluence pages or Jira issues.

This is not a generic chatbot demo. The system is designed as an enterprise knowledge retrieval product where traceability, freshness, metadata filtering, and source attribution are core requirements.

Example user question:

> Welche Unterlagen benoetige ich fuer die Schadenmeldung in der privaten Haftpflichtversicherung?

Expected system behavior:

- retrieve relevant Confluence onboarding/process pages
- optionally include related Jira tickets about documentation gaps or process clarifications
- answer in German
- include citations to source pages or tickets
- refuse or qualify the answer if the available sources are insufficient

## 2. User Stories

As a new support agent, I want to ask German questions about insurance products and claims processes, so that I can onboard faster without manually searching many wiki pages.

As a claims handler, I want to retrieve required documents for a specific claim type, so that I can process customer cases consistently.

As a product owner, I want to search Jira tickets related to unclear documentation, so that I can identify knowledge gaps and improve internal guidance.

As a knowledge manager, I want every generated answer to include citations, so that I can verify whether the answer is based on approved internal content.

As an operations lead, I want search results to be filterable by source, product line, label, and update time, so that users can narrow down answers to the relevant business context.

As an admin, I want updated Confluence pages and Jira issues to be synced incrementally, so that the search index stays fresh without reprocessing all content.

## 3. Data Source Design

### 3.1 Confluence

Confluence is treated as the primary source for approved knowledge.

Typical content:

- product descriptions
- onboarding documents
- claims process documentation
- FAQ pages
- escalation rules
- internal policy explanations

Relevant fields:

- page id
- title
- space key
- labels
- body content
- version
- last updated timestamp
- author or owner team
- web URL
- access scope

Confluence pages are expected to be more authoritative than Jira tickets. During retrieval and answer generation, Confluence content should usually be preferred when both Confluence and Jira contain overlapping information.

### 3.2 Jira

Jira is treated as a secondary source for operational and historical knowledge.

Typical content:

- support questions
- documentation bugs
- product clarification tickets
- claims process incidents
- tasks to update internal documentation
- discussions in comments

Relevant fields:

- issue id
- issue key
- summary
- description
- comments
- project key
- issue type
- status
- labels
- created and updated timestamps
- linked Confluence pages
- web URL
- access scope

Jira data is useful but noisy. It may contain unresolved discussions, outdated assumptions, or incorrect intermediate conclusions. The system should expose Jira sources, but the answer generation layer must avoid treating every Jira comment as authoritative.

### 3.3 Mock Data Strategy

The MVP starts with mock Atlassian APIs instead of requiring real Atlassian credentials.

The mock APIs should imitate the shape of real Confluence and Jira responses:

- `GET /wiki/api/v2/pages`
- `GET /wiki/api/v2/pages/{id}`
- `GET /rest/api/3/search`

The domain content should be synthetic but realistic German insurance content. The first dataset should cover:

- Hausratversicherung
- private Haftpflichtversicherung
- Rechtsschutzversicherung
- Wohngebaeudeversicherung
- Kfz-Schaden
- Schadenmeldung
- Wartezeiten
- Ausschluesse
- benoetigte Unterlagen
- Eskalationsprozesse

Public insurance materials, such as German insurance association sample conditions, can be used as inspiration for topics and terminology. The public demo dataset should still be written as synthetic internal company documentation to avoid copyright and licensing problems.

## 4. Document Contract

All source-specific records are normalized into a common internal document model before chunking and embedding.

```text
Document {
  id: string
  text: string
  metadata: {
    source: "confluence" | "jira"
    source_id: string
    title: string
    url: string
    labels: string[]
    updated_at: datetime
    version?: string
    space_key?: string
    project_key?: string
    issue_key?: string
    issue_type?: string
    status?: string
    owner_team?: string
    access_scope?: string
  }
}
```

The `text` field is used for chunking, embeddings, and retrieval.

The `metadata` field is used for:

- source filtering
- citation generation
- incremental sync
- access control
- ranking adjustments
- observability and debugging

This contract keeps the downstream RAG pipeline independent from Atlassian-specific APIs. If the company later adds SharePoint, ServiceNow, or internal PDFs, only a new connector and normalizer should be required.

## 5. System Architecture

### 5.1 High-Level Architecture

```text
Confluence API          Jira API
      |                    |
      v                    v
Source Connectors / API Clients
      |
      v
Document Normalizer
      |
      v
Chunking Pipeline
      |
      v
Embedding Service
      |
      v
PostgreSQL + pgvector
      |
      v
Retrieval Service
      |
      v
LLM Answer Service
      |
      v
Dashboard UI
```

### 5.2 Component Responsibilities

Source connectors fetch raw records from Confluence and Jira. They handle pagination, authentication, retry behavior, and incremental sync boundaries.

The document normalizer converts raw source records into the common `Document` contract.

The chunking pipeline splits documents into retrievable units. It preserves parent document metadata for citations.

The embedding service converts chunks and user queries into vectors using a multilingual embedding model that performs well in German.

PostgreSQL with pgvector stores chunks, embeddings, metadata, and source document references in one database.

The retrieval service performs semantic search, metadata filtering, and ranking.

The LLM answer service generates German answers from retrieved context and enforces citation and refusal rules.

The dashboard UI provides chat/search interaction, source filters, retrieved citations, and source previews.

### 5.3 Framework Positioning

The MVP should not depend on LangGraph. The first version is a deterministic RAG pipeline, not a multi-step autonomous agent.

LangChain can be used selectively for model adapters, text splitters, or vector store integration, but the core project interfaces should remain framework-independent.

LangGraph becomes relevant in a later version if the system needs stateful multi-step workflows, for example:

- classify query intent
- route between Confluence, Jira, or both
- generate and validate JQL
- ask for human approval before answering sensitive claims questions
- retry with fallback retrieval
- maintain long-running investigation state

Graph databases are not part of the MVP. They may be evaluated later if the product needs explicit relationship traversal, such as policy-to-coverage-to-exclusion graphs.

## 6. Retrieval Strategy

### 6.1 MVP Retrieval Flow

```text
User question
  -> language normalization
  -> query embedding
  -> pgvector top-k retrieval
  -> metadata filters
  -> context assembly
  -> LLM answer generation
  -> citations returned to UI
```

The system should support filters such as:

- source: Confluence or Jira
- product line
- label
- project key
- space key
- updated date
- issue status

### 6.2 Chunking Strategy

Confluence pages should be chunked by heading and paragraph where possible. This preserves semantic structure and improves citation quality.

Jira issues should initially be indexed as issue-level documents because summary, description, and comments are usually short and context-dependent. If comments become long, comments can be chunked separately while preserving the parent issue key.

Each chunk should store:

```text
chunk_id
document_id
chunk_index
content
embedding
metadata
```

### 6.3 Ranking Strategy

The MVP uses vector similarity as the primary ranking signal.

Ranking should be adjusted by source quality:

- approved Confluence pages rank higher than Jira comments
- newer versions rank higher than outdated pages
- exact label or product filters rank higher than generic matches
- resolved Jira tickets may rank higher than open discussions for factual answers

### 6.4 Answer Generation Rules

The LLM must answer in German.

The LLM must cite source documents used in the answer.

The LLM must not invent policy details that are not present in retrieved context.

If the retrieved context is insufficient, the system should respond with a controlled fallback:

```text
Ich kann diese Frage anhand der verfuegbaren Quellen nicht verlaesslich beantworten.
Bitte pruefen Sie die offiziellen Versicherungsbedingungen oder eskalieren Sie an das zustaendige Fachteam.
```

For conflicting sources, the answer should prefer approved Confluence content and mention that related Jira tickets indicate a possible documentation gap.

## 7. Deployment Plan

### 7.1 MVP Deployment

The MVP should run with Docker Compose.

Services:

- dashboard frontend
- backend API
- ingestion worker
- PostgreSQL with pgvector

Optional local services:

- local embedding model or external embedding API
- local LLM through Ollama or external LLM provider

The first deployable version should run locally and on a small cloud VM.

### 7.2 Production Evolution

A production-grade version would add:

- real Atlassian Cloud authentication
- secret management
- scheduled ingestion jobs
- retry and dead-letter queues
- structured logging
- tracing for retrieval and LLM calls
- evaluation datasets
- SSO
- role-based access control
- monitoring and alerting
- backup and restore for PostgreSQL
- CI/CD

The architecture keeps ingestion, retrieval, answer generation, and frontend responsibilities separated so that they can later be deployed independently.

## 8. Risks and Tradeoffs

### Hallucination

Risk: The LLM may generate answers that are not supported by retrieved sources.

Mitigation:

- require citations
- use strict answer prompts
- refuse when context is insufficient
- evaluate answers against test questions

### Outdated Knowledge

Risk: Search results may use outdated Confluence pages or old Jira discussions.

Mitigation:

- store `updated_at` and version metadata
- run incremental sync
- prefer newer approved pages
- show source timestamps in the UI

### Permission Leakage

Risk: Users may retrieve content they are not allowed to see.

Mitigation:

- store source-level access metadata
- apply permission filters before retrieval
- never rely only on frontend filtering
- align with Atlassian permission model in production

### Noisy Jira Data

Risk: Jira comments may contain unverified or obsolete information.

Mitigation:

- rank Confluence higher for factual answers
- expose Jira tickets as supporting evidence
- treat unresolved tickets as non-authoritative

### Poor German Retrieval Quality

Risk: Embedding model may perform poorly on German insurance terminology.

Mitigation:

- use multilingual embeddings
- build a German evaluation set
- test queries with synonyms and insurance-specific vocabulary

### Framework Lock-In

Risk: Overusing LangChain or LangGraph may make the system hard to maintain or migrate.

Mitigation:

- define internal interfaces for connectors, normalizers, retrievers, and generators
- keep LangChain/LangGraph behind adapter layers
- start with a deterministic pipeline

## 9. MVP Scope

### In Scope

- synthetic German insurance dataset
- mock Confluence API
- mock Jira API
- source connectors
- document normalization
- chunking
- PostgreSQL with pgvector
- semantic retrieval
- metadata filtering
- German answer generation
- citations to source documents
- simple dashboard UI
- Docker Compose deployment

### Out of Scope

- real SSO
- full Atlassian permission sync
- write-back to Confluence or Jira
- Graph DB
- LangGraph workflow orchestration
- automated claims decisioning
- production monitoring
- multi-tenant deployment

## 10. Milestones

### Milestone 1: Architecture and Dataset Design

Deliverables:

- architecture proposal
- document contract
- synthetic Confluence/Jira dataset design
- mock API design

### Milestone 2: Ingestion and Normalization

Deliverables:

- Confluence connector
- Jira connector
- normalized documents
- ingestion logs

### Milestone 3: Vector Storage and Retrieval

Deliverables:

- PostgreSQL + pgvector schema
- chunking pipeline
- embedding pipeline
- semantic search endpoint

### Milestone 4: RAG Answer API

Deliverables:

- German question-answering endpoint
- citation support
- fallback behavior for insufficient context
- basic evaluation questions

### Milestone 5: Dashboard

Deliverables:

- chat/search UI
- filters
- citation preview
- source links

### Milestone 6: Production Hardening Plan

Deliverables:

- security review
- permission model design
- incremental sync strategy
- deployment documentation

## 11. Open Questions

- Which embedding model should be selected for German insurance terminology?
- Should the backend be implemented in Python only, or split into Spring Boot for business APIs and Python for the RAG pipeline?
- How should source permissions be represented in the MVP without integrating real Atlassian SSO?
- Should Jira tickets be included in answer context by default, or only when the user explicitly selects Jira?
- What is the minimum evaluation dataset required before calling the MVP reliable?

## 12. Recommended Initial Decision

Build the MVP as a deterministic RAG system without LangGraph and without a graph database.

Use mock Atlassian APIs and synthetic German insurance content first. Keep source connectors, document normalization, retrieval, and answer generation separated by clear interfaces.

Use PostgreSQL with pgvector for both metadata and vector search. Introduce LangGraph only after the basic pipeline works and there is a concrete need for stateful multi-step orchestration.
