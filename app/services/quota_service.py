from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import QuotaLedger, User, UserQuota, utc_now


class MessageQuotaExhausted(Exception):
    pass


def ensure_signup_quota(db: Session, user: User) -> UserQuota:
    quota = db.get(UserQuota, user.id)
    if quota:
        return quota

    amount = settings.signup_message_quota
    quota = UserQuota(
        user_id=user.id,
        remaining_messages=amount,
        granted_messages=amount,
        used_messages=0,
        updated_at=utc_now(),
    )
    db.add(quota)
    db.flush()
    db.add(
        QuotaLedger(
            user_id=user.id,
            type="grant",
            amount=amount,
            balance_after=amount,
            reason="signup_bonus",
        )
    )
    return quota


def get_user_quota(db: Session, user: User) -> UserQuota:
    quota = ensure_signup_quota(db, user)
    db.commit()
    db.refresh(quota)
    return quota


def consume_message_quota(db: Session, user: User, request_id: str) -> UserQuota:
    ensure_signup_quota(db, user)
    result = db.execute(
        update(UserQuota)
        .where(UserQuota.user_id == user.id, UserQuota.remaining_messages >= 1)
        .values(
            remaining_messages=UserQuota.remaining_messages - 1,
            used_messages=UserQuota.used_messages + 1,
            updated_at=utc_now(),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise MessageQuotaExhausted

    quota = db.get(UserQuota, user.id)
    if quota is None:
        db.rollback()
        raise MessageQuotaExhausted

    db.add(
        QuotaLedger(
            user_id=user.id,
            type="consume",
            amount=-1,
            balance_after=quota.remaining_messages,
            reason="chat_stream",
            request_id=request_id,
        )
    )
    db.commit()
    db.refresh(quota)
    return quota


def refund_message_quota(db: Session, user: User, request_id: str, reason: str = "chat_stream_failed") -> UserQuota:
    ensure_signup_quota(db, user)
    quota = db.get(UserQuota, user.id)
    if quota is None:
        raise MessageQuotaExhausted

    quota.remaining_messages += 1
    quota.used_messages = max(0, quota.used_messages - 1)
    quota.updated_at = utc_now()
    db.add(quota)
    db.flush()
    db.add(
        QuotaLedger(
            user_id=user.id,
            type="refund",
            amount=1,
            balance_after=quota.remaining_messages,
            reason=reason,
            request_id=request_id,
        )
    )
    db.commit()
    db.refresh(quota)
    return quota
