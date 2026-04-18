"""
Flask 路由集成测试

使用 Flask test client + SQLite 内存数据库，验证 API 路由的请求/响应。
不依赖外部服务。

覆盖路由：
- GET  /api/status
- GET  /api/history
- GET  /api/search
- GET  /api/stats
- DELETE /api/question/<id>
"""

import io
import uuid
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base, User, SystemProviderConfig
from db import crud

# 测试用户 ID，与 client fixture 中的 session['user_id'] 一致
TEST_USER_ID = 1


@pytest.fixture
def test_db():
    """内存数据库 + 建表 + 创建测试用户"""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    # 创建测试用户（与 client session 中的 user_id 匹配）
    user = User(
        id=TEST_USER_ID, username="test", email="test@test.com", password_hash="x"
    )
    session.add(user)
    session.commit()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def avatar_upload_dir(tmp_path, monkeypatch):
    avatar_dir = tmp_path / "uploads"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("routes.auth.settings.upload_dir", avatar_dir)
    yield avatar_dir


@pytest.fixture
def client(test_db):
    """Flask test client，用内存数据库替换 SessionLocal"""

    # 创建一个 context manager 代理，让 with SessionLocal() as db 使用 test_db
    class FakeSessionLocal:
        def __call__(self):
            return self

        def __enter__(self):
            return test_db

        def __exit__(self, *args):
            pass

    fake = FakeSessionLocal()
    with (
        patch("web_app.SessionLocal", fake),
        patch("routes.settings.SessionLocal", fake),
        patch("routes.questions.SessionLocal", fake),
        patch("routes.stats.SessionLocal", fake),
        patch("routes.upload.SessionLocal", fake),
        patch("routes.chat.SessionLocal", fake),
        patch("routes.auth.SessionLocal", fake),
    ):
        from web_app import app

        app.config["TESTING"] = True
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = TEST_USER_ID
                sess["username"] = "test"
                sess["session_version"] = 0
            yield c


# ── /api/status ──────────────────────────────────────────


class TestStatusRoute:
    """GET /api/status"""

    def test_returns_success(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "status" in data

    def test_contains_model_info(self, client):
        resp = client.get("/api/status")
        status = resp.get_json()["status"]
        assert "available_models" in status
        assert isinstance(status["available_models"], list)
        assert len(status["available_models"]) >= 1

    def test_falls_back_to_managed_provider(self, client, test_db):
        provider = SystemProviderConfig(
            id=str(uuid.uuid4()),
            category="openai",
            name="平台 OpenAI",
            is_active=True,
            api_key="sk-managed",
            base_url="https://example.com",
            model_name="gpt-4o-mini",
        )
        ocr_provider = SystemProviderConfig(
            id=str(uuid.uuid4()),
            category="paddleocr",
            name="平台 OCR",
            is_active=True,
            api_key="ocr-token",
            base_url="https://ocr.example.com",
            model_name="PaddleOCR-VL-1.5",
        )
        test_db.add(provider)
        test_db.add(ocr_provider)
        test_db.commit()

        status = client.get("/api/status").get_json()["status"]
        openai = next(m for m in status["available_models"] if m["value"] == "openai")
        assert openai["configured"] is True
        assert openai["managed"] is True
        assert openai["default_model"] == "gpt-4o-mini"
        assert status["paddleocr_configured"] is True


# ── /api/history ─────────────────────────────────────────


class TestHistoryRoute:
    """GET /api/history"""

    def test_empty_history(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["items"] == []
        assert data["total"] == 0

    def test_pagination_params(self, client):
        resp = client.get("/api/history?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_invalid_date_format(self, client):
        resp = client.get("/api/history?start_date=not-a-date")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False


# ── /api/search ──────────────────────────────────────────


class TestSearchRoute:
    """GET /api/search"""

    def test_requires_search_param(self, client):
        """无搜索条件应返回 400"""
        resp = client.get("/api/search")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_search_by_keyword(self, client):
        resp = client.get("/api/search?keyword=导数")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "items" in data

    def test_search_by_question_type(self, client):
        resp = client.get("/api/search?question_type=选择题")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ── /api/stats ───────────────────────────────────────────


class TestStatsRoute:
    """GET /api/stats"""

    def test_empty_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_tags"] == 0


# ── DELETE /api/question/<id> ────────────────────────────


class TestDeleteQuestionRoute:
    """DELETE /api/question/<id>"""

    def test_delete_nonexistent(self, client):
        resp = client.delete("/api/question/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False

    def test_delete_existing(self, client, test_db):
        """先入库再删除"""
        from db.crud import save_questions_to_db

        qs = [
            {
                "question_id": "1",
                "question_type": "选择题",
                "content_blocks": [{"block_type": "text", "content": "测试题目"}],
                "has_formula": False,
                "has_image": False,
            }
        ]
        save_questions_to_db(
            test_db,
            qs,
            {
                "original_filename": "test.pdf",
                "subject": "数学",
            },
            user_id=TEST_USER_ID,
        )

        # 查询刚插入的题目 ID
        from db.models import Question

        q = test_db.query(Question).first()
        assert q is not None

        resp = client.delete(f"/api/question/{q.id}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ── /api/error-bank ────────────────────────────────────


class TestErrorBankRoute:
    """GET /api/error-bank"""

    def test_empty(self, client):
        resp = client.get("/api/error-bank")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["items"] == []
        assert data["total"] == 0

    def test_with_filters(self, client):
        resp = client.get("/api/error-bank?subject=数学&question_type=选择题")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_pagination(self, client):
        resp = client.get("/api/error-bank?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_invalid_date(self, client):
        resp = client.get("/api/error-bank?start_date=bad")
        assert resp.status_code == 400

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db

        qs = [
            {
                "question_id": "1",
                "question_type": "选择题",
                "content_blocks": [{"block_type": "text", "content": "错题库测试"}],
                "has_formula": False,
                "has_image": False,
            }
        ]
        save_questions_to_db(
            test_db,
            qs,
            {
                "original_filename": "test.pdf",
                "subject": "数学",
            },
            user_id=TEST_USER_ID,
        )
        resp = client.get("/api/error-bank")
        data = resp.get_json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["subject"] == "数学"
        assert "knowledge_tags" in item


# ── /api/subjects ──────────────────────────────────────


class TestSubjectsRoute:
    """GET /api/subjects"""

    def test_empty(self, client):
        resp = client.get("/api/subjects")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["subjects"] == []

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "t"}],
                    "has_formula": False,
                    "has_image": False,
                }
            ],
            {"original_filename": "a.pdf", "subject": "高中数学"},
            user_id=TEST_USER_ID,
        )
        resp = client.get("/api/subjects")
        assert "高中数学" in resp.get_json()["subjects"]


# ── /api/question-types ────────────────────────────────


class TestQuestionTypesRoute:
    """GET /api/question-types"""

    def test_empty(self, client):
        resp = client.get("/api/question-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["question_types"] == []


# ── PATCH /api/question/<id>/answer ────────────────────


class TestUpdateAnswerRoute:
    """PATCH /api/question/<id>/answer"""

    def test_missing_field(self, client):
        resp = client.patch("/api/question/1/answer", json={})
        assert resp.status_code == 400

    def test_nonexistent(self, client):
        resp = client.patch("/api/question/99999/answer", json={"user_answer": "A"})
        assert resp.status_code == 404

    def test_save_answer(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "答案测试"}],
                    "has_formula": False,
                    "has_image": False,
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        from db.models import Question

        q = test_db.query(Question).first()
        resp = client.patch(f"/api/question/{q.id}/answer", json={"user_answer": "选B"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user_answer"] == "选B"


# ── POST /api/export-from-db ──────────────────────────


class TestExportFromDbRoute:
    """POST /api/export-from-db"""

    def test_empty_ids(self, client):
        resp = client.post("/api/export-from-db", json={"selected_ids": []})
        assert resp.status_code == 400

    def test_nonexistent_ids(self, client):
        resp = client.post("/api/export-from-db", json={"selected_ids": [99999]})
        assert resp.status_code == 404


# ── PATCH /api/question/<id>/review-status ────────────


class TestUpdateReviewStatusRoute:
    """PATCH /api/question/<id>/review-status"""

    def test_missing_field(self, client):
        resp = client.patch("/api/question/1/review-status", json={})
        assert resp.status_code == 400

    def test_invalid_status(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "状态测试"}],
                    "has_formula": False,
                    "has_image": False,
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        from db.models import Question

        q = test_db.query(Question).first()
        resp = client.patch(
            f"/api/question/{q.id}/review-status", json={"review_status": "无效"}
        )
        assert resp.status_code == 400

    def test_nonexistent(self, client):
        resp = client.patch(
            "/api/question/99999/review-status", json={"review_status": "已掌握"}
        )
        assert resp.status_code == 404

    def test_update_status(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [
                        {"block_type": "text", "content": "复习状态测试"}
                    ],
                    "has_formula": False,
                    "has_image": False,
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        from db.models import Question

        q = test_db.query(Question).first()
        resp = client.patch(
            f"/api/question/{q.id}/review-status", json={"review_status": "已掌握"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["review_status"] == "已掌握"


# ── GET /api/dashboard-stats ─────────────────────────


class TestDashboardStatsRoute:
    """GET /api/dashboard-stats"""

    def test_empty(self, client):
        resp = client.get("/api/dashboard-stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "review_stats" in data
        assert "total_questions" in data
        assert "daily_counts" in data
        assert "tag_stats" in data
        assert "tag_status_stats" in data
        assert "tag_type_stats" in data
        assert "subjects" in data

    def test_with_data(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "统计测试"}],
                    "has_formula": False,
                    "has_image": False,
                    "knowledge_tags": ["导数"],
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        resp = client.get("/api/dashboard-stats")
        data = resp.get_json()
        assert data["total_questions"] == 1
        assert len(data["daily_counts"]) == 30
        assert "mastered" in data["daily_counts"][0]
        assert data["subjects"] == ["数学"]
        assert any(t["tag_name"] == "导数" for t in data["tag_status_stats"])

    def test_subject_filter(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "数学题"}],
                    "has_formula": False,
                    "has_image": False,
                    "knowledge_tags": ["函数"],
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "2",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "英语题"}],
                    "has_formula": False,
                    "has_image": False,
                    "knowledge_tags": ["语法"],
                }
            ],
            {"original_filename": "b.pdf", "subject": "英语"},
            user_id=TEST_USER_ID,
        )
        resp = client.get("/api/dashboard-stats")
        data = resp.get_json()
        assert data["total_questions"] == 2
        resp = client.get("/api/dashboard-stats?subject=数学")
        data = resp.get_json()
        assert data["total_questions"] == 1
        assert any(t["tag_name"] == "函数" for t in data["tag_stats"])


# ── GET /api/error-bank?review_status ────────────────


class TestErrorBankReviewStatusFilter:
    """GET /api/error-bank with review_status filter"""

    def test_filter_by_review_status(self, client, test_db):
        from db.crud import save_questions_to_db, update_review_status

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "待复习题"}],
                    "has_formula": False,
                    "has_image": False,
                },
                {
                    "question_id": "2",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "已掌握题"}],
                    "has_formula": False,
                    "has_image": False,
                },
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        from db.models import Question

        qs = test_db.query(Question).all()
        update_review_status(test_db, qs[1].id, "已掌握")

        resp = client.get("/api/error-bank?review_status=已掌握")
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["review_status"] == "已掌握"


# ── POST /api/ai-analysis ─────────────────────────────


class TestAiAnalysisRoute:
    """POST /api/ai-analysis"""

    def test_empty_ids(self, client):
        resp = client.post("/api/ai-analysis", json={"question_ids": []})
        assert resp.status_code == 400

    def test_missing_ids(self, client):
        resp = client.post("/api/ai-analysis", json={})
        assert resp.status_code == 400

    def test_too_many_ids(self, client):
        resp = client.post(
            "/api/ai-analysis", json={"question_ids": list(range(1, 22))}
        )
        assert resp.status_code == 400

    def test_nonexistent_ids(self, client):
        resp = client.post("/api/ai-analysis", json={"question_ids": [99999]})
        assert resp.status_code == 404

    def test_success(self, client, test_db):
        from db.crud import save_questions_to_db

        save_questions_to_db(
            test_db,
            [
                {
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "AI分析测试"}],
                    "has_formula": False,
                    "has_image": False,
                    "knowledge_tags": ["导数"],
                }
            ],
            {"original_filename": "a.pdf", "subject": "数学"},
            user_id=TEST_USER_ID,
        )
        from db.models import Question

        q = test_db.query(Question).first()
        resp = client.post("/api/ai-analysis", json={"question_ids": [q.id]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "analysis" in data
        analysis = data["analysis"]
        assert "summary" in analysis
        assert "weak_points" in analysis
        assert "suggestions" in analysis
        assert "per_question" in analysis
        assert len(analysis["per_question"]) == 1


# ── POST /api/config/model ─────────────────────────────


class TestSwitchModelRoute:
    """POST /api/config/model"""

    def test_unauthenticated(self, client):
        """未登录应返回 401"""
        # 清除 session 中的 user_id
        with client.session_transaction() as sess:
            sess.pop("user_id", None)

        resp = client.post(
            "/api/config/model",
            json={
                "model_provider": "openai",
                "model_name": "gpt-4o",
            },
        )
        assert resp.status_code == 401
        # 未登录可能返回 HTML 或 JSON，只验证状态码

    def test_missing_model_provider(self, client):
        """缺少 model_provider 参数应返回 400"""
        resp = client.post(
            "/api/config/model",
            json={
                "model_name": "gpt-4o",
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "model_provider" in data["error"]

    def test_invalid_provider_id(self, client):
        """无效的 provider_id 格式应返回 400"""
        resp = client.post(
            "/api/config/model",
            json={
                "model_provider": "openai",
                "provider_id": "invalid-uuid",
                "model_name": "gpt-4o",
            },
        )
        # UUID 格式验证失败返回 400
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "provider_id" in data["error"] or "无效" in data["error"]

    def test_switch_without_provider_id(self, client, test_db):
        """不带 provider_id 时切换到当前 active provider"""
        from db.models import ProviderConfig
        import uuid

        # 创建已配置的 provider（使用有效 UUID）
        provider = ProviderConfig(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            category="openai",
            name="Test OpenAI",
            api_key="test-key",
            model_name="gpt-3.5-turbo",
            is_active=True,
        )
        test_db.add(provider)
        test_db.commit()

        resp = client.post(
            "/api/config/model",
            json={
                "model_provider": "openai",
                "model_name": "gpt-4o",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["model_name"] == "gpt-4o"

        # 验证数据库已更新
        test_db.refresh(provider)
        assert provider.model_name == "gpt-4o"

    def test_switch_with_provider_id(self, client, test_db):
        """带 provider_id 时切换到指定 provider 并设为 active"""
        from db.models import ProviderConfig
        import uuid

        # 创建两个 provider（使用有效 UUID）
        provider1_id = str(uuid.uuid4())
        provider2_id = str(uuid.uuid4())
        provider1 = ProviderConfig(
            id=provider1_id,
            user_id=TEST_USER_ID,
            category="openai",
            name="OpenAI 1",
            api_key="key1",
            model_name="gpt-3.5-turbo",
            is_active=True,
        )
        provider2 = ProviderConfig(
            id=provider2_id,
            user_id=TEST_USER_ID,
            category="openai",
            name="OpenAI 2",
            api_key="key2",
            model_name="gpt-4",
            is_active=False,
        )
        test_db.add_all([provider1, provider2])
        test_db.commit()

        resp = client.post(
            "/api/config/model",
            json={
                "model_provider": "openai",
                "provider_id": provider2_id,
                "model_name": "gpt-4o-mini",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["model_name"] == "gpt-4o-mini"

        # 验证 provider2 被设为 active，provider1 被设为 inactive
        test_db.refresh(provider1)
        test_db.refresh(provider2)
        assert provider1.is_active is False
        assert provider2.is_active is True
        assert provider2.model_name == "gpt-4o-mini"

    def test_switch_unconfigured_provider(self, client, test_db):
        """切换到未配置的 provider（无 api_key）应返回 400"""
        from db.models import ProviderConfig
        import uuid

        # 创建未配置的 provider（使用有效 UUID，但 api_key 为空）
        provider = ProviderConfig(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            category="openai",
            name="Unconfigured",
            api_key="",
            model_name="",
            is_active=False,
        )
        test_db.add(provider)
        test_db.commit()

        resp = client.post(
            "/api/config/model",
            json={
                "model_provider": "openai",
                "provider_id": provider.id,
                "model_name": "gpt-4o",
            },
        )
        # api_key 验证失败返回 400（Bad Request）
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "API Key" in data["error"] or "未配置" in data["error"]


# ── /api/auth/me / /api/auth/profile ─────────────────────


class TestAuthProfileRoutes:
    """认证资料接口"""

    def test_auth_me_returns_profile_fields(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.display_name = "测试同学"
        user.nickname = "小测"
        user.avatar_path = "avatars/test-avatar.png"
        user.avatar_url = None
        test_db.commit()

        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["username"] == "test"
        assert data["user"]["display_name"] == "测试同学"
        assert data["user"]["nickname"] == "小测"
        assert data["user"]["avatar_url"] == "/uploads/avatars/test-avatar.png"

    def test_auth_me_returns_quota_snapshot(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 5
        user.daily_free_used = 2
        user.daily_free_quota_date = "2000-01-01"
        test_db.commit()

        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        quota = data["user"]["quota"]
        assert quota["daily_free_quota"] == 5
        assert quota["daily_free_used"] == 0
        assert quota["remaining"] == 5
        assert quota["quota_date"] != "2000-01-01"
        assert quota["reset_at"] is not None

    def test_update_profile_success(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.avatar_path = "avatars/original.png"
        user.avatar_url = None
        test_db.commit()

        resp = client.patch(
            "/api/auth/profile",
            json={
                "display_name": "新的显示名",
                "nickname": "新的昵称",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user"]["display_name"] == "新的显示名"
        assert data["user"]["nickname"] == "新的昵称"
        assert data["user"]["avatar_url"] == "/uploads/avatars/original.png"

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        assert user.display_name == "新的显示名"
        assert user.nickname == "新的昵称"
        assert user.avatar_path == "avatars/original.png"

    def test_update_profile_allows_clearing_fields(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.display_name = "原显示名"
        user.nickname = "原昵称"
        user.avatar_path = "avatars/original.png"
        user.avatar_url = None
        test_db.commit()

        resp = client.patch(
            "/api/auth/profile",
            json={
                "display_name": "   ",
                "nickname": "",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["display_name"] is None
        assert data["user"]["nickname"] is None
        assert data["user"]["avatar_url"] == "/uploads/avatars/original.png"

    def test_upload_profile_avatar_success(self, client, test_db, avatar_upload_dir):
        old_avatar = avatar_upload_dir / "avatars" / "old.png"
        old_avatar.parent.mkdir(parents=True, exist_ok=True)
        old_avatar.write_bytes(b"old-image")

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.avatar_path = "avatars/old.png"
        user.avatar_url = None
        test_db.commit()

        resp = client.post(
            "/api/auth/profile/avatar",
            data={"file": (io.BytesIO(b"new-avatar-bytes"), "avatar.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user"]["avatar_url"].startswith("/uploads/avatars/")
        assert data["user"]["avatar_url"].endswith(".png")
        assert not old_avatar.exists()

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        assert user.avatar_path is not None
        assert user.avatar_path.startswith("avatars/")
        saved_avatar = avatar_upload_dir / user.avatar_path
        assert saved_avatar.exists()

    def test_upload_profile_avatar_rejects_invalid_extension(self, client):
        resp = client.post(
            "/api/auth/profile/avatar",
            data={"file": (io.BytesIO(b"plain-text"), "avatar.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "仅支持" in data["error"]

    def test_upload_profile_avatar_requires_file(self, client):
        resp = client.post(
            "/api/auth/profile/avatar",
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "请选择头像图片" in data["error"]

    def test_delete_profile_avatar_success(self, client, test_db, avatar_upload_dir):
        avatar_file = avatar_upload_dir / "avatars" / "delete-me.png"
        avatar_file.parent.mkdir(parents=True, exist_ok=True)
        avatar_file.write_bytes(b"avatar-data")

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.avatar_path = "avatars/delete-me.png"
        user.avatar_url = None
        test_db.commit()

        resp = client.delete("/api/auth/profile/avatar")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user"]["avatar_url"] is None
        assert not avatar_file.exists()

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        assert user.avatar_path is None
