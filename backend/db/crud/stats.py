"""统计信息 CRUD"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import UploadBatch, Question, KnowledgeTag, QuestionTagMapping
from db.crud.questions import VALID_REVIEW_STATUSES

logger = logging.getLogger(__name__)


def _get_filters():
    """延迟导入共享过滤函数，避免循环导入"""
    from db.crud import _filter_by_subject, _filter_by_user
    return _filter_by_subject, _filter_by_user


def get_statistics(db: Session, subject: Optional[str] = None, user_id=None) -> Dict[str, Any]:
    """获取统计信息"""
    _filter_by_subject, _filter_by_user = _get_filters()

    q_query = _filter_by_subject(db.query(func.count(Question.id)), subject)
    if user_id is not None:
        q_query = q_query.filter(Question.user_id == user_id)
    total_questions = q_query.scalar()

    batch_query = db.query(func.count(UploadBatch.id))
    if user_id is not None:
        batch_query = batch_query.filter(UploadBatch.user_id == user_id)
    total_batches = batch_query.scalar()

    total_tags = db.query(func.count(KnowledgeTag.id)).scalar()

    # 按科目统计
    subject_q = db.query(UploadBatch.subject, func.count(Question.id)).join(Question)
    if user_id is not None:
        subject_q = subject_q.filter(Question.user_id == user_id)
    subject_stats = subject_q.group_by(UploadBatch.subject).all()

    return {
        "total_questions": total_questions or 0,
        "total_batches": total_batches or 0,
        "total_tags": total_tags or 0,
        "by_subject": {s: c for s, c in subject_stats}
    }


def get_knowledge_stats(db: Session, subject: Optional[str] = None, limit: Optional[int] = None, user_id=None) -> List[Dict]:
    """
    获取知识点统计信息

    Args:
        subject: 可选，按学科筛选
        limit: 可选，返回前 N 条
        user_id: 可选，按用户隔离

    Returns:
        [{"tag_name": "xxx", "count": 10}, ...]
    """
    query = db.query(
        KnowledgeTag.tag_name,
        func.count(QuestionTagMapping.question_id).label("count")
    ).join(
        QuestionTagMapping, QuestionTagMapping.tag_id == KnowledgeTag.id
    )

    if user_id is not None:
        query = query.join(Question, Question.id == QuestionTagMapping.question_id).filter(
            Question.user_id == user_id
        )

    if subject:
        query = query.filter(KnowledgeTag.subject == subject)

    query = query.group_by(
        KnowledgeTag.id, KnowledgeTag.tag_name
    ).order_by(
        func.count(QuestionTagMapping.question_id).desc()
    )

    if limit:
        query = query.limit(limit)

    stats = query.all()

    return [{"tag_name": tag_name, "count": count} for tag_name, count in stats]


def get_review_status_stats(db: Session, subject: Optional[str] = None, user_id=None) -> Dict[str, int]:
    """按复习状态分组统计数量"""
    _filter_by_subject, _filter_by_user = _get_filters()

    query = _filter_by_subject(db.query(
        Question.review_status,
        func.count(Question.id)
    ), subject)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)

    rows = query.group_by(Question.review_status).all()

    result = {s: 0 for s in VALID_REVIEW_STATUSES}
    for status, count in rows:
        key = status or '待复习'
        if key in result:
            result[key] += count
        else:
            result['待复习'] += count
    return result


def get_today_mastered_count(db: Session, subject: Optional[str] = None, user_id=None) -> int:
    """获取今日新掌握的题目数（updated_at 在今天且状态为已掌握）"""
    _filter_by_subject, _filter_by_user = _get_filters()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    query = _filter_by_subject(db.query(func.count(Question.id)).filter(
        Question.updated_at >= today_start,
        Question.review_status == '已掌握',
    ), subject)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return query.scalar() or 0


def get_daily_counts(db: Session, days: int = 7, subject: Optional[str] = None, user_id=None) -> List[Dict[str, Any]]:
    """获取最近 N 天每日新增题目数 + 每日新增已掌握数"""
    from datetime import timedelta
    _filter_by_subject, _filter_by_user = _get_filters()

    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

    # SQLite 兼容：使用 func.date() 提取日期字符串
    date_expr = func.date(Question.created_at)

    # 新增题目数
    query = _filter_by_subject(db.query(
        date_expr.label('date'),
        func.count(Question.id).label('count')
    ).filter(Question.created_at >= cutoff), subject)
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    rows = query.group_by(date_expr).order_by(date_expr).all()
    date_map = {str(row.date): row.count for row in rows}

    # 每日新增已掌握数（按 updated_at 统计）
    mastered_date_expr = func.date(Question.updated_at)
    mq = _filter_by_subject(db.query(
        mastered_date_expr.label('date'),
        func.count(Question.id).label('count')
    ).filter(
        Question.updated_at >= cutoff,
        Question.review_status == '已掌握',
    ), subject)
    if user_id is not None:
        mq = mq.filter(Question.user_id == user_id)
    mastered_rows = mq.group_by(mastered_date_expr).order_by(mastered_date_expr).all()
    mastered_map = {str(row.date): row.count for row in mastered_rows}

    # 填充缺失的日期
    result = []
    for i in range(days):
        d = cutoff + timedelta(days=i)
        date_key = d.strftime('%Y-%m-%d')
        date_str = d.strftime('%m-%d')
        result.append({
            'date': date_str,
            'count': date_map.get(date_key, 0),
            'mastered': mastered_map.get(date_key, 0),
        })

    return result


def get_tag_status_stats(db: Session, subject: Optional[str] = None, limit: int = 10, user_id=None) -> List[Dict]:
    """
    知识点 × 掌握状态统计（堆叠柱状图用）

    Returns:
        [{"tag_name": "函数", "待复习": 3, "复习中": 2, "已掌握": 5}, ...]
    """
    query = db.query(
        KnowledgeTag.tag_name,
        Question.review_status,
        func.count(Question.id).label('count')
    ).join(
        QuestionTagMapping, QuestionTagMapping.tag_id == KnowledgeTag.id
    ).join(
        Question, Question.id == QuestionTagMapping.question_id
    )

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    if subject:
        query = query.filter(KnowledgeTag.subject == subject)

    rows = query.group_by(
        KnowledgeTag.tag_name, Question.review_status
    ).all()

    # 按 tag 聚合
    tag_data = {}
    tag_totals = {}
    for tag_name, status, count in rows:
        if tag_name not in tag_data:
            tag_data[tag_name] = {'tag_name': tag_name, **{s: 0 for s in VALID_REVIEW_STATUSES}}
            tag_totals[tag_name] = 0
        key = status or '待复习'
        if key in VALID_REVIEW_STATUSES:
            tag_data[tag_name][key] += count
        else:
            tag_data[tag_name]['待复习'] += count
        tag_totals[tag_name] += count

    # 按总数降序，取 top N
    sorted_tags = sorted(tag_data.keys(), key=lambda t: tag_totals[t], reverse=True)[:limit]
    return [tag_data[t] for t in sorted_tags]


def get_tag_type_stats(db: Session, subject: Optional[str] = None, tag_limit: int = 8, user_id=None) -> Dict[str, Any]:
    """
    知识点 × 题型交叉统计（热力图用）

    Returns:
        {"tags": ["函数", ...], "types": ["选择题", ...], "data": [[3, 1, ...], ...]}
    """
    query = db.query(
        KnowledgeTag.tag_name,
        Question.question_type,
        func.count(Question.id).label('count')
    ).join(
        QuestionTagMapping, QuestionTagMapping.tag_id == KnowledgeTag.id
    ).join(
        Question, Question.id == QuestionTagMapping.question_id
    ).filter(
        Question.question_type.isnot(None),
        Question.question_type != '',
    )

    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    if subject:
        query = query.filter(KnowledgeTag.subject == subject)

    rows = query.group_by(
        KnowledgeTag.tag_name, Question.question_type
    ).all()

    # 收集所有 tag 和 type
    tag_totals = {}
    type_set = set()
    cross = {}
    for tag_name, q_type, count in rows:
        tag_totals[tag_name] = tag_totals.get(tag_name, 0) + count
        type_set.add(q_type)
        cross[(tag_name, q_type)] = count

    # 按总数取 top N tag
    sorted_tags = sorted(tag_totals.keys(), key=lambda t: tag_totals[t], reverse=True)[:tag_limit]
    sorted_types = sorted(type_set)

    # 构建矩阵
    data = []
    for tag in sorted_tags:
        row = [cross.get((tag, t), 0) for t in sorted_types]
        data.append(row)

    return {"tags": sorted_tags, "types": sorted_types, "data": data}
