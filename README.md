# SupportAgent

RAG pipeline over a real Confluence space + Jira project, for the
"Insurance Knowledge Search Dashboard" portfolio project. See
`architecture-proposal-v0.1.de.md` for the full design.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
docker compose up -d postgres
```

Copy `.env.example` to `.env` and fill in:

- `ATLASSIAN_BASE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` - Confluence/Jira Cloud API token
- `CONFLUENCE_SPACE_KEY`, `JIRA_PROJECT_KEY` - the space/project to read from and write to
- `EMBEDDING_API_KEY` - Alibaba Cloud Model Studio (DashScope) API key, used via its
  OpenAI-compatible endpoint (`EMBEDDING_BASE_URL`) for both embeddings and chat (`CHAT_MODEL`)
- `DATABASE_URL` - points at the pgvector container started by `docker compose up`

## Pipeline

```bash
# 1. Seed the Confluence space + Jira project with sample insurance content
python -m supportagent.seed

# 2. Pull real Confluence pages (tagged "insurance-kb") + Jira issues, normalize to Documents
python -m supportagent.ingest

# 3. Chunk -> embed -> store in pgvector
python -m supportagent.index
```

## RAG Answer API

```bash
uvicorn supportagent.api:app --reload
```

`POST /ask` with `{"question": "..."}` retrieves relevant chunks from pgvector,
generates a German answer with citations (`[1]`, `[2]`, ...), and returns the
cited sources. If the retrieved context doesn't support an answer, it returns
a fixed controlled-refusal message instead.

### PDF data prep

`pdf_to_confluence.py` extracts `§`-numbered sections from German insurance
terms PDFs (Musterbedingungen/AVB) into Confluence page drafts. See the
module docstring for the dry-run / save workflow.

## Project layout

- `models.py` - shared `Document` contract
- `html_utils.py`, `adf_utils.py` - Confluence storage-format HTML and Jira ADF conversions
- `atlassian_client.py` - real Confluence v2 / Jira v3 REST client
- `seed_content.py`, `seed.py` - sample data + script to create it in Confluence/Jira
- `ingest.py` - pulls real data back out and normalizes it to `Document`
- `chunking.py`, `embeddings.py`, `vector_store.py`, `index.py` - chunk/embed/store pipeline

## Tests

```bash
python -m pytest
```
