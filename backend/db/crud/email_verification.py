"""注册邮箱验证码 CRUD"""

from datetime import datetime

from db.models import EmailVerification


def get_verification_by_email(db, email: str):
    return db.query(EmailVerification).filter(EmailVerification.email == email).first()


def upsert_registration_code(
    db,
    email: str,
    code_hash: str,
    expires_at: datetime,
    last_sent_at: datetime,
) -> EmailVerification:
    row = get_verification_by_email(db, email)
    if row:
        row.code_hash = code_hash
        row.expires_at = expires_at
        row.last_sent_at = last_sent_at
        # 不重置 attempts：防止攻击者反复请求新验证码来绕过尝试次数限制
    else:
        row = EmailVerification(
            email=email,
            code_hash=code_hash,
            expires_at=expires_at,
            last_sent_at=last_sent_at,
            attempts=0,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_verification_by_email(db, email: str) -> None:
    row = get_verification_by_email(db, email)
    if row:
        db.delete(row)
        db.commit()


def increment_verification_attempts(db, email: str) -> int:
    row = get_verification_by_email(db, email)
    if not row:
        return 0
    row.attempts = (row.attempts or 0) + 1
    db.commit()
    return row.attempts
