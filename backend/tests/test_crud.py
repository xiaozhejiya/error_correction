"""
数据库 CRUD 函数单元测试

使用 SQLite 内存数据库，不依赖磁盘文件。

覆盖函数：
- compute_content_hash
- save_questions_to_db
- get_existing_subjects
- get_existing_tag_names
- get_or_create_tag
- question_exists
- get_questions_by_subject
- get_questions_by_tag
- get_all_tags
- get_statistics
"""

import pytest

from tests.conftest import make_question
from db.crud import (
    compute_content_hash,
    save_questions_to_db,
    get_existing_subjects,
    get_existing_tag_names,
    get_or_create_tag,
    question_exists,
    get_questions_by_subject,
    get_questions_by_tag,
    get_all_tags,
    get_statistics,
    query_questions,
    update_user_answer,
    get_existing_question_types,
    get_questions_by_ids,
    update_review_status,
    get_review_status_stats,
    get_daily_counts,
)


# ═══════════════════════════════════════════════════════════
# compute_content_hash
# ═══════════════════════════════════════════════════════════


class TestComputeContentHash:
    """compute_content_hash 测试"""

    def test_text_blocks(self):
        blocks = [
            {"block_type": "text", "content": "求函数 f(x) 的导数"},
        ]
        h = compute_content_hash(blocks)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex

    def test_same_content_same_hash(self):
        blocks = [{"block_type": "text", "content": "hello"}]
        assert compute_content_hash(blocks) == compute_content_hash(blocks)

    def test_different_content_different_hash(self):
        b1 = [{"block_type": "text", "content": "A"}]
        b2 = [{"block_type": "text", "content": "B"}]
        assert compute_content_hash(b1) != compute_content_hash(b2)

    def test_ignores_image_blocks(self):
        """只用 text 类型计算哈希"""
        b1 = [{"block_type": "text", "content": "hello"}]
        b2 = [
            {"block_type": "text", "content": "hello"},
            {"block_type": "image", "content": "/images/xxx.jpg"},
        ]
        assert compute_content_hash(b1) == compute_content_hash(b2)

    def test_empty_blocks_uses_json(self):
        """无文本 block 时用完整 JSON 作为哈希源"""
        b1 = [{"block_type": "image", "content": "/img/a.jpg"}]
        b2 = [{"block_type": "image", "content": "/img/b.jpg"}]
        assert compute_content_hash(b1) != compute_content_hash(b2)

    def test_empty_list(self):
        """空列表应产生有效哈希"""
        h = compute_content_hash([])
        assert isinstance(h, str)
        assert len(h) == 64

    def test_multiple_text_blocks_joined(self):
        """多个 text block 内容用空格连接"""
        b_separate = [
            {"block_type": "text", "content": "A"},
            {"block_type": "text", "content": "B"},
        ]
        b_joined = [{"block_type": "text", "content": "A B"}]
        assert compute_content_hash(b_separate) == compute_content_hash(b_joined)

    def test_unicode(self):
        blocks = [{"block_type": "text", "content": "求证：∀ε>0，∃δ>0"}]
        h = compute_content_hash(blocks)
        assert len(h) == 64


# ═══════════════════════════════════════════════════════════
# get_or_create_tag
# ═══════════════════════════════════════════════════════════


class TestGetOrCreateTag:
    """get_or_create_tag 测试"""

    def test_create_new_tag(self, db):
        tag = get_or_create_tag(db, "三角函数", "高中数学")
        assert tag.tag_name == "三角函数"
        assert tag.subject == "高中数学"
        assert tag.id is not None

    def test_get_existing_tag(self, db):
        tag1 = get_or_create_tag(db, "导数", "高中数学")
        tag2 = get_or_create_tag(db, "导数", "高中数学")
        assert tag1.id == tag2.id

    def test_same_name_different_subject(self, db):
        """同名标签不同科目应创建不同记录"""
        t1 = get_or_create_tag(db, "力", "高中物理")
        t2 = get_or_create_tag(db, "力", "初中物理")
        assert t1.id != t2.id


# ═══════════════════════════════════════════════════════════
# save_questions_to_db & query functions
# ═══════════════════════════════════════════════════════════




class TestSaveQuestionsToDB:
    """save_questions_to_db 测试"""

    def test_basic_save(self, db):
        qs = [make_question("1"), make_question("2")]
        batch_info = {"original_filename": "test.pdf", "subject": "高中数学"}
        result = save_questions_to_db(db, qs, batch_info)
        assert result["created"] == 2
        assert result["duplicates"] == 0

    def test_dedup_same_content(self, db):
        """相同内容的题目第二次入库应标记为重复"""
        qs = [make_question("1", text="重复题")]
        batch_info = {"original_filename": "a.pdf", "subject": "数学"}

        r1 = save_questions_to_db(db, qs, batch_info)
        assert r1["created"] == 1

        r2 = save_questions_to_db(db, qs, batch_info)
        assert r2["created"] == 0
        assert r2["duplicates"] == 1

    def test_skip_empty_content(self, db):
        """content_blocks 为空的题目应被跳过"""
        qs = [{"question_id": "1", "content_blocks": []}]
        batch_info = {"original_filename": "a.pdf", "subject": "数学"}
        result = save_questions_to_db(db, qs, batch_info)
        assert result["created"] == 0
        assert result["duplicates"] == 0

    def test_with_tags(self, db):
        qs = [make_question("1", tags=["导数", "极值"])]
        batch_info = {"original_filename": "a.pdf", "subject": "高中数学"}
        result = save_questions_to_db(db, qs, batch_info)
        assert result["created"] == 1

        tags = get_all_tags(db, subject="高中数学")
        tag_names = {t.tag_name for t in tags}
        assert "导数" in tag_names
        assert "极值" in tag_names

    def test_default_subject(self, db):
        """未提供 subject 时应使用 '未知'"""
        qs = [make_question("1")]
        batch_info = {"original_filename": "a.pdf"}
        save_questions_to_db(db, qs, batch_info)
        subjects = get_existing_subjects(db)
        assert "未知" in subjects


class TestQuestionExists:
    """question_exists 测试"""

    def test_not_exists(self, db):
        assert question_exists(db, "nonexistent_hash") is None

    def test_exists_after_save(self, db):
        qs = [make_question("1", text="check_exists")]
        batch_info = {"original_filename": "a.pdf", "subject": "数学"}
        save_questions_to_db(db, qs, batch_info)

        content_hash = compute_content_hash(qs[0]["content_blocks"])
        assert question_exists(db, content_hash) is not None


class TestGetExistingSubjects:
    """get_existing_subjects 测试"""

    def test_empty_db(self, db):
        assert get_existing_subjects(db) == []

    def test_returns_distinct(self, db):
        batch_info = {"original_filename": "a.pdf", "subject": "高中数学"}
        save_questions_to_db(db, [make_question("1")], batch_info)
        save_questions_to_db(db, [make_question("2", text="t2")], batch_info)
        subjects = get_existing_subjects(db)
        assert subjects.count("高中数学") == 1


class TestGetExistingTagNames:
    """get_existing_tag_names 测试"""

    def test_empty_db(self, db):
        assert get_existing_tag_names(db) == []

    def test_returns_tags(self, db):
        qs = [make_question("1", tags=["导数", "函数"])]
        save_questions_to_db(db, qs, {"original_filename": "a.pdf", "subject": "数学"})
        tags = get_existing_tag_names(db)
        assert "导数" in tags
        assert "函数" in tags

    def test_filter_by_subject(self, db):
        save_questions_to_db(
            db,
            [make_question("1", tags=["导数"])],
            {"original_filename": "a.pdf", "subject": "高中数学"}
        )
        save_questions_to_db(
            db,
            [make_question("2", text="t2", tags=["电场"])],
            {"original_filename": "b.pdf", "subject": "高中物理"}
        )
        math_tags = get_existing_tag_names(db, subject="高中数学")
        assert "导数" in math_tags
        assert "电场" not in math_tags


class TestGetQuestionsBySubject:
    """get_questions_by_subject 测试"""

    def test_empty(self, db):
        assert get_questions_by_subject(db, "数学") == []

    def test_filter_by_subject(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "高中数学"}
        )
        save_questions_to_db(
            db,
            [make_question("2", text="t2")],
            {"original_filename": "b.pdf", "subject": "高中物理"}
        )
        math_qs = get_questions_by_subject(db, "高中数学")
        assert len(math_qs) == 1

    def test_pagination(self, db):
        qs = [make_question(str(i), text=f"q{i}") for i in range(5)]
        save_questions_to_db(db, qs, {"original_filename": "a.pdf", "subject": "数学"})
        page1 = get_questions_by_subject(db, "数学", limit=2, offset=0)
        page2 = get_questions_by_subject(db, "数学", limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2


class TestGetQuestionsByTag:
    """get_questions_by_tag 测试"""

    def test_empty(self, db):
        assert get_questions_by_tag(db, "不存在的标签") == []

    def test_filter(self, db):
        save_questions_to_db(
            db,
            [make_question("1", tags=["导数"]), make_question("2", text="t2", tags=["极值"])],
            {"original_filename": "a.pdf", "subject": "数学"}
        )
        result = get_questions_by_tag(db, "导数")
        assert len(result) == 1


class TestGetAllTags:
    """get_all_tags 测试"""

    def test_empty(self, db):
        assert get_all_tags(db) == []

    def test_filter_by_subject(self, db):
        get_or_create_tag(db, "导数", "高中数学")
        get_or_create_tag(db, "电场", "高中物理")
        db.commit()

        math_tags = get_all_tags(db, subject="高中数学")
        assert len(math_tags) == 1
        assert math_tags[0].tag_name == "导数"


class TestGetStatistics:
    """get_statistics 测试"""

    def test_empty_db(self, db):
        stats = get_statistics(db)
        assert stats["total_questions"] == 0
        assert stats["total_batches"] == 0
        assert stats["total_tags"] == 0
        assert stats["by_subject"] == {}

    def test_with_data(self, db):
        save_questions_to_db(
            db,
            [make_question("1", tags=["导数"]), make_question("2", text="t2")],
            {"original_filename": "a.pdf", "subject": "高中数学"}
        )
        stats = get_statistics(db)
        assert stats["total_questions"] == 2
        assert stats["total_batches"] == 1
        assert stats["total_tags"] == 1
        assert stats["by_subject"]["高中数学"] == 2


# ═══════════════════════════════════════════════════════════
# query_questions
# ═══════════════════════════════════════════════════════════


class TestQueryQuestions:
    """query_questions 统一查询测试"""

    def _seed(self, db):
        save_questions_to_db(
            db,
            [make_question("1", tags=["导数"]), make_question("2", text="物理题", qtype="填空题")],
            {"original_filename": "a.pdf", "subject": "高中数学"},
        )
        save_questions_to_db(
            db,
            [make_question("3", text="电场强度", tags=["电场"])],
            {"original_filename": "b.pdf", "subject": "高中物理"},
        )

    def test_no_filter(self, db):
        self._seed(db)
        qs, total = query_questions(db)
        assert total == 3
        assert len(qs) == 3

    def test_filter_by_subject(self, db):
        self._seed(db)
        qs, total = query_questions(db, subject="高中物理")
        assert total == 1
        assert len(qs) == 1

    def test_filter_by_keyword(self, db):
        self._seed(db)
        qs, total = query_questions(db, keyword="电场")
        assert total == 1

    def test_filter_by_question_type(self, db):
        self._seed(db)
        qs, total = query_questions(db, question_type="填空题")
        assert total == 1

    def test_combined_filters(self, db):
        self._seed(db)
        qs, total = query_questions(db, subject="高中数学", question_type="选择题")
        assert total == 1

    def test_pagination(self, db):
        self._seed(db)
        qs, total = query_questions(db, page=1, page_size=2)
        assert total == 3
        assert len(qs) == 2
        qs2, _ = query_questions(db, page=2, page_size=2)
        assert len(qs2) == 1


# ═══════════════════════════════════════════════════════════
# query_questions — 多标签筛选
# ═══════════════════════════════════════════════════════════


class TestQueryQuestionsMultiTag:
    """query_questions 逗号分隔多标签筛选（OR 语义）"""

    def _seed(self, db):
        save_questions_to_db(
            db,
            [make_question("1", tags=["导数", "极限"]), make_question("2", tags=["积分"])],
            {"original_filename": "a.pdf", "subject": "高中数学"},
        )
        save_questions_to_db(
            db,
            [make_question("3", text="电场强度", tags=["电场"])],
            {"original_filename": "b.pdf", "subject": "高中物理"},
        )

    def test_single_tag(self, db):
        self._seed(db)
        qs, total = query_questions(db, knowledge_tag="导数")
        assert total == 1

    def test_multi_tag_or(self, db):
        """逗号分隔多标签应返回匹配任一标签的题目"""
        self._seed(db)
        qs, total = query_questions(db, knowledge_tag="导数,积分")
        assert total == 2

    def test_multi_tag_with_spaces(self, db):
        """标签前后空格应被忽略"""
        self._seed(db)
        qs, total = query_questions(db, knowledge_tag=" 导数 , 电场 ")
        assert total == 2

    def test_multi_tag_no_match(self, db):
        self._seed(db)
        qs, total = query_questions(db, knowledge_tag="不存在的标签")
        assert total == 0

    def test_empty_after_strip(self, db):
        """只有逗号和空格时不应报错"""
        self._seed(db)
        qs, total = query_questions(db, knowledge_tag=", ,")
        # tag_list 为空，不触发过滤，应返回全部
        assert total == 3


# ═══════════════════════════════════════════════════════════
# update_user_answer
# ═══════════════════════════════════════════════════════════


class TestUpdateUserAnswer:
    """update_user_answer 测试"""

    def test_update_answer(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        q = db.query(Question).first()
        result = update_user_answer(db, q.id, "答案是 A")
        assert result is not None
        assert result.user_answer == "答案是 A"
        assert result.updated_at is not None

    def test_nonexistent_question(self, db):
        result = update_user_answer(db, 99999, "答案")
        assert result is None


# ═══════════════════════════════════════════════════════════
# get_questions_by_ids
# ═══════════════════════════════════════════════════════════


class TestGetQuestionsByIds:
    """get_questions_by_ids 测试"""

    def test_get_by_ids(self, db):
        save_questions_to_db(
            db,
            [make_question("1"), make_question("2", text="t2")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        all_qs = db.query(Question).all()
        ids = [q.id for q in all_qs]
        result = get_questions_by_ids(db, ids)
        assert len(result) == 2

    def test_empty_ids(self, db):
        result = get_questions_by_ids(db, [])
        assert result == []


# ═══════════════════════════════════════════════════════════
# update_review_status
# ═══════════════════════════════════════════════════════════


class TestUpdateReviewStatus:
    """update_review_status 测试"""

    def test_update_status(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        q = db.query(Question).first()
        result = update_review_status(db, q.id, "复习中")
        assert result is not None
        assert result.review_status == "复习中"
        assert result.updated_at is not None

    def test_update_to_mastered(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        q = db.query(Question).first()
        result = update_review_status(db, q.id, "已掌握")
        assert result.review_status == "已掌握"

    def test_invalid_status(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        q = db.query(Question).first()
        with pytest.raises(ValueError):
            update_review_status(db, q.id, "无效状态")

    def test_nonexistent_question(self, db):
        result = update_review_status(db, 99999, "待复习")
        assert result is None


# ═══════════════════════════════════════════════════════════
# get_review_status_stats
# ═══════════════════════════════════════════════════════════


class TestGetReviewStatusStats:
    """get_review_status_stats 测试"""

    def test_empty_db(self, db):
        stats = get_review_status_stats(db)
        assert stats == {'待复习': 0, '复习中': 0, '已掌握': 0}

    def test_with_data(self, db):
        save_questions_to_db(
            db,
            [make_question("1"), make_question("2", text="t2"), make_question("3", text="t3")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        qs = db.query(Question).all()
        # 默认都是 '待复习' 或 None
        update_review_status(db, qs[1].id, "复习中")
        update_review_status(db, qs[2].id, "已掌握")

        stats = get_review_status_stats(db)
        assert stats['复习中'] == 1
        assert stats['已掌握'] == 1


# ═══════════════════════════════════════════════════════════
# query_questions with review_status filter
# ═══════════════════════════════════════════════════════════


class TestQueryQuestionsReviewStatus:
    """query_questions review_status 筛选测试"""

    def test_filter_by_review_status(self, db):
        save_questions_to_db(
            db,
            [make_question("1"), make_question("2", text="t2")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        from db.models import Question
        qs = db.query(Question).all()
        update_review_status(db, qs[0].id, "已掌握")

        result, total = query_questions(db, review_status="已掌握")
        assert total == 1
        assert result[0].review_status == "已掌握"


# ═══════════════════════════════════════════════════════════
# get_daily_counts
# ═══════════════════════════════════════════════════════════


class TestGetDailyCounts:
    """get_daily_counts 测试"""

    def test_empty_db(self, db):
        result = get_daily_counts(db, days=7)
        assert len(result) == 7
        assert all(d['count'] == 0 for d in result)

    def test_with_data(self, db):
        save_questions_to_db(
            db,
            [make_question("1")],
            {"original_filename": "a.pdf", "subject": "数学"},
        )
        result = get_daily_counts(db, days=7)
        assert len(result) == 7
        # 今天应该有 1 条
        total = sum(d['count'] for d in result)
        assert total == 1
