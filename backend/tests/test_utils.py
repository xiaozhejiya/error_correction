"""
utils.py 工具函数的单元测试

覆盖函数：
- prepare_input (文件验证与复制)
"""

import os
import pytest
from src.utils import prepare_input


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """使用临时目录作为 settings.pages_dir"""
    pages_dir = tmp_path / "pages"
    monkeypatch.setattr("core.config.settings.pages_dir", pages_dir)
    return pages_dir


class TestPrepareInput:
    """prepare_input 测试"""

    def test_pdf_passthrough(self, mock_env, tmp_path):
        """PDF 文件应直接复制到 PAGES_DIR，不做转换"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        result = prepare_input(str(pdf_path))

        assert len(result) == 1
        assert result[0].endswith(".pdf")
        assert os.path.exists(result[0])
        # 验证内容一致
        with open(result[0], "rb") as f:
            assert f.read() == b"%PDF-1.4 fake content"

    def test_image_passthrough(self, mock_env, tmp_path):
        """图片文件应直接复制到 PAGES_DIR，保留原始格式"""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff fake jpg")

        result = prepare_input(str(img_path))

        assert len(result) == 1
        assert result[0].endswith(".jpg")
        assert os.path.exists(result[0])

    def test_png_passthrough(self, mock_env, tmp_path):
        """PNG 图片也应直接复制"""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"\x89PNG fake")

        result = prepare_input(str(img_path))

        assert len(result) == 1
        assert result[0].endswith(".png")

    def test_file_not_found(self):
        """文件不存在应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            prepare_input("non_existent_file.pdf")

    def test_unsupported_format(self, tmp_path):
        """不支持的文件格式应抛出 ValueError"""
        txt_path = tmp_path / "test.txt"
        txt_path.touch()

        with pytest.raises(ValueError) as excinfo:
            prepare_input(str(txt_path))
        assert "不支持的文件格式" in str(excinfo.value)

    def test_creates_pages_dir(self, mock_env, tmp_path):
        """PAGES_DIR 不存在时应自动创建"""
        assert not mock_env.exists()

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        prepare_input(str(pdf_path))

        assert mock_env.exists()
