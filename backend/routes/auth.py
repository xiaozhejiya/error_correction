import hmac
import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from core.config import settings
from core.mail import send_smtp_email
from core.quota import get_daily_quota_snapshot
from db import SessionLocal
from db import crud

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

_AVATAR_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
_AVATAR_MAX_SIZE_MB = 5


def _hash_registration_code(email: str, code: str, pepper: str) -> str:
    raw = f"{email.lower().strip()}:{code}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _generate_six_digit_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def _avatar_upload_dir() -> str:
    return os.path.join(str(settings.upload_dir), "avatars")


def _serialize_user(user, db=None):
    avatar_url = None
    avatar_path = (getattr(user, "avatar_path", None) or "").strip()
    legacy_avatar_url = (getattr(user, "avatar_url", None) or "").strip()
    if avatar_path:
        avatar_url = f"/uploads/{avatar_path.replace(os.sep, '/')}"
    elif legacy_avatar_url:
        avatar_url = legacy_avatar_url
    quota = get_daily_quota_snapshot(db, user) if db is not None else {
        "daily_free_quota": max(int(getattr(user, "daily_free_quota", 5) or 5), 0),
        "daily_free_used": max(int(getattr(user, "daily_free_used", 0) or 0), 0),
        "remaining": max(int(getattr(user, "daily_free_quota", 5) or 5) - int(getattr(user, "daily_free_used", 0) or 0), 0),
        "quota_date": getattr(user, "daily_free_quota_date", None),
        "reset_at": None,
    }
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "nickname": user.nickname,
        "avatar_url": avatar_url,
        "is_admin": user.is_admin,
        "quota": quota,
    }


def _normalize_profile_text(value, max_length: int):
    text = (value or "").strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ValueError(f"长度不能超过 {max_length} 个字符")
    return text


def _current_user_id():
    return session.get("user_id")


def _delete_avatar_file_if_exists(avatar_path: str | None):
    if not avatar_path:
        return
    normalized = os.path.normpath(avatar_path)
    prefix = f"avatars{os.sep}"
    if normalized != "avatars" and not normalized.startswith(prefix):
        return
    file_path = os.path.abspath(os.path.join(str(settings.upload_dir), normalized))
    avatar_root = os.path.abspath(_avatar_upload_dir())
    if not file_path.startswith(avatar_root + os.sep):
        return
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


def _save_avatar_file(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("请选择头像图片")

    ext = os.path.splitext(file_storage.filename)[1].lower().lstrip('.')
    if ext not in _AVATAR_ALLOWED_EXTENSIONS:
        raise ValueError(f"头像仅支持 {', '.join(sorted(_AVATAR_ALLOWED_EXTENSIONS))} 格式")

    file_storage.seek(0, 2)
    file_size = file_storage.tell()
    file_storage.seek(0)
    max_bytes = _AVATAR_MAX_SIZE_MB * 1024 * 1024
    if file_size <= 0:
        raise ValueError("头像文件不能为空")
    if file_size > max_bytes:
        raise ValueError(f"头像大小不能超过 {_AVATAR_MAX_SIZE_MB}MB")

    avatar_dir = _avatar_upload_dir()
    os.makedirs(avatar_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(avatar_dir, filename)
    file_storage.save(file_path)
    return f"avatars/{filename}", file_path


@bp.route("/register", methods=["POST"])
def auth_register():
    """用户注册（需先调用 /send-code?type=register 并填写正确验证码）。"""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()

    if not email or "@" not in email:
        return jsonify({"success": False, "error": "邮箱格式不正确"}), 400
    if not username:
        return jsonify({"success": False, "error": "用户名不能为空"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码至少 6 位"}), 400
    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"success": False, "error": "请输入 6 位邮箱验证码"}), 400

    pepper = (current_app.secret_key or "dev-secret-change-in-production")[:64]
    submitted_hash = _hash_registration_code(email, code, pepper)
    now = datetime.utcnow()

    with SessionLocal() as db:
        if crud.get_user_by_email(db, email):
            return jsonify({"success": False, "error": "该邮箱已注册"}), 409

        row = crud.get_verification_by_email(db, email)
        if not row:
            return jsonify({"success": False, "error": "请先获取邮箱验证码"}), 400
        if row.expires_at < now:
            crud.delete_verification_by_email(db, email)
            return jsonify({"success": False, "error": "验证码已过期，请重新获取"}), 400
        if (row.attempts or 0) >= settings.registration_max_attempts:
            crud.delete_verification_by_email(db, email)
            return jsonify({"success": False, "error": "验证失败次数过多，请重新获取验证码"}), 400

        if not hmac.compare_digest(row.code_hash, submitted_hash):
            crud.increment_verification_attempts(db, email)
            return jsonify({"success": False, "error": "验证码错误"}), 400

        pwd_hash = generate_password_hash(password)
        user = crud.create_user(db, email=email, password_hash=pwd_hash, username=username)
        crud.delete_verification_by_email(db, email)
        user_payload = _serialize_user(user, db)
        session_version_out = user.session_version or 0

    session["user_id"] = user_payload["id"]
    session["username"] = user_payload["username"]
    session["is_admin"] = bool(user_payload["is_admin"])
    session["session_version"] = session_version_out
    return jsonify({"success": True, "user": user_payload}), 201


@bp.route("/send-code", methods=["POST"])
def send_code():
    """发送验证码（支持注册和找回密码两种场景）。

    请求体：{ email, type: 'register' | 'reset' }
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code_type = (data.get("type") or "register").strip().lower()

    if not email or "@" not in email:
        return jsonify({"success": False, "error": "邮箱格式不正确"}), 400

    now = datetime.utcnow()
    code = _generate_six_digit_code()
    pepper = (current_app.secret_key or "dev-secret-change-in-production")[:64]
    code_hash = _hash_registration_code(email, code, pepper)
    expires_at = now + timedelta(minutes=settings.registration_code_ttl_minutes)

    with SessionLocal() as db:
        row = crud.get_verification_by_email(db, email)
        if row and row.last_sent_at:
            delta = (now - row.last_sent_at).total_seconds()
            if delta < settings.registration_send_interval_seconds:
                wait = int(settings.registration_send_interval_seconds - delta)
                return jsonify(
                    {"success": False, "error": f"发送过于频繁，请 {wait} 秒后再试"}
                ), 429

        user = crud.get_user_by_email(db, email)
        if (code_type == "register" and user) or (code_type == "reset" and not user):
            crud.upsert_registration_code(db, email, "anti-enum-dummy", now + timedelta(minutes=1), now)
            return jsonify({"success": True, "message": "验证码已发送"})

        crud.upsert_registration_code(db, email, code_hash, expires_at, now)

    subject_text = "找回密码" if code_type == "reset" else "注册"
    smtp_ok = bool(settings.smtp_host and settings.smtp_from)
    if smtp_ok:
        try:
            send_smtp_email(
                host=settings.smtp_host,
                port=settings.smtp_port,
                user=settings.smtp_user,
                password=settings.smtp_password,
                mail_from=settings.smtp_from,
                use_tls=settings.smtp_use_tls,
                to_addr=email,
                subject=f"【智卷系统】{subject_text}验证码",
                body=f"您的{subject_text}验证码为：{code}，{settings.registration_code_ttl_minutes} 分钟内有效。请勿泄露给他人。",
                async_send=True,
            )
        except Exception:
            logger.exception("发送验证码邮件失败")
            return jsonify({"success": False, "error": "邮件发送失败，请稍后重试"}), 502
    else:
        if current_app.debug:
            logger.warning(
                "[开发模式] 未配置 SMTP，验证码（仅调试用） email=%s code=%s",
                email,
                code,
            )
        else:
            return jsonify(
                {"success": False, "error": "服务器未配置发信，无法发送验证码"}
            ), 503

    return jsonify({"success": True, "message": "验证码已发送"})


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    """通过邮箱验证码重置密码。

    请求体：{ email, code, password }
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"success": False, "error": "邮箱格式不正确"}), 400
    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"success": False, "error": "请输入 6 位验证码"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "密码至少 6 位"}), 400

    pepper = (current_app.secret_key or "dev-secret-change-in-production")[:64]
    submitted_hash = _hash_registration_code(email, code, pepper)
    now = datetime.utcnow()

    with SessionLocal() as db:
        user = crud.get_user_by_email(db, email)
        if not user:
            return jsonify({"success": False, "error": "验证码错误"}), 400

        row = crud.get_verification_by_email(db, email)
        if not row:
            return jsonify({"success": False, "error": "请先获取验证码"}), 400
        if row.expires_at < now:
            crud.delete_verification_by_email(db, email)
            return jsonify({"success": False, "error": "验证码已过期，请重新获取"}), 400
        if (row.attempts or 0) >= settings.registration_max_attempts:
            crud.delete_verification_by_email(db, email)
            return jsonify({"success": False, "error": "验证失败次数过多，请重新获取验证码"}), 400

        if not hmac.compare_digest(row.code_hash, submitted_hash):
            crud.increment_verification_attempts(db, email)
            return jsonify({"success": False, "error": "验证码错误"}), 400

        if check_password_hash(user.password_hash, password):
            return jsonify({"success": False, "error": "新密码不能与原密码相同"}), 400

        new_hash = generate_password_hash(password)
        crud.update_user_password(db, email, new_hash)
        crud.delete_verification_by_email(db, email)

    return jsonify({"success": True, "message": "密码重置成功"})


@bp.route("/login", methods=["POST"])
def auth_login():
    """用户登录（支持邮箱或用户名）"""
    data = request.get_json() or {}
    identifier = (data.get("email") or data.get("identifier") or "").strip()
    password = data.get("password") or ""

    if not identifier:
        return jsonify({"error": "请输入邮箱或用户名"}), 400

    with SessionLocal() as db:
        user = crud.get_user_by_login(db, identifier)
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "账号或密码错误"}), 401
        session["user_id"] = user.id
        session["username"] = user.username
        session["is_admin"] = bool(user.is_admin)
        session["session_version"] = user.session_version or 0
        return jsonify({"user": _serialize_user(user, db)})


@bp.route("/logout", methods=["POST"])
def auth_logout():
    """退出登录"""
    session.clear()
    return jsonify({"ok": True})


@bp.route("/me", methods=["GET"])
def auth_me():
    """获取当前登录用户"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "未登录", "code": "UNAUTHORIZED"}), 401
    with SessionLocal() as db:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            session.clear()
            return jsonify({"error": "用户不存在", "code": "UNAUTHORIZED"}), 401
        return jsonify({"user": _serialize_user(user, db)})


@bp.route("/profile", methods=["PATCH"])
def update_profile():
    """更新当前用户资料"""
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"success": False, "error": "未登录"}), 401

    data = request.get_json() or {}
    try:
        display_name = _normalize_profile_text(data.get("display_name"), 50)
        nickname = _normalize_profile_text(data.get("nickname"), 50)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    with SessionLocal() as db:
        user = crud.update_user_profile(
            db,
            user_id,
            display_name=display_name,
            nickname=nickname,
        )
        if not user:
            session.clear()
            return jsonify({"success": False, "error": "用户不存在"}), 404
        return jsonify({"success": True, "user": _serialize_user(user, db)})


@bp.route("/profile/avatar", methods=["POST"])
def upload_profile_avatar():
    """上传当前用户头像"""
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"success": False, "error": "未登录"}), 401

    file = request.files.get("file")
    saved_avatar_path = None
    saved_file_path = None
    try:
        saved_avatar_path, saved_file_path = _save_avatar_file(file)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("保存头像文件失败")
        return jsonify({"success": False, "error": "头像上传失败，请稍后重试"}), 500

    with SessionLocal() as db:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            if saved_file_path and os.path.exists(saved_file_path):
                os.remove(saved_file_path)
            session.clear()
            return jsonify({"success": False, "error": "用户不存在"}), 404

        old_avatar_path = getattr(user, "avatar_path", None)
        try:
            user = crud.update_user_avatar(db, user_id, saved_avatar_path)
        except Exception:
            if saved_file_path and os.path.exists(saved_file_path):
                os.remove(saved_file_path)
            raise

    _delete_avatar_file_if_exists(old_avatar_path)
    return jsonify({"success": True, "user": _serialize_user(user)})


@bp.route("/profile/avatar", methods=["DELETE"])
def delete_profile_avatar():
    """删除当前用户头像"""
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"success": False, "error": "未登录"}), 401

    with SessionLocal() as db:
        user = crud.get_user_by_id(db, user_id)
        if not user:
            session.clear()
            return jsonify({"success": False, "error": "用户不存在"}), 404
        old_avatar_path = getattr(user, "avatar_path", None)
        user = crud.update_user_avatar(db, user_id, None)

    _delete_avatar_file_if_exists(old_avatar_path)
    return jsonify({"success": True, "user": _serialize_user(user)})
