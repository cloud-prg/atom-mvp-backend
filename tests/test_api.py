from app.routers import auth as auth_router
from app.models import EmailVerificationCode, User, UserQuota
from app.services.auth_service import create_oauth_state, hash_verification_code


def admin_login(client):
    return client.post("/api/auth/admin/login", json={"username": "admin", "password": "admin"})


def create_email_user(client, db_session, email: str):
    response = admin_login(client)
    assert response.status_code == 200
    from app.models import User

    user = db_session.query(User).filter_by(email=email.strip().lower()).first()
    if user is None:
        user = User(email=email.strip().lower(), nickname=email.split("@", 1)[0])
        db_session.add(user)
        db_session.commit()
    return user


def email_login(client, db_session, email: str):
    create_email_user(client, db_session, email)
    verification = client.post("/api/auth/email/code", json={"email": email})
    assert verification.status_code == 200

    code = "123456"
    record = db_session.query(EmailVerificationCode).filter_by(email=email.strip().lower()).order_by(EmailVerificationCode.created_at.desc()).first()
    assert record is not None
    record.code_hash = hash_verification_code(email, code)
    db_session.add(record)
    db_session.commit()
    return client.post("/api/auth/email/verify", json={"email": email, "code": code})


def test_admin_login_and_me(client):
    login = admin_login(client)
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@local.atom"


def test_admin_login_does_not_create_message_quota(client, db_session):
    login = admin_login(client)
    assert login.status_code == 200
    token = login.json()["token"]

    quota = client.get("/api/quotas/me", headers={"Authorization": f"Bearer {token}"})
    admin = db_session.query(User).filter_by(email="admin@local.atom").one()

    assert quota.status_code == 200
    assert quota.json() == {
        "remaining_messages": 999999,
        "granted_messages": 999999,
        "used_messages": 0,
    }
    assert db_session.get(UserQuota, admin.id) is None


def test_email_code_login_existing_user_and_me(client, db_session):
    login = email_login(client, db_session, "User@gmail.com")
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@gmail.com"


def test_email_code_login_requires_valid_code(client):
    response = client.post("/api/auth/email/verify", json={"email": "verify@gmail.com", "code": "000000"})
    assert response.status_code == 400


def test_email_code_login_creates_unregistered_email(client, db_session):
    verification = client.post("/api/auth/email/code", json={"email": "newuser@gmail.com"})
    assert verification.status_code == 200
    record = db_session.query(EmailVerificationCode).filter_by(email="newuser@gmail.com").order_by(EmailVerificationCode.created_at.desc()).first()
    assert record is not None
    record.code_hash = hash_verification_code("newuser@gmail.com", "123456")
    db_session.add(record)
    db_session.commit()

    response = client.post("/api/auth/email/verify", json={"email": "newuser@gmail.com", "code": "123456"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "newuser@gmail.com"


def test_email_code_request_only_allows_configured_domain(client):
    response = client.post("/api/auth/email/code", json={"email": "blocked@example.com"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only @gmail.com email accounts are allowed"


def test_github_oauth_login_requires_configuration(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "github_client_id", None, raising=False)
    monkeypatch.setattr(auth_router.settings, "github_client_secret", None, raising=False)

    response = client.get("/api/auth/oauth/github/login")

    assert response.status_code == 503
    assert response.json()["detail"] == "GitHub OAuth is not configured"


def test_github_oauth_login_redirects_to_github(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "github_client_id", "github-client-id", raising=False)
    monkeypatch.setattr(auth_router.settings, "github_client_secret", "github-client-secret", raising=False)
    monkeypatch.setattr(auth_router.settings, "auth_redirect_base_url", "http://127.0.0.1:8000", raising=False)

    response = client.get("/api/auth/oauth/github/login", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=github-client-id" in location
    assert "redirect_uri=http%3A%2F%2F127.0.0.1%3A8000%2Fapi%2Fauth%2Foauth%2Fgithub%2Fcallback" in location
    assert "scope=user%3Aemail" in location


def test_github_oauth_callback_creates_local_session(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "github_client_id", "github-client-id", raising=False)
    monkeypatch.setattr(auth_router.settings, "github_client_secret", "github-client-secret", raising=False)
    monkeypatch.setattr(
        auth_router.settings,
        "frontend_auth_callback_url",
        "http://127.0.0.1:5173/auth/callback",
        raising=False,
    )

    class FakeGitHubOAuthClient:
        def exchange_code_for_token(self, code: str) -> str:
            assert code == "github-code"
            return "github-access-token"

        def fetch_user(self, access_token: str) -> dict:
            assert access_token == "github-access-token"
            return {
                "login": "octocat",
                "name": "The Octocat",
                "email": None,
            }

        def fetch_primary_email(self, access_token: str) -> str | None:
            assert access_token == "github-access-token"
            return "octocat@example.com"

    monkeypatch.setattr(auth_router, "GitHubOAuthClient", FakeGitHubOAuthClient, raising=False)

    state = create_oauth_state()
    response = client.get(f"/api/auth/oauth/github/callback?code=github-code&state={state}", follow_redirects=False)

    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("http://127.0.0.1:5173/auth/callback?")
    assert "token=" in location

    token = location.split("token=", 1)[1].split("&", 1)[0]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "octocat@example.com"
    assert me.json()["nickname"] == "The Octocat"


def test_new_user_gets_signup_message_quota(client, db_session):
    login = email_login(client, db_session, "quota@gmail.com")
    assert login.status_code == 200
    token = login.json()["token"]

    quota = client.get("/api/quotas/me", headers={"Authorization": f"Bearer {token}"})

    assert quota.status_code == 200
    assert quota.json() == {
        "remaining_messages": 6,
        "granted_messages": 6,
        "used_messages": 0,
    }


def test_chat_stream_consumes_message_quota(client, db_session):
    login = email_login(client, db_session, "consume@gmail.com")
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"content": "hello quota", "client_message_id": "quota-1", "search_mode": "off"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert "message.completed" in "".join(response.iter_text())

    quota = client.get("/api/quotas/me", headers=headers)
    assert quota.status_code == 200
    assert quota.json()["remaining_messages"] == 5
    assert quota.json()["used_messages"] == 1


def test_chat_stream_does_not_consume_message_quota_when_response_fails(client, db_session, monkeypatch):
    async def failing_stream_chat_response(prompt, search_results):
        raise RuntimeError("provider failed")
        yield ""

    monkeypatch.setattr("app.services.chat_service.stream_chat_response", failing_stream_chat_response)
    login = email_login(client, db_session, "failed-quota@gmail.com")
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"content": "hello quota", "client_message_id": "quota-failed-1", "search_mode": "off"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())
        assert "message.interrupted" in text
        assert "message.completed" not in text

    quota = client.get("/api/quotas/me", headers=headers)
    assert quota.status_code == 200
    assert quota.json()["remaining_messages"] == 6
    assert quota.json()["used_messages"] == 0


def test_chat_stream_rejects_when_message_quota_exhausted(client, db_session):
    login = email_login(client, db_session, "limited@gmail.com")
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    for index in range(6):
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"content": f"quota message {index}", "client_message_id": f"quota-limit-{index}", "search_mode": "off"},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert "message.completed" in "".join(response.iter_text())

    exhausted = client.post(
        "/api/chat/stream",
        json={"content": "one more", "client_message_id": "quota-limit-7", "search_mode": "off"},
        headers=headers,
    )

    assert exhausted.status_code == 402
    assert exhausted.json()["detail"] == "Message quota exhausted"


def test_admin_chat_stream_is_not_limited_by_message_quota(client, db_session):
    login = admin_login(client)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    for index in range(7):
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"content": f"admin quota message {index}", "client_message_id": f"admin-quota-{index}", "search_mode": "off"},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            assert "message.completed" in "".join(response.iter_text())

    admin = db_session.query(User).filter_by(email="admin@local.atom").one()
    assert db_session.get(UserQuota, admin.id) is None


def test_github_oauth_callback_rejects_invalid_state(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "github_client_id", "github-client-id", raising=False)
    monkeypatch.setattr(auth_router.settings, "github_client_secret", "github-client-secret", raising=False)

    response = client.get("/api/auth/oauth/github/callback?code=github-code&state=bad-state", follow_redirects=False)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid GitHub OAuth state"


def test_conversation_and_message_crud(client, auth_headers):
    created = client.post("/api/conversations", json={"title": "Planning"}, headers=auth_headers)
    assert created.status_code == 200
    conversation_id = created.json()["id"]

    message = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"role": "user", "content": "hello", "client_message_id": "m-1"},
        headers=auth_headers,
    )
    assert message.status_code == 200
    assert message.json()["content"] == "hello"

    messages = client.get(f"/api/conversations/{conversation_id}/messages", headers=auth_headers)
    assert messages.status_code == 200
    assert len(messages.json()) == 1


def test_mock_search_fallback(client, auth_headers):
    response = client.post(
        "/api/search",
        json={"query": "latest AI workbench patterns", "mode": "force"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["status"] == "completed"
    assert len(body["results"]) >= 1


def test_chat_stream_creates_recoverable_messages(client, auth_headers):
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"content": "今天的 AI 工作台怎么做", "client_message_id": "stream-1", "search_mode": "auto"},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())

    assert "message.created" in text
    assert "message.completed" in text

    conversations = client.get("/api/conversations", headers=auth_headers).json()
    assert len(conversations) == 1
    conversation_id = conversations[0]["id"]

    messages = client.get(f"/api/conversations/{conversation_id}/messages", headers=auth_headers).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[-1]["status"] == "completed"
