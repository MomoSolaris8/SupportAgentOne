import os
from typing import Any

import requests


class ToolConfigurationError(RuntimeError):
    pass


def require_token(value: str | None, env_name: str) -> str:
    if not isinstance(value, str):
        value = None
    token = value or os.environ.get(env_name)
    if not token:
        raise ToolConfigurationError(f"Missing access token. Pass access_token or set {env_name}.")
    return token


def request_json(
    method: str,
    url: str,
    *,
    access_token: str | None = None,
    api_key: str | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    data: bytes | str | None = None,
    timeout: int = 15,
) -> Any:
    headers: dict[str, str] = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        params = {**(params or {}), "key": api_key}

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_body,
        data=data,
        timeout=timeout,
    )
    if response.status_code == 204:
        return {"ok": True, "status_code": response.status_code}
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.status_code >= 400:
        return {
            "ok": False,
            "status_code": response.status_code,
            "error": payload,
        }
    return payload
