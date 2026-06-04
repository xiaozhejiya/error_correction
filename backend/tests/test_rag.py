"""
RAG 模块单元测试 + 路由集成测试

覆盖：
- core/rag.py 文本构建、余弦相似度、索引/检索
- /api/error-bank/find 语义搜索（embedding 优先，hash 降级）
- /api/rag/reindex 索引重建
- CRUD 集成：save_questions_to_db 自动索引、delete_question 自动清理

使用 SQLite 内存数据库 + mock embedding API，不依赖外部服务。
"""

import json
import os
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from tests.conftest import make_question
from db.models import Base, User, Project, Question, RagDocumentChunk, UploadBatch, QuestionTagMapping, KnowledgeTag
from db import crud


# ═══════════════════════════════════════════════════════════
# Mock Embedding 辅助
# ═══════════════════════════════════════════════════════════

def _fake_embed_texts(texts, batch_size=100):
    """返回确定性的伪向量（基于文本哈希），用于测试"""
    results = []
    for text in texts:
        if text is None:
            results.append(None)
        else:
            seed = hash(text) % 10000
            vec = [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]
            norm = sum(x * x for x in vec) ** 0.5
            vec = [x / norm for x in vec] if norm > 0 else [0.0] * 8
            results.append(vec)
    return results


def _ensure_user(db, user_id=1, project_id=1):
    """确保测试用户和默认项目存在"""
    if not db.query(User).filter_by(id=user_id).first():
        db.add(User(id=user_id, username="test", email=f"test{user_id}@test.com", password_hash="x"))
        db.flush()
    if not db.query(Project).filter_by(id=project_id).first():
        db.add(Project(id=project_id, user_id=user_id, name="默认错题库", project_type="question"))
        db.flush()


# ═══════════════════════════════════════════════════════════
# core/rag.py 单元测试
# ═══════════════════════════════════════════════════════════


class TestExtractTextFromBlocks:
    """_extract_text_from_blocks 测试"""

    def test_normal_blocks(self):
        from core.rag import _extract_text_from_blocks
        blocks = json.dumps([
            {"block_type": "text", "content": "求函数 f(x) 的导数"},
            {"block_type": "text", "content": "其中 x > 0"},
        ])
        result = _extract_text_from_blocks(blocks)
        assert "求函数" in result
        assert "其中 x > 0" in result

    def test_empty_content(self):
        from core.rag import _extract_text_from_blocks
        assert _extract_text_from_blocks("") == ""
        assert _extract_text_from_blocks(None) == ""

    def test_image_blocks_included(self):
        """RAG 场景下图片路径也作为上下文保留"""
        from core.rag import _extract_text_from_blocks
        blocks = json.dumps([
            {"block_type": "text", "content": "题目文本"},
            {"block_type": "image", "content": "/images/xxx.jpg"},
        ])
        result = _extract_text_from_blocks(blocks)
        assert "题目文本" in result
        assert "/images/xxx.jpg" in result

    def test_invalid_json(self):
        from core.rag import _extract_text_from_blocks
        assert _extract_text_from_blocks("not-json") == ""


class TestExtractOptionsText:
    """_extract_options_text 测试"""

    def test_normal_options(self):
        from core.rag import _extract_options_text
        options = json.dumps([
            {"label": "A", "content": "选项一"},
            {"label": "B", "content": "选项二"},
        ])
        result = _extract_options_text(options)
        assert "A" in result
        assert "选项一" in result

    def test_empty_options(self):
        from core.rag import _extract_options_text
        assert _extract_options_text("") == ""
        assert _extract_options_text(None) == ""
        assert _extract_options_text("[]") == ""


class TestBuildQuestionChunks:
    """build_question_chunks 测试"""

    def test_basic_chunk(self, db):
        from core.rag import build_question_chunks
        _ensure_user(db)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject="数学")
        db.add(batch)
        db.flush()
        q = Question(
            user_id=1, batch_id=batch.id,
            content_hash="abc123",
            question_type="选择题",
            content_json=json.dumps([{"block_type": "text", "content": "求导数"}]),
            answer="f'(x) = 2x",
        )
        db.add(q)
        db.flush()

        chunks = build_question_chunks(q)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert "求导数" in chunk["content"]
        assert "数学" in chunk["content"]
        assert "选择题" in chunk["content"]
        assert "f'(x) = 2x" in chunk["content"]
        assert chunk["content_hash"] == "abc123"
        assert chunk["metadata"]["subject"] == "数学"

    def test_with_tags(self, db):
        from core.rag import build_question_chunks
        _ensure_user(db)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject="物理")
        db.add(batch)
        db.flush()
        q = Question(
            user_id=1, batch_id=batch.id,
            content_hash="def456",
            question_type="填空题",
            content_json=json.dumps([{"block_type": "text", "content": "牛顿第二定律"}]),
        )
        db.add(q)
        db.flush()

        tag = KnowledgeTag(tag_name="力学", subject="物理")
        db.add(tag)
        db.flush()
        db.add(QuestionTagMapping(question_id=q.id, tag_id=tag.id))
        db.flush()

        db.refresh(q)
        chunks = build_question_chunks(q)
        assert "力学" in chunks[0]["content"]
        assert "力学" in chunks[0]["metadata"]["tags"]


class TestCosineSimilarity:
    """cosine_similarity 测试"""

    def test_identical_vectors(self):
        from core.rag import cosine_similarity
        v = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        from core.rag import cosine_similarity
        assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9

    def test_opposite_vectors(self):
        from core.rag import cosine_similarity
        assert abs(cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 1e-9

    def test_zero_vector(self):
        from core.rag import cosine_similarity
        assert cosine_similarity([0, 0], [1, 2]) == 0.0

    def test_similar_vectors_high_score(self):
        from core.rag import cosine_similarity
        a = [1.0, 1.0, 0.0]
        b = [1.0, 0.9, 0.1]
        assert cosine_similarity(a, b) > 0.9


# ═══════════════════════════════════════════════════════════
# 索引操作测试（mock embedding API）
# ═══════════════════════════════════════════════════════════


class TestIndexQuestion:
    """index_question 测试"""

    def _make_db_question(self, db, qid=1, text="测试题目", subject="数学"):
        _ensure_user(db)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject=subject, project_id=1)
        db.add(batch)
        db.flush()
        q = Question(
            id=qid, user_id=1, project_id=1, batch_id=batch.id,
            content_hash=f"hash_{qid}",
            question_type="选择题",
            content_json=json.dumps([{"block_type": "text", "content": text}]),
            answer="答案",
        )
        db.add(q)
        db.commit()
        return q

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_index_new_question(self, mock_embed, db):
        from core.rag import index_question
        self._make_db_question(db, qid=1)

        result = index_question(db, 1)
        assert result is True

        chunk = db.query(RagDocumentChunk).filter_by(source_id=1).first()
        assert chunk is not None
        assert chunk.source_type == "question"
        assert "测试题目" in chunk.content
        assert chunk.vector_json is not None

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_index_skips_unchanged(self, mock_embed, db):
        from core.rag import index_question
        self._make_db_question(db, qid=1)

        index_question(db, 1)
        call_count = mock_embed.call_count

        index_question(db, 1)
        assert mock_embed.call_count == call_count

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_index_updates_on_content_change(self, mock_embed, db):
        from core.rag import index_question
        self._make_db_question(db, qid=1)

        index_question(db, 1)

        q = db.query(Question).get(1)
        q.content_json = json.dumps([{"block_type": "text", "content": "更新后的题目"}])
        q.content_hash = "new_hash"
        db.commit()

        index_question(db, 1)
        chunk = db.query(RagDocumentChunk).filter_by(source_id=1).first()
        assert "更新后的题目" in chunk.content
        assert chunk.content_hash == "new_hash"

    def test_index_nonexistent_question(self, db):
        from core.rag import index_question
        assert index_question(db, 99999) is False


class TestDeleteQuestionChunks:
    """delete_question_chunks 测试"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_delete_chunks(self, mock_embed, db):
        from core.rag import index_question, delete_question_chunks

        _ensure_user(db)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject="数学", project_id=1)
        db.add(batch)
        db.flush()
        q = Question(
            id=1, user_id=1, project_id=1, batch_id=batch.id,
            content_hash="hash1",
            content_json=json.dumps([{"block_type": "text", "content": "题目"}]),
        )
        db.add(q)
        db.commit()

        index_question(db, 1)
        assert db.query(RagDocumentChunk).filter_by(source_id=1).count() == 1

        count = delete_question_chunks(db, 1)
        assert count == 1
        assert db.query(RagDocumentChunk).filter_by(source_id=1).count() == 0


# ═══════════════════════════════════════════════════════════
# 语义检索测试
# ═══════════════════════════════════════════════════════════


class TestRetrieveContext:
    """retrieve_context 测试"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_basic_retrieve(self, mock_embed, db):
        from core.rag import index_question, retrieve_context

        _ensure_user(db)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject="数学", project_id=1)
        db.add(batch)
        db.flush()
        for i in range(1, 3):
            q = Question(
                id=i, user_id=1, project_id=1, batch_id=batch.id,
                content_hash=f"hash_{i}",
                question_type="选择题",
                content_json=json.dumps([{"block_type": "text", "content": f"题目{i}内容"}]),
            )
            db.add(q)
        db.commit()

        index_question(db, 1)
        index_question(db, 2)

        results = retrieve_context(db, "题目1", user_id=1)
        assert len(results) > 0
        assert all("score" in r for r in results)

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_retrieve_with_project_filter(self, mock_embed, db):
        from core.rag import index_question, retrieve_context

        _ensure_user(db)
        _ensure_user(db, project_id=2)
        batch = UploadBatch(user_id=1, original_filename="test.pdf", subject="数学", project_id=1)
        db.add(batch)
        db.flush()

        q1 = Question(
            id=1, user_id=1, project_id=1, batch_id=batch.id,
            content_hash="h1",
            content_json=json.dumps([{"block_type": "text", "content": "项目1题目"}]),
        )
        q2 = Question(
            id=2, user_id=1, project_id=2, batch_id=batch.id,
            content_hash="h2",
            content_json=json.dumps([{"block_type": "text", "content": "项目2题目"}]),
        )
        db.add_all([q1, q2])
        db.commit()

        index_question(db, 1)
        index_question(db, 2)

        results = retrieve_context(db, "题目", user_id=1, project_id=1)
        assert all(r["source_id"] == 1 for r in results)

    @patch("core.rag.embed_texts", return_value=[None])
    def test_retrieve_no_embedding(self, mock_embed, db):
        from core.rag import retrieve_context
        assert retrieve_context(db, "查询", user_id=1) == []

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_retrieve_empty_db(self, mock_embed, db):
        from core.rag import retrieve_context
        assert retrieve_context(db, "查询", user_id=1) == []

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_retrieve_without_user_filter_for_admin(self, mock_embed, db):
        from core.rag import index_question, retrieve_context

        _ensure_user(db, user_id=1, project_id=1)
        _ensure_user(db, user_id=2, project_id=2)

        batch1 = UploadBatch(user_id=1, original_filename="a.pdf", subject="数学", project_id=1)
        batch2 = UploadBatch(user_id=2, original_filename="b.pdf", subject="物理", project_id=2)
        db.add_all([batch1, batch2])
        db.flush()

        db.add_all(
            [
                Question(
                    id=1, user_id=1, project_id=1, batch_id=batch1.id,
                    content_hash="admin_h1",
                    content_json=json.dumps([{"block_type": "text", "content": "函数题目"}]),
                ),
                Question(
                    id=2, user_id=2, project_id=2, batch_id=batch2.id,
                    content_hash="admin_h2",
                    content_json=json.dumps([{"block_type": "text", "content": "力学题目"}]),
                ),
            ]
        )
        db.commit()

        index_question(db, 1)
        index_question(db, 2)

        results = retrieve_context(db, "题目", user_id=None, top_k=10)
        source_ids = {item["source_id"] for item in results}
        assert {1, 2}.issubset(source_ids)


# ═══════════════════════════════════════════════════════════
# CRUD 集成测试
# ═══════════════════════════════════════════════════════════


class TestCrudRagIntegration:
    """测试 CRUD 操作与 RAG 索引的集成"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_save_questions_auto_indexes(self, mock_embed, db):
        """save_questions_to_db 成功后应自动建立 RAG 索引"""
        _ensure_user(db)
        batch_info = {"original_filename": "test.pdf", "subject": "数学"}
        questions = [make_question("q1", text="二次函数求导")]

        crud.save_questions_to_db(db, questions, batch_info, user_id=1, project_id=1)

        chunk = db.query(RagDocumentChunk).filter_by(source_type="question").first()
        assert chunk is not None
        assert "二次函数求导" in chunk.content

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_delete_question_cleans_chunks(self, mock_embed, db):
        """delete_question 应删除关联的 RAG chunk"""
        _ensure_user(db)
        batch_info = {"original_filename": "test.pdf", "subject": "数学"}
        questions = [make_question("q1", text="要删除的题")]
        crud.save_questions_to_db(db, questions, batch_info, user_id=1, project_id=1)

        q = db.query(Question).first()
        assert db.query(RagDocumentChunk).filter_by(source_id=q.id).count() == 1

        crud.delete_question(db, q.id, user_id=1)
        assert db.query(RagDocumentChunk).filter_by(source_id=q.id).count() == 0


# ═══════════════════════════════════════════════════════════
# 路由集成测试
# ═══════════════════════════════════════════════════════════

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
    user = User(
        id=TEST_USER_ID, username="test", email="test@test.com", password_hash="x"
    )
    session.add(user)
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    """Flask test client，用内存数据库替换 SessionLocal"""
    from web_app import app

    class FakeSessionLocal:
        def __call__(self):
            return self
        def __enter__(self):
            return test_db
        def __exit__(self, *args):
            pass

    fake = FakeSessionLocal()
    app.config["TESTING"] = True

    with patch("web_app.SessionLocal", fake), \
         patch("routes.questions.SessionLocal", fake), \
         patch("routes.chat.SessionLocal", fake), \
         patch("routes.settings.SessionLocal", fake), \
         patch("routes.stats.SessionLocal", fake), \
         patch("routes.upload.SessionLocal", fake), \
         patch("routes.auth.SessionLocal", fake):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = TEST_USER_ID
                sess["username"] = "test"
                sess["session_version"] = 0
            yield c


def _seed_question(db, qid=1, text="测试题目", subject="数学", project_id=1):
    """直接在 DB 中创建一条题目"""
    if not db.query(Project).filter_by(id=project_id).first():
        db.add(Project(id=project_id, user_id=TEST_USER_ID, name=f"项目{project_id}", project_type="question"))
        db.flush()
    batch = UploadBatch(user_id=TEST_USER_ID, original_filename="test.pdf", subject=subject, project_id=project_id)
    db.add(batch)
    db.flush()
    q = Question(
        id=qid, user_id=TEST_USER_ID, project_id=project_id, batch_id=batch.id,
        content_hash=f"route_hash_{qid}",
        question_type="选择题",
        content_json=json.dumps([{"block_type": "text", "content": text}]),
        answer="参考答案",
    )
    db.add(q)
    db.commit()
    return q


class TestErrorBankFindRoute:
    """GET /api/error-bank/find 路由测试"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_embedding_search_returns_results(self, mock_embed, client, test_db):
        _seed_question(test_db, qid=1, text="二次函数顶点式")
        from core.rag import index_question
        index_question(test_db, 1)

        resp = client.get("/api/error-bank/find?q=二次函数")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert len(data["items"]) > 0

    @patch("core.rag.embed_texts", return_value=[None])
    def test_fallback_to_hash_search(self, mock_embed, client, test_db):
        """embedding 不可用时应降级到 hash 搜索"""
        _seed_question(test_db, qid=1, text="二次函数")

        resp = client.get("/api/error-bank/find?q=二次函数")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

    def test_empty_query_returns_error(self, client, test_db):
        resp = client.get("/api/error-bank/find?q=")
        data = resp.get_json()
        assert resp.status_code == 400


class TestRagReindexRoute:
    """POST /api/rag/reindex 路由测试"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_reindex_all_questions(self, mock_embed, client, test_db):
        _seed_question(test_db, qid=1, text="题目一")
        _seed_question(test_db, qid=2, text="题目二", project_id=1)

        resp = client.post("/api/rag/reindex")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["indexed"] >= 2

    def test_reindex_empty(self, client, test_db):
        resp = client.post("/api/rag/reindex")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["total"] == 0


class TestQuestionUpdateReindex:
    """测试题目更新后自动重建 RAG 索引"""

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_edit_question_reindexes(self, mock_embed, client, test_db):
        _seed_question(test_db, qid=1, text="原始内容")
        from core.rag import index_question
        index_question(test_db, 1)

        resp = client.patch("/api/question/1", json={"content": "更新后的内容"})
        assert resp.status_code == 200

        chunk = test_db.query(RagDocumentChunk).filter_by(source_id=1).first()
        assert "更新后的内容" in chunk.content

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_save_answer_reindexes(self, mock_embed, client, test_db):
        _seed_question(test_db, qid=1, text="测试题目")
        from core.rag import index_question
        index_question(test_db, 1)
        calls_before = mock_embed.call_count

        resp = client.put("/api/question/1/answer", json={"answer": "AI生成的新答案"})
        assert resp.status_code == 200

        assert mock_embed.call_count > calls_before

    @patch("core.rag.embed_texts", side_effect=_fake_embed_texts)
    def test_save_user_answer_reindexes(self, mock_embed, client, test_db):
        _seed_question(test_db, qid=1, text="测试题目")
        from core.rag import index_question
        index_question(test_db, 1)
        calls_before = mock_embed.call_count

        resp = client.patch("/api/question/1/answer", json={"user_answer": "学生最新作答"})
        assert resp.status_code == 200

        chunk = test_db.query(RagDocumentChunk).filter_by(source_id=1).first()
        assert "用户作答：学生最新作答" in chunk.content
        assert mock_embed.call_count > calls_before


POSTGRES_TEST_URL = os.getenv("APP_TEST_POSTGRES_URL") or os.getenv("APP_DATABASE_URL")


@pytest.mark.skipif(
    not POSTGRES_TEST_URL or not POSTGRES_TEST_URL.startswith("postgresql"),
    reason="未提供 PostgreSQL 测试连接串",
)
def test_pgvector_sql_compatibility_smoke():
    from sqlalchemy import text

    engine = create_engine(POSTGRES_TEST_URL, echo=False, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("DROP TABLE IF EXISTS test_vector"))
            conn.execute(text("CREATE TABLE test_vector (id serial PRIMARY KEY, embedding vector(3))"))
            conn.execute(
                text(
                    "INSERT INTO test_vector (embedding) "
                    "VALUES (CAST('[1,2,3]' AS vector)), (CAST('[4,5,6]' AS vector))"
                )
            )
            rows = conn.execute(
                text(
                    "SELECT id FROM test_vector "
                    "ORDER BY embedding <=> CAST('[0,2,1]' AS vector) "
                    "LIMIT 1"
                )
            ).fetchall()
            assert rows
            assert rows[0][0] == 1
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS test_vector"))
        engine.dispose()
