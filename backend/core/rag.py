"""
RAG 核心模块 — 错题库语义检索

提供 embedding 生成、索引构建和向量检索能力。
第一版使用 SQLite 存储向量，纯 Python 计算余弦相似度。
"""

import json
import logging
from typing import Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from db import is_postgresql_backend
from db.models import Question, RagDocumentChunk, QuestionTagMapping, KnowledgeTag, UploadBatch

logger = logging.getLogger(__name__)


def _serialize_vector(vector: Optional[list[float]]) -> Optional[str]:
    if vector is None:
        return None
    return json.dumps(vector, ensure_ascii=False, separators=(",", ":"))


def _write_postgres_vector(db: Session, chunk_id: int, vector: Optional[list[float]]):
    if not is_postgresql_backend(db.bind):
        return
    if vector is None:
        db.execute(
            text(
                "UPDATE rag_document_chunks "
                "SET embedding_vector = NULL "
                "WHERE id = :chunk_id"
            ),
            {"chunk_id": chunk_id},
        )
        return
    db.execute(
        text(
            "UPDATE rag_document_chunks "
            "SET embedding_vector = CAST(:vector AS vector) "
            "WHERE id = :chunk_id"
        ),
        {
            "chunk_id": chunk_id,
            "vector": _serialize_vector(vector),
        },
    )


# ---------------------------------------------------------------------------
# 文本构建
# ---------------------------------------------------------------------------

def _extract_text_from_blocks(content_json: str) -> str:
    """从 content_json 提取纯文本"""
    if not content_json:
        return ""
    try:
        blocks = json.loads(content_json) if isinstance(content_json, str) else content_json
    except (json.JSONDecodeError, TypeError):
        return ""
    parts = []
    for block in blocks:
        if isinstance(block, dict):
            text = block.get("content", "").strip()
            if text:
                parts.append(text)
        elif isinstance(block, str):
            parts.append(block.strip())
    return "\n".join(parts)


def _extract_options_text(options_json: str) -> str:
    """从 options_json 提取选项文本"""
    if not options_json:
        return ""
    try:
        options = json.loads(options_json) if isinstance(options_json, str) else options_json
    except (json.JSONDecodeError, TypeError):
        return ""
    if not options:
        return ""
    parts = []
    for opt in options:
        if isinstance(opt, dict):
            label = opt.get("label", "")
            content = opt.get("content", "")
            if label or content:
                parts.append(f"{label}. {content}" if label else content)
        elif isinstance(opt, str):
            parts.append(opt)
    return "\n".join(parts)


def build_question_chunks(question: Question) -> list[dict]:
    """将 Question 转换为可索引的文本块列表

    Args:
        question: Question ORM 对象（需要已加载 batch 和 tags 关系）

    Returns:
        [{"content": str, "metadata": dict, "content_hash": str}, ...]
    """
    content_text = _extract_text_from_blocks(question.content_json)
    options_text = _extract_options_text(question.options_json)
    answer_text = (question.answer or "").strip()
    user_answer_text = (question.user_answer or "").strip()

    subject = question.batch.subject if question.batch else ""
    question_type = question.question_type or ""
    tags = []
    if question.tags:
        for mapping in question.tags:
            if mapping.tag:
                tags.append(mapping.tag.tag_name)

    parts = []
    if subject:
        parts.append(f"科目：{subject}")
    if question_type:
        parts.append(f"题型：{question_type}")
    if tags:
        parts.append(f"知识点：{'、'.join(tags)}")
    if content_text:
        parts.append(f"题干：{content_text}")
    if options_text:
        parts.append(f"选项：{options_text}")
    if answer_text:
        parts.append(f"答案：{answer_text}")
    if user_answer_text:
        parts.append(f"用户作答：{user_answer_text}")

    chunk_content = "\n".join(parts)

    if len(chunk_content) > 8000:
        chunk_content = chunk_content[:8000]

    metadata = {
        "subject": subject,
        "question_type": question_type,
        "tags": tags,
    }

    return [{
        "content": chunk_content,
        "metadata": metadata,
        "content_hash": question.content_hash or "",
    }]


# ---------------------------------------------------------------------------
# Embedding 生成
# ---------------------------------------------------------------------------

def _get_embedding_client():
    """获取 OpenAI 兼容的 embedding 客户端

    优先使用专门的 RAG Embedding 配置，若未配置则尝试复用 OpenAI provider。
    """
    from core.config import settings

    # 1. 优先尝试独立配置的 RAG Embedding 凭据
    api_key = settings.rag_embedding_api_key
    base_url = settings.rag_embedding_base_url

    # 2. 如果没有独立配置，尝试回退到默认的 OpenAI provider
    if not api_key:
        try:
            provider = settings.get_provider("openai")
            if provider.configured:
                api_key = provider.api_key
                # 仅在未显式指定时复用 provider 的 base_url
                if not base_url:
                    base_url = provider.base_url
        except (ValueError, KeyError):
            pass

    if not api_key:
        return None, None

    try:
        from openai import OpenAI
        import httpx

        kwargs = {"api_key": api_key, "timeout": 30}
        if base_url:
            # 兼容性处理：如果 base_url 指向 DeepSeek，则自动置空（DeepSeek 无 embedding 接口）
            # 除非用户显式在 APP_RAG_EMBEDDING_BASE_URL 中指定了它
            if "deepseek.com" in base_url.lower() and not settings.rag_embedding_base_url:
                logger.warning("检测到 OpenAI Base URL 指向 DeepSeek，已自动跳过其 Embedding 调用")
                return None, None
            kwargs["base_url"] = base_url

        if settings.trust_env:
            kwargs["http_client"] = httpx.Client(trust_env=True)

        client = OpenAI(**kwargs)
        return client, settings.rag_embedding_model
    except Exception as e:
        logger.warning("创建 embedding 客户端失败: %s", e)
        return None, None


def embed_texts(texts: list[str], batch_size: int = 100) -> list[Optional[list[float]]]:
    """批量生成 embedding 向量

    Args:
        texts: 文本列表
        batch_size: 每批处理数量（embedding API 通常限制 100）

    Returns:
        与 texts 等长的列表，每个元素是浮点数列表或 None（失败时）
    """
    if not texts:
        return []

    client, model = _get_embedding_client()
    if client is None:
        logger.warning("embedding 客户端未配置，跳过向量生成")
        return [None] * len(texts)

    results: list[Optional[list[float]]] = [None] * len(texts)

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        try:
            response = client.embeddings.create(model=model, input=batch)
            for i, item in enumerate(response.data):
                results[start + i] = item.embedding
        except Exception as e:
            logger.error("embedding API 调用失败 (batch %d-%d): %s", start, start + len(batch), e)

    return results


# ---------------------------------------------------------------------------
# 余弦相似度
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# 索引操作
# ---------------------------------------------------------------------------

def index_question(db: Session, question_id: int) -> bool:
    """为单道错题建立或刷新 RAG 索引

    Args:
        db: 数据库会话
        question_id: 题目 ID

    Returns:
        True 如果成功索引（或已是最新），False 如果失败
    """
    from sqlalchemy.orm import joinedload

    question = (
        db.query(Question)
        .options(
            joinedload(Question.batch),
            joinedload(Question.tags).joinedload(QuestionTagMapping.tag),
        )
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        return False

    chunks = build_question_chunks(question)
    if not chunks:
        return False

    chunk_data = chunks[0]

    existing = (
        db.query(RagDocumentChunk)
        .filter(
            RagDocumentChunk.source_type == "question",
            RagDocumentChunk.source_id == question_id,
            RagDocumentChunk.chunk_index == 0,
        )
        .first()
    )

    # 检查是否已有相同内容的索引
    has_vector = False
    if existing:
        # 检查 PostgreSQL 向量列是否真的有值
        if is_postgresql_backend(db.bind):
            res = db.execute(
                text("SELECT 1 FROM rag_document_chunks WHERE id = :id AND embedding_vector IS NOT NULL"),
                {"id": existing.id}
            ).first()
            has_vector = bool(res)
        else:
            has_vector = bool(existing.vector_json)

    if existing and has_vector and existing.content_hash == chunk_data["content_hash"] and existing.content == chunk_data["content"]:
        return True

    vectors = embed_texts([chunk_data["content"]])
    vector = vectors[0] if vectors else None

    from core.config import settings

    vector_json = _serialize_vector(vector)

    try:
        with db.begin_nested():
            if existing:
                existing.content = chunk_data["content"]
                existing.metadata_json = json.dumps(chunk_data["metadata"], ensure_ascii=False)
                existing.content_hash = chunk_data["content_hash"]
                existing.embedding_model = settings.rag_embedding_model if vector else None
                existing.vector_json = vector_json
                target_chunk = existing
            else:
                target_chunk = RagDocumentChunk(
                    user_id=question.user_id,
                    project_id=question.project_id,
                    source_type="question",
                    source_id=question_id,
                    chunk_index=0,
                    content=chunk_data["content"],
                    metadata_json=json.dumps(chunk_data["metadata"], ensure_ascii=False),
                    content_hash=chunk_data["content_hash"],
                    embedding_model=settings.rag_embedding_model if vector else None,
                    vector_json=vector_json,
                )
                db.add(target_chunk)

            db.flush()
            _write_postgres_vector(db, target_chunk.id, vector)
        return True
    except Exception as e:
        logger.error("索引题目 %d 失败: %s", question_id, e)
        return False


def delete_question_chunks(db: Session, question_id: int) -> int:
    """删除错题关联的所有 RAG chunk"""
    return (
        db.query(RagDocumentChunk)
        .filter(
            RagDocumentChunk.source_type == "question",
            RagDocumentChunk.source_id == question_id,
        )
        .delete(synchronize_session=False)
    )


# ---------------------------------------------------------------------------
# 语义检索
# ---------------------------------------------------------------------------

def retrieve_context(
    db: Session,
    query: str,
    user_id: Optional[int],
    project_id: Optional[int] = None,
    subject: Optional[str] = None,
    question_type: Optional[str] = None,
    knowledge_tag: Optional[str] = None,
    top_k: int = 6,
) -> list[dict]:
    """语义检索错题上下文"""
    vectors = embed_texts([query])
    query_vector = vectors[0] if vectors else None

    if query_vector is None:
        logger.warning("查询 embedding 生成失败，无法执行语义检索")
        return []

    allowed_ids = None
    if subject or question_type or knowledge_tag:
        question_query = db.query(Question.id).filter(Question.user_id == user_id)
        if user_id is None:
            question_query = db.query(Question.id)
        if project_id is not None:
            question_query = question_query.filter(Question.project_id == project_id)
        if subject:
            question_query = question_query.join(UploadBatch).filter(UploadBatch.subject == subject)
        if question_type:
            question_query = question_query.filter(Question.question_type == question_type)
        if knowledge_tag:
            from db.crud.tags import _parse_tag_list
            tag_list = _parse_tag_list(knowledge_tag)
            if tag_list:
                question_query = (
                    question_query
                    .join(QuestionTagMapping)
                    .join(KnowledgeTag)
                    .filter(KnowledgeTag.tag_name.in_(tag_list))
                )
        allowed_ids = [row[0] for row in question_query.distinct().all()]
        if not allowed_ids:
            return []

    if is_postgresql_backend(db.bind):
        return _retrieve_context_postgresql(
            db,
            query_vector=query_vector,
            user_id=user_id,
            project_id=project_id,
            allowed_ids=allowed_ids,
            top_k=top_k,
        )

    q = (
        db.query(RagDocumentChunk)
        .filter(
            RagDocumentChunk.source_type == "question",
            RagDocumentChunk.vector_json.isnot(None),
        )
    )
    if user_id is not None:
        q = q.filter(RagDocumentChunk.user_id == user_id)
    if project_id is not None:
        q = q.filter(RagDocumentChunk.project_id == project_id)

    chunks = q.all()
    if allowed_ids is not None:
        allowed_set = set(allowed_ids)
        chunks = [c for c in chunks if c.source_id in allowed_set]
    if not chunks:
        return []

    scored = []
    for chunk in chunks:
        try:
            chunk_vector = json.loads(chunk.vector_json)
            score = cosine_similarity(query_vector, chunk_vector)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_results = scored[:top_k]

    results = []
    for chunk, score in top_results:
        metadata = {}
        if chunk.metadata_json:
            try:
                metadata = json.loads(chunk.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass
        results.append({
            "chunk_id": chunk.id,
            "source_id": chunk.source_id,
            "content": chunk.content,
            "metadata": metadata,
            "score": round(score, 4),
        })

    return results


def _retrieve_context_postgresql(
    db: Session,
    *,
    query_vector: list[float],
    user_id: Optional[int],
    project_id: Optional[int],
    allowed_ids: Optional[list[int]],
    top_k: int,
) -> list[dict]:
    where_clauses = [
        "source_type = 'question'",
        "embedding_vector IS NOT NULL",
    ]
    params = {
        "query_vector": _serialize_vector(query_vector),
        "limit": top_k,
    }

    if user_id is not None:
        where_clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    if project_id is not None:
        where_clauses.append("project_id = :project_id")
        params["project_id"] = project_id
    if allowed_ids is not None:
        where_clauses.append("source_id IN :allowed_ids")
        params["allowed_ids"] = allowed_ids

    sql = text(
        "SELECT id, source_id, content, metadata_json, "
        "1 - (embedding_vector <=> CAST(:query_vector AS vector)) AS score "
        "FROM rag_document_chunks "
        f"WHERE {' AND '.join(where_clauses)} "
        "ORDER BY embedding_vector <=> CAST(:query_vector AS vector) "
        "LIMIT :limit"
    )
    if allowed_ids is not None:
        sql = sql.bindparams(bindparam("allowed_ids", expanding=True))

    rows = db.execute(sql, params).mappings().all()
    results = []
    for row in rows:
        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        results.append(
            {
                "chunk_id": row["id"],
                "source_id": row["source_id"],
                "content": row["content"],
                "metadata": metadata,
                "score": round(float(row["score"] or 0.0), 4),
            }
        )
    return results
