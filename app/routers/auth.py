from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import EmailVerificationRequestIn, EmailVerificationRequestOut, EmailVerifyIn, LoginIn, LoginOut, UserOut
from app.services.auth_service import (
    GitHubOAuthClient,
    create_oauth_state,
    create_email_verification_code,
    login_admin_user,
    login_or_create_oauth_user,
    logout,
    verify_email_code_and_login,
    verify_oauth_state,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/admin/login", response_model=LoginOut)
def admin_login(payload: LoginIn, db: Session = Depends(get_db)) -> LoginOut:
    try:
        token, user = login_admin_user(db, payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid admin credentials") from exc
    return LoginOut(token=token, user=UserOut.model_validate(user))


@router.post("/email/code", response_model=EmailVerificationRequestOut)
def request_email_verification(payload: EmailVerificationRequestIn, db: Session = Depends(get_db)) -> EmailVerificationRequestOut:
    try:
        create_email_verification_code(db, payload.email)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response is not None else "Email provider request failed"
        raise HTTPException(status_code=502, detail=f"Email provider request failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Email provider request failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EmailVerificationRequestOut(
        ok=True,
        expires_in_seconds=settings.email_verification_ttl_minutes * 60,
    )


@router.post("/email/verify", response_model=LoginOut)
def verify_email(payload: EmailVerifyIn, db: Session = Depends(get_db)) -> LoginOut:
    try:
        token, user = verify_email_code_and_login(db, payload.email, payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LoginOut(token=token, user=UserOut.model_validate(user))


@router.post("/logout")
def logout_route(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict[str, bool]:
    if authorization and authorization.lower().startswith("bearer "):
        logout(db, authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


def _github_oauth_configured() -> bool:
    return bool(settings.github_client_id and settings.github_client_secret)


@router.get("/oauth/github/login")
def github_oauth_login() -> RedirectResponse:
    if not _github_oauth_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    state = create_oauth_state()
    return RedirectResponse(GitHubOAuthClient().build_authorize_url(state))


@router.get("/oauth/github/callback")
def github_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        query = urlencode({"error": error})
        return RedirectResponse(f"{settings.frontend_auth_callback_url}?{query}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing GitHub OAuth code")
    if not verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid GitHub OAuth state")
    if not _github_oauth_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    oauth_client = GitHubOAuthClient()
    try:
        access_token = oauth_client.exchange_code_for_token(code)
        github_user = oauth_client.fetch_user(access_token)
        email = github_user.get("email") or oauth_client.fetch_primary_email(access_token)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="GitHub OAuth request failed") from exc

    if not email:
        raise HTTPException(status_code=400, detail="GitHub account does not expose a verified email")

    nickname = github_user.get("name") or github_user.get("login") or email.split("@", 1)[0]
    token, user = login_or_create_oauth_user(db, email=email, nickname=nickname)
    query = urlencode({"token": token, "user_id": user.id})
    return RedirectResponse(f"{settings.frontend_auth_callback_url}?{query}")
