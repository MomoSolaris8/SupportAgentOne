import os
from langfuse import get_client


def get_langfuse_client():
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return None
    if not os.environ.get("LANGFUSE_SECRET_KEY"):
        return None
    return get_client()
