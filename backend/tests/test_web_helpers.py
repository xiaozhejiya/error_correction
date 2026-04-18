"""
web_app.py 中纯函数的单元测试

覆盖函数：
- allowed_file
- _safe_join
"""

import os
import pytest
from routes.upload import allowed_file
from web_app import _safe_join


# ═══════════════════════════════════════════════════════════
# allowed_file
# ═══════════════════════════════════════════════════════════


class TestAllowedFile:
    """allowed_file 测试"""

    def test_pdf(self):
        assert allowed_file("test.pdf") is True

    def test_png(self):
        assert allowed_file("photo.png") is True

    def test_jpg(self):
        assert allowed_file("image.jpg") is True

    def test_jpeg(self):
        assert allowed_file("image.jpeg") is True

    def test_bmp(self):
        assert allowed_file("image.bmp") is True

    def test_tiff(self):
        assert allowed_file("image.tiff") is True

    def test_webp(self):
        assert allowed_file("image.webp") is True

    def test_exe_rejected(self):
        assert allowed_file("malware.exe") is False

    def test_py_rejected(self):
        assert allowed_file("script.py") is False

    def test_txt_rejected(self):
        assert allowed_file("notes.txt") is False

    def test_no_extension(self):
        assert allowed_file("noext") is False

    def test_empty_string(self):
        assert allowed_file("") is False

    def test_case_insensitive(self):
        """扩展名大写应被接受"""
        assert allowed_file("photo.PNG") is True
        assert allowed_file("doc.PDF") is True

    def test_multiple_dots(self):
        """多个点的文件名应以最后一个扩展名为准"""
        assert allowed_file("my.file.pdf") is True
        assert allowed_file("my.pdf.exe") is False

    def test_hidden_file(self):
        assert allowed_file(".pdf") is False  # ".pdf" 被视为无扩展名的隐藏文件


# ═══════════════════════════════════════════════════════════
# _safe_join
# ═══════════════════════════════════════════════════════════


class TestSafeJoin:
    """_safe_join 路径安全校验测试"""

    def test_valid_relative_path(self, tmp_path):
        base = str(tmp_path)
        result = _safe_join(base, "file.txt")
        assert result is not None
        assert result == os.path.abspath(os.path.join(base, "file.txt"))

    def test_nested_path(self, tmp_path):
        base = str(tmp_path)
        result = _safe_join(base, "sub/dir/file.txt")
        assert result is not None

    def test_traversal_rejected(self, tmp_path):
        """目录遍历攻击应被阻止"""
        base = str(tmp_path)
        result = _safe_join(base, "../../../etc/passwd")
        assert result is None

    def test_double_dot_in_middle(self, tmp_path):
        base = str(tmp_path)
        result = _safe_join(base, "sub/../../../etc/passwd")
        assert result is None

    def test_valid_dotdot_within_base(self, tmp_path):
        """不跳出 base 的 .. 应被允许"""
        base = str(tmp_path)
        # sub/../file.txt 等价于 file.txt，仍在 base 内
        result = _safe_join(base, "sub/../file.txt")
        assert result is not None

    def test_empty_rel_path(self, tmp_path):
        """空路径不应通过（等于 base 本身，不以 base+sep 开头）"""
        base = str(tmp_path)
        result = _safe_join(base, "")
        assert result is None


