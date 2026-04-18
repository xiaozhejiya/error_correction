"""每日免费体验额度辅助逻辑。"""

from __future__ import annotations

from datetime import datetime, timedelta

from db import crud

DEFAULT_DAILY_FREE_QUOTA = 5
QUOTA_EXCEEDED_CODE = "DAILY_FREE_QUOTA_EXCEEDED"
QUOTA_EXCEEDED_ERROR = "今日免费体验次数已用完"


def _today_str() -> str:
    return datetime.utcnow().date().isoformat()


def _next_reset_at() -> str:
    next_day = datetime.utcnow().date() + timedelta(days=1)
    return f"{next_day.isoformat()}T00:00:00Z"


def sync_daily_quota_state(db, user):
    """按当天日期修正用户额度状态。"""
    changed = False
    today = _today_str()

    if getattr(user, "daily_free_quota", None) is None:
        user.daily_free_quota = DEFAULT_DAILY_FREE_QUOTA
        changed = True
    if getattr(user, "daily_free_used", None) is None:
        user.daily_free_used = 0
        changed = True

    if getattr(user, "daily_free_quota_date", None) != today:
        user.daily_free_quota_date = today
        user.daily_free_used = 0
        changed = True

    if changed:
        db.flush()
    return user


def get_daily_quota_snapshot(db, user) -> dict:
    """返回当前用户的额度信息，并在必要时按天重置。"""
    sync_daily_quota_state(db, user)
    quota = max(int(getattr(user, "daily_free_quota", DEFAULT_DAILY_FREE_QUOTA) or 0), 0)
    used = max(int(getattr(user, "daily_free_used", 0) or 0), 0)
    remaining = max(quota - used, 0)
    return {
        "daily_free_quota": quota,
        "daily_free_used": used,
        "remaining": remaining,
        "quota_date": user.daily_free_quota_date,
        "reset_at": _next_reset_at(),
    }


def consume_daily_free_quota(db, user, amount: int = 1) -> dict:
    """扣减用户免费额度并返回最新快照。"""
    sync_daily_quota_state(db, user)
    user.daily_free_used = max(int(user.daily_free_used or 0), 0) + max(int(amount or 0), 0)
    db.commit()
    db.refresh(user)
    return get_daily_quota_snapshot(db, user)


def build_quota_exceeded_payload(db, user) -> dict:
    quota = get_daily_quota_snapshot(db, user)
    return {
        "success": False,
        "error": QUOTA_EXCEEDED_ERROR,
        "code": QUOTA_EXCEEDED_CODE,
        "quota": quota,
    }


def quota_exceeded_response(db, user):
    return build_quota_exceeded_payload(db, user), 429


def has_daily_free_quota(db, user) -> bool:
    quota = get_daily_quota_snapshot(db, user)
    return quota["remaining"] > 0


def uses_server_provider(db, user_id: int | None, category: str) -> bool:
    """是否走服务器托管 provider。"""
    if not user_id:
        return True
    provider = crud.get_active_provider(db, user_id, category)
    return provider is None


def uses_server_llm(db, user_id: int | None, provider: str) -> bool:
    return uses_server_provider(db, user_id, provider)


def uses_server_ocr(db, user_id: int | None) -> bool:
    return uses_server_provider(db, user_id, "paddleocr")
