"""
教学辅导对话 API 路由测试

使用 Flask test client + SQLite 内存数据库，验证新增路由的请求/响应。

覆盖路由：
- PUT  /api/question/<id>/answer
- GET  /api/question/<id>/chats
- POST /api/chat
- GET  /api/chat/sessions
- GET  /api/chat/<id>/messages
- POST /api/chat/<id>/stream（参数校验部分）
"""

import json
import pytest
from unittest.mock import patch
import uuid
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base, ChatMessage, ProviderConfig, User
from db import crud
from tests.conftest import make_question


TEST_USER_ID = 1


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    _ensure_test_user(test_db)

    class FakeSessionLocal:
        def __call__(self):
            return self

        def __enter__(self):
            return test_db

        def __exit__(self, *args):
            pass

    fake = FakeSessionLocal()
    with patch("web_app.SessionLocal", fake), \
         patch("routes.chat.SessionLocal", fake), \
         patch("routes.questions.SessionLocal", fake), \
         patch("routes.settings.SessionLocal", fake), \
         patch("routes.auth.SessionLocal", fake):
        from web_app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['user_id'] = TEST_USER_ID
                sess['username'] = 'test'
                sess['session_version'] = 0
            yield c



def _ensure_test_user(test_db):
    user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
    if user:
        return user

    user = User(id=TEST_USER_ID, username="test", email="test@test.com", password_hash="x")
    test_db.add(user)
    test_db.commit()
    return user



def _seed_question(test_db):
    _ensure_test_user(test_db)
    questions = [make_question("q1", text="测试题目")]
    batch_info = {"original_filename": "test.pdf", "subject": "数学"}
    crud.save_questions_to_db(test_db, questions, batch_info, user_id=TEST_USER_ID)
    from db.models import Question
    return test_db.query(Question).first()


# ═══════════════════════════════════════════════════════════
# PUT /api/question/<id>/answer
# ═══════════════════════════════════════════════════════════


class TestSaveQuestionAnswer:

    def test_save_answer(self, client, test_db):
        q = _seed_question(test_db)
        resp = client.put(
            f"/api/question/{q.id}/answer",
            json={"answer": "正确答案是 B"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["answer"] == "正确答案是 B"

    def test_missing_answer_field(self, client, test_db):
        q = _seed_question(test_db)
        resp = client.put(f"/api/question/{q.id}/answer", json={})
        assert resp.status_code == 400

    def test_nonexistent_question(self, client, test_db):
        resp = client.put("/api/question/99999/answer", json={"answer": "A"})
        assert resp.status_code == 404

    def test_too_long_answer(self, client, test_db):
        q = _seed_question(test_db)
        resp = client.put(
            f"/api/question/{q.id}/answer",
            json={"answer": "x" * 50001},
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════
# GET /api/question/<id>/chats
# ═══════════════════════════════════════════════════════════


class TestGetQuestionChats:

    def test_empty(self, client, test_db):
        q = _seed_question(test_db)
        resp = client.get(f"/api/question/{q.id}/chats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["sessions"] == []

    def test_with_sessions(self, client, test_db):
        q = _seed_question(test_db)
        crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        resp = client.get(f"/api/question/{q.id}/chats")
        data = resp.get_json()
        assert len(data["sessions"]) == 2


# ═══════════════════════════════════════════════════════════
# POST /api/chat
# ═══════════════════════════════════════════════════════════


class TestCreateChat:

    def test_create(self, client, test_db):
        q = _seed_question(test_db)
        resp = client.post("/api/chat", json={"question_id": q.id})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "id" in data["session"]
        uuid.UUID(str(data["session"]["id"]))

    def test_missing_question_id(self, client, test_db):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        uuid.UUID(str(data["session"]["id"]))

    def test_nonexistent_question(self, client, test_db):
        resp = client.post("/api/chat", json={"question_id": 99999})
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# GET /api/chat/sessions
# ═══════════════════════════════════════════════════════════


class TestGetChatSessions:

    def test_empty(self, client, test_db):
        resp = client.get("/api/chat/sessions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
        assert data["sessions"] == []

    def test_pagination(self, client, test_db):
        q = _seed_question(test_db)
        for _ in range(5):
            crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        resp = client.get("/api/chat/sessions?page=1&page_size=2")
        data = resp.get_json()
        assert data["total"] == 5
        assert len(data["sessions"]) == 2
        assert data["total_pages"] == 3


# ═══════════════════════════════════════════════════════════
# GET /api/chat/<id>/messages
# ═══════════════════════════════════════════════════════════


class TestGetChatMessages:

    def test_empty(self, client, test_db):
        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        resp = client.get(f"/api/chat/{session.public_id}/messages")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["messages"] == []
        assert data["hasMore"] is False

    def test_with_messages(self, client, test_db):
        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        crud.add_chat_message(test_db, session.id, "user", "你好")
        crud.add_chat_message(test_db, session.id, "assistant", "你好呀")
        resp = client.get(f"/api/chat/{session.public_id}/messages")
        data = resp.get_json()
        assert len(data["messages"]) == 2

    def test_cursor_pagination(self, client, test_db):
        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            crud.add_chat_message(test_db, session.id, role, f"消息{i}")

        resp = client.get(f"/api/chat/{session.public_id}/messages?limit=3")
        data = resp.get_json()
        assert len(data["messages"]) == 3
        assert data["hasMore"] is True


# ═══════════════════════════════════════════════════════════
# POST /api/chat/<id>/stream（参数校验）
# ═══════════════════════════════════════════════════════════


class TestStreamChat:

    def test_empty_message(self, client, test_db):
        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        resp = client.post(
            f"/api/chat/{session.public_id}/stream",
            json={"message": ""},
        )
        assert resp.status_code == 400

    def test_invalid_model_provider(self, client, test_db):
        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=TEST_USER_ID)
        resp = client.post(
            f"/api/chat/{session.public_id}/stream",
            json={"message": "你好", "model_provider": "invalid_provider"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "不支持" in data["error"]

    def test_nonexistent_session(self, client, test_db):
        resp = client.post(
            "/api/chat/00000000-0000-0000-0000-000000000000/stream",
            json={"message": "你好"},
        )
        assert resp.status_code == 404

    def test_server_managed_chat_consumes_quota_after_success(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 5
        user.daily_free_used = 0
        user.daily_free_quota_date = datetime.utcnow().date().isoformat()
        test_db.commit()

        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=1)

        def fake_stream_teach(**kwargs):
            yield {"type": "content", "content": "老师回答"}

        with patch("core.config.Settings.load_providers_from_db", return_value=None), \
             patch("agents.teach.stream_teach", side_effect=fake_stream_teach):
            resp = client.post(
                f"/api/chat/{session.public_id}/stream",
                json={"message": "你好", "model_provider": "openai"},
            )

        assert resp.status_code == 200
        body = b"".join(resp.response).decode("utf-8")
        assert '"token": "老师回答"' in body
        assert '"done": true' in body

        user = test_db.query(User).filter(User.id == 1).first()
        assert user.daily_free_used == 1

        messages = test_db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.id).all()
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[0].content == "你好"
        assert messages[1].content == "老师回答"

    def test_user_owned_provider_chat_does_not_consume_quota(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 5
        user.daily_free_used = 0
        user.daily_free_quota_date = datetime.utcnow().date().isoformat()
        test_db.add(ProviderConfig(
            id=str(uuid.uuid4()),
            user_id=1,
            category="openai",
            name="我的 OpenAI",
            is_active=True,
            api_key="sk-test",
            base_url="https://example.com",
            model_name="gpt-4o-mini",
        ))
        test_db.commit()

        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=1)

        def fake_stream_teach(**kwargs):
            yield {"type": "content", "content": "用户自有模型回复"}

        with patch("core.config.Settings.load_providers_from_db", return_value=None), \
             patch("agents.teach.stream_teach", side_effect=fake_stream_teach):
            resp = client.post(
                f"/api/chat/{session.public_id}/stream",
                json={"message": "你好", "model_provider": "openai"},
            )

        assert resp.status_code == 200
        user = test_db.query(User).filter(User.id == 1).first()
        assert user.daily_free_used == 0

    def test_quota_exhausted_chat_returns_429_and_does_not_save_user_message(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 5
        user.daily_free_used = 5
        user.daily_free_quota_date = datetime.utcnow().date().isoformat()
        test_db.commit()

        q = _seed_question(test_db)
        session = crud.create_chat_session(test_db, q.id, user_id=1)

        with patch("core.config.Settings.load_providers_from_db", return_value=None):
            resp = client.post(
                f"/api/chat/{session.public_id}/stream",
                json={"message": "你好", "model_provider": "openai"},
            )

        assert resp.status_code == 429
        data = resp.get_json()
        assert data["success"] is False
        assert data["code"] == "DAILY_FREE_QUOTA_EXCEEDED"
        assert data["quota"]["remaining"] == 0

        messages = test_db.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
        assert messages == []
