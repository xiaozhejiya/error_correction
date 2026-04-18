"""
文件操作相关工具
"""

import os
import json
import requests
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


@tool(parse_docstring=True)
def download_image(image_url: str, save_path: str) -> str:
    """从URL下载图片到本地

    下载PaddleOCR返回的图片URL到本地目录，用于后续的题目渲染。

    Args:
        image_url: 图片的URL地址
        save_path: 保存路径（相对于ASSETS_DIR）

    Returns:
        下载结果消息
    """
    try:
        assets_dir = os.getenv("ASSETS_DIR", "output/assets")
        full_path = os.path.abspath(os.path.join(assets_dir, save_path))
        if not full_path.startswith(os.path.abspath(assets_dir) + os.sep):
            return "错误: 非法保存路径"

        # 创建目录
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 下载图片
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(full_path, 'wb') as f:
                f.write(response.content)
            return f"成功下载图片到: {full_path}"
        else:
            return f"下载失败: HTTP {response.status_code}"

    except Exception as e:
        return f"下载出错: {str(e)}"


@tool(parse_docstring=True)
def read_ocr_result(result_path: str) -> Dict[str, Any]:
    """读取PaddleOCR的解析结果

    从JSON文件读取PaddleOCR的结构化解析结果，供Agent分析和处理。

    Args:
        result_path: OCR结果文件路径（JSON格式）

    Returns:
        OCR解析结果字典
    """
    try:
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result

    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}
