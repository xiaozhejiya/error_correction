"""
Flask 路由集成测试

使用 Flask test client + SQLite 内存数据库，验证 API 路由的请求/响应。
不依赖外部服务。

覆盖路由：
- GET  /api/health
- GET  /api/status
- GET  /api/history
- GET  /api/search
- GET  /api/stats
- DELETE /api/question/<id>
"""

import io
import json
import os
import sys
import types
import uuid
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base, User, ProviderConfig, SystemProviderConfig, Question, QuotaUsageEvent
from db import crud

# 测试用户 ID，与 client fixture 中的 session['user_id'] 一致
TEST_USER_ID = 1


def _seed_split_run(db, tmp_path, *, user_id, run_id, question_text):
    """Create an isolated succeeded split run with its own questions.json."""
    run_dir = tmp_path / f"user-{user_id}" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    questions = [
        {
            "uid": "0",
            "question_id": "1",
            "question_type": "选择题",
            "content_blocks": [{"block_type": "text", "content": question_text}],
            "has_formula": False,
            "has_image": False,
        }
    ]
    (run_dir / "questions.json").write_text(
        json.dumps(questions, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "split_metadata.json").write_text(
        json.dumps({"subject": "数学"}, ensure_ascii=False), encoding="utf-8"
    )
    crud.create_workflow_run(
        db,
        user_id=user_id,
        run_type="split",
        status="succeeded",
        public_id=run_id,
        subject="数学",
        model_provider="openai",
        file_names=[f"user-{user_id}.pdf"],
        result_dir=str(run_dir),
        question_count=1,
    )
    return questions


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
        patch("routes.notes.SessionLocal", fake),
        patch("routes.device.SessionLocal", fake),
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


class TestHealthRoute:
    """GET /api/health"""

    def test_returns_success_without_login(self, client):
        with client.session_transaction() as sess:
            sess.clear()

        resp = client.get("/api/health")

        assert resp.status_code == 200
        assert resp.get_json() == {"success": True, "status": "ok"}


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


class TestModelOptionsRoute:
    """GET /api/models/options"""

    def test_returns_system_and_personal_options(self, client, test_db):
        system_provider = SystemProviderConfig(
            id=str(uuid.uuid4()),
            category="openai",
            name="平台 DeepSeek",
            is_active=True,
            api_key="sk-managed",
            base_url="https://example.com",
            model_name="deepseek-chat,deepseek-reasoner",
        )
        personal_provider = ProviderConfig(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            category="openai",
            name="我的 OpenAI",
            is_active=True,
            api_key="sk-personal",
            base_url="https://personal.example.com",
            model_name="gpt-4o-mini",
        )
        test_db.add(system_provider)
        test_db.add(personal_provider)
        test_db.commit()

        resp = client.get("/api/models/options")
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["success"] is True
        assert data["groups"] == [
            {"key": "system", "label": "平台托管"},
            {"key": "personal", "label": "个人配置"},
        ]
        assert data["default_option_id"] == (
            f"personal:openai:{personal_provider.id}:gpt-4o-mini"
        )

        options = data["options"]
        assert any(
            item["source"] == "system"
            and item["provider_id"] == system_provider.id
            and item["model_name"] == "deepseek-chat"
            for item in options
        )
        assert any(
            item["source"] == "personal"
            and item["provider_id"] == personal_provider.id
            and item["model_name"] == "gpt-4o-mini"
            for item in options
        )


class TestDeviceCaptureRoutes:
    """POST /api/device/bind and /api/device/capture"""

    def test_capture_requires_bound_device(self, client):
        resp = client.post(
            "/api/device/capture",
            data={
                "device_id": "unbound-device",
                "image": (io.BytesIO(b"jpeg-bytes"), "capture.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 404
        assert resp.get_json()["success"] is False

    def test_bound_device_capture_enters_workbench_session(
        self, client, test_db, tmp_path, monkeypatch
    ):
        from core.state import clear_user_session, get_user_session
        from db.models import DeviceCapture

        clear_user_session(TEST_USER_ID)
        monkeypatch.setattr("routes.device.settings.upload_dir", tmp_path)

        bind_resp = client.post("/api/device/bind", json={})
        assert bind_resp.status_code == 200
        bind_data = bind_resp.get_json()
        assert bind_data["success"] is True
        device_uuid = bind_data["device_uuid"]
        assert bind_data["qr_payload"].endswith(device_uuid)

        capture_resp = client.post(
            "/api/device/capture",
            data={
                "device_uuid": device_uuid,
                "image": (
                    io.BytesIO(b"\xff\xd8fake-jpeg\xff\xd9"),
                    "capture.jpg",
                ),
            },
            content_type="multipart/form-data",
        )
        assert capture_resp.status_code == 201
        data = capture_resp.get_json()
        assert data["success"] is True
        assert data["file_key"]

        us = get_user_session(TEST_USER_ID)
        saved = us["session_files"][data["file_key"]]
        assert saved["filename"] == "capture.jpg"
        assert os.path.exists(saved["filepath"])

        capture = test_db.query(DeviceCapture).first()
        assert capture is not None
        assert capture.device_uuid == device_uuid
        assert capture.user_id == TEST_USER_ID

        list_resp = client.get(f"/api/device/images?device_uuid={device_uuid}")
        assert list_resp.status_code == 200
        images = list_resp.get_json()["images"]
        assert len(images) == 1
        assert images[0]["file_key"] == data["file_key"]


class TestSplitQuotaRules:
    """POST /api/split 的额度扣减规则"""

    def test_erase_and_split_consume_twelve_quota_for_two_multi_page_pdfs(
        self, client, test_db, tmp_path, monkeypatch
    ):
        from core.state import clear_user_session, get_user_session

        clear_user_session(TEST_USER_ID)
        pdf_one = tmp_path / "sample-2.pdf"
        pdf_two = tmp_path / "sample-4.pdf"
        pdf_one.write_bytes(b"%PDF-1.4 fake pdf one")
        pdf_two.write_bytes(b"%PDF-1.4 fake pdf two")

        us = get_user_session(TEST_USER_ID)
        us["session_files"]["file-1"] = {
            "filename": "sample-2.pdf",
            "filepath": str(pdf_one),
        }
        us["session_files"]["file-2"] = {
            "filename": "sample-4.pdf",
            "filepath": str(pdf_two),
        }
        us["session_file_order"] = ["file-1", "file-2"]

        rendered_paths = []
        for index in range(6):
            page_path = tmp_path / f"page-{index + 1}.png"
            page_path.write_bytes(b"fake image")
            rendered_paths.append(
                {
                    "input_path": str(page_path),
                    "preview_path": str(page_path),
                }
            )

        monkeypatch.setattr(
            "routes.upload._expand_erase_sources",
            lambda file_paths: rendered_paths,
        )
        monkeypatch.setattr("routes.upload.settings.model_path", tmp_path)

        class DummyInferenceEngine:
            def run(self, image_bytes):
                return Image.new("RGB", (8, 8), color="white")

        monkeypatch.setitem(
            sys.modules,
            "text_eraser_model.inference",
            types.SimpleNamespace(InferenceEngine=DummyInferenceEngine),
        )

        erase_resp = client.post("/api/erase")
        assert erase_resp.status_code == 200
        erase_data = erase_resp.get_json()
        assert erase_data["success"] is True
        assert len(erase_data["images"]) == 6

        cache_path = tmp_path / f"ocr_cache_{TEST_USER_ID}.json"
        cache_path.write_text(json.dumps([{}, {}, {}, {}, {}, {}]), encoding="utf-8")
        monkeypatch.setattr("routes.upload.settings.results_dir", tmp_path)

        class DummyRun:
            public_id = "run-test"
            result_dir = str(tmp_path / "run-test")

        monkeypatch.setattr(
            "routes.upload.resolve_llm_selection",
            lambda *args, **kwargs: {
                "source": "system",
                "model_name": "deepseek-chat",
            },
        )
        monkeypatch.setattr("routes.upload._read_split_subject", lambda *args, **kwargs: "数学")
        monkeypatch.setattr("routes.upload.run_store.create_split_run", lambda *args, **kwargs: DummyRun())
        monkeypatch.setattr("routes.upload.run_store.mark_succeeded", lambda *args, **kwargs: None)
        monkeypatch.setattr("routes.upload.crud.save_split_record", lambda *args, **kwargs: None)

        invoke_results = iter([
            None,
            {
                "questions": [
                    {
                        "uid": "1",
                        "question_id": "1",
                        "question_type": "选择题",
                        "content_blocks": [{"block_type": "text", "content": "测试题"}],
                        "has_formula": False,
                        "has_image": False,
                    }
                ],
                "warnings": [],
                "ocr_data": [{}, {}, {}, {}, {}, {}],
            },
        ])
        monkeypatch.setattr(
            "routes.upload.workflow_graph.invoke",
            lambda *args, **kwargs: next(invoke_results),
        )

        split_resp = client.post("/api/split", json={"model_provider": "openai"})
        assert split_resp.status_code == 200
        split_data = split_resp.get_json()
        assert split_data["success"] is True

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        test_db.refresh(user)
        assert user.daily_free_used == 12

    def test_split_consumes_one_quota_per_ocr_page(self, client, test_db, tmp_path, monkeypatch):
        from core.state import clear_user_session, get_user_session

        clear_user_session(TEST_USER_ID)
        upload_file = tmp_path / "sample.pdf"
        upload_file.write_bytes(b"%PDF-1.4 fake pdf")

        us = get_user_session(TEST_USER_ID)
        us["session_files"]["file-1"] = {
            "filename": "sample.pdf",
            "filepath": str(upload_file),
        }
        us["session_file_order"] = ["file-1"]

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 100
        user.daily_free_used = 0
        test_db.commit()

        class DummyRun:
            public_id = "run-test-1"
            result_dir = str(tmp_path / "results")

        monkeypatch.setattr(
            "routes.upload.resolve_llm_selection",
            lambda *args, **kwargs: {
                "source": "system",
                "model_name": "deepseek-chat",
            },
        )
        monkeypatch.setattr("routes.upload._read_split_subject", lambda *args, **kwargs: "数学")
        monkeypatch.setattr("routes.upload.run_store.create_split_run", lambda *args, **kwargs: DummyRun())
        monkeypatch.setattr("routes.upload.run_store.mark_succeeded", lambda *args, **kwargs: None)
        monkeypatch.setattr("routes.upload.crud.save_split_record", lambda *args, **kwargs: None)

        invoke_results = iter([
            None,
            {
                "questions": [
                    {
                        "uid": "1",
                        "question_id": "1",
                        "question_type": "选择题",
                        "content_blocks": [{"block_type": "text", "content": "测试题"}],
                        "has_formula": False,
                        "has_image": False,
                    }
                ],
                "warnings": [],
                "ocr_data": [{}, {}, {}],
            },
        ])
        monkeypatch.setattr(
            "routes.upload.workflow_graph.invoke",
            lambda *args, **kwargs: next(invoke_results),
        )

        resp = client.post("/api/split", json={"model_provider": "openai"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

        test_db.refresh(user)
        assert user.daily_free_used == 3

    def test_split_rejects_when_remaining_quota_is_less_than_cached_page_count(self, client, test_db, tmp_path, monkeypatch):
        from core.state import clear_user_session, get_user_session

        clear_user_session(TEST_USER_ID)
        upload_file = tmp_path / "sample.pdf"
        upload_file.write_bytes(b"%PDF-1.4 fake pdf")

        results_dir = tmp_path / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("routes.upload.settings.results_dir", results_dir)

        us = get_user_session(TEST_USER_ID)
        us["session_files"]["file-1"] = {
            "filename": "sample.pdf",
            "filepath": str(upload_file),
        }
        us["session_file_order"] = ["file-1"]

        cache_path = results_dir / f"ocr_cache_{TEST_USER_ID}.json"
        cache_path.write_text(json.dumps([{}, {}, {}]), encoding="utf-8")
        monkeypatch.setattr("routes.upload._ocr_cache_path", lambda user_id: str(cache_path))

        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 100
        user.daily_free_used = 98
        user.daily_free_quota_date = datetime.utcnow().date().isoformat()
        test_db.commit()

        monkeypatch.setattr(
            "routes.upload.resolve_llm_selection",
            lambda *args, **kwargs: {
                "source": "system",
                "model_name": "deepseek-chat",
            },
        )

        resp = client.post("/api/split", json={"model_provider": "openai"})
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["success"] is False
        assert data["code"] == "DAILY_FREE_QUOTA_EXCEEDED"
        assert data["required_amount"] == 3
        assert data["quota"]["remaining"] == 2
        assert "需要 3 个额度" in data["error"]


# ── POST /api/notes/ ─────────────────────────────────────


class TestNotesRoute:
    """POST /api/notes/"""

    @pytest.mark.parametrize("project_id", ["0", "999999"])
    def test_create_note_rejects_unknown_project_before_ai_work(self, client, test_db, monkeypatch, project_id):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        user.daily_free_quota = 5
        user.daily_free_used = 0
        user.daily_free_quota_date = datetime.utcnow().date().isoformat()
        test_db.commit()

        def fail_if_model_selection_runs(*args, **kwargs):
            raise AssertionError("model selection should not run for an invalid note project")

        monkeypatch.setattr("routes.notes.resolve_llm_selection", fail_if_model_selection_runs)

        resp = client.post(
            "/api/notes/",
            data={
                "project_id": project_id,
                "files": (io.BytesIO(b"fake-image"), "note.png"),
            },
            content_type="multipart/form-data",
        )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert data["error"] == "项目不存在"
        test_db.refresh(user)
        assert user.daily_free_used == 0


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


class TestMultiUserWorkflowRunIsolation:
    """Split-run routes must not leak questions across users."""

    def test_get_questions_requires_run_owner(self, client, test_db, tmp_path):
        test_db.add(
            User(id=2, username="other", email="other@test.com", password_hash="x")
        )
        test_db.commit()

        _seed_split_run(
            test_db,
            tmp_path,
            user_id=TEST_USER_ID,
            run_id="user-1-run",
            question_text="current user question",
        )
        _seed_split_run(
            test_db,
            tmp_path,
            user_id=2,
            run_id="user-2-run",
            question_text="other user question",
        )

        own_resp = client.get("/api/questions?run_id=user-1-run")
        assert own_resp.status_code == 200
        own_data = own_resp.get_json()
        assert own_data["run_id"] == "user-1-run"
        assert own_data["questions"][0]["content_blocks"][0]["content"] == (
            "current user question"
        )

        other_resp = client.get("/api/questions?run_id=user-2-run")
        assert other_resp.status_code == 200
        other_data = other_resp.get_json()
        assert other_data["questions"] == []
        assert "run_id" not in other_data

    def test_save_to_db_rejects_other_users_run(self, client, test_db, tmp_path):
        test_db.add(
            User(id=2, username="other", email="other2@test.com", password_hash="x")
        )
        test_db.commit()
        _seed_split_run(
            test_db,
            tmp_path,
            user_id=2,
            run_id="other-owned-run",
            question_text="should not import",
        )

        resp = client.post(
            "/api/save-to-db",
            json={"run_id": "other-owned-run", "selected_ids": ["0"]},
        )
        assert resp.status_code == 400
        assert test_db.query(Question).count() == 0

    def test_save_to_db_imports_current_users_run(self, client, test_db, tmp_path):
        project = crud.create_project(
            test_db,
            "Current user bank",
            user_id=TEST_USER_ID,
        )
        _seed_split_run(
            test_db,
            tmp_path,
            user_id=TEST_USER_ID,
            run_id="own-run-to-import",
            question_text="import me",
        )

        resp = client.post(
            "/api/save-to-db",
            json={
                "run_id": "own-run-to-import",
                "selected_ids": ["0"],
                "project_id": project.id,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["run_id"] == "own-run-to-import"

        saved = test_db.query(Question).all()
        assert len(saved) == 1
        assert saved[0].user_id == TEST_USER_ID
        assert "import me" in saved[0].content_json

    def test_save_to_db_imports_split_record_without_run_id(self, client, test_db):
        project = crud.create_project(test_db, "History Bank", user_id=TEST_USER_ID)
        record = crud.save_split_record(
            test_db,
            subject="数学",
            model_provider="openai",
            file_names=["history.jpg"],
            questions=[
                {
                    "uid": "hist_0",
                    "question_id": "1",
                    "question_type": "选择题",
                    "content_blocks": [{"block_type": "text", "content": "from history"}],
                    "has_formula": False,
                    "has_image": False,
                }
            ],
            user_id=TEST_USER_ID,
        )

        resp = client.post(
            "/api/save-to-db",
            json={
                "split_record_id": record.id,
                "selected_ids": ["hist_0"],
                "project_id": project.id,
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["split_record_id"] == record.id

        saved = test_db.query(Question).all()
        assert len(saved) == 1
        assert saved[0].user_id == TEST_USER_ID
        assert "from history" in saved[0].content_json


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
        assert quota["daily_free_quota"] == 100
        assert quota["daily_free_used"] == 0
        assert quota["remaining"] == 100
        assert quota["quota_date"] != "2000-01-01"
        assert quota["reset_at"] is not None

    def test_auth_me_returns_daily_quota_chart(self, client, test_db):
        user = test_db.query(User).filter(User.id == TEST_USER_ID).first()
        today = datetime.utcnow().date()
        user.daily_free_quota = 100
        user.daily_free_used = 8
        user.daily_free_quota_date = today.isoformat()
        test_db.add_all(
            [
                QuotaUsageEvent(
                    user_id=user.id,
                    action_type="chat",
                    amount=2,
                    summary="AI 对话",
                    quota_date=(today - timedelta(days=2)).isoformat(),
                    created_at=datetime.utcnow() - timedelta(days=2),
                ),
                QuotaUsageEvent(
                    user_id=user.id,
                    action_type="erase",
                    amount=3,
                    summary="擦除笔记",
                    quota_date=(today - timedelta(days=1)).isoformat(),
                    created_at=datetime.utcnow() - timedelta(days=1),
                ),
                QuotaUsageEvent(
                    user_id=user.id,
                    action_type="split",
                    amount=5,
                    summary="分割题目",
                    quota_date=today.isoformat(),
                    created_at=datetime.utcnow(),
                ),
            ]
        )
        test_db.commit()

        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        daily_chart = data["user"]["quota"]["usage_stats"]["daily_chart"]
        assert daily_chart["range_days"] == 14
        assert len(daily_chart["days"]) == 14
        assert daily_chart["actions"][0]["key"] == "chat"
        assert daily_chart["days"][-3]["chat"] == 2
        assert daily_chart["days"][-2]["erase"] == 3
        assert daily_chart["days"][-1]["split"] == 5
        assert daily_chart["days"][-1]["total"] == 5

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
