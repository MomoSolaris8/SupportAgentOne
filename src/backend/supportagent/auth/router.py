from fastapi import APIRouter, Depends, Request, Response

from .dependencies import get_current_user
from .router_config import AUTH_COOKIE_NAME, AUTH_COOKIE_PATH
from .schemas import AuthUser, LoginRequest, RegisterRequest, UserPublic
from .security import cookie_secure, session_ttl_days
from .service import login_user, register_user
from .store import delete_session_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def public_user(user: AuthUser) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=session_ttl_days() * 24 * 60 * 60,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path=AUTH_COOKIE_PATH,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
    )


@router.post("/register", response_model=UserPublic)
def register(request: RegisterRequest, response: Response) -> UserPublic:
    session = register_user(request)
    set_session_cookie(response, session.token)
    return public_user(session.user)


@router.post("/login", response_model=UserPublic)
def login(request: LoginRequest, response: Response) -> UserPublic:
    session = login_user(request)
    set_session_cookie(response, session.token)
    return public_user(session.user)


@router.get("/me", response_model=UserPublic)
def me(user: AuthUser = Depends(get_current_user)) -> UserPublic:
    return public_user(user)


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        delete_session_token(token)
    clear_session_cookie(response)
    return {"ok": True}
