"""
笔记 CRUD 操作
"""

import json
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session, selectinload

from db.models import Note, NoteTagMapping, KnowledgeTag

logger = logging.getLogger(__name__)


def save_note(
    db: Session,
    title: str,
    subject: str,
    content_markdown: str,
    source_images: List[str],
    ocr_text: str,
    knowledge_tags: List[str] = None,
    user_id: int = None,
) -> Note:
    """保存一条笔记到数据库

    Args:
        title: 笔记标题
        subject: 科目
        content_markdown: LLM 整理后的 Markdown 内容
        source_images: 原始上传图片路径列表
        ocr_text: OCR 识别的原始文本
        knowledge_tags: 知识点标签名称列表
        user_id: 用户 ID

    Returns:
        创建的 Note 对象
    """
    note = Note(
        user_id=user_id,
        title=title,
        subject=subject,
        content_markdown=content_markdown,
        source_images_json=json.dumps(source_images, ensure_ascii=False),
        ocr_text=ocr_text,
    )
    db.add(note)
    db.flush()  # 获取 note.id

    # 创建知识点标签关联
    if knowledge_tags:
        from db.crud.tags import get_or_create_tag
        for tag_name in knowledge_tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            tag = get_or_create_tag(db, tag_name, subject or "")
            mapping = NoteTagMapping(note_id=note.id, tag_id=tag.id)
            db.add(mapping)

    db.commit()
    db.refresh(note)
    return note


def get_notes(
    db: Session,
    user_id: int = None,
    subject: str = None,
    knowledge_tag: str = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple:
    """分页查询笔记列表

    Returns:
        (笔记列表, 总数)
    """
    query = db.query(Note).options(
        selectinload(Note.tags).selectinload(NoteTagMapping.tag),
    )

    if user_id is not None:
        query = query.filter(Note.user_id == user_id)
    if subject:
        query = query.filter(Note.subject == subject)
    if keyword:
        query = query.filter(
            Note.title.ilike(f"%{keyword}%") |
            Note.content_markdown.ilike(f"%{keyword}%")
        )
    if knowledge_tag:
        query = query.join(NoteTagMapping).join(KnowledgeTag).filter(
            KnowledgeTag.tag_name == knowledge_tag
        )

    total = query.count()
    notes = (
        query.order_by(Note.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return notes, total


def get_note_by_id(db: Session, note_id: int) -> Optional[Note]:
    """根据 ID 获取单条笔记"""
    return db.query(Note).options(
        selectinload(Note.tags).selectinload(NoteTagMapping.tag),
    ).filter(Note.id == note_id).first()


def update_note(
    db: Session,
    note_id: int,
    title: str = None,
    content_markdown: str = None,
    subject: str = None,
    knowledge_tags: List[str] = None,
) -> Optional[Note]:
    """更新笔记内容

    Args:
        note_id: 笔记 ID
        title: 新标题（None 不更新）
        content_markdown: 新 Markdown 内容（None 不更新）
        subject: 新科目（None 不更新）
        knowledge_tags: 新标签列表（None 不更新，空列表清空标签）

    Returns:
        更新后的 Note 对象，不存在返回 None
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        return None

    if title is not None:
        note.title = title
    if content_markdown is not None:
        note.content_markdown = content_markdown
    if subject is not None:
        note.subject = subject

    # 更新标签：先删后建
    if knowledge_tags is not None:
        db.query(NoteTagMapping).filter(NoteTagMapping.note_id == note_id).delete()
        from db.crud.tags import get_or_create_tag
        for tag_name in knowledge_tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            tag = get_or_create_tag(db, tag_name, note.subject or "")
            db.add(NoteTagMapping(note_id=note.id, tag_id=tag.id))

    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note_id: int) -> bool:
    """删除笔记（级联删除标签关联）"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True
