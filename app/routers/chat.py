from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ChatStreamIn
from app.services.chat_service import stream_chat
from app.services.quota_service import MessageQuotaExhausted, consume_message_quota

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
def stream(payload: ChatStreamIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        consume_message_quota(db, user, payload.client_message_id)
    except MessageQuotaExhausted as exc:
        raise HTTPException(status_code=402, detail="Message quota exhausted") from exc

    return StreamingResponse(
        stream_chat(
            db=db,
            user=user,
            content=payload.content,
            client_message_id=payload.client_message_id,
            conversation_id=payload.conversation_id,
            search_mode=payload.search_mode,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
