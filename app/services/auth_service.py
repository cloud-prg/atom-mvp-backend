from datetime import timedelta
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SessionToken, User, utc_now


def hash_token(token: str) -> str:
    return sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()


def login_or_create_user(db: Session, email: str, nickname: str) -> tuple[str, User]:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(email=normalized_email, nickname=nickname.strip())
        db.add(user)
        db.flush()
    else:
        user.nickname = nickname.strip()

    raw_token = token_urlsafe(32)
    session = SessionToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    return raw_token, user


def logout(db: Session, token: str) -> None:
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == hash_token(token)))
    if session:
        db.delete(session)
        db.commit()

