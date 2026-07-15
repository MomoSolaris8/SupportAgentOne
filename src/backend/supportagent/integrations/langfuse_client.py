import logging
import os

from langfuse import Langfuse

logger = logging.getLogger(__name__)


def get_langfuse_client():
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    base_url = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if not public_key:
        logger.info("langfuse_disabled missing_public_key")
        return None
    if not secret_key:
        logger.info("langfuse_disabled missing_secret_key")
        return None

    client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
    )
    try:
        if not client.auth_check():
            logger.warning("langfuse_disabled auth_check_failed base_url=%s", base_url)
            return None
    except Exception:
        logger.exception("langfuse_auth_check_failed base_url=%s", base_url)
        return None

    logger.info("langfuse_enabled base_url=%s", base_url)
    return client
