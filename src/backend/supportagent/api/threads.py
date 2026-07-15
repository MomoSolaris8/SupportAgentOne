from fastapi import APIRouter, Depends, HTTPException

from supportagent.api.schemas import (
    ConversationThread,
    ConversationThreadsResponse,
    ThreadMessage,
    ThreadMessagesResponse,
    UpdateThreadMessageRequest,
)
from supportagent.auth.dependencies import get_current_user
from supportagent.auth.schemas import AuthUser
from supportagent.memory.service import (
    delete_thread_user_turn,
    get_thread_messages,
    list_conversation_threads,
    update_thread_user_message,
)

router = APIRouter(tags=["Threads"])


@router.get("/threads", response_model=ConversationThreadsResponse)
def threads(user: AuthUser = Depends(get_current_user)) -> ConversationThreadsResponse:
    thread_records = list_conversation_threads(user_id=user.id)
    return ConversationThreadsResponse(
        threads=[
            ConversationThread(
                thread_id=thread.thread_id,
                title=thread.title,
                updated_at=thread.updated_at.isoformat(),
                message_count=thread.message_count,
            )
            for thread in thread_records
        ]
    )


@router.get("/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
def thread_messages(
    thread_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ThreadMessagesResponse:
    messages = get_thread_messages(thread_id=thread_id, user_id=user.id)
    return ThreadMessagesResponse(
        thread_id=thread_id,
        messages=[
            ThreadMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
        ],
    )


@router.patch("/threads/{thread_id}/messages/{message_id}", response_model=ThreadMessagesResponse)
def update_thread_message(
    thread_id: str,
    message_id: int,
    request: UpdateThreadMessageRequest,
    user: AuthUser = Depends(get_current_user),
) -> ThreadMessagesResponse:
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")
    updated = update_thread_user_message(
        thread_id=thread_id,
        user_id=user.id,
        message_id=message_id,
        content=content,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Message not found.")
    return thread_messages(thread_id, user)


@router.delete("/threads/{thread_id}/messages/{message_id}", response_model=ThreadMessagesResponse)
def delete_thread_message(
    thread_id: str,
    message_id: int,
    user: AuthUser = Depends(get_current_user),
) -> ThreadMessagesResponse:
    deleted = delete_thread_user_turn(
        thread_id=thread_id,
        user_id=user.id,
        message_id=message_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found.")
    return thread_messages(thread_id, user)
