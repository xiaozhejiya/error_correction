import logging

from flask import Blueprint, request, jsonify, session

from db import SessionLocal
from db import crud

logger = logging.getLogger(__name__)

bp = Blueprint('stats', __name__)


@bp.route('/stats', methods=['GET'])
def get_stats():
    """
    获取知识点统计信息
    """
    try:
        subject = request.args.get('subject', type=str) or None
        with SessionLocal() as db:
            stats = crud.get_knowledge_stats(db, subject=subject, user_id=session.get('user_id'))
            return jsonify({
                'success': True,
                'stats': stats,
                'total_tags': len(stats)
            })

    except Exception as e:
        logger.exception("获取统计失败")
        return jsonify({'success': False, 'error': '获取统计失败，请稍后重试'}), 500


@bp.route('/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """获取 Dashboard 所需的完整统计数据，支持 ?subject= 学科筛选"""
    try:
        subject = request.args.get('subject') or None
        uid = session.get('user_id')
        with SessionLocal() as db:
            # 可用学科列表（按当前用户隔离）
            subjects = crud.get_existing_subjects(db, user_id=uid)

            # 复习状态统计
            review_stats = crud.get_review_status_stats(db, subject=subject, user_id=uid)

            # 总体统计
            statistics = crud.get_statistics(db, subject=subject, user_id=uid)

            # 知识点标签统计 top 10（横向条形图）
            tag_stats = crud.get_knowledge_stats(db, subject=subject, limit=10, user_id=uid)

            # 知识点 × 掌握状态（堆叠柱状图）
            tag_status_stats = crud.get_tag_status_stats(db, subject=subject, limit=10, user_id=uid)

            # 知识点 × 题型（热力图）
            tag_type_stats = crud.get_tag_type_stats(db, subject=subject, tag_limit=8, user_id=uid)

            # 今日掌握数
            today_mastered = crud.get_today_mastered_count(db, subject=subject, user_id=uid)

            # 最近30天每日新增 + 已掌握趋势
            daily_counts = crud.get_daily_counts(db, days=30, subject=subject, user_id=uid)

            return jsonify({
                'success': True,
                'subjects': subjects,
                'review_stats': review_stats,
                'today_mastered': today_mastered,
                'total_questions': statistics['total_questions'],
                'by_subject': statistics['by_subject'],
                'tag_stats': tag_stats,
                'tag_status_stats': tag_status_stats,
                'tag_type_stats': tag_type_stats,
                'daily_counts': daily_counts,
            })

    except Exception as e:
        logger.exception("获取 Dashboard 统计失败")
        return jsonify({'success': False, 'error': '获取统计失败，请稍后重试'}), 500
