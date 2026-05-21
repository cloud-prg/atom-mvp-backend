from datetime import timedelta
from hmac import compare_digest, new as hmac_new
from hashlib import sha256
from random import SystemRandom
from secrets import token_urlsafe
from time import time
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EmailVerificationCode, SessionToken, User, utc_now
from app.services.quota_service import ensure_signup_quota


def _as_aware_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_now().tzinfo)
    return value


def hash_token(token: str) -> str:
    return sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()


def hash_verification_code(email: str, code: str) -> str:
    normalized_email = email.strip().lower()
    return sha256(f"{settings.session_secret}:{normalized_email}:{code}".encode("utf-8")).hexdigest()


def normalize_allowed_email(email: str) -> str:
    normalized_email = email.strip().lower()
    allowed_domain = settings.allowed_email_domain.strip().lower()
    if not normalized_email.endswith(f"@{allowed_domain}"):
        raise ValueError(f"Only @{allowed_domain} email accounts are allowed")
    return normalized_email


def send_email_verification_code(email: str, code: str) -> None:
    if not settings.resend_api_key:
        raise ValueError("Email provider is not configured")
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.email_from,
            "to": [email],
            "subject": "Atom MVP verification code",
            "text": f"Your Atom MVP verification code is {code}. It expires in {settings.email_verification_ttl_minutes} minutes.",
        },
        timeout=10,
    )
    response.raise_for_status()


def create_email_verification_code(db: Session, email: str) -> None:
    normalized_email = normalize_allowed_email(email)
    code = f"{SystemRandom().randint(0, 999999):06d}"
    verification = EmailVerificationCode(
        email=normalized_email,
        code_hash=hash_verification_code(normalized_email, code),
        purpose="login",
        expires_at=utc_now() + timedelta(minutes=settings.email_verification_ttl_minutes),
    )
    db.add(verification)
    db.commit()
    send_email_verification_code(normalized_email, code)


def consume_email_verification_code(db: Session, email: str, code: str) -> None:
    normalized_email = normalize_allowed_email(email)
    now = utc_now()
    verification = db.scalar(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == "login",
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    if (
        verification is None
        or _as_aware_utc(verification.expires_at) < now
        or not compare_digest(verification.code_hash, hash_verification_code(normalized_email, code))
    ):
        raise ValueError("Invalid or expired verification code")
    verification.consumed_at = now
    db.add(verification)


def verify_email_code_and_login(db: Session, email: str, code: str) -> tuple[str, User]:
    normalized_email = normalize_allowed_email(email)
    consume_email_verification_code(db, normalized_email, code)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(email=normalized_email, nickname=normalized_email.split("@", 1)[0])
        db.add(user)
        db.flush()
    ensure_signup_quota(db, user)
    token = build_session_for_user(db, user)
    return token, user


def login_admin_user(db: Session, username: str, password: str) -> tuple[str, User]:
    if username != "admin" or password != "admin":
        raise ValueError("Invalid admin credentials")
    email = "admin@local.atom"
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, nickname="admin")
        db.add(user)
        db.flush()
    token = build_session_for_user(db, user)
    return token, user


def build_session_for_user(db: Session, user: User) -> str:
    raw_token = token_urlsafe(32)
    session = SessionToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    return raw_token


def login_or_create_oauth_user(db: Session, email: str, nickname: str) -> tuple[str, User]:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(email=normalized_email, nickname=nickname.strip())
        db.add(user)
        db.flush()
        ensure_signup_quota(db, user)
    elif nickname.strip():
        user.nickname = nickname.strip()
        ensure_signup_quota(db, user)

    token = build_session_for_user(db, user)
    return token, user


def logout(db: Session, token: str) -> None:
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == hash_token(token)))
    if session:
        db.delete(session)
        db.commit()


def create_oauth_state() -> str:
    issued_at = str(int(time()))
    nonce = token_urlsafe(24)
    payload = f"{issued_at}.{nonce}"
    signature = hmac_new(settings.session_secret.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_oauth_state(state: str | None, max_age_seconds: int = 600) -> bool:
    if not state:
        return False
    parts = state.split(".")
    if len(parts) != 3:
        return False
    issued_at, nonce, signature = parts
    if not issued_at.isdigit() or not nonce:
        return False
    if int(time()) - int(issued_at) > max_age_seconds:
        return False

    payload = f"{issued_at}.{nonce}"
    expected = hmac_new(settings.session_secret.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()
    return compare_digest(signature, expected)


class GitHubOAuthClient:
    authorize_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    user_url = "https://api.github.com/user"
    emails_url = "https://api.github.com/user/emails"

    def build_authorize_url(self, state: str) -> str:
        redirect_uri = f"{settings.auth_redirect_base_url.rstrip('/')}/api/auth/oauth/github/callback"
        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": redirect_uri,
                "scope": "user:email",
                "state": state,
            }
        )
        return f"{self.authorize_url}?{query}"

    def exchange_code_for_token(self, code: str) -> str:
        response = httpx.post(
            self.token_url,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError("GitHub did not return an access token")
        return access_token

    def fetch_user(self, access_token: str) -> dict:
        response = httpx.get(
            self.user_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def fetch_primary_email(self, access_token: str) -> str | None:
        response = httpx.get(
            self.emails_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        response.raise_for_status()
        emails = response.json()
        for email in emails:
            if email.get("primary") and email.get("verified") and email.get("email"):
                return email["email"]
        for email in emails:
            if email.get("verified") and email.get("email"):
                return email["email"]
        return None
