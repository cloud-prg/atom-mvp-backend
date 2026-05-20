from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Message, User
from app.schemas import ConversationCreate, ConversationOut, MessageCreate, MessageOut
from app.services.conversation_service import (
    create_conversation,
    delete_conversation,
    get_conversation_for_user,
    list_conversations,
    list_messages,
    touch_conversation,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def index(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list:
    return list_conversations(db, user)


@router.post("", response_model=ConversationOut)
def create(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_conversation(db, user, payload.title)


@router.get("/{conversation_id}", response_model=ConversationOut)
def show(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = get_conversation_for_user(db, user, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
def destroy(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = get_conversation_for_user(db, user, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    delete_conversation(db, conversation)
    return {"ok": True}


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def messages(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = get_conversation_for_user(db, user, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return list_messages(db, conversation)


@router.post("/{conversation_id}/messages", response_model=MessageOut)
def create_message(
    conversation_id: str,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_conversation_for_user(db, user, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    message = Message(
        conversation_id=conversation.id,
        role=payload.role,
        content=payload.content,
        client_message_id=payload.client_message_id,
        status="completed",
    )
    db.add(message)
    touch_conversation(db, conversation, payload.content if payload.role == "user" else None)
    db.commit()
    db.refresh(message)
    return message

