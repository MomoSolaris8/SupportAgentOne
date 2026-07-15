from fastapi import HTTPException, Request, status

from .router_config import AUTH_COOKIE_NAME
from .schemas import AuthUser
from .store import get_user_by_session_token


def get_current_user(request: Request) -> AuthUser:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = get_user_by_session_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    return user
