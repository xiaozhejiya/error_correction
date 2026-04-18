"""知识点标签 CRUD"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import KnowledgeTag

logger = logging.getLogger(__name__)


def _parse_tag_list(knowledge_tag: str) -> List[str]:
    """将逗号分隔的标签字符串拆分为去空白的非空列表"""
    return [t.strip() for t in knowledge_tag.split(',') if t.strip()]


def get_or_create_tag(db: Session, tag_name: str, subject: str) -> KnowledgeTag:
    """获取或创建知识点标签"""
    tag = db.query(KnowledgeTag).filter_by(
        tag_name=tag_name,
        subject=subject
    ).first()

    if not tag:
        tag = KnowledgeTag(tag_name=tag_name, subject=subject)
        db.add(tag)
        db.flush()

    return tag


def get_existing_tag_names(db: Session, subject: Optional[str] = None) -> List[str]:
    """获取数据库中已有的知识点标签名称列表（字符串）"""
    query = db.query(KnowledgeTag.tag_name).distinct()
    if subject:
        query = query.filter(KnowledgeTag.subject == subject)
    rows = query.order_by(KnowledgeTag.tag_name).all()
    return [r[0] for r in rows]


def get_all_tags(db: Session, subject: Optional[str] = None) -> List[KnowledgeTag]:
    """获取所有标签（可按科目筛选）"""
    query = db.query(KnowledgeTag)
    if subject:
        query = query.filter(KnowledgeTag.subject == subject)
    return query.order_by(KnowledgeTag.tag_name).all()
