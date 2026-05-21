from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ChatStreamIn
from app.services.attachment_service import parse_uploads
from app.services.chat_service import stream_chat
from app.services.quota_service import MessageQuotaExhausted, ensure_available_message_quota

router = APIRouter(prefix="/chat", tags=["chat"])


def _ensure_quota(db: Session, user: User) -> None:
    try:
        ensure_available_message_quota(db, user)
    except MessageQuotaExhausted as exc:
        raise HTTPException(status_code=402, detail="Message quota exhausted") from exc


def _stream_response(
    db: Session,
    user: User,
    content: str,
    client_message_id: str,
    conversation_id: str | None,
    search_mode: str,
    network_search: bool | None = None,
    attachments=None,
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(
            db=db,
            user=user,
            content=content,
            client_message_id=client_message_id,
            conversation_id=conversation_id,
            search_mode="force" if network_search else search_mode,
            attachments=attachments,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _form_str(value: object, field: str, required: bool = True) -> str | None:
    if value is None:
        if required:
            raise HTTPException(status_code=422, detail=f"Missing form field: {field}")
        return None
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail=f"Invalid form field: {field}")
    return value


@router.post("/stream")
async def stream(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_quota(db, user)
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        content = _form_str(form.get("content"), "content")
        client_message_id = _form_str(form.get("client_message_id"), "client_message_id")
        conversation_id = _form_str(form.get("conversation_id"), "conversation_id", required=False)
        search_mode = _form_str(form.get("search_mode", "off"), "search_mode") or "off"
        if search_mode not in {"off", "auto", "force"}:
            raise HTTPException(status_code=422, detail="Invalid form field: search_mode")

        uploads = [
            value
            for value in [*form.getlist("attachments"), *form.getlist("files")]
            if isinstance(value, (UploadFile, StarletteUploadFile))
        ]
        attachments = await parse_uploads(uploads)
        return _stream_response(
            db=db,
            user=user,
            content=content or "",
            client_message_id=client_message_id or "",
            conversation_id=conversation_id,
            search_mode=search_mode,
            network_search=_parse_bool(form.get("network_search")),
            attachments=attachments,
        )

    try:
        payload = ChatStreamIn.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return _stream_response(
        db=db,
        user=user,
        content=payload.content,
        client_message_id=payload.client_message_id,
        conversation_id=payload.conversation_id,
        search_mode=payload.search_mode,
        network_search=payload.network_search,
    )


@router.post("/stream-with-attachments")
async def stream_with_attachments(
    content: str = Form(...),
    client_message_id: str = Form(...),
    conversation_id: str | None = Form(default=None),
    search_mode: str = Form(default="off", pattern="^(off|auto|force)$"),
    network_search: bool = Form(default=False),
    files: list[UploadFile] | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_quota(db, user)

    attachments = await parse_uploads(files)
    return _stream_response(
        db=db,
        user=user,
        content=content,
        client_message_id=client_message_id,
        conversation_id=conversation_id,
        search_mode=search_mode,
        network_search=network_search,
        attachments=attachments,
    )
