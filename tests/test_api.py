def test_login_and_me(client):
    login = client.post("/api/auth/login", json={"email": "User@Example.com", "nickname": "User"})
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


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

