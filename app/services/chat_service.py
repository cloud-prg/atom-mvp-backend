import json
from collections.abc import AsyncIterator

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Conversation, Message, SearchResult as SearchResultModel, SearchRun, User, utc_now
from app.services.ai_provider import stream_chat_response
from app.services.conversation_service import create_conversation, get_conversation_for_user, touch_conversation
from app.services.search_provider import search


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_chat(
    db: Session,
    user: User,
    content: str,
    client_message_id: str,
    conversation_id: str | None,
    search_mode: str,
) -> AsyncIterator[str]:
    conversation = (
        get_conversation_for_user(db, user, conversation_id)
        if conversation_id
        else create_conversation(db, user, "New chat")
    )
    if conversation is None:
        yield sse("message.failed", {"detail": "Conversation not found"})
        return

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=content,
        status="completed",
        client_message_id=client_message_id,
    )
    db.add(user_message)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        yield sse("message.failed", {"detail": "Duplicate client message id"})
        return

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
        client_message_id=None,
    )
    db.add(assistant_message)
    touch_conversation(db, conversation, content)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(conversation)

    yield sse(
        "message.created",
        {
            "conversation": {"id": conversation.id, "title": conversation.title},
            "user_message": {"id": user_message.id, "content": user_message.content},
            "assistant_message": {"id": assistant_message.id, "status": assistant_message.status},
        },
    )

    provider, search_status, results = await search(content, search_mode)
    if search_status == "completed":
        run = SearchRun(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            query=content,
            provider=provider,
            status="completed",
        )
        db.add(run)
        db.flush()
        for result in results:
            db.add(
                SearchResultModel(
                    search_run_id=run.id,
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    source=result.source,
                    published_at=result.published_at,
                )
            )
        db.commit()
        yield sse("search.completed", {"provider": provider, "results": [result.__dict__ for result in results]})
    elif search_status == "failed":
        yield sse("search.failed", {"provider": provider, "detail": "Search provider failed"})

    full_content = ""
    try:
        async for chunk in stream_chat_response(content, results):
            full_content += chunk
            assistant_message.content = full_content
            assistant_message.updated_at = utc_now()
            db.add(assistant_message)
            db.commit()
            yield sse("message.delta", {"id": assistant_message.id, "delta": chunk, "content": full_content})
    except Exception as exc:
        assistant_message.status = "interrupted"
        assistant_message.updated_at = utc_now()
        db.add(assistant_message)
        db.commit()
        yield sse("message.interrupted", {"id": assistant_message.id, "detail": str(exc)})
        return

    assistant_message.status = "completed"
    assistant_message.updated_at = utc_now()
    conversation.updated_at = utc_now()
    db.add_all([assistant_message, conversation])
    db.commit()
    yield sse("message.completed", {"id": assistant_message.id, "content": full_content})

