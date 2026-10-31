from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from langfuse import get_client

from supportagent.api.exception_handlers import register_exception_handlers
from supportagent.api.middleware import register_request_logging
from supportagent.api.router import register_routes
from supportagent.core.logging_config import configure_logging
from supportagent.db.session import engine

load_dotenv()
configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    engine.dispose()
    get_client().shutdown()


app = FastAPI(title="SupportAgent", lifespan=lifespan)
register_request_logging(app)
register_exception_handlers(app)
register_routes(app)
