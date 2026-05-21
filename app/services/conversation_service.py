from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.models import Conversation, Message, SearchResult, SearchRun, User, utc_now


def list_conversations(db: Session, user: User) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(desc(Conversation.updated_at))
        )
    )


def create_conversation(db: Session, user: User, title: str | None = None) -> Conversation:
    conversation = Conversation(user_id=user.id, title=(title or "New chat").strip() or "New chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_for_user(db: Session, user: User, conversation_id: str) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )


def delete_conversation(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.commit()


def update_conversation_title(db: Session, conversation: Conversation, title: str) -> Conversation:
    conversation.title = title.strip() or "New chat"
    conversation.updated_at = utc_now()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def clear_conversation_context(db: Session, conversation: Conversation) -> None:
    search_run_ids = select(SearchRun.id).where(SearchRun.conversation_id == conversation.id)
    db.execute(delete(SearchResult).where(SearchResult.search_run_id.in_(search_run_ids)))
    db.execute(delete(SearchRun).where(SearchRun.conversation_id == conversation.id))
    db.execute(delete(Message).where(Message.conversation_id == conversation.id))
    conversation.updated_at = utc_now()
    db.add(conversation)
    db.commit()


def list_messages(db: Session, conversation: Conversation) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at, Message.id)
        )
    )


def title_from_content(content: str) -> str:
    normalized = " ".join(content.strip().split())
    if not normalized:
        return "New chat"
    return normalized[:40] + ("..." if len(normalized) > 40 else "")


def touch_conversation(db: Session, conversation: Conversation, first_user_content: str | None = None) -> None:
    if conversation.title == "New chat" and first_user_content:
        conversation.title = title_from_content(first_user_content)
    conversation.updated_at = utc_now()
    db.add(conversation)
