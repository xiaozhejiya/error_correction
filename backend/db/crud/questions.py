"""题目 CRUD"""

import hashlib
import json
import logging
import re
import math
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session, joinedload, selectinload

from db.models import UploadBatch, Question, QuestionEmbedding, KnowledgeTag, QuestionTagMapping
from db.crud.tags import _parse_tag_list, get_or_create_tag

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "local-hash-v1"
EMBEDDING_DIM = 256
SEMANTIC_EXPANSIONS = {
    "方法": ["工艺", "处理", "方案"],
    "处理方法": ["工艺", "处理效应", "甲工艺", "乙工艺"],
    "两个": ["两种", "甲乙"],
    "谁更好": ["显著提高", "比较", "判断"],
    "更好": ["显著提高", "提高", "比较"],
    "比较": ["判断", "显著", "差异"],
    "分工": ["工艺", "甲工艺", "乙工艺", "处理"],
    "方差": ["样本方差", "统计", "配对试验"],
    "均值": ["样本均值", "平均数"],
}


def _parse_filter_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _get_filters():
    """延迟导入共享过滤函数，避免循环导入"""
    from db.crud import _filter_by_subject, _filter_by_user
    return _filter_by_subject, _filter_by_user


def _safe_json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _content_blocks_text(content_blocks) -> str:
    parts = []
    for block in content_blocks or []:
        if isinstance(block, dict):
            content = block.get("content") or block.get("text") or ""
            if content:
                parts.append(str(content))
    return " ".join(parts)


def _question_search_text(question: Question) -> Dict[str, str]:
    content_blocks = _safe_json_loads(question.content_json, [])
    options = _safe_json_loads(question.options_json, [])
    option_text = ""
    if isinstance(options, list):
        option_text = " ".join(str(item.get("content") if isinstance(item, dict) else item) for item in options)
    elif isinstance(options, dict):
        option_text = " ".join(str(v) for v in options.values())

    tags = []
    for mapping in question.tags or []:
        if mapping.tag:
            tags.append(mapping.tag.tag_name)

    subject = question.batch.subject if question.batch else ""
    body = _content_blocks_text(content_blocks)
    return {
        "body": body,
        "options": option_text,
        "answer": question.answer or "",
        "subject": subject or "",
        "type": question.question_type or "",
        "tags": " ".join(tags),
        "all": " ".join([
            body,
            option_text,
            question.answer or "",
            subject or "",
            question.question_type or "",
            " ".join(tags),
        ]),
    }


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _expand_query_text(text: str) -> str:
    expanded = [str(text or "")]
    for key, values in SEMANTIC_EXPANSIONS.items():
        if key in text:
            expanded.extend(values)
    return " ".join(expanded)


def _search_tokens(text: str) -> List[str]:
    normalized = _normalize_search_text(text)
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized)
    tokens = []
    latin_buffer = []
    han_chars = []
    for word in words:
        if re.fullmatch(r"[\u4e00-\u9fff]", word):
            han_chars.append(word)
            if latin_buffer:
                tokens.extend(latin_buffer)
                latin_buffer = []
        else:
            latin_buffer.append(word)
    tokens.extend(latin_buffer)
    tokens.extend(han_chars)
    tokens.extend("".join(han_chars[i:i + 2]) for i in range(max(0, len(han_chars) - 1)))
    return [token for token in tokens if token]


def _cosine_score(query_tokens: List[str], target_tokens: List[str]) -> float:
    if not query_tokens or not target_tokens:
        return 0.0
    q_counter = Counter(query_tokens)
    t_counter = Counter(target_tokens)
    common = set(q_counter) & set(t_counter)
    dot = sum(q_counter[token] * t_counter[token] for token in common)
    q_norm = math.sqrt(sum(value * value for value in q_counter.values()))
    t_norm = math.sqrt(sum(value * value for value in t_counter.values()))
    if not q_norm or not t_norm:
        return 0.0
    return dot / (q_norm * t_norm)


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Build a deterministic lightweight embedding via feature hashing."""
    tokens = _search_tokens(text)
    vector = [0.0] * dim
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.6 if len(token) >= 2 else 1.0
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


def _vector_cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _question_embedding_text(question: Question) -> str:
    fields = _question_search_text(question)
    return " ".join([
        fields["body"],
        fields["body"],
        fields["tags"],
        fields["tags"],
        fields["subject"],
        fields["type"],
        fields["options"],
        fields["answer"],
    ])


def _embedding_text_hash(text: str) -> str:
    return hashlib.sha256(_normalize_search_text(text).encode("utf-8")).hexdigest()


def ensure_question_embedding(db: Session, question: Question) -> QuestionEmbedding:
    """Create or refresh a cached vector for a question."""
    text = _question_embedding_text(question)
    text_hash = _embedding_text_hash(text)
    embedding = getattr(question, "embedding", None)
    if (
        embedding
        and embedding.model_name == EMBEDDING_MODEL_NAME
        and embedding.text_hash == text_hash
    ):
        return embedding

    vector = _hash_embedding(text)
    if not embedding:
        embedding = QuestionEmbedding(question_id=question.id)
        db.add(embedding)
    embedding.model_name = EMBEDDING_MODEL_NAME
    embedding.text_hash = text_hash
    embedding.vector_json = json.dumps(vector, separators=(",", ":"))
    embedding.updated_at = datetime.utcnow()
    return embedding


def _question_match_score(query: str, question: Question) -> Tuple[float, List[str]]:
    query_text = _normalize_search_text(_expand_query_text(query))
    query_tokens = _search_tokens(query_text)
    fields = _question_search_text(question)
    reasons = []

    field_weights = {
        "body": 0.46,
        "tags": 0.22,
        "subject": 0.10,
        "type": 0.08,
        "answer": 0.08,
        "options": 0.06,
    }
    weighted = 0.0
    for field, weight in field_weights.items():
        field_text = _normalize_search_text(fields[field])
        if not field_text:
            continue
        field_score = _cosine_score(query_tokens, _search_tokens(field_text))
        if query_text and query_text in field_text:
            field_score = max(field_score, 0.95)
        weighted += field_score * weight
        if field_score >= 0.18:
            labels = {
                "body": "题干相似",
                "tags": "知识点匹配",
                "subject": "学科匹配",
                "type": "题型匹配",
                "answer": "答案/解析相似",
                "options": "选项相似",
            }
            reasons.append(labels[field])

    all_text = _normalize_search_text(fields["all"])
    exact_hits = sum(1 for token in set(query_tokens) if len(token) >= 2 and token in all_text)
    score = min(1.0, weighted + min(0.18, exact_hits * 0.035))
    if exact_hits:
        reasons.append("关键词命中")
    return score, list(dict.fromkeys(reasons))[:3]


def find_questions_by_natural_language(
    db: Session,
    query_text: str,
    limit: int = 8,
    user_id=None,
    project_id=None,
) -> List[Dict[str, Any]]:
    """Find likely questions from a natural language description."""
    query = db.query(Question).join(UploadBatch)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    if project_id is not None:
        query = query.filter(Question.project_id == project_id)

    questions = (
        query.options(
            selectinload(Question.batch),
            selectinload(Question.tags).selectinload(QuestionTagMapping.tag),
            selectinload(Question.embedding),
        )
        .order_by(Question.created_at.desc())
        .limit(2000)
        .all()
    )

    expanded_query_text = _expand_query_text(query_text)
    query_vector = _hash_embedding(expanded_query_text)
    matches = []
    for question in questions:
        embedding = ensure_question_embedding(db, question)
        vector_score = _vector_cosine(query_vector, _safe_json_loads(embedding.vector_json, []))
        lexical_score, reasons = _question_match_score(expanded_query_text, question)
        score = min(1.0, vector_score * 0.78 + lexical_score * 0.22)
        if score <= 0:
            continue
        if vector_score >= 0.16:
            reasons = ["向量语义相似", *reasons]
        matches.append({
            "question": question,
            "score": score,
            "reasons": list(dict.fromkeys(reasons))[:3],
        })

    db.commit()
    matches.sort(key=lambda item: (item["score"], item["question"].created_at or datetime.min), reverse=True)
    return matches[:limit]


def compute_content_hash(content_blocks: List[Dict]) -> str:
    """
    基于 content_blocks 计算去重哈希
    使用题目文本内容计算 SHA256
    """
    text_parts = []
    for block in content_blocks:
        if block.get("block_type") == "text":
            text_parts.append(block.get("content", ""))

    text = " ".join(text_parts).strip()
    if not text:
        # 如果没有文本内容，使用整个 content_blocks 的 JSON 作为哈希源
        text = json.dumps(content_blocks, ensure_ascii=False)

    return hashlib.sha256(text.encode()).hexdigest()


def compute_project_content_hash(content_blocks: List[Dict], project_id=None) -> str:
    """Calculate the stored dedupe hash; scoped by project when available."""
    base_hash = compute_content_hash(content_blocks)
    if project_id is None:
        return base_hash
    return hashlib.sha256(f"{project_id}:{base_hash}".encode()).hexdigest()


def question_exists(db, content_hash, user_id=None, project_id=None):
    """检查题目是否已存在（通过内容哈希 + 用户隔离）"""
    hashes = [content_hash]
    if project_id is not None:
        scoped_hash = hashlib.sha256(f"{project_id}:{content_hash}".encode()).hexdigest()
        hashes.append(scoped_hash)
    q = db.query(Question).filter(Question.content_hash.in_(hashes))
    if user_id is not None:
        q = q.filter(Question.user_id == user_id)
    if project_id is not None:
        q = q.filter(Question.project_id == project_id)
    return q.first()


def save_questions_to_db(
    db: Session,
    questions: List[Dict],
    batch_info: Dict[str, Any],
    user_id=None,
    project_id=None,
) -> Dict[str, int]:
    """
    批量入库题目

    Args:
        db: 数据库会话
        questions: 题目列表（字典格式，来自 questions.json）
        batch_info: 批次信息，包含 original_filename, file_path 等

    Returns:
        dict: {"created": 新增数量, "duplicates": 重复数量}
    """
    # 科目由编排智能体识别，不再使用关键词匹配
    subject = batch_info.get("subject") or "未知"
    project_id = project_id or batch_info.get("project_id")

    # 创建批次记录
    batch = UploadBatch(
        user_id=user_id,
        project_id=project_id,
        original_filename=batch_info.get("original_filename", "未知"),
        subject=subject,
        file_path=batch_info.get("file_path", ""),
        upload_time=batch_info.get("upload_time") or datetime.utcnow()
    )
    db.add(batch)
    db.flush()  # 获取 batch.id

    created = 0
    duplicates = 0

    for q in questions:
        content_blocks = q.get("content_blocks", [])
        if not content_blocks:
            continue

        content_hash = compute_content_hash(content_blocks)

        # 检查是否已存在
        if question_exists(db, content_hash, user_id=user_id, project_id=project_id):
            duplicates += 1
            continue

        # 创建题目记录
        question = Question(
            user_id=user_id,
            project_id=project_id,
            batch_id=batch.id,
            content_hash=compute_project_content_hash(content_blocks, project_id),
            question_type=q.get("question_type"),
            content_json=json.dumps(content_blocks, ensure_ascii=False),
            options_json=json.dumps(q.get("options"), ensure_ascii=False) if q.get("options") else None,
            has_formula=q.get("has_formula", False),
            has_image=q.get("has_image", False),
            image_refs_json=json.dumps(q.get("image_refs"), ensure_ascii=False) if q.get("image_refs") else None,
            needs_correction=q.get("needs_correction", False),
            ocr_issues_json=json.dumps(q.get("ocr_issues"), ensure_ascii=False) if q.get("ocr_issues") else None,
            answer=q.get("answer") or None,
            user_answer=q.get("user_answer") or None,
        )
        db.add(question)
        db.flush()

        # 处理知识点标签
        knowledge_tags = q.get("knowledge_tags") or []
        for tag_name in knowledge_tags:
            tag = get_or_create_tag(db, tag_name, subject)
            mapping = QuestionTagMapping(
                question_id=question.id,
                tag_id=tag.id
            )
            db.add(mapping)

        db.flush()
        question.tags = db.query(QuestionTagMapping).filter(
            QuestionTagMapping.question_id == question.id
        ).all()

        # 同时更新本地 Hash 向量和 RAG 语义索引
        ensure_question_embedding(db, question)
        try:
            from core.rag import index_question
            index_question(db, question.id)
        except Exception as e:
            logger.warning("Failed to auto-index question %d: %s", question.id, e)

        created += 1

    db.commit()

    return {"created": created, "duplicates": duplicates}


def get_questions_by_subject(
    db: Session,
    subject: str,
    limit: int = 100,
    offset: int = 0,
    user_id=None,
) -> List[Question]:
    """按科目查询题目"""
    query = db.query(Question).join(UploadBatch).filter(
        UploadBatch.subject == subject
    )
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return query.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()


def get_questions_by_tag(
    db: Session,
    tag_name: str,
    limit: int = 100,
    offset: int = 0,
    user_id=None,
) -> List[Question]:
    """按标签查询题目"""
    query = db.query(Question).join(QuestionTagMapping).join(KnowledgeTag).filter(
        KnowledgeTag.tag_name == tag_name
    )
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return query.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()


def get_history_questions(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    user_id=None,
) -> Tuple[List[Question], int]:
    """
    分页查询历史题目（全部题目）

    Args:
        db: 数据库会话
        start_date: 开始日期筛选
        end_date: 结束日期筛选
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        (题目列表, 总数)
    """
    query = db.query(Question).join(UploadBatch)

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)

    if start_date:
        query = query.filter(UploadBatch.upload_time >= start_date)
    if end_date:
        from datetime import timedelta
        query = query.filter(UploadBatch.upload_time < end_date + timedelta(days=1))

    # 获取总数
    total = query.count()

    # 分页查询
    offset = (page - 1) * page_size
    questions = (
        query.options(selectinload(Question.batch), selectinload(Question.tags).selectinload(QuestionTagMapping.tag))
        .order_by(Question.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return questions, total


def search_questions(
    db: Session,
    keyword: Optional[str] = None,
    knowledge_tag: Optional[str] = None,
    question_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user_id=None,
) -> Tuple[List[Question], int]:
    """
    搜索题目（知识点/题型/关键字）

    Args:
        db: 数据库会话
        keyword: 关键字搜索（匹配题目内容 content_json）
        knowledge_tag: 知识点标签筛选
        question_type: 题型筛选
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        (题目列表, 总数)
    """
    query = db.query(Question)

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)

    # 关键字搜索：匹配 content_json 中的内容
    if keyword:
        escaped = re.sub(r"([%_\\])", r"\\\1", keyword)
        query = query.filter(Question.content_json.ilike(f"%{escaped}%"))

    # 题型筛选
    if question_type:
        query = query.filter(Question.question_type == question_type)

    # 知识点标签筛选（支持逗号分隔多选，OR 语义）
    if knowledge_tag:
        tag_list = _parse_tag_list(knowledge_tag)
        if tag_list:
            query = query.join(QuestionTagMapping).join(KnowledgeTag).filter(
                KnowledgeTag.tag_name.in_(tag_list)
            )

    # 获取总数（需要先去除distinct，因为join可能产生重复）
    total = query.distinct().count()

    # 分页查询
    offset = (page - 1) * page_size
    questions = (
        query.distinct()
        .options(selectinload(Question.batch), selectinload(Question.tags).selectinload(QuestionTagMapping.tag))
        .order_by(Question.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return questions, total


def query_questions(
    db: Session,
    subject: Optional[str] = None,
    knowledge_tag: Optional[str] = None,
    question_type: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    review_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user_id=None,
    project_id=None,
    include_grand_total: bool = False,
) -> Tuple[List[Question], int, Optional[int]]:
    """
    统一查询题目（合并 get_history_questions 和 search_questions 的能力）

    支持所有筛选条件任意组合。
    """
    query = db.query(Question).join(UploadBatch)

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    if project_id is not None:
        query = query.filter(Question.project_id == project_id)

    # 未筛选的总收录数（仅按用户隔离）
    grand_total = 0
    if include_grand_total:
        grand_total = query.distinct().count()

    subject_list = _parse_filter_list(subject)
    if subject_list:
        query = query.filter(UploadBatch.subject.in_(subject_list))

    question_type_list = _parse_filter_list(question_type)
    if question_type_list:
        query = query.filter(Question.question_type.in_(question_type_list))

    if keyword:
        escaped = re.sub(r"([%_\\])", r"\\\1", keyword)
        query = query.filter(Question.content_json.ilike(f"%{escaped}%"))

    if knowledge_tag:
        tag_list = _parse_tag_list(knowledge_tag)
        if tag_list:
            query = query.join(QuestionTagMapping).join(KnowledgeTag).filter(
                KnowledgeTag.tag_name.in_(tag_list)
            )

    if start_date:
        query = query.filter(Question.created_at >= start_date)
    if end_date:
        from datetime import timedelta
        query = query.filter(Question.created_at < end_date + timedelta(days=1))

    review_status_list = _parse_filter_list(review_status)
    if review_status_list:
        query = query.filter(Question.review_status.in_(review_status_list))

    total = query.distinct().count()

    offset = (page - 1) * page_size
    questions = (
        query.distinct()
        .options(selectinload(Question.batch), selectinload(Question.tags).selectinload(QuestionTagMapping.tag))
        .order_by(Question.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if include_grand_total:
        return questions, total, grand_total
    return questions, total


def get_questions_by_ids(db: Session, question_ids: List[int], user_id=None) -> List[Question]:
    """按 ID 列表批量查询题目"""
    if not question_ids:
        return []
    query = (
        db.query(Question)
        .options(joinedload(Question.batch), joinedload(Question.tags).joinedload(QuestionTagMapping.tag))
        .filter(Question.id.in_(question_ids))
    )
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return query.all()


def delete_question(db: Session, question_id: int, user_id=None) -> bool:
    """
    删除题目

    Args:
        db: 数据库会话
        question_id: 题目ID
        user_id: 用户ID（非 None 时校验归属）

    Returns:
        是否删除成功
    """
    query = db.query(Question).filter(Question.id == question_id)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    question = query.first()
    if not question:
        return False

    try:
        batch_id = question.batch_id
        from core.rag import delete_question_chunks

        delete_question_chunks(db, question_id)

        # 删除关联的标签映射
        db.query(QuestionTagMapping).filter(QuestionTagMapping.question_id == question_id).delete()

        # 删除题目
        db.delete(question)

        # 检查批次是否已空，若空则清理
        if batch_id:
            other_q = db.query(Question.id).filter(Question.batch_id == batch_id).first()
            if not other_q:
                db.query(UploadBatch).filter(UploadBatch.id == batch_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"删除题目 {question_id} 失败: {e}")
        raise

    return True


def update_user_answer(db: Session, question_id: int, user_answer: str, user_id=None) -> Optional[Question]:
    """更新用户答案"""
    query = db.query(Question).filter(Question.id == question_id)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    question = query.first()
    if not question:
        return None

    try:
        question.user_answer = user_answer
        question.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        logger.error(f"更新题目 {question_id} 答案失败: {e}")
        raise


def update_question_answer(db: Session, question_id: int, answer: str, user_id=None) -> Optional[Question]:
    """保存/更新题目答案（Markdown 格式）"""
    query = db.query(Question).filter(Question.id == question_id)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    question = query.first()
    if not question:
        return None

    try:
        question.answer = answer
        question.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        logger.error(f"保存题目 {question_id} 答案失败: {e}")
        raise


VALID_REVIEW_STATUSES = ('待复习', '复习中', '已掌握')


def update_review_status(db: Session, question_id: int, review_status: str, user_id=None) -> Optional[Question]:
    """更新题目复习状态"""
    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"无效的复习状态: {review_status}，可选值: {VALID_REVIEW_STATUSES}")

    query = db.query(Question).filter(Question.id == question_id)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    question = query.first()
    if not question:
        return None

    try:
        question.review_status = review_status
        question.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        db.rollback()
        logger.error(f"更新题目 {question_id} 复习状态失败: {e}")
        raise


def get_existing_subjects(db, user_id=None, project_id=None):
    """获取数据库中已有的所有科目名称（去重）"""
    query = db.query(UploadBatch.subject).distinct().filter(
        UploadBatch.subject.isnot(None),
        UploadBatch.subject != "",
    )
    if user_id is not None:
        query = query.filter(UploadBatch.user_id == user_id)
    if project_id is not None:
        query = query.filter(UploadBatch.project_id == project_id)
    return [r[0] for r in query.all()]


def get_existing_question_types(db: Session, user_id=None, project_id=None) -> List[str]:
    """获取数据库中已有的所有题型（去重）"""
    query = db.query(Question.question_type).distinct().filter(
        Question.question_type.isnot(None),
        Question.question_type != "",
    )
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    if project_id is not None:
        query = query.filter(Question.project_id == project_id)
    return [r[0] for r in query.all()]
