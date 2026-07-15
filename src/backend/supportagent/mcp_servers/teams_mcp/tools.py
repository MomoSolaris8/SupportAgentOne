from typing import Any
from urllib.parse import quote

from pydantic import Field
from pydantic.fields import FieldInfo

from supportagent.mcp_servers.http import request_json, require_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TOKEN_ENV = "MS_GRAPH_ACCESS_TOKEN"


def _token(access_token: str | None) -> str:
    return require_token(access_token, GRAPH_TOKEN_ENV)


def _value(value: Any) -> Any:
    return None if isinstance(value, FieldInfo) else value


def _user_base(user_id: str) -> str:
    if user_id == "me":
        return f"{GRAPH_BASE_URL}/me"
    return f"{GRAPH_BASE_URL}/users/{quote(user_id, safe='')}"


def _drive_root(user_id: str, folder_path: str | None = None) -> str:
    base = f"{_user_base(user_id)}/drive/root"
    if not folder_path or folder_path in {"root", "/"}:
        return base
    return f"{base}:/{quote(folder_path.strip('/'), safe='/')}:/"


def _attendee(email: str, name: str | None = None, type_: str = "required") -> dict[str, Any]:
    return {
        "type": type_,
        "emailAddress": {
            "address": email,
            "name": name or email,
        },
    }


def get_my_profile(
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Get the signed-in Microsoft account profile."""
    return request_json(
        "GET",
        f"{GRAPH_BASE_URL}/me",
        access_token=_token(access_token),
        params={"$select": "id,displayName,mail,userPrincipalName,preferredLanguage"},
    )


def batch_get_user_info(
    emails: list[str] | None = Field(default=None, description="Email addresses to resolve."),
    phones: list[str] | None = Field(default=None, description="Phone numbers to match against mobilePhone."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> dict[str, Any]:
    """Batch resolve Microsoft 365 users by email/userPrincipalName and optionally phone."""
    token = _token(access_token)
    emails = _value(emails)
    phones = _value(phones)
    results: list[Any] = []
    missing: list[str] = []

    for email in emails or []:
        user = request_json(
            "GET",
            f"{GRAPH_BASE_URL}/users/{quote(email, safe='')}",
            access_token=token,
            params={"$select": "id,displayName,mail,userPrincipalName,mobilePhone"},
        )
        if isinstance(user, dict) and user.get("ok") is False:
            missing.append(email)
        else:
            results.append(user)

    if phones:
        users = request_json(
            "GET",
            f"{GRAPH_BASE_URL}/users",
            access_token=token,
            params={"$select": "id,displayName,mail,userPrincipalName,mobilePhone", "$top": 999},
        )
        values = users.get("value", []) if isinstance(users, dict) else []
        phone_set = {phone.strip() for phone in phones}
        results.extend(
            user
            for user in values
            if user.get("mobilePhone") and user["mobilePhone"].strip() in phone_set
        )

    return {"users": results, "missing": missing}


def create_calendar(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    name: str = Field(..., description="Calendar display name."),
    color: str | None = Field(default=None, description="Calendar color."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Create a Microsoft 365 calendar for a user."""
    color = _value(color)
    body: dict[str, Any] = {"name": name}
    if color:
        body["color"] = color
    return request_json("POST", f"{_user_base(user_id)}/calendars", access_token=_token(access_token), json_body=body)


def delete_calendar(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Delete a calendar."""
    return request_json("DELETE", f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}", access_token=_token(access_token))


def get_calendar_info(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Get calendar metadata."""
    return request_json("GET", f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}", access_token=_token(access_token))


def get_calendars_list(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """List user calendars."""
    return request_json("GET", f"{_user_base(user_id)}/calendars", access_token=_token(access_token))


def update_calendar(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    name: str | None = Field(default=None, description="New calendar display name."),
    color: str | None = Field(default=None, description="New calendar color."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Update calendar metadata."""
    name = _value(name)
    color = _value(color)
    body = {key: value for key, value in {"name": name, "color": color}.items() if value is not None}
    return request_json("PATCH", f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}", access_token=_token(access_token), json_body=body)


def create_calendar_event(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    subject: str = Field(..., description="Event subject."),
    start_time: str = Field(..., description="ISO 8601 start time, e.g. 2026-07-14T09:00:00."),
    end_time: str = Field(..., description="ISO 8601 end time, e.g. 2026-07-14T10:00:00."),
    timezone: str = Field(default="UTC", description="Windows timezone id, e.g. UTC or W. Europe Standard Time."),
    body: str | None = Field(default=None, description="HTML event body."),
    location: str | None = Field(default=None, description="Location display name."),
    attendees: list[str] | None = Field(default=None, description="Attendee email addresses."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Create a calendar event."""
    timezone = _value(timezone) or "UTC"
    body = _value(body)
    location = _value(location)
    attendees = _value(attendees)
    payload: dict[str, Any] = {
        "subject": subject,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }
    if body:
        payload["body"] = {"contentType": "HTML", "content": body}
    if location:
        payload["location"] = {"displayName": location}
    if attendees:
        payload["attendees"] = [_attendee(email) for email in attendees]
    return request_json(
        "POST",
        f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}/events",
        access_token=_token(access_token),
        json_body=payload,
    )


def create_default_calendar_event(
    subject: str = Field(..., description="Event subject."),
    start_time: str = Field(..., description="ISO 8601 start time, e.g. 2026-07-16T13:00:00."),
    end_time: str = Field(..., description="ISO 8601 end time, e.g. 2026-07-16T14:00:00."),
    timezone: str = Field(default="W. Europe Standard Time", description="Windows timezone id."),
    body: str | None = Field(default=None, description="HTML event body."),
    location: str | None = Field(default=None, description="Location display name."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Create an event in the signed-in user's default calendar."""
    timezone = _value(timezone) or "W. Europe Standard Time"
    body = _value(body)
    location = _value(location)
    payload: dict[str, Any] = {
        "subject": subject,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }
    if body:
        payload["body"] = {"contentType": "HTML", "content": body}
    if location:
        payload["location"] = {"displayName": location}
    return request_json(
        "POST",
        f"{GRAPH_BASE_URL}/me/events",
        access_token=_token(access_token),
        json_body=payload,
    )


def append_calendar_event_attendee(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    event_id: str = Field(..., description="Event id."),
    attendees: list[str] = Field(..., description="Attendee email addresses to add."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Append attendees to an existing calendar event."""
    token = _token(access_token)
    url = f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}"
    event = request_json("GET", url, access_token=token, params={"$select": "attendees"})
    existing = event.get("attendees", []) if isinstance(event, dict) else []
    existing_emails = {item.get("emailAddress", {}).get("address", "").lower() for item in existing}
    merged = existing + [_attendee(email) for email in attendees if email.lower() not in existing_emails]
    return request_json("PATCH", url, access_token=token, json_body={"attendees": merged})


def get_calendar_event(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    event_id: str = Field(..., description="Event id."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Get calendar event details."""
    return request_json(
        "GET",
        f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
        access_token=_token(access_token),
    )


def update_calendar_event(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    event_id: str = Field(..., description="Event id."),
    subject: str | None = None,
    body: str | None = None,
    location: str | None = None,
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Update event subject, body, or location."""
    subject = _value(subject)
    body = _value(body)
    location = _value(location)
    payload: dict[str, Any] = {}
    if subject is not None:
        payload["subject"] = subject
    if body is not None:
        payload["body"] = {"contentType": "HTML", "content": body}
    if location is not None:
        payload["location"] = {"displayName": location}
    return request_json(
        "PATCH",
        f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
        access_token=_token(access_token),
        json_body=payload,
    )


def delete_calendar_event(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    calendar_id: str = Field(..., description="Calendar id."),
    event_id: str = Field(..., description="Event id."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Delete a calendar event."""
    return request_json(
        "DELETE",
        f"{_user_base(user_id)}/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
        access_token=_token(access_token),
    )


def create_document(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    name: str = Field(..., description="File name, e.g. notes.txt."),
    content: str = Field(default="", description="Text content to upload."),
    folder_path: str | None = Field(default=None, description="OneDrive folder path, defaults to root."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Create or replace a text document in OneDrive."""
    content = _value(content) or ""
    folder_path = _value(folder_path)
    folder = "" if not folder_path or folder_path in {"root", "/"} else f"{folder_path.strip('/')}/"
    url = f"{_user_base(user_id)}/drive/root:/{quote(folder + name, safe='/')}:/content"
    return request_json("PUT", url, access_token=_token(access_token), data=content)


def get_document(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    item_id: str | None = Field(default=None, description="Drive item id."),
    path: str | None = Field(default=None, description="Drive item path."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Get OneDrive document metadata. Pass either item_id or path."""
    item_id = _value(item_id)
    path = _value(path)
    if item_id:
        url = f"{_user_base(user_id)}/drive/items/{quote(item_id, safe='')}"
    elif path:
        url = f"{_user_base(user_id)}/drive/root:/{quote(path.strip('/'), safe='/')}"
    else:
        return {"ok": False, "error": "Pass item_id or path."}
    return request_json("GET", url, access_token=_token(access_token))


def create_folder(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    name: str = Field(..., description="Folder name."),
    parent_path: str | None = Field(default=None, description="Parent folder path, defaults to root."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Create a OneDrive folder."""
    parent_path = _value(parent_path)
    url = f"{_drive_root(user_id, parent_path)}/children"
    return request_json(
        "POST",
        url,
        access_token=_token(access_token),
        json_body={"name": name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"},
    )


def list_folder_files(
    user_id: str = Field(default="me", description="Microsoft Graph user id, UPN, or 'me'."),
    folder_path: str | None = Field(default=None, description="Folder path, defaults to root."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """List files in a OneDrive folder."""
    folder_path = _value(folder_path)
    return request_json("GET", f"{_drive_root(user_id, folder_path)}/children", access_token=_token(access_token))


def create_message(
    chat_id: str = Field(..., description="Teams chat id."),
    content: str = Field(..., description="HTML message content."),
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """Send a message to a Microsoft Teams chat."""
    return request_json(
        "POST",
        f"{GRAPH_BASE_URL}/chats/{quote(chat_id, safe='')}/messages",
        access_token=_token(access_token),
        json_body={"body": {"contentType": "html", "content": content}},
    )


def list_chats(
    access_token: str | None = Field(default=None, description="Microsoft Graph access token."),
) -> Any:
    """List Teams chats visible to the signed-in user."""
    return request_json(
        "GET",
        f"{GRAPH_BASE_URL}/me/chats",
        access_token=_token(access_token),
        params={"$top": 50},
    )


TEAMS_TOOLS = [
    get_my_profile,
    batch_get_user_info,
    create_calendar,
    delete_calendar,
    get_calendar_info,
    get_calendars_list,
    update_calendar,
    create_calendar_event,
    create_default_calendar_event,
    append_calendar_event_attendee,
    get_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    create_document,
    get_document,
    create_folder,
    list_folder_files,
    list_chats,
    create_message,
]
