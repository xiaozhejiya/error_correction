"""题目 CRUD"""

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session, joinedload, selectinload

from db.models import UploadBatch, Question, KnowledgeTag, QuestionTagMapping
from db.crud.tags import _parse_tag_list, get_or_create_tag

logger = logging.getLogger(__name__)


def _get_filters():
    """延迟导入共享过滤函数，避免循环导入"""
    from db.crud import _filter_by_subject, _filter_by_user
    return _filter_by_subject, _filter_by_user


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


def question_exists(db, content_hash, user_id=None):
    """检查题目是否已存在（通过内容哈希 + 用户隔离）"""
    q = db.query(Question).filter(Question.content_hash == content_hash)
    if user_id is not None:
        q = q.filter(Question.user_id == user_id)
    return q.first()


def save_questions_to_db(
    db: Session,
    questions: List[Dict],
    batch_info: Dict[str, Any],
    user_id=None,
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

    # 创建批次记录
    batch = UploadBatch(
        user_id=user_id,
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
        if question_exists(db, content_hash, user_id=user_id):
            duplicates += 1
            continue

        # 创建题目记录
        question = Question(
            user_id=user_id,
            batch_id=batch.id,
            content_hash=content_hash,
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
) -> Tuple[List[Question], int]:
    """
    统一查询题目（合并 get_history_questions 和 search_questions 的能力）

    支持所有筛选条件任意组合。
    """
    query = db.query(Question).join(UploadBatch)

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)

    # 未筛选的总收录数（仅按用户隔离）
    grand_total = query.distinct().count()

    if subject:
        query = query.filter(UploadBatch.subject == subject)

    if question_type:
        query = query.filter(Question.question_type == question_type)

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

    if review_status:
        query = query.filter(Question.review_status == review_status)

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

    return questions, total, grand_total


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
        # 删除关联的标签映射
        db.query(QuestionTagMapping).filter(QuestionTagMapping.question_id == question_id).delete()

        # 删除题目
        db.delete(question)
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


def get_existing_subjects(db, user_id=None):
    """获取数据库中已有的所有科目名称（去重）"""
    query = db.query(UploadBatch.subject).distinct().filter(
        UploadBatch.subject.isnot(None),
        UploadBatch.subject != "",
    )
    if user_id is not None:
        query = query.filter(UploadBatch.user_id == user_id)
    return [r[0] for r in query.all()]


def get_existing_question_types(db: Session, user_id=None) -> List[str]:
    """获取数据库中已有的所有题型（去重）"""
    query = db.query(Question.question_type).distinct().filter(
        Question.question_type.isnot(None),
        Question.question_type != "",
    )
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return [r[0] for r in query.all()]
