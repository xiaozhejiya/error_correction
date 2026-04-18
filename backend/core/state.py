"""
全局会话状态 — 供各 Blueprint 模块共享

所有需要跨路由访问的运行时变量集中在此模块，
通过 session_lock 保护并发写操作。

会话状态按 user_id 隔离，每个用户拥有独立的上传/分割上下文。
"""

import threading

from src.workflow import build_workflow

# 全局工作流图（无状态，可安全共享）
workflow_graph = build_workflow()

# 线程锁（全局共享）
session_lock = threading.Lock()

# ── 按用户隔离的会话状态 ──────────────────────────────────

_user_sessions: dict = {}


def get_user_session(user_id) -> dict:
    """获取或创建指定用户的会话状态"""
    key = user_id if user_id is not None else "anon"
    if key not in _user_sessions:
        _user_sessions[key] = {
            "current_thread_id": None,
            "session_files": {},          # file_key → {filename, filepath}
            "session_file_order": [],     # 上传顺序
            "cancelled_file_keys": set(), # 已取消的文件 key
            "erased_file_paths": None,    # 擦除后的文件路径列表
            "ocr_cache_uses_server_ocr": False,  # OCR 预览缓存是否已消耗平台 OCR 额度
        }
    return _user_sessions[key]


def clear_user_session(user_id):
    """清除指定用户的会话状态"""
    key = user_id if user_id is not None else "anon"
    _user_sessions.pop(key, None)
