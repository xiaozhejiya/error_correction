"""对话 CRUD（支持题目绑定对话和独立对话）"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session, selectinload

from db.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


def create_chat_session(
    db: Session,
    question_id: int = None,
    user_id: int = None,
    title: str = "新对话",
) -> ChatSession:
    """创建对话会话

    Args:
        question_id: 绑定的题目 ID（可选，None 为独立对话）
        user_id: 用户 ID
        title: 对话标题
    """
    session = ChatSession(question_id=question_id, user_id=user_id, title=title)
    if not getattr(session, "public_id", None):
        session.public_id = str(uuid.uuid4())
    db.add(session)
    try:
        db.commit()
        db.refresh(session)
        return session
    except Exception as e:
        db.rollback()
        logger.error(f"创建对话会话失败: {e}")
        raise


_VALID_ROLES = ('user', 'assistant')

def get_chat_session_by_public_id(db: Session, public_id: str, user_id=None) -> Optional[ChatSession]:
    query = db.query(ChatSession).filter(ChatSession.public_id == public_id)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    return query.first()


def add_chat_message(db: Session, session_id: int, role: str, content: str, user_id=None) -> ChatMessage:
    """向对话中追加一条消息"""
    if role not in _VALID_ROLES:
        raise ValueError(f"无效的消息角色: {role}（可选: {', '.join(_VALID_ROLES)}）")
    # 验证 session 归属
    if user_id is not None:
        owner_check = db.query(ChatSession).filter(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        ).first()
        if not owner_check:
            raise ValueError("对话不存在或无权操作")
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    try:
        db.query(ChatSession).filter(ChatSession.id == session_id).update(
            {"updated_at": datetime.utcnow()}, synchronize_session=False
        )
        db.commit()
        db.refresh(msg)
        return msg
    except Exception as e:
        db.rollback()
        logger.error(f"添加对话消息失败: {e}")
        raise


def get_chat_messages(
    db: Session,
    session_id: int,
    limit: int = 30,
    before_id: Optional[int] = None,
    user_id=None,
) -> Dict[str, Any]:
    """游标分页获取对话消息"""
    # 验证 session 归属
    if user_id is not None:
        owner_check = db.query(ChatSession).filter(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        ).first()
        if not owner_check:
            return {"messages": [], "hasMore": False}
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    if before_id:
        query = query.filter(ChatMessage.id < before_id)

    rows = query.order_by(ChatMessage.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    messages = rows[:limit]
    messages.reverse()

    return {
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in messages
        ],
        "hasMore": has_more,
    }


def get_chat_sessions_by_question(db: Session, question_id: int, limit: int = 50, user_id=None) -> List[ChatSession]:
    """获取某道题目的对话会话"""
    query = db.query(ChatSession).filter(ChatSession.question_id == question_id)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    return query.order_by(ChatSession.updated_at.desc()).limit(limit).all()


def get_user_chat_sessions(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[ChatSession], int]:
    """获取用户的独立对话列表（不含题目绑定的对话）"""
    query = db.query(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatSession.question_id == None,
    )
    total = query.count()
    sessions = (
        query.order_by(ChatSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return sessions, total


def get_all_chat_sessions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user_id=None,
) -> Tuple[List[ChatSession], int]:
    """分页获取对话会话（user_id 非 None 时按用户过滤）"""
    query = db.query(ChatSession)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    total = query.count()
    sessions = (
        query.options(selectinload(ChatSession.question))
        .order_by(ChatSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return sessions, total


def update_chat_session_title(db: Session, session_id: int, title: str, user_id=None) -> Optional[ChatSession]:
    """更新对话标题"""
    query = db.query(ChatSession).filter(ChatSession.id == session_id)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    session = query.first()
    if not session:
        return None
    session.title = title
    db.commit()
    db.refresh(session)
    return session


def delete_chat_session(db: Session, session_id: int, user_id=None) -> bool:
    """删除对话（级联删除消息）"""
    query = db.query(ChatSession).filter(ChatSession.id == session_id)
    if user_id is not None:
        query = query.filter(ChatSession.user_id == user_id)
    session = query.first()
    if not session:
        return False
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return True
