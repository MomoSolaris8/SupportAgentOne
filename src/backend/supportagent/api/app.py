from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from supportagent.api.exception_handlers import register_exception_handlers
from supportagent.api.router import register_routes
from supportagent.claims import ensure_claim_schema
from supportagent.core.logging_config import configure_logging
from supportagent.mcp_client.store import ensure_mcp_schema
from supportagent.rag.builtin_seed import ensure_rag_schema, seed_builtin_rag_if_enabled
from supportagent.uploads import ensure_upload_schema

load_dotenv()
configure_logging()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_rag_schema()
    ensure_mcp_schema()
    ensure_upload_schema()
    ensure_claim_schema()
    seed_builtin_rag_if_enabled()
    yield


app = FastAPI(title="SupportAgent", lifespan=lifespan)
register_exception_handlers(app)
register_routes(app)
