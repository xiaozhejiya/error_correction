"""Provider Config CRUD"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from db.models import ProviderConfig, SystemProviderConfig

logger = logging.getLogger(__name__)


def _mask_secret(value: str, visible: int = 4) -> str:
    """脱敏显示密钥"""
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * 4 + value[-visible:]


def _serialize_provider(p) -> dict:
    """序列化 provider 为前端可用 dict（密钥脱敏）"""
    d = {
        "id": p.id,
        "name": p.name,
        "is_active": p.is_active,
        "api_key_set": bool(p.api_key),
        "api_key_hint": _mask_secret(p.api_key),
        "base_url": p.base_url or "",
        "model_name": p.model_name or "",
    }
    if p.category == "openai":
        d["light_model_name"] = p.light_model_name or ""
        d["supports_function_calling"] = p.supports_function_calling
    elif p.category == "paddleocr":
        d["use_doc_orientation"] = p.use_doc_orientation
        d["use_doc_unwarping"] = p.use_doc_unwarping
        d["use_chart_recognition"] = p.use_chart_recognition
    return d


def _empty_provider_payload() -> dict:
    return {
        "openai_providers": [],
        "anthropic_providers": [],
        "paddleocr_providers": [],
        "active_openai_id": None,
        "active_anthropic_id": None,
        "active_paddleocr_id": None,
    }


def get_user_providers(db: Session, user_id: int) -> dict:
    """获取用户的所有 provider 配置，按类别分组返回"""
    providers = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == user_id
    ).order_by(ProviderConfig.created_at).all()

    result = _empty_provider_payload()
    category_key = {
        "openai": "openai_providers",
        "anthropic": "anthropic_providers",
        "paddleocr": "paddleocr_providers",
    }
    active_key = {
        "openai": "active_openai_id",
        "anthropic": "active_anthropic_id",
        "paddleocr": "active_paddleocr_id",
    }

    for p in providers:
        key = category_key.get(p.category)
        if key:
            result[key].append(_serialize_provider(p))
        if p.is_active:
            ak = active_key.get(p.category)
            if ak:
                result[ak] = p.id

    return result


def get_system_providers(db: Session) -> dict:
    """获取系统级 provider 配置，供管理员管理平台托管服务"""
    providers = db.query(SystemProviderConfig).order_by(SystemProviderConfig.created_at).all()

    result = _empty_provider_payload()
    category_key = {
        "openai": "openai_providers",
        "anthropic": "anthropic_providers",
        "paddleocr": "paddleocr_providers",
    }
    active_key = {
        "openai": "active_openai_id",
        "anthropic": "active_anthropic_id",
        "paddleocr": "active_paddleocr_id",
    }

    for p in providers:
        key = category_key.get(p.category)
        if key:
            result[key].append(_serialize_provider(p))
        if p.is_active:
            ak = active_key.get(p.category)
            if ak:
                result[ak] = p.id

    return result


def save_user_providers(db: Session, user_id: int, data: dict) -> None:
    """保存用户的 provider 配置（全量覆盖）

    data 结构:
        openai_providers: [{ id, name, api_key?, base_url, model_name, ... }]
        anthropic_providers: [...]
        paddleocr_providers: [...]
        active_openai_id: str | None
        active_anthropic_id: str | None
        active_paddleocr_id: str | None
    """
    active_ids = {
        "openai": data.get("active_openai_id"),
        "anthropic": data.get("active_anthropic_id"),
        "paddleocr": data.get("active_paddleocr_id"),
    }

    # 读取已有配置（用于保留未重新提交的 api_key）
    existing = {
        p.id: p for p in db.query(ProviderConfig).filter(
            ProviderConfig.user_id == user_id
        ).all()
    }

    # 收集本次提交的所有 ID
    submitted_ids = set()
    items_to_save = []

    category_map = {
        "openai_providers": "openai",
        "anthropic_providers": "anthropic",
        "paddleocr_providers": "paddleocr",
    }

    for list_key, category in category_map.items():
        for item in data.get(list_key, []):
            pid = item.get("id")
            submitted_ids.add(pid)
            old = existing.get(pid)

            # API Key：前端提交了新值则更新，否则保留旧值
            new_api_key = item.get("api_key") or item.get("api_token") or ""
            if not new_api_key and old:
                new_api_key = old.api_key or ""

            base_url = item.get("base_url") or item.get("api_url") or ""
            model_name = item.get("model_name") or item.get("model") or ""

            items_to_save.append({
                "id": pid,
                "category": category,
                "name": item.get("name", ""),
                "is_active": pid == active_ids.get(category),
                "api_key": new_api_key,
                "base_url": base_url,
                "model_name": model_name,
                "light_model_name": item.get("light_model_name", ""),
                "supports_function_calling": item.get("supports_function_calling", True),
                "use_doc_orientation": item.get("use_doc_orientation", False),
                "use_doc_unwarping": item.get("use_doc_unwarping", False),
                "use_chart_recognition": item.get("use_chart_recognition", False),
            })

    # 删除已移除的 provider
    for pid in set(existing.keys()) - submitted_ids:
        db.delete(existing[pid])

    # 更新或新增
    for item in items_to_save:
        old = existing.get(item["id"])
        if old:
            for k, v in item.items():
                setattr(old, k, v)
        else:
            p = ProviderConfig(user_id=user_id, **item)
            db.add(p)

    db.commit()


def save_system_providers(db: Session, data: dict) -> None:
    """保存系统级 provider 配置（全量覆盖）"""
    active_ids = {
        "openai": data.get("active_openai_id"),
        "anthropic": data.get("active_anthropic_id"),
        "paddleocr": data.get("active_paddleocr_id"),
    }

    existing = {p.id: p for p in db.query(SystemProviderConfig).all()}
    submitted_ids = set()
    items_to_save = []

    category_map = {
        "openai_providers": "openai",
        "anthropic_providers": "anthropic",
        "paddleocr_providers": "paddleocr",
    }

    for list_key, category in category_map.items():
        for item in data.get(list_key, []):
            pid = item.get("id")
            submitted_ids.add(pid)
            old = existing.get(pid)

            new_api_key = item.get("api_key") or item.get("api_token") or ""
            if not new_api_key and old:
                new_api_key = old.api_key or ""

            items_to_save.append({
                "id": pid,
                "category": category,
                "name": item.get("name", ""),
                "is_active": pid == active_ids.get(category),
                "api_key": new_api_key,
                "base_url": item.get("base_url") or item.get("api_url") or "",
                "model_name": item.get("model_name") or item.get("model") or "",
                "light_model_name": item.get("light_model_name", ""),
                "supports_function_calling": item.get("supports_function_calling", True),
                "use_doc_orientation": item.get("use_doc_orientation", False),
                "use_doc_unwarping": item.get("use_doc_unwarping", False),
                "use_chart_recognition": item.get("use_chart_recognition", False),
            })

    for pid in set(existing.keys()) - submitted_ids:
        db.delete(existing[pid])

    for item in items_to_save:
        old = existing.get(item["id"])
        if old:
            for k, v in item.items():
                setattr(old, k, v)
        else:
            db.add(SystemProviderConfig(**item))

    db.commit()


def get_active_provider(db: Session, user_id: int, category: str) -> Optional[ProviderConfig]:
    """获取用户指定类别的激活 provider（用于后端调用 LLM/OCR 时读取凭据）"""
    return db.query(ProviderConfig).filter(
        ProviderConfig.user_id == user_id,
        ProviderConfig.category == category,
        ProviderConfig.is_active == True,
    ).first()


def get_active_system_provider(db: Session, category: str) -> Optional[SystemProviderConfig]:
    """获取系统级激活 provider（用于平台托管 provider）"""
    return db.query(SystemProviderConfig).filter(
        SystemProviderConfig.category == category,
        SystemProviderConfig.is_active == True,
    ).first()
