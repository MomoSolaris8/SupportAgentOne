from dotenv import load_dotenv
from fastapi import FastAPI

from supportagent.api.router import register_routes
from supportagent.core.logging_config import configure_logging
from supportagent.mcp_client.store import ensure_mcp_schema
from supportagent.rag.builtin_seed import ensure_rag_schema, seed_builtin_rag_if_enabled
from supportagent.uploads import ensure_upload_schema

load_dotenv()
configure_logging()

app = FastAPI(title="SupportAgent")
register_routes(app)


@app.on_event("startup")
def startup() -> None:
    ensure_rag_schema()
    ensure_mcp_schema()
    ensure_upload_schema()
    seed_builtin_rag_if_enabled()
