"""用户认证 CRUD"""

import logging
from sqlalchemy import func

from db.models import User

logger = logging.getLogger(__name__)


def create_user(db, email, password_hash, username, is_admin=False):
    """创建用户"""
    user = User(
        email=email,
        password_hash=password_hash,
        username=username,
        display_name=username,
        is_admin=is_admin,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise


def get_user_by_email(db, email):
    """按邮箱查询用户"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db, user_id):
    """按 ID 查询用户"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_login(db, identifier):
    """按邮箱或用户名查询用户（登录用，大小写不敏感邮箱）"""
    identifier = identifier.strip()
    return db.query(User).filter(
        (func.lower(User.email) == identifier.lower()) | (User.username == identifier)
    ).first()


def update_user_profile(db, user_id: int, *, display_name=None, nickname=None):
    """更新用户资料"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.display_name = display_name
    user.nickname = nickname
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def update_user_avatar(db, user_id: int, avatar_path):
    """更新用户头像路径"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.avatar_path = avatar_path
    user.avatar_url = None
    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def update_user_password(db, email: str, new_password_hash: str) -> bool:
    """按邮箱更新用户密码，成功返回 True"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    user.password_hash = new_password_hash
    user.session_version = (user.session_version or 0) + 1
    try:
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
