from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, LoginOut, UserOut
from app.services.auth_service import login_or_create_user, logout

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> LoginOut:
    token, user = login_or_create_user(db, payload.email, payload.nickname)
    return LoginOut(token=token, user=UserOut.model_validate(user))


@router.post("/logout")
def logout_route(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict[str, bool]:
    if authorization and authorization.lower().startswith("bearer "):
        logout(db, authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user

