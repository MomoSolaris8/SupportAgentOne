import os
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode

import requests
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.mcp_client.store import consume_oauth_state, save_oauth_state, upsert_user_credentials


MICROSOFT_PROVIDER = "microsoft"


def microsoft_tenant() -> str:
    return os.environ.get("MICROSOFT_TENANT", "consumers")


def microsoft_scopes() -> str:
    return os.environ.get(
        "MICROSOFT_SCOPES",
        "offline_access User.Read Calendars.ReadWrite Files.ReadWrite",
    )


def frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000")


def redirect_uri() -> str:
    return os.environ.get(
        "MICROSOFT_REDIRECT_URI",
        "http://localhost:8000/auth/microsoft/callback",
    )


def microsoft_start(user: AuthUser = Depends(get_current_user)) -> RedirectResponse:
    client_id = os.environ.get("MICROSOFT_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="MICROSOFT_CLIENT_ID is not configured.")

    state = token_urlsafe(32)
    save_oauth_state(state, user.id, MICROSOFT_PROVIDER)
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri(),
            "response_mode": "query",
            "scope": microsoft_scopes(),
            "state": state,
        }
    )
    return RedirectResponse(
        f"https://login.microsoftonline.com/{microsoft_tenant()}/oauth2/v2.0/authorize?{query}"
    )


def microsoft_callback(request: Request) -> RedirectResponse:
    error = request.query_params.get("error")
    if error:
        description = request.query_params.get("error_description", error)
        return RedirectResponse(f"{frontend_url()}?microsoft=error&reason={description}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing Microsoft OAuth code or state.")

    user_id = consume_oauth_state(state, MICROSOFT_PROVIDER)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired Microsoft OAuth state.")

    client_id = os.environ.get("MICROSOFT_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="MICROSOFT_CLIENT_ID is not configured.")

    data = {
        "client_id": client_id,
        "scope": microsoft_scopes(),
        "code": code,
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }
    client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET")
    if client_secret:
        data["client_secret"] = client_secret

    response = requests.post(
        f"https://login.microsoftonline.com/{microsoft_tenant()}/oauth2/v2.0/token",
        data=data,
        timeout=20,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"Microsoft token exchange failed: {response.text}")

    payload = response.json()
    credentials = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))
        ).isoformat(),
        "scope": payload.get("scope"),
        "token_type": payload.get("token_type", "Bearer"),
    }
    upsert_user_credentials(user_id, "teams_mcp", credentials)
    return RedirectResponse(f"{frontend_url()}?microsoft=connected")
