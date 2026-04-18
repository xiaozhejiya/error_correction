"""
教学辅导对话 CRUD 函数单元测试

使用 SQLite 内存数据库，不依赖磁盘文件。

覆盖函数：
- update_question_answer
- create_chat_session
- add_chat_message
- get_chat_messages（游标分页）
- get_chat_sessions_by_question
- get_all_chat_sessions
"""

import pytest

from tests.conftest import make_question
from db.crud import (
    save_questions_to_db,
    update_question_answer,
    create_chat_session,
    add_chat_message,
    get_chat_messages,
    get_chat_sessions_by_question,
    get_all_chat_sessions,
)


# ═══════════════════════════════════════════════════════════
# helper
# ═══════════════════════════════════════════════════════════


def _seed_question(db):
    """插入一道题目并返回其 ORM 对象"""
    questions = [make_question("q1", text="测试题目")]
    batch_info = {"original_filename": "test.pdf", "subject": "数学"}
    result = save_questions_to_db(db, questions, batch_info)
    assert result["created"] == 1
    from db.models import Question
    return db.query(Question).first()


# ═══════════════════════════════════════════════════════════
# update_question_answer
# ═══════════════════════════════════════════════════════════


class TestUpdateQuestionAnswer:

    def test_save_answer(self, db):
        q = _seed_question(db)
        result = update_question_answer(db, q.id, "答案是 A")
        assert result is not None
        assert result.answer == "答案是 A"

    def test_update_existing_answer(self, db):
        q = _seed_question(db)
        update_question_answer(db, q.id, "旧答案")
        result = update_question_answer(db, q.id, "新答案")
        assert result.answer == "新答案"

    def test_nonexistent_question(self, db):
        result = update_question_answer(db, 99999, "答案")
        assert result is None


# ═══════════════════════════════════════════════════════════
# create_chat_session
# ═══════════════════════════════════════════════════════════


class TestCreateChatSession:

    def test_create(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        assert session.id is not None
        assert session.question_id == q.id

    def test_multiple_sessions(self, db):
        q = _seed_question(db)
        s1 = create_chat_session(db, q.id)
        s2 = create_chat_session(db, q.id)
        assert s1.id != s2.id


# ═══════════════════════════════════════════════════════════
# add_chat_message
# ═══════════════════════════════════════════════════════════


class TestAddChatMessage:

    def test_add_user_message(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        msg = add_chat_message(db, session.id, "user", "你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.session_id == session.id

    def test_add_assistant_message(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        msg = add_chat_message(db, session.id, "assistant", "你好呀")
        assert msg.role == "assistant"

    def test_invalid_role_rejected(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        with pytest.raises(ValueError, match="无效的消息角色"):
            add_chat_message(db, session.id, "system", "不允许的角色")

    def test_updates_session_timestamp(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        original_updated = session.updated_at
        add_chat_message(db, session.id, "user", "消息")
        db.refresh(session)
        assert session.updated_at >= original_updated


# ═══════════════════════════════════════════════════════════
# get_chat_messages（游标分页）
# ═══════════════════════════════════════════════════════════


class TestGetChatMessages:

    def _seed_messages(self, db, count=5):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        for i in range(count):
            role = "user" if i % 2 == 0 else "assistant"
            add_chat_message(db, session.id, role, f"消息{i}")
        return session

    def test_basic_fetch(self, db):
        session = self._seed_messages(db, 5)
        result = get_chat_messages(db, session.id, limit=30)
        assert len(result["messages"]) == 5
        assert result["hasMore"] is False

    def test_limit(self, db):
        session = self._seed_messages(db, 10)
        result = get_chat_messages(db, session.id, limit=3)
        assert len(result["messages"]) == 3
        assert result["hasMore"] is True

    def test_messages_in_order(self, db):
        session = self._seed_messages(db, 5)
        result = get_chat_messages(db, session.id, limit=30)
        ids = [m["id"] for m in result["messages"]]
        assert ids == sorted(ids)

    def test_cursor_pagination(self, db):
        session = self._seed_messages(db, 10)
        # 第一页
        page1 = get_chat_messages(db, session.id, limit=4)
        assert len(page1["messages"]) == 4
        assert page1["hasMore"] is True

        # 第二页：before_id 为第一页第一条的 id
        first_id = page1["messages"][0]["id"]
        page2 = get_chat_messages(db, session.id, limit=30, before_id=first_id)
        # page2 的所有消息 id 应小于 first_id
        for m in page2["messages"]:
            assert m["id"] < first_id

    def test_empty_session(self, db):
        q = _seed_question(db)
        session = create_chat_session(db, q.id)
        result = get_chat_messages(db, session.id, limit=30)
        assert len(result["messages"]) == 0
        assert result["hasMore"] is False


# ═══════════════════════════════════════════════════════════
# get_chat_sessions_by_question
# ═══════════════════════════════════════════════════════════


class TestGetChatSessionsByQuestion:

    def test_returns_sessions(self, db):
        q = _seed_question(db)
        create_chat_session(db, q.id)
        create_chat_session(db, q.id)
        sessions = get_chat_sessions_by_question(db, q.id)
        assert len(sessions) == 2

    def test_no_sessions(self, db):
        q = _seed_question(db)
        sessions = get_chat_sessions_by_question(db, q.id)
        assert sessions == []

    def test_limit(self, db):
        q = _seed_question(db)
        for _ in range(5):
            create_chat_session(db, q.id)
        sessions = get_chat_sessions_by_question(db, q.id, limit=3)
        assert len(sessions) == 3


# ═══════════════════════════════════════════════════════════
# get_all_chat_sessions
# ═══════════════════════════════════════════════════════════


class TestGetAllChatSessions:

    def test_pagination(self, db):
        q = _seed_question(db)
        for _ in range(5):
            create_chat_session(db, q.id)

        sessions, total = get_all_chat_sessions(db, page=1, page_size=2)
        assert total == 5
        assert len(sessions) == 2

        sessions2, _ = get_all_chat_sessions(db, page=2, page_size=2)
        assert len(sessions2) == 2

    def test_empty(self, db):
        sessions, total = get_all_chat_sessions(db)
        assert total == 0
        assert sessions == []
