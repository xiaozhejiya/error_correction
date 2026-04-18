"""SMTP 发信（注册验证码等）。"""

import logging
import smtplib
import threading
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _send_sync(
    host, port, user, password, mail_from, use_tls, to_addr, msg,
):
    if port == 465:
        smtp = smtplib.SMTP_SSL(host, port, timeout=15)
    else:
        smtp = smtplib.SMTP(host, port, timeout=15)
        if use_tls:
            smtp.starttls()

    with smtp:
        if user and password:
            smtp.login(user, password)
        smtp.sendmail(mail_from, [to_addr], msg.as_string())

    logger.info("已发送邮件至 %s", to_addr)


def send_smtp_email(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    mail_from: str,
    use_tls: bool,
    to_addr: str,
    subject: str,
    body: str,
    async_send: bool = True,
) -> None:
    if not host or not mail_from:
        raise ValueError("SMTP 未配置：需要 smtp_host 与 smtp_from")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_addr

    if async_send:
        t = threading.Thread(
            target=_send_sync,
            args=(host, port, user, password, mail_from, use_tls, to_addr, msg),
            daemon=True,
        )
        t.start()
        logger.info("邮件发送任务已提交（异步）: %s", to_addr)
    else:
        _send_sync(host, port, user, password, mail_from, use_tls, to_addr, msg)
