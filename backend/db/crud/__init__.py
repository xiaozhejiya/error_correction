"""
数据库 CRUD 操作

所有公共函数从子模块汇总导出，保持 ``from db import crud; crud.xxx()`` 的使用方式不变。
"""

from typing import Optional

from db.models import UploadBatch, Question


# ── 共享过滤辅助函数 ──────────────────────────────────────────

def _filter_by_subject(query, subject: Optional[str]):
    """如有学科筛选，为 Question 查询追加 JOIN UploadBatch 过滤"""
    if subject:
        return query.join(UploadBatch).filter(UploadBatch.subject == subject)
    return query


def _filter_by_user(query, user_id):
    if user_id is not None:
        query = query.filter(Question.user_id == user_id)
    return query


# ── 子模块导出 ────────────────────────────────────────────────

from db.crud.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_login,
    update_user_password,
)

from db.crud.email_verification import (
    get_verification_by_email,
    upsert_registration_code,
    delete_verification_by_email,
    increment_verification_attempts,
)

from db.crud.tags import (
    _parse_tag_list,
    get_or_create_tag,
    get_existing_tag_names,
    get_all_tags,
)

from db.crud.questions import (
    compute_content_hash,
    question_exists,
    save_questions_to_db,
    get_questions_by_subject,
    get_questions_by_tag,
    get_history_questions,
    search_questions,
    query_questions,
    get_questions_by_ids,
    delete_question,
    update_user_answer,
    update_question_answer,
    update_review_status,
    get_existing_subjects,
    get_existing_question_types,
    VALID_REVIEW_STATUSES,
)

from db.crud.stats import (
    get_statistics,
    get_knowledge_stats,
    get_review_status_stats,
    get_today_mastered_count,
    get_daily_counts,
    get_tag_status_stats,
    get_tag_type_stats,
)

from db.crud.chat import (
    create_chat_session,
    add_chat_message,
    get_chat_messages,
    get_chat_sessions_by_question,
    get_all_chat_sessions,
    get_user_chat_sessions,
    update_chat_session_title,
    delete_chat_session,
)

from db.crud.split_records import (
    MAX_SPLIT_RECORDS,
    save_split_record,
    _cleanup_old_split_records,
    get_recent_split_records,
    get_split_record_by_id,
)

from db.crud.providers import (
    _mask_secret,
    _serialize_provider,
    get_user_providers,
    save_user_providers,
    get_active_provider,
)

from db.crud.notes import (
    save_note,
    get_notes,
    get_note_by_id,
    update_note,
    delete_note,
)

__all__ = [
    # shared helpers
    "_filter_by_subject",
    "_filter_by_user",
    # users
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "get_user_by_login",
    "update_user_password",
    # email verification
    "get_verification_by_email",
    "upsert_registration_code",
    "delete_verification_by_email",
    "increment_verification_attempts",
    # tags
    "_parse_tag_list",
    "get_or_create_tag",
    "get_existing_tag_names",
    "get_all_tags",
    # questions
    "compute_content_hash",
    "question_exists",
    "save_questions_to_db",
    "get_questions_by_subject",
    "get_questions_by_tag",
    "get_history_questions",
    "search_questions",
    "query_questions",
    "get_questions_by_ids",
    "delete_question",
    "update_user_answer",
    "update_question_answer",
    "update_review_status",
    "get_existing_subjects",
    "get_existing_question_types",
    "VALID_REVIEW_STATUSES",
    # stats
    "get_statistics",
    "get_knowledge_stats",
    "get_review_status_stats",
    "get_today_mastered_count",
    "get_daily_counts",
    "get_tag_status_stats",
    "get_tag_type_stats",
    # chat
    "create_chat_session",
    "add_chat_message",
    "get_chat_messages",
    "get_chat_sessions_by_question",
    "get_all_chat_sessions",
    "get_user_chat_sessions",
    "update_chat_session_title",
    "delete_chat_session",
    # split_records
    "MAX_SPLIT_RECORDS",
    "save_split_record",
    "_cleanup_old_split_records",
    "get_recent_split_records",
    "get_split_record_by_id",
    # providers
    "_mask_secret",
    "_serialize_provider",
    "get_user_providers",
    "save_user_providers",
    "get_active_provider",
    # notes
    "save_note",
    "get_notes",
    "get_note_by_id",
    "update_note",
    "delete_note",
]
