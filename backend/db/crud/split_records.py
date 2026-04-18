"""分割历史记录 CRUD"""

import json
import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import SplitRecord

logger = logging.getLogger(__name__)


MAX_SPLIT_RECORDS = 20


def save_split_record(
    db: Session,
    subject: Optional[str],
    model_provider: str,
    file_names: List[str],
    questions: List[Dict],
    user_id=None,
) -> SplitRecord:
    """保存一次分割操作的完整结果，超过上限自动清理最旧记录"""
    record = SplitRecord(
        user_id=user_id,
        subject=subject,
        model_provider=model_provider,
        file_names_json=json.dumps(file_names, ensure_ascii=False),
        questions_json=json.dumps(questions, ensure_ascii=False),
        question_count=len(questions),
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        _cleanup_old_split_records(db, user_id=user_id)
        return record
    except Exception as e:
        db.rollback()
        logger.error(f"保存分割记录失败: {e}")
        raise


def _cleanup_old_split_records(db: Session, user_id=None):
    """删除超出上限的最旧分割记录（按用户隔离）"""
    count_query = db.query(func.count(SplitRecord.id))
    if user_id is not None:
        count_query = count_query.filter(SplitRecord.user_id == user_id)
    count = count_query.scalar()
    if count <= MAX_SPLIT_RECORDS:
        return
    overflow = count - MAX_SPLIT_RECORDS
    ids_query = db.query(SplitRecord.id)
    if user_id is not None:
        ids_query = ids_query.filter(SplitRecord.user_id == user_id)
    old_ids = [
        row[0] for row in
        ids_query.order_by(SplitRecord.created_at.asc())
        .limit(overflow)
        .all()
    ]
    try:
        db.query(SplitRecord).filter(SplitRecord.id.in_(old_ids)).delete(synchronize_session=False)
        db.commit()
        logger.info(f"已清理 {overflow} 条过期分割记录")
    except Exception as e:
        db.rollback()
        logger.error(f"清理分割记录失败: {e}")


def get_recent_split_records(db, limit: int = 10, user_id=None):
    """获取最近 N 条分割记录（不加载 questions_json 大字段）"""
    from sqlalchemy.orm import defer
    query = (
        db.query(SplitRecord)
        .options(defer(SplitRecord.questions_json))
    )
    if user_id is not None:
        query = query.filter(SplitRecord.user_id == user_id)
    return query.order_by(SplitRecord.created_at.desc()).limit(limit).all()


def get_split_record_by_id(db: Session, record_id: int, user_id=None) -> Optional[SplitRecord]:
    """按 ID 获取单条分割记录（含完整 questions_json）"""
    query = db.query(SplitRecord).filter(SplitRecord.id == record_id)
    if user_id is not None:
        query = query.filter(SplitRecord.user_id == user_id)
    return query.first()
