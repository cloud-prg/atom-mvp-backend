from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import QuotaOut
from app.services.quota_service import get_user_quota

router = APIRouter(prefix="/quotas", tags=["quotas"])


@router.get("/me", response_model=QuotaOut)
def me_quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> QuotaOut:
    quota = get_user_quota(db, user)
    return QuotaOut(
        remaining_messages=quota.remaining_messages,
        granted_messages=quota.granted_messages,
        used_messages=quota.used_messages,
    )
